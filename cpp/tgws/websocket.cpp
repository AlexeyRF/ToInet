#include "websocket.h"
#include <iostream>
#include <sstream>

namespace tgws {

RawWebSocket::RawWebSocket() : connected(false) {}

RawWebSocket::~RawWebSocket() {
    close();
}

void RawWebSocket::close() {
    if (connected) {
        send_frame(WsOpcode::Close, nullptr, 0);
        connected = false;
    }
    sock.close();
    frag_buffer.clear();
}

bool RawWebSocket::connect(const std::string& host, int port, const std::string& domain,
                           const std::string& path, const std::string& sni,
                           bool secure, int timeout_sec) {
    close();
    std::string actual_sni = sni.empty() ? domain : sni;

    if (!sock.connect(host, port, actual_sni, secure, timeout_sec)) {
        return false;
    }

    uint8_t rand_key[16];
    random_bytes(rand_key, 16);
    std::string ws_key = base64_encode(rand_key, 16);

    std::ostringstream req;
    req << "GET " << path << " HTTP/1.1\r\n"
        << "Host: " << domain << "\r\n"
        << "Upgrade: websocket\r\n"
        << "Connection: Upgrade\r\n"
        << "Sec-WebSocket-Key: " << ws_key << "\r\n"
        << "Sec-WebSocket-Version: 13\r\n"
        << "Sec-WebSocket-Protocol: binary\r\n"
        << "\r\n";

    std::string req_str = req.str();
    if (!sock.send_all(req_str.data(), req_str.size())) {
        close();
        return false;
    }

    std::string resp_headers;
    if (!sock.read_until(resp_headers, "\r\n\r\n", timeout_sec)) {
        close();
        return false;
    }

    // Verify HTTP 101 Switching Protocols
    if (resp_headers.find(" 101 ") == std::string::npos &&
        resp_headers.find(" 101\r\n") == std::string::npos) {
        close();
        return false;
    }

    connected = true;
    return true;
}

bool RawWebSocket::send_frame(WsOpcode opcode, const void* data, size_t len) {
    if (!sock.is_valid()) return false;

    std::vector<uint8_t> header;
    header.reserve(14);

    uint8_t b0 = 0x80 | static_cast<uint8_t>(opcode); // FIN=1
    header.push_back(b0);

    // Client frames MUST be masked
    if (len <= 125) {
        header.push_back(0x80 | static_cast<uint8_t>(len));
    } else if (len <= 65535) {
        header.push_back(0x80 | 126);
        header.push_back(static_cast<uint8_t>((len >> 8) & 0xFF));
        header.push_back(static_cast<uint8_t>(len & 0xFF));
    } else {
        header.push_back(0x80 | 127);
        for (int i = 7; i >= 0; --i) {
            header.push_back(static_cast<uint8_t>((len >> (i * 8)) & 0xFF));
        }
    }

    uint32_t mask = 0;
    random_bytes(&mask, sizeof(mask));
    const uint8_t* mask_bytes = reinterpret_cast<const uint8_t*>(&mask);
    header.insert(header.end(), mask_bytes, mask_bytes + 4);

    if (!sock.send_all(header.data(), header.size())) {
        return false;
    }

    if (len > 0 && data) {
        std::vector<uint8_t> masked(len);
        ws_mask_copy(static_cast<const uint8_t*>(data), masked.data(), len, mask);
        if (!sock.send_all(masked.data(), masked.size())) {
            return false;
        }
    }
    return true;
}

bool RawWebSocket::send(const void* data, size_t len) {
    return send_frame(WsOpcode::Binary, data, len);
}

bool RawWebSocket::send_batch(const std::vector<std::vector<uint8_t>>& parts) {
    for (const auto& part : parts) {
        if (!send(part.data(), part.size())) {
            return false;
        }
    }
    return true;
}

bool RawWebSocket::read_frame(WsOpcode& out_opcode, std::vector<uint8_t>& out_payload, bool& out_fin) {
    uint8_t hdr[2];
    if (!sock.recv_exact(hdr, 2)) return false;

    out_fin = (hdr[0] & 0x80) != 0;
    out_opcode = static_cast<WsOpcode>(hdr[0] & 0x0F);

    bool masked = (hdr[1] & 0x80) != 0;
    uint64_t payload_len = hdr[1] & 0x7F;

    if (payload_len == 126) {
        uint8_t ext[2];
        if (!sock.recv_exact(ext, 2)) return false;
        payload_len = (static_cast<uint64_t>(ext[0]) << 8) | ext[1];
    } else if (payload_len == 127) {
        uint8_t ext[8];
        if (!sock.recv_exact(ext, 8)) return false;
        payload_len = 0;
        for (int i = 0; i < 8; ++i) {
            payload_len = (payload_len << 8) | ext[i];
        }
    }

    if (payload_len > 32 * 1024 * 1024) {
        return false; // Guard against insane frame size
    }

    uint32_t mask = 0;
    if (masked) {
        if (!sock.recv_exact(&mask, 4)) return false;
    }

    out_payload.resize(payload_len);
    if (payload_len > 0) {
        if (!sock.recv_exact(out_payload.data(), payload_len)) return false;
        if (masked) {
            ws_mask_inplace(out_payload.data(), payload_len, mask);
        }
    }
    return true;
}

bool RawWebSocket::recv(std::vector<uint8_t>& out_payload) {
    out_payload.clear();
    while (is_open()) {
        WsOpcode opcode;
        std::vector<uint8_t> frame_data;
        bool fin = false;

        if (!read_frame(opcode, frame_data, fin)) {
            close();
            return false;
        }

        if (opcode == WsOpcode::Close) {
            close();
            return false;
        }

        if (opcode == WsOpcode::Ping) {
            send_frame(WsOpcode::Pong, frame_data.data(), frame_data.size());
            continue;
        }

        if (opcode == WsOpcode::Pong) {
            continue;
        }

        if (opcode == WsOpcode::Binary || opcode == WsOpcode::Text) {
            if (fin) {
                out_payload = std::move(frame_data);
                return true;
            } else {
                frag_buffer = std::move(frame_data);
            }
        } else if (opcode == WsOpcode::Continuation) {
            frag_buffer.insert(frag_buffer.end(), frame_data.begin(), frame_data.end());
            if (fin) {
                out_payload = std::move(frag_buffer);
                frag_buffer.clear();
                return true;
            }
        }
    }
    return false;
}

} // namespace tgws
