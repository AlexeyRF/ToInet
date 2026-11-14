#include "tls_socket.h"
#include <iostream>
#include <algorithm>
#include <chrono>

namespace tgws {

static bool g_winsock_initialized = false;

static void ensure_winsock() {
    if (!g_winsock_initialized) {
        WSADATA wsa;
        WSAStartup(MAKEWORD(2, 2), &wsa);
        g_winsock_initialized = true;
    }
}

TlsSocket::TlsSocket()
    : sock(INVALID_SOCKET), tls_active(false) {
    ensure_winsock();
    SecInvalidateHandle(&hCred);
    SecInvalidateHandle(&hCtxt);
    std::memset(&stream_sizes, 0, sizeof(stream_sizes));
}

TlsSocket::~TlsSocket() {
    close();
}

void TlsSocket::close() {
    if (tls_active && SecIsValidHandle(&hCtxt)) {
        DeleteSecurityContext(&hCtxt);
        SecInvalidateHandle(&hCtxt);
    }
    if (SecIsValidHandle(&hCred)) {
        FreeCredentialsHandle(&hCred);
        SecInvalidateHandle(&hCred);
    }
    if (sock != INVALID_SOCKET) {
        closesocket(sock);
        sock = INVALID_SOCKET;
    }
    tls_active = false;
    dec_buffer.clear();
    pending_data.clear();
}

SOCKET TlsSocket::detach_raw_socket() {
    SOCKET s = sock;
    sock = INVALID_SOCKET;
    close();
    return s;
}

int TlsSocket::recv_raw(void* buf, size_t len) {
    if (sock == INVALID_SOCKET || len == 0) return -1;
    int r = ::recv(sock, reinterpret_cast<char*>(buf), static_cast<int>(len), 0);
    return r;
}

int TlsSocket::send_raw(const void* buf, size_t len) {
    if (sock == INVALID_SOCKET || len == 0) return -1;
    size_t total = 0;
    while (total < len) {
        int r = ::send(sock, reinterpret_cast<const char*>(buf) + total, static_cast<int>(len - total), 0);
        if (r <= 0) return -1;
        total += r;
    }
    return static_cast<int>(total);
}

bool TlsSocket::connect(const std::string& host, int port, const std::string& sni, bool use_tls, int timeout_sec) {
    close();
    ensure_winsock();

    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    addrinfo* result = nullptr;
    std::string port_str = std::to_string(port);
    if (getaddrinfo(host.c_str(), port_str.c_str(), &hints, &result) != 0) {
        return false;
    }

    SOCKET s = INVALID_SOCKET;
    for (addrinfo* ptr = result; ptr != nullptr; ptr = ptr->ai_next) {
        s = socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol);
        if (s == INVALID_SOCKET) continue;

        // Set non-blocking for connect timeout
        u_long mode = 1;
        ioctlsocket(s, FIONBIO, &mode);

        int res = ::connect(s, ptr->ai_addr, static_cast<int>(ptr->ai_addrlen));
        if (res == SOCKET_ERROR && WSAGetLastError() == WSAEWOULDBLOCK) {
            fd_set write_fds, err_fds;
            FD_ZERO(&write_fds);
            FD_ZERO(&err_fds);
            FD_SET(s, &write_fds);
            FD_SET(s, &err_fds);

            timeval tv{};
            tv.tv_sec = timeout_sec;
            tv.tv_usec = 0;

            int sel = select(0, nullptr, &write_fds, &err_fds, &tv);
            if (sel > 0 && FD_ISSET(s, &write_fds) && !FD_ISSET(s, &err_fds)) {
                int opt_err = 0;
                int opt_len = sizeof(opt_err);
                getsockopt(s, SOL_SOCKET, SO_ERROR, reinterpret_cast<char*>(&opt_err), &opt_len);
                if (opt_err == 0) {
                    res = 0; // Success
                }
            }
        }

        // Restore blocking mode
        mode = 0;
        ioctlsocket(s, FIONBIO, &mode);

        if (res == 0) {
            // TCP_NODELAY and socket buffer sizes
            int nodelay = 1;
            setsockopt(s, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));
            int buf_sz = 256 * 1024;
            setsockopt(s, SOL_SOCKET, SO_RCVBUF, reinterpret_cast<const char*>(&buf_sz), sizeof(buf_sz));
            setsockopt(s, SOL_SOCKET, SO_SNDBUF, reinterpret_cast<const char*>(&buf_sz), sizeof(buf_sz));

            // Socket timeout for send/recv
            DWORD tv_ms = timeout_sec * 1000;
            setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&tv_ms), sizeof(tv_ms));
            setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, reinterpret_cast<const char*>(&tv_ms), sizeof(tv_ms));
            break;
        }

        closesocket(s);
        s = INVALID_SOCKET;
    }

    freeaddrinfo(result);
    if (s == INVALID_SOCKET) return false;

    sock = s;
    if (use_tls) {
        std::string server_sni = sni.empty() ? host : sni;
        if (!perform_tls_handshake(server_sni, timeout_sec)) {
            close();
            return false;
        }
    }
    return true;
}

bool TlsSocket::attach(SOCKET s, const std::string& sni, bool use_tls, int timeout_sec) {
    close();
    sock = s;
    if (use_tls) {
        if (!perform_tls_handshake(sni, timeout_sec)) {
            close();
            return false;
        }
    }
    return true;
}

bool TlsSocket::perform_tls_handshake(const std::string& sni, int timeout_sec) {
    SCHANNEL_CRED creds{};
    creds.dwVersion = SCHANNEL_CRED_VERSION;
    creds.grbitEnabledProtocols = SP_PROT_TLS1_2_CLIENT | SP_PROT_TLS1_3_CLIENT;
    creds.dwFlags = SCH_CRED_NO_DEFAULT_CREDS | SCH_CRED_MANUAL_CRED_VALIDATION;

    SECURITY_STATUS status = AcquireCredentialsHandleW(
        nullptr, const_cast<LPWSTR>(UNISP_NAME_W), SECPKG_CRED_OUTBOUND,
        nullptr, &creds, nullptr, nullptr, &hCred, nullptr
    );
    if (status != SEC_E_OK) return false;

    std::wstring wsni(sni.begin(), sni.end());

    SecBuffer out_bufs[1];
    out_bufs[0].pvBuffer = nullptr;
    out_bufs[0].BufferType = SECBUFFER_TOKEN;
    out_bufs[0].cbBuffer = 0;

    SecBufferDesc out_desc{};
    out_desc.ulVersion = SECBUFFER_VERSION;
    out_desc.cBuffers = 1;
    out_desc.pBuffers = out_bufs;

    DWORD flags = ISC_REQ_SEQUENCE_DETECT | ISC_REQ_REPLAY_DETECT |
                  ISC_REQ_CONFIDENTIALITY | ISC_REQ_ALLOCATE_MEMORY |
                  ISC_REQ_STREAM;

    DWORD ret_flags = 0;
    status = InitializeSecurityContextW(
        &hCred, nullptr, const_cast<LPWSTR>(wsni.c_str()), flags, 0, 0,
        nullptr, 0, &hCtxt, &out_desc, &ret_flags, nullptr
    );

    if (status != SEC_I_CONTINUE_NEEDED) {
        FreeCredentialsHandle(&hCred);
        SecInvalidateHandle(&hCred);
        return false;
    }

    if (out_bufs[0].cbBuffer > 0 && out_bufs[0].pvBuffer) {
        if (send_raw(out_bufs[0].pvBuffer, out_bufs[0].cbBuffer) < 0) {
            FreeContextBuffer(out_bufs[0].pvBuffer);
            return false;
        }
        FreeContextBuffer(out_bufs[0].pvBuffer);
        out_bufs[0].pvBuffer = nullptr;
    }

    std::vector<uint8_t> in_buffer(16384);
    size_t in_data_len = 0;

    while (status == SEC_I_CONTINUE_NEEDED || status == SEC_E_INCOMPLETE_MESSAGE) {
        if (status == SEC_E_INCOMPLETE_MESSAGE || in_data_len == 0) {
            int r = recv_raw(in_buffer.data() + in_data_len, in_buffer.size() - in_data_len);
            if (r <= 0) return false;
            in_data_len += r;
        }

        SecBuffer in_bufs[2];
        in_bufs[0].pvBuffer = in_buffer.data();
        in_bufs[0].cbBuffer = static_cast<unsigned long>(in_data_len);
        in_bufs[0].BufferType = SECBUFFER_TOKEN;

        in_bufs[1].pvBuffer = nullptr;
        in_bufs[1].cbBuffer = 0;
        in_bufs[1].BufferType = SECBUFFER_EMPTY;

        SecBufferDesc in_desc{};
        in_desc.ulVersion = SECBUFFER_VERSION;
        in_desc.cBuffers = 2;
        in_desc.pBuffers = in_bufs;

        out_bufs[0].pvBuffer = nullptr;
        out_bufs[0].BufferType = SECBUFFER_TOKEN;
        out_bufs[0].cbBuffer = 0;

        out_desc.cBuffers = 1;
        out_desc.pBuffers = out_bufs;

        status = InitializeSecurityContextW(
            &hCred, &hCtxt, const_cast<LPWSTR>(wsni.c_str()), flags, 0, 0,
            &in_desc, 0, nullptr, &out_desc, &ret_flags, nullptr
        );

        if (status == SEC_E_OK || status == SEC_I_CONTINUE_NEEDED) {
            if (out_bufs[0].cbBuffer > 0 && out_bufs[0].pvBuffer) {
                if (send_raw(out_bufs[0].pvBuffer, out_bufs[0].cbBuffer) < 0) {
                    FreeContextBuffer(out_bufs[0].pvBuffer);
                    return false;
                }
                FreeContextBuffer(out_bufs[0].pvBuffer);
                out_bufs[0].pvBuffer = nullptr;
            }
        }

        if (status == SEC_E_INCOMPLETE_MESSAGE) {
            if (in_data_len == in_buffer.size()) {
                in_buffer.resize(in_buffer.size() * 2);
            }
            continue;
        }

        // Handle extra data returned in in_bufs[1]
        if (in_bufs[1].BufferType == SECBUFFER_EXTRA && in_bufs[1].cbBuffer > 0) {
            size_t extra_bytes = in_bufs[1].cbBuffer;
            std::memmove(in_buffer.data(), in_buffer.data() + (in_data_len - extra_bytes), extra_bytes);
            in_data_len = extra_bytes;
        } else {
            in_data_len = 0;
        }

        if (status == SEC_E_OK) {
            if (in_data_len > 0) {
                pending_data.insert(pending_data.end(), in_buffer.data(), in_buffer.data() + in_data_len);
            }
            break;
        }

        if (FAILED(status)) {
            return false;
        }
    }

    if (status != SEC_E_OK) return false;

    QueryContextAttributesW(&hCtxt, SECPKG_ATTR_STREAM_SIZES, &stream_sizes);
    tls_active = true;
    return true;
}

int TlsSocket::send(const void* data, size_t len) {
    if (!tls_active) {
        return send_raw(data, len);
    }

    const uint8_t* p = static_cast<const uint8_t*>(data);
    size_t total_sent = 0;

    std::vector<uint8_t> msg_buffer(stream_sizes.cbHeader + stream_sizes.cbMaximumMessage + stream_sizes.cbTrailer);

    while (total_sent < len) {
        size_t chunk_len = (std::min)(len - total_sent, static_cast<size_t>(stream_sizes.cbMaximumMessage));

        SecBuffer bufs[4];
        bufs[0].pvBuffer = msg_buffer.data();
        bufs[0].cbBuffer = stream_sizes.cbHeader;
        bufs[0].BufferType = SECBUFFER_STREAM_HEADER;

        bufs[1].pvBuffer = msg_buffer.data() + stream_sizes.cbHeader;
        bufs[1].cbBuffer = static_cast<unsigned long>(chunk_len);
        bufs[1].BufferType = SECBUFFER_DATA;
        std::memcpy(bufs[1].pvBuffer, p + total_sent, chunk_len);

        bufs[2].pvBuffer = msg_buffer.data() + stream_sizes.cbHeader + chunk_len;
        bufs[2].cbBuffer = stream_sizes.cbTrailer;
        bufs[2].BufferType = SECBUFFER_STREAM_TRAILER;

        bufs[3].pvBuffer = nullptr;
        bufs[3].cbBuffer = 0;
        bufs[3].BufferType = SECBUFFER_EMPTY;

        SecBufferDesc desc{};
        desc.ulVersion = SECBUFFER_VERSION;
        desc.cBuffers = 4;
        desc.pBuffers = bufs;

        SECURITY_STATUS st = EncryptMessage(&hCtxt, 0, &desc, 0);
        if (st != SEC_E_OK) return -1;

        size_t total_enc = bufs[0].cbBuffer + bufs[1].cbBuffer + bufs[2].cbBuffer;
        if (send_raw(msg_buffer.data(), total_enc) < 0) return -1;

        total_sent += chunk_len;
    }

    return static_cast<int>(total_sent);
}

bool TlsSocket::send_all(const void* data, size_t len) {
    return send(data, len) == static_cast<int>(len);
}

int TlsSocket::recv(void* buf, size_t max_len) {
    if (!tls_active) {
        return recv_raw(buf, max_len);
    }

    if (!pending_data.empty()) {
        size_t take = (std::min)(max_len, pending_data.size());
        std::memcpy(buf, pending_data.data(), take);
        pending_data.erase(pending_data.begin(), pending_data.begin() + take);
        return static_cast<int>(take);
    }

    if (dec_buffer.empty()) {
        dec_buffer.resize(32768);
    }

    size_t in_len = 0;
    while (true) {
        int r = recv_raw(dec_buffer.data() + in_len, dec_buffer.size() - in_len);
        if (r <= 0) return r;
        in_len += r;

        while (in_len > 0) {
            SecBuffer bufs[4];
            bufs[0].pvBuffer = dec_buffer.data();
            bufs[0].cbBuffer = static_cast<unsigned long>(in_len);
            bufs[0].BufferType = SECBUFFER_DATA;

            bufs[1].pvBuffer = nullptr;
            bufs[1].cbBuffer = 0;
            bufs[1].BufferType = SECBUFFER_EMPTY;

            bufs[2].pvBuffer = nullptr;
            bufs[2].cbBuffer = 0;
            bufs[2].BufferType = SECBUFFER_EMPTY;

            bufs[3].pvBuffer = nullptr;
            bufs[3].cbBuffer = 0;
            bufs[3].BufferType = SECBUFFER_EMPTY;

            SecBufferDesc desc{};
            desc.ulVersion = SECBUFFER_VERSION;
            desc.cBuffers = 4;
            desc.pBuffers = bufs;

            SECURITY_STATUS st = DecryptMessage(&hCtxt, &desc, 0, nullptr);

            if (st == SEC_E_INCOMPLETE_MESSAGE) {
                if (in_len == dec_buffer.size()) {
                    dec_buffer.resize(dec_buffer.size() * 2);
                }
                break; // Need more network bytes
            }

            if (st == SEC_I_CONTEXT_EXPIRED) {
                return 0; // TLS session closed
            }

            if (st != SEC_E_OK) {
                return -1;
            }

            // Locate decrypted data buffer and extra buffer
            SecBuffer* pData = nullptr;
            SecBuffer* pExtra = nullptr;
            for (int i = 0; i < 4; ++i) {
                if (bufs[i].BufferType == SECBUFFER_DATA && !pData) pData = &bufs[i];
                if (bufs[i].BufferType == SECBUFFER_EXTRA && !pExtra) pExtra = &bufs[i];
            }

            if (pData && pData->cbBuffer > 0) {
                pending_data.insert(pending_data.end(), static_cast<uint8_t*>(pData->pvBuffer), static_cast<uint8_t*>(pData->pvBuffer) + pData->cbBuffer);
            }

            if (pExtra && pExtra->cbBuffer > 0) {
                size_t extra = pExtra->cbBuffer;
                std::memmove(dec_buffer.data(), dec_buffer.data() + (in_len - extra), extra);
                in_len = extra;
            } else {
                in_len = 0;
            }

            if (!pending_data.empty()) {
                size_t take = (std::min)(max_len, pending_data.size());
                std::memcpy(buf, pending_data.data(), take);
                pending_data.erase(pending_data.begin(), pending_data.begin() + take);
                return static_cast<int>(take);
            }
        }
    }
}

bool TlsSocket::recv_exact(void* buf, size_t len) {
    uint8_t* p = static_cast<uint8_t*>(buf);
    size_t total = 0;
    while (total < len) {
        int r = recv(p + total, len - total);
        if (r <= 0) return false;
        total += r;
    }
    return true;
}

bool TlsSocket::read_until(std::string& out, const std::string& delimiter, int timeout_sec) {
    out.clear();
    auto start = std::chrono::steady_clock::now();
    char c = 0;
    while (true) {
        if (recv_exact(&c, 1)) {
            out.push_back(c);
            if (out.size() >= delimiter.size() &&
                out.compare(out.size() - delimiter.size(), delimiter.size(), delimiter) == 0) {
                return true;
            }
        } else {
            return false;
        }
        if (std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - start).count() > timeout_sec) {
            return false;
        }
    }
}

} // namespace tgws
