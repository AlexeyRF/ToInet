#pragma once

#include "tls_socket.h"
#include "crypto.h"
#include <string>
#include <vector>
#include <memory>

namespace tgws {

enum class WsOpcode : uint8_t {
    Continuation = 0x0,
    Text         = 0x1,
    Binary       = 0x2,
    Close        = 0x8,
    Ping         = 0x9,
    Pong         = 0xA
};

class RawWebSocket {
public:
    RawWebSocket();
    ~RawWebSocket();

    // Connects to target host:port, optionally uses TLS, performs WebSocket handshake
    bool connect(const std::string& host, int port, const std::string& domain,
                 const std::string& path = "/apiws", const std::string& sni = "",
                 bool secure = true, int timeout_sec = 10);

    // Send binary WebSocket frame (masked)
    bool send(const void* data, size_t len);
    bool send(const std::vector<uint8_t>& data) { return send(data.data(), data.size()); }
    bool send_batch(const std::vector<std::vector<uint8_t>>& parts);

    // Receive a complete binary message (handles unmasking, ping/pong, and frame reassembly)
    bool recv(std::vector<uint8_t>& out_payload);

    bool is_open() const { return connected && sock.is_valid(); }
    void close();

    TlsSocket& get_socket() { return sock; }

private:
    TlsSocket sock;
    bool connected;
    std::vector<uint8_t> frag_buffer;

    bool read_frame(WsOpcode& out_opcode, std::vector<uint8_t>& out_payload, bool& out_fin);
    bool send_frame(WsOpcode opcode, const void* data, size_t len);
};

} // namespace tgws
