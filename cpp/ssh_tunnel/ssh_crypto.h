#pragma once

#include <cstdint>
#include <cstddef>
#include <vector>
#include <array>
#include <string>

namespace ssh_tunnel {

// Cryptographically secure random bytes via Windows CNG
void random_bytes(void* dest, size_t len);

// Constant-time memory comparison
bool constant_time_eq(const uint8_t* a, const uint8_t* b, size_t len);

// Hash algorithms
enum class HashAlg {
    SHA1,
    SHA256,
    SHA512
};

std::vector<uint8_t> hash_data(HashAlg alg, const void* data, size_t len);
std::vector<uint8_t> hmac_data(HashAlg alg, const void* key, size_t key_len, const void* data, size_t data_len);

// Streaming / reusable HMAC context for packet MACs
class HmacContext {
public:
    HmacContext() = default;
    ~HmacContext();

    HmacContext(const HmacContext&) = delete;
    HmacContext& operator=(const HmacContext&) = delete;

    bool init(HashAlg alg, const uint8_t* key, size_t key_len);
    bool compute(uint32_t seq_num, const uint8_t* packet, size_t packet_len, uint8_t* out_mac);
    size_t mac_size() const { return mac_len_; }

private:
    void* alg_handle_{ nullptr };
    std::vector<uint8_t> key_;
    size_t mac_len_{ 0 };
};

// AES-128-CTR / AES-256-CTR via Windows CNG (ECB + 128-bit big-endian counter)
class AesCtr {
public:
    AesCtr() = default;
    ~AesCtr();

    AesCtr(const AesCtr&) = delete;
    AesCtr& operator=(const AesCtr&) = delete;

    bool init(const uint8_t* key, size_t key_len, const uint8_t iv[16]);
    bool process(const uint8_t* in, uint8_t* out, size_t len);
    bool process_inplace(uint8_t* data, size_t len);

private:
    void* key_handle_{ nullptr };
    uint8_t counter_[16]{};
    uint8_t keystream_[16]{};
    size_t keystream_pos_{ 16 };

    bool encrypt_counter(uint8_t out[16]);
    void increment_counter();
};

// X25519 (Curve25519 Diffie-Hellman, RFC 7748)
void x25519_scalarmult_base(uint8_t out[32], const uint8_t scalar[32]);
void x25519_scalarmult(uint8_t out[32], const uint8_t scalar[32], const uint8_t point[32]);

} // namespace ssh_tunnel
