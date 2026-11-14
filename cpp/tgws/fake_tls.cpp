#include "fake_tls.h"
#include "crypto.h"
#include <ctime>
#include <cstring>
#include <algorithm>
#include <ws2tcpip.h>

namespace tgws {

static const uint8_t SERVER_HELLO_TEMPLATE[] = {
    0x16, 0x03, 0x03, 0x00, 0x7a,
    0x02, 0x00, 0x00, 0x76,
    0x03, 0x03,
    // 11: 32 bytes server random
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x20, // 43: session id len
    // 44: 32 bytes session id
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x13, 0x01, 0x00, // TLS_AES_128_GCM_SHA256
    0x00, 0x2e,
    0x00, 0x33, 0x00, 0x24, 0x00, 0x1d, 0x00, 0x20,
    // 89: 32 bytes key exchange pubkey
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00, 0x2b, 0x00, 0x02, 0x03, 0x04
};

static const uint8_t CCS_FRAME[] = { 0x14, 0x03, 0x03, 0x00, 0x01, 0x01 };

FakeTlsResult verify_client_hello(const uint8_t* data, size_t len, const uint8_t secret[16]) {
    FakeTlsResult res{};
    if (len < 43) return res;
    if (data[0] != TLS_RECORD_HANDSHAKE) return res;
    if (data[5] != 0x01) return res; // Handshake type = ClientHello

    res.client_random.assign(data + 11, data + 11 + 32);

    std::vector<uint8_t> zeroed(data, data + len);
    std::memset(zeroed.data() + 11, 0, 32);

    auto expected = hmac_sha256(secret, 16, zeroed.data(), zeroed.size());

    // Compare first 28 bytes in constant time
    if (!hmac_compare_constant_time(expected.data(), res.client_random.data(), 28)) {
        return res;
    }

    // Timestamp XOR at bytes 28..31
    uint32_t ts_xor = 0;
    for (int i = 0; i < 4; ++i) {
        reinterpret_cast<uint8_t*>(&ts_xor)[i] = res.client_random[28 + i] ^ expected[28 + i];
    }

    uint32_t now = static_cast<uint32_t>(std::time(nullptr));
    int64_t diff = static_cast<int64_t>(now) - static_cast<int64_t>(ts_xor);
    if (diff < -120 || diff > 120) {
        return res; // Timestamp out of tolerance
    }

    res.timestamp = ts_xor;

    res.session_id.assign(32, 0);
    if (len >= 44 + 32 && data[43] == 0x20) {
        res.session_id.assign(data + 44, data + 44 + 32);
    }

    res.valid = true;
    return res;
}

std::vector<uint8_t> build_server_hello(const uint8_t secret[16],
                                        const uint8_t client_random[32],
                                        const uint8_t session_id[32]) {
    std::vector<uint8_t> sh(std::begin(SERVER_HELLO_TEMPLATE), std::end(SERVER_HELLO_TEMPLATE));
    std::memcpy(sh.data() + 44, session_id, 32);
    random_bytes(sh.data() + 89, 32);

    // Random encrypted dummy application data (1900 - 2100 bytes)
    uint16_t enc_sz = 1900 + (rand() % 201);
    std::vector<uint8_t> app_record;
    app_record.reserve(5 + enc_sz);
    app_record.push_back(0x17);
    app_record.push_back(0x03);
    app_record.push_back(0x03);
    app_record.push_back(static_cast<uint8_t>((enc_sz >> 8) & 0xFF));
    app_record.push_back(static_cast<uint8_t>(enc_sz & 0xFF));
    size_t old_sz = app_record.size();
    app_record.resize(old_sz + enc_sz);
    random_bytes(app_record.data() + old_sz, enc_sz);

    std::vector<uint8_t> resp;
    resp.insert(resp.end(), sh.begin(), sh.end());
    resp.insert(resp.end(), std::begin(CCS_FRAME), std::end(CCS_FRAME));
    resp.insert(resp.end(), app_record.begin(), app_record.end());

    std::vector<uint8_t> hmac_input;
    hmac_input.reserve(32 + resp.size());
    hmac_input.insert(hmac_input.end(), client_random, client_random + 32);
    hmac_input.insert(hmac_input.end(), resp.begin(), resp.end());

    auto s_rand = hmac_sha256(secret, 16, hmac_input.data(), hmac_input.size());
    std::memcpy(resp.data() + 11, s_rand.data(), 32);

    return resp;
}

std::vector<uint8_t> wrap_tls_record(const void* data, size_t len) {
    const uint8_t* p = static_cast<const uint8_t*>(data);
    std::vector<uint8_t> out;
    size_t offset = 0;
    while (offset < len) {
        size_t chunk = (std::min)(len - offset, TLS_APPDATA_MAX);
        out.push_back(0x17);
        out.push_back(0x03);
        out.push_back(0x03);
        out.push_back(static_cast<uint8_t>((chunk >> 8) & 0xFF));
        out.push_back(static_cast<uint8_t>(chunk & 0xFF));
        out.insert(out.end(), p + offset, p + offset + chunk);
        offset += chunk;
    }
    return out;
}

void proxy_to_masking_domain(SOCKET client_sock, const std::string& domain, const uint8_t* initial_data, size_t initial_len) {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo* res = nullptr;
    if (getaddrinfo(domain.c_str(), "443", &hints, &res) != 0) return;

    SOCKET mask_sock = INVALID_SOCKET;
    for (addrinfo* ptr = res; ptr != nullptr; ptr = ptr->ai_next) {
        mask_sock = socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol);
        if (mask_sock == INVALID_SOCKET) continue;
        if (::connect(mask_sock, ptr->ai_addr, static_cast<int>(ptr->ai_addrlen)) == 0) {
            break;
        }
        closesocket(mask_sock);
        mask_sock = INVALID_SOCKET;
    }
    freeaddrinfo(res);
    if (mask_sock == INVALID_SOCKET) return;

    if (initial_data && initial_len > 0) {
        ::send(mask_sock, reinterpret_cast<const char*>(initial_data), static_cast<int>(initial_len), 0);
    }

    // Bidirectional relay until EOF
    char buf[16384];
    while (true) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(client_sock, &fds);
        FD_SET(mask_sock, &fds);

        timeval tv{ 30, 0 };
        int sel = select(0, &fds, nullptr, nullptr, &tv);
        if (sel <= 0) break;

        if (FD_ISSET(client_sock, &fds)) {
            int r = ::recv(client_sock, buf, sizeof(buf), 0);
            if (r <= 0) break;
            if (::send(mask_sock, buf, r, 0) <= 0) break;
        }
        if (FD_ISSET(mask_sock, &fds)) {
            int r = ::recv(mask_sock, buf, sizeof(buf), 0);
            if (r <= 0) break;
            if (::send(client_sock, buf, r, 0) <= 0) break;
        }
    }
    closesocket(mask_sock);
}

FakeTlsStream::FakeTlsStream(SOCKET s) : sock(s), read_left(0) {}

bool FakeTlsStream::read_tls_payload() {
    while (true) {
        uint8_t hdr[5];
        size_t h_read = 0;
        while (h_read < 5) {
            int r = ::recv(sock, reinterpret_cast<char*>(hdr) + h_read, static_cast<int>(5 - h_read), 0);
            if (r <= 0) return false;
            h_read += r;
        }

        uint8_t rtype = hdr[0];
        uint16_t rlen = (static_cast<uint16_t>(hdr[3]) << 8) | hdr[4];

        if (rtype == TLS_RECORD_CCS) {
            // Skip ChangeCipherSpec
            std::vector<uint8_t> dummy(rlen);
            size_t d_read = 0;
            while (d_read < rlen) {
                int r = ::recv(sock, reinterpret_cast<char*>(dummy.data()) + d_read, static_cast<int>(rlen - d_read), 0);
                if (r <= 0) return false;
                d_read += r;
            }
            continue;
        }

        if (rtype != TLS_RECORD_APPDATA) {
            return false;
        }

        read_buf.resize(rlen);
        size_t b_read = 0;
        while (b_read < rlen) {
            int r = ::recv(sock, reinterpret_cast<char*>(read_buf.data()) + b_read, static_cast<int>(rlen - b_read), 0);
            if (r <= 0) return false;
            b_read += r;
        }
        read_left = rlen;
        return true;
    }
}

int FakeTlsStream::recv(void* buf, size_t max_len) {
    if (read_left == 0) {
        if (!read_tls_payload()) return 0;
    }

    size_t offset = read_buf.size() - read_left;
    size_t take = (std::min)(max_len, read_left);
    std::memcpy(buf, read_buf.data() + offset, take);
    read_left -= take;
    return static_cast<int>(take);
}

bool FakeTlsStream::recv_exact(void* buf, size_t len) {
    uint8_t* p = static_cast<uint8_t*>(buf);
    size_t total = 0;
    while (total < len) {
        int r = recv(p + total, len - total);
        if (r <= 0) return false;
        total += r;
    }
    return true;
}

int FakeTlsStream::send(const void* data, size_t len) {
    std::vector<uint8_t> rec = wrap_tls_record(data, len);
    size_t total = 0;
    while (total < rec.size()) {
        int r = ::send(sock, reinterpret_cast<const char*>(rec.data()) + total, static_cast<int>(rec.size() - total), 0);
        if (r <= 0) return -1;
        total += r;
    }
    return static_cast<int>(len);
}

bool FakeTlsStream::send_all(const void* data, size_t len) {
    return send(data, len) == static_cast<int>(len);
}

} // namespace tgws
