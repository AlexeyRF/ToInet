#pragma once

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <array>

namespace tgws {

// Cryptographically secure random bytes
void random_bytes(void* dest, size_t len);

// Hex helpers
std::string hex_encode(const void* data, size_t len);
std::string hex_encode(const std::vector<uint8_t>& data);
bool hex_decode(const std::string& hex, std::vector<uint8_t>& out);
bool hex_decode(const std::string& hex, uint8_t* out, size_t max_len);

// Base64 helper
std::string base64_encode(const void* data, size_t len);

// SHA-256
class Sha256 {
public:
    Sha256();
    ~Sha256();
    void reset();
    void update(const void* data, size_t len);
    void finalize(uint8_t out[32]);
    std::array<uint8_t, 32> finalize();

    static std::array<uint8_t, 32> hash(const void* data, size_t len);
    static std::array<uint8_t, 32> hash(const std::vector<uint8_t>& data) {
        return hash(data.data(), data.size());
    }

private:
    void* hash_handle;
};

// HMAC-SHA256
std::array<uint8_t, 32> hmac_sha256(const void* key, size_t key_len, const void* data, size_t data_len);
bool hmac_compare_constant_time(const uint8_t* a, const uint8_t* b, size_t len);

// AES-256-CTR stream cipher
class Aes256Ctr {
public:
    Aes256Ctr();
    Aes256Ctr(const uint8_t key[32], const uint8_t iv[16]);
    ~Aes256Ctr();

    void init(const uint8_t key[32], const uint8_t iv[16]);
    void process(const uint8_t* in, uint8_t* out, size_t len);
    void process_inplace(uint8_t* data, size_t len);
    void skip(size_t bytes);

private:
    void* key_handle;
    std::vector<uint8_t> key_object;
    uint8_t counter[16];
    uint8_t keystream[16];
    size_t keystream_pos;

    void encrypt_counter(uint8_t out[16]);
    void increment_counter();
};

// Fast WebSocket masking using AVX2 and 64-bit word operations
void ws_mask_inplace(uint8_t* data, size_t len, uint32_t mask);
void ws_mask_copy(const uint8_t* src, uint8_t* dst, size_t len, uint32_t mask);

} // namespace tgws
