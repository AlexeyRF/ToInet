#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <immintrin.h>
#include "crypto.h"
#include <cstring>
#include <iomanip>
#include <sstream>

#pragma comment(lib, "bcrypt.lib")

namespace tgws {

static BCRYPT_ALG_HANDLE get_sha256_alg() {
    static BCRYPT_ALG_HANDLE h = nullptr;
    if (!h) {
        BCryptOpenAlgorithmProvider(&h, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
    }
    return h;
}

static BCRYPT_ALG_HANDLE get_hmac_sha256_alg() {
    static BCRYPT_ALG_HANDLE h = nullptr;
    if (!h) {
        BCryptOpenAlgorithmProvider(&h, BCRYPT_SHA256_ALGORITHM, nullptr, BCRYPT_ALG_HANDLE_HMAC_FLAG);
    }
    return h;
}

static BCRYPT_ALG_HANDLE get_aes_ecb_alg() {
    static BCRYPT_ALG_HANDLE h = nullptr;
    if (!h) {
        BCryptOpenAlgorithmProvider(&h, BCRYPT_AES_ALGORITHM, nullptr, 0);
        if (h) {
            BCryptSetProperty(h, BCRYPT_CHAINING_MODE, (PUCHAR)BCRYPT_CHAIN_MODE_ECB, sizeof(BCRYPT_CHAIN_MODE_ECB), 0);
        }
    }
    return h;
}

void random_bytes(void* dest, size_t len) {
    if (!dest || len == 0) return;
    BCryptGenRandom(nullptr, static_cast<PUCHAR>(dest), static_cast<ULONG>(len), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
}

std::string hex_encode(const void* data, size_t len) {
    static const char hex_chars[] = "0123456789abcdef";
    const uint8_t* p = static_cast<const uint8_t*>(data);
    std::string res;
    res.reserve(len * 2);
    for (size_t i = 0; i < len; ++i) {
        res.push_back(hex_chars[(p[i] >> 4) & 0x0F]);
        res.push_back(hex_chars[p[i] & 0x0F]);
    }
    return res;
}

std::string hex_encode(const std::vector<uint8_t>& data) {
    return hex_encode(data.data(), data.size());
}

static inline int hex_char_val(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

bool hex_decode(const std::string& hex, std::vector<uint8_t>& out) {
    out.clear();
    if (hex.size() % 2 != 0) return false;
    out.resize(hex.size() / 2);
    return hex_decode(hex, out.data(), out.size());
}

bool hex_decode(const std::string& hex, uint8_t* out, size_t max_len) {
    if (hex.size() % 2 != 0 || (hex.size() / 2) > max_len) return false;
    for (size_t i = 0; i < hex.size(); i += 2) {
        int hi = hex_char_val(hex[i]);
        int lo = hex_char_val(hex[i + 1]);
        if (hi < 0 || lo < 0) return false;
        out[i / 2] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return true;
}

std::string base64_encode(const void* data, size_t len) {
    static const char b64_table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const uint8_t* p = static_cast<const uint8_t*>(data);
    std::string out;
    out.reserve(((len + 2) / 3) * 4);

    for (size_t i = 0; i < len; i += 3) {
        uint32_t val = (p[i] << 16);
        if (i + 1 < len) val |= (p[i + 1] << 8);
        if (i + 2 < len) val |= p[i + 2];

        out.push_back(b64_table[(val >> 18) & 0x3F]);
        out.push_back(b64_table[(val >> 12) & 0x3F]);
        out.push_back((i + 1 < len) ? b64_table[(val >> 6) & 0x3F] : '=');
        out.push_back((i + 2 < len) ? b64_table[val & 0x3F] : '=');
    }
    return out;
}

// SHA-256
Sha256::Sha256() : hash_handle(nullptr) {
    reset();
}

Sha256::~Sha256() {
    if (hash_handle) {
        BCryptDestroyHash(static_cast<BCRYPT_HASH_HANDLE>(hash_handle));
        hash_handle = nullptr;
    }
}

void Sha256::reset() {
    if (hash_handle) {
        BCryptDestroyHash(static_cast<BCRYPT_HASH_HANDLE>(hash_handle));
        hash_handle = nullptr;
    }
    BCRYPT_ALG_HANDLE alg = get_sha256_alg();
    if (alg) {
        BCRYPT_HASH_HANDLE h = nullptr;
        if (BCryptCreateHash(alg, &h, nullptr, 0, nullptr, 0, 0) >= 0) {
            hash_handle = h;
        }
    }
}

void Sha256::update(const void* data, size_t len) {
    if (hash_handle && data && len > 0) {
        BCryptHashData(static_cast<BCRYPT_HASH_HANDLE>(hash_handle),
                       static_cast<PUCHAR>(const_cast<void*>(data)),
                       static_cast<ULONG>(len), 0);
    }
}

void Sha256::finalize(uint8_t out[32]) {
    if (hash_handle) {
        BCryptFinishHash(static_cast<BCRYPT_HASH_HANDLE>(hash_handle), out, 32, 0);
        BCryptDestroyHash(static_cast<BCRYPT_HASH_HANDLE>(hash_handle));
        hash_handle = nullptr;
    } else {
        std::memset(out, 0, 32);
    }
}

std::array<uint8_t, 32> Sha256::finalize() {
    std::array<uint8_t, 32> out{};
    finalize(out.data());
    return out;
}

std::array<uint8_t, 32> Sha256::hash(const void* data, size_t len) {
    Sha256 s;
    s.update(data, len);
    return s.finalize();
}

// HMAC-SHA256
std::array<uint8_t, 32> hmac_sha256(const void* key, size_t key_len, const void* data, size_t data_len) {
    std::array<uint8_t, 32> out{};
    BCRYPT_ALG_HANDLE alg = get_hmac_sha256_alg();
    if (!alg) return out;

    BCRYPT_HASH_HANDLE h = nullptr;
    if (BCryptCreateHash(alg, &h, nullptr, 0,
                         static_cast<PUCHAR>(const_cast<void*>(key)),
                         static_cast<ULONG>(key_len), 0) >= 0) {
        if (data && data_len > 0) {
            BCryptHashData(h, static_cast<PUCHAR>(const_cast<void*>(data)),
                           static_cast<ULONG>(data_len), 0);
        }
        BCryptFinishHash(h, out.data(), 32, 0);
        BCryptDestroyHash(h);
    }
    return out;
}

bool hmac_compare_constant_time(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t diff = 0;
    for (size_t i = 0; i < len; ++i) {
        diff |= (a[i] ^ b[i]);
    }
    return diff == 0;
}

// AES-256-CTR
Aes256Ctr::Aes256Ctr() : key_handle(nullptr), keystream_pos(16) {
    std::memset(counter, 0, sizeof(counter));
    std::memset(keystream, 0, sizeof(keystream));
}

Aes256Ctr::Aes256Ctr(const uint8_t key[32], const uint8_t iv[16]) : Aes256Ctr() {
    init(key, iv);
}

Aes256Ctr::~Aes256Ctr() {
    if (key_handle) {
        BCryptDestroyKey(static_cast<BCRYPT_KEY_HANDLE>(key_handle));
        key_handle = nullptr;
    }
}

Aes256Ctr::Aes256Ctr(Aes256Ctr&& other) noexcept
    : key_handle(other.key_handle),
      keystream_pos(other.keystream_pos) {
    std::memcpy(counter, other.counter, sizeof(counter));
    std::memcpy(keystream, other.keystream, sizeof(keystream));
    other.key_handle = nullptr;
}

Aes256Ctr& Aes256Ctr::operator=(Aes256Ctr&& other) noexcept {
    if (this != &other) {
        if (key_handle) {
            BCryptDestroyKey(static_cast<BCRYPT_KEY_HANDLE>(key_handle));
        }
        key_handle = other.key_handle;
        keystream_pos = other.keystream_pos;
        std::memcpy(counter, other.counter, sizeof(counter));
        std::memcpy(keystream, other.keystream, sizeof(keystream));
        other.key_handle = nullptr;
    }
    return *this;
}

void Aes256Ctr::init(const uint8_t key[32], const uint8_t iv[16]) {
    if (key_handle) {
        BCryptDestroyKey(static_cast<BCRYPT_KEY_HANDLE>(key_handle));
        key_handle = nullptr;
    }

    BCRYPT_ALG_HANDLE alg = get_aes_ecb_alg();
    if (!alg) return;

    BCRYPT_KEY_HANDLE kh = nullptr;
    if (BCryptGenerateSymmetricKey(alg, &kh, nullptr, 0,
                                   const_cast<PUCHAR>(key), 32, 0) >= 0) {
        key_handle = kh;
    }

    std::memcpy(counter, iv, 16);
    keystream_pos = 16; // Force initial block generation
}

void Aes256Ctr::increment_counter() {
    for (int i = 15; i >= 0; --i) {
        if (++counter[i] != 0) break;
    }
}

void Aes256Ctr::encrypt_counter(uint8_t out[16]) {
    if (!key_handle) {
        std::memset(out, 0, 16);
        return;
    }
    ULONG bytes_written = 0;
    BCryptEncrypt(static_cast<BCRYPT_KEY_HANDLE>(key_handle), counter, 16, nullptr, nullptr, 0, out, 16, &bytes_written, 0);
    increment_counter();
}

void Aes256Ctr::process(const uint8_t* in, uint8_t* out, size_t len) {
    if (!in || !out || len == 0) return;

    size_t i = 0;
    // Finish any leftover bytes in keystream
    while (keystream_pos < 16 && i < len) {
        out[i] = in[i] ^ keystream[keystream_pos++];
        ++i;
    }

    // Process full 16-byte blocks
    while (i + 16 <= len) {
        encrypt_counter(keystream);
        uint64_t* out64 = reinterpret_cast<uint64_t*>(out + i);
        const uint64_t* in64 = reinterpret_cast<const uint64_t*>(in + i);
        const uint64_t* ks64 = reinterpret_cast<const uint64_t*>(keystream);
        out64[0] = in64[0] ^ ks64[0];
        out64[1] = in64[1] ^ ks64[1];
        i += 16;
    }

    // Remaining tail
    if (i < len) {
        encrypt_counter(keystream);
        keystream_pos = 0;
        while (i < len) {
            out[i] = in[i] ^ keystream[keystream_pos++];
            ++i;
        }
    }
}

void Aes256Ctr::process_inplace(uint8_t* data, size_t len) {
    process(data, data, len);
}

void Aes256Ctr::skip(size_t bytes) {
    uint8_t dummy[64];
    while (bytes > 0) {
        size_t chunk = (std::min)(bytes, sizeof(dummy));
        process(dummy, dummy, chunk);
        bytes -= chunk;
    }
}

// WebSocket SIMD / 64-bit Masking
void ws_mask_inplace(uint8_t* data, size_t len, uint32_t mask) {
    if (!data || len == 0) return;
    size_t i = 0;

#if defined(__AVX2__) || defined(_M_X64) || defined(_M_IX86)
    if (len >= 32) {
        __m256i vmask = _mm256_set1_epi32(static_cast<int>(mask));
        for (; i + 32 <= len; i += 32) {
            __m256i chunk = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(data + i));
            chunk = _mm256_xor_si256(chunk, vmask);
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(data + i), chunk);
        }
    }
#endif

    uint64_t mask64 = (static_cast<uint64_t>(mask) << 32) | mask;
    for (; i + 8 <= len; i += 8) {
        *reinterpret_cast<uint64_t*>(data + i) ^= mask64;
    }

    const uint8_t* m8 = reinterpret_cast<const uint8_t*>(&mask);
    for (; i < len; ++i) {
        data[i] ^= m8[i & 3];
    }
}

void ws_mask_copy(const uint8_t* src, uint8_t* dst, size_t len, uint32_t mask) {
    if (!src || !dst || len == 0) return;
    size_t i = 0;

#if defined(__AVX2__) || defined(_M_X64) || defined(_M_IX86)
    if (len >= 32) {
        __m256i vmask = _mm256_set1_epi32(static_cast<int>(mask));
        for (; i + 32 <= len; i += 32) {
            __m256i chunk = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(src + i));
            chunk = _mm256_xor_si256(chunk, vmask);
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(dst + i), chunk);
        }
    }
#endif

    uint64_t mask64 = (static_cast<uint64_t>(mask) << 32) | mask;
    for (; i + 8 <= len; i += 8) {
        uint64_t chunk = *reinterpret_cast<const uint64_t*>(src + i);
        *reinterpret_cast<uint64_t*>(dst + i) = chunk ^ mask64;
    }

    const uint8_t* m8 = reinterpret_cast<const uint8_t*>(&mask);
    for (; i < len; ++i) {
        dst[i] = src[i] ^ m8[i & 3];
    }
}

} // namespace tgws
