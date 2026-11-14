#pragma once

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <schannel.h>
#define SECURITY_WIN32
#include <security.h>
#include <schnlsp.h>

#include <string>
#include <vector>
#include <cstdint>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "secur32.lib")
#pragma comment(lib, "crypt32.lib")

namespace tgws {

class TlsSocket {
public:
    TlsSocket();
    ~TlsSocket();

    // Connects to host:port. If use_tls is true, performs TLS handshake using Schannel and SNI.
    bool connect(const std::string& host, int port, const std::string& sni = "", bool use_tls = true, int timeout_sec = 10);
    
    // Attach an existing connected socket and optionally negotiate TLS
    bool attach(SOCKET sock, const std::string& sni = "", bool use_tls = true, int timeout_sec = 10);

    // Send and receive
    int send(const void* data, size_t len);
    int recv(void* buf, size_t max_len);
    bool recv_exact(void* buf, size_t len);
    bool send_all(const void* data, size_t len);

    // Read until a delimiter sequence (e.g. "\r\n\r\n" for HTTP headers)
    bool read_until(std::string& out, const std::string& delimiter, int timeout_sec = 10);

    bool is_valid() const { return sock != INVALID_SOCKET; }
    bool is_tls() const { return tls_active; }
    void close();

    SOCKET get_raw_socket() const { return sock; }
    SOCKET detach_raw_socket();

private:
    SOCKET sock;
    bool tls_active;
    CredHandle hCred;
    CtxtHandle hCtxt;
    SecPkgContext_StreamSizes stream_sizes;
    std::vector<uint8_t> dec_buffer;
    std::vector<uint8_t> pending_data;

    bool perform_tls_handshake(const std::string& sni, int timeout_sec);
    int recv_raw(void* buf, size_t len);
    int send_raw(const void* buf, size_t len);
};

} // namespace tgws
