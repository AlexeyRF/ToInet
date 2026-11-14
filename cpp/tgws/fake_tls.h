#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <memory>
#include <winsock2.h>

namespace tgws {

constexpr uint8_t TLS_RECORD_CCS = 0x14;
constexpr uint8_t TLS_RECORD_HANDSHAKE = 0x16;
constexpr uint8_t TLS_RECORD_APPDATA = 0x17;
constexpr size_t TLS_APPDATA_MAX = 16384;

struct FakeTlsResult {
    bool valid = false;
    std::vector<uint8_t> client_random;
    std::vector<uint8_t> session_id;
    uint32_t timestamp = 0;
};

// Verifies ClientHello record against MTProto secret and timestamp (+-120s)
FakeTlsResult verify_client_hello(const uint8_t* data, size_t len, const uint8_t secret[16]);

// Builds ServerHello + ChangeCipherSpec + dummy ApplicationData response
std::vector<uint8_t> build_server_hello(const uint8_t secret[16],
                                        const uint8_t client_random[32],
                                        const uint8_t session_id[32]);

// Wraps arbitrary payload into TLS 0x17 Application Data records
std::vector<uint8_t> wrap_tls_record(const void* data, size_t len);

// Transparent proxy to masking domain on port 443
void proxy_to_masking_domain(SOCKET client_sock, const std::string& domain, const uint8_t* initial_data, size_t initial_len);

// Stream wrapper that unpacks incoming TLS Application Data and wraps outgoing
class FakeTlsStream {
public:
    explicit FakeTlsStream(SOCKET sock);

    int recv(void* buf, size_t max_len);
    bool recv_exact(void* buf, size_t len);
    int send(const void* data, size_t len);
    bool send_all(const void* data, size_t len);

private:
    SOCKET sock;
    std::vector<uint8_t> read_buf;
    size_t read_left;

    bool read_tls_payload();
};

} // namespace tgws
