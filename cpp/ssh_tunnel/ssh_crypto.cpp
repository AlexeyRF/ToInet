#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include "ssh_crypto.h"
#include <cstring>

#pragma comment(lib, "bcrypt.lib")

namespace ssh_tunnel {

static LPCWSTR get_bcrypt_alg_id(HashAlg alg) {
    switch (alg) {
        case HashAlg::SHA1:   return BCRYPT_SHA1_ALGORITHM;
        case HashAlg::SHA256: return BCRYPT_SHA256_ALGORITHM;
        case HashAlg::SHA512: return BCRYPT_SHA512_ALGORITHM;
    }
    return BCRYPT_SHA256_ALGORITHM;
}

static size_t get_hash_len(HashAlg alg) {
    switch (alg) {
        case HashAlg::SHA1:   return 20;
        case HashAlg::SHA256: return 32;
        case HashAlg::SHA512: return 64;
    }
    return 32;
}

static BCRYPT_ALG_HANDLE get_hash_alg_handle(HashAlg alg) {
    static BCRYPT_ALG_HANDLE h_sha1 = nullptr;
    static BCRYPT_ALG_HANDLE h_sha256 = nullptr;
    static BCRYPT_ALG_HANDLE h_sha512 = nullptr;

    BCRYPT_ALG_HANDLE* target = &h_sha256;
    if (alg == HashAlg::SHA1) target = &h_sha1;
    else if (alg == HashAlg::SHA512) target = &h_sha512;

    if (!*target) {
        BCryptOpenAlgorithmProvider(target, get_bcrypt_alg_id(alg), nullptr, 0);
    }
    return *target;
}

static BCRYPT_ALG_HANDLE get_hmac_alg_handle(HashAlg alg) {
    static BCRYPT_ALG_HANDLE h_sha1 = nullptr;
    static BCRYPT_ALG_HANDLE h_sha256 = nullptr;
    static BCRYPT_ALG_HANDLE h_sha512 = nullptr;

    BCRYPT_ALG_HANDLE* target = &h_sha256;
    if (alg == HashAlg::SHA1) target = &h_sha1;
    else if (alg == HashAlg::SHA512) target = &h_sha512;

    if (!*target) {
        BCryptOpenAlgorithmProvider(target, get_bcrypt_alg_id(alg), nullptr, BCRYPT_ALG_HANDLE_HMAC_FLAG);
    }
    return *target;
}

static BCRYPT_ALG_HANDLE get_aes_ecb_alg() {
    static BCRYPT_ALG_HANDLE h = nullptr;
    if (!h) {
        if (BCryptOpenAlgorithmProvider(&h, BCRYPT_AES_ALGORITHM, nullptr, 0) == 0 && h) {
            BCryptSetProperty(h, BCRYPT_CHAINING_MODE, (PUCHAR)BCRYPT_CHAIN_MODE_ECB, sizeof(BCRYPT_CHAIN_MODE_ECB), 0);
        }
    }
    return h;
}

void random_bytes(void* dest, size_t len) {
    if (!dest || len == 0) return;
    BCryptGenRandom(nullptr, static_cast<PUCHAR>(dest), static_cast<ULONG>(len), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
}

bool constant_time_eq(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t diff = 0;
    for (size_t i = 0; i < len; ++i) {
        diff |= a[i] ^ b[i];
    }
    return diff == 0;
}

std::vector<uint8_t> hash_data(HashAlg alg, const void* data, size_t len) {
    size_t hlen = get_hash_len(alg);
    std::vector<uint8_t> out(hlen, 0);
    BCRYPT_ALG_HANDLE hAlg = get_hash_alg_handle(alg);
    if (!hAlg) return out;

    BCRYPT_HASH_HANDLE hHash = nullptr;
    if (BCryptCreateHash(hAlg, &hHash, nullptr, 0, nullptr, 0, 0) == 0 && hHash) {
        if (len > 0) {
            BCryptHashData(hHash, const_cast<PUCHAR>(static_cast<const uint8_t*>(data)), static_cast<ULONG>(len), 0);
        }
        BCryptFinishHash(hHash, out.data(), static_cast<ULONG>(hlen), 0);
        BCryptDestroyHash(hHash);
    }
    return out;
}

std::vector<uint8_t> hmac_data(HashAlg alg, const void* key, size_t key_len, const void* data, size_t data_len) {
    size_t hlen = get_hash_len(alg);
    std::vector<uint8_t> out(hlen, 0);
    BCRYPT_ALG_HANDLE hAlg = get_hmac_alg_handle(alg);
    if (!hAlg) return out;

    BCRYPT_HASH_HANDLE hHash = nullptr;
    if (BCryptCreateHash(hAlg, &hHash, nullptr, 0,
                         const_cast<PUCHAR>(static_cast<const uint8_t*>(key)),
                         static_cast<ULONG>(key_len), 0) == 0 && hHash) {
        if (data_len > 0) {
            BCryptHashData(hHash, const_cast<PUCHAR>(static_cast<const uint8_t*>(data)), static_cast<ULONG>(data_len), 0);
        }
        BCryptFinishHash(hHash, out.data(), static_cast<ULONG>(hlen), 0);
        BCryptDestroyHash(hHash);
    }
    return out;
}

HmacContext::~HmacContext() = default;

bool HmacContext::init(HashAlg alg, const uint8_t* key, size_t key_len) {
    alg_handle_ = get_hmac_alg_handle(alg);
    if (!alg_handle_) return false;
    key_.assign(key, key + key_len);
    mac_len_ = get_hash_len(alg);
    return true;
}

bool HmacContext::compute(uint32_t seq_num, const uint8_t* packet, size_t packet_len, uint8_t* out_mac) {
    if (!alg_handle_ || mac_len_ == 0) return false;
    BCRYPT_HASH_HANDLE hHash = nullptr;
    if (BCryptCreateHash(static_cast<BCRYPT_ALG_HANDLE>(alg_handle_), &hHash, nullptr, 0,
                         key_.data(), static_cast<ULONG>(key_.size()), 0) != 0 || !hHash) {
        return false;
    }

    uint8_t seq_be[4] = {
        static_cast<uint8_t>((seq_num >> 24) & 0xFF),
        static_cast<uint8_t>((seq_num >> 16) & 0xFF),
        static_cast<uint8_t>((seq_num >> 8) & 0xFF),
        static_cast<uint8_t>(seq_num & 0xFF)
    };
    BCryptHashData(hHash, seq_be, 4, 0);
    if (packet_len > 0) {
        BCryptHashData(hHash, const_cast<PUCHAR>(packet), static_cast<ULONG>(packet_len), 0);
    }
    NTSTATUS status = BCryptFinishHash(hHash, out_mac, static_cast<ULONG>(mac_len_), 0);
    BCryptDestroyHash(hHash);
    return status == 0;
}

AesCtr::~AesCtr() {
    if (key_handle_) {
        BCryptDestroyKey(static_cast<BCRYPT_KEY_HANDLE>(key_handle_));
        key_handle_ = nullptr;
    }
}

bool AesCtr::init(const uint8_t* key, size_t key_len, const uint8_t iv[16]) {
    if (key_handle_) {
        BCryptDestroyKey(static_cast<BCRYPT_KEY_HANDLE>(key_handle_));
        key_handle_ = nullptr;
    }
    BCRYPT_ALG_HANDLE hAlg = get_aes_ecb_alg();
    if (!hAlg) return false;

    BCRYPT_KEY_HANDLE hKey = nullptr;
    if (BCryptGenerateSymmetricKey(hAlg, &hKey, nullptr, 0,
                                   const_cast<PUCHAR>(key), static_cast<ULONG>(key_len), 0) != 0) {
        return false;
    }
    key_handle_ = hKey;
    std::memcpy(counter_, iv, 16);
    keystream_pos_ = 16;
    return true;
}

bool AesCtr::encrypt_counter(uint8_t out[16]) {
    if (!key_handle_) return false;
    ULONG out_len = 0;
    return BCryptEncrypt(static_cast<BCRYPT_KEY_HANDLE>(key_handle_),
                         counter_, 16, nullptr, nullptr, 0,
                         out, 16, &out_len, 0) == 0;
}

void AesCtr::increment_counter() {
    for (int i = 15; i >= 0; --i) {
        if (++counter_[i] != 0) break;
    }
}

bool AesCtr::process(const uint8_t* in, uint8_t* out, size_t len) {
    if (!key_handle_) return false;
    for (size_t i = 0; i < len; ++i) {
        if (keystream_pos_ >= 16) {
            if (!encrypt_counter(keystream_)) return false;
            increment_counter();
            keystream_pos_ = 0;
        }
        out[i] = in[i] ^ keystream_[keystream_pos_++];
    }
    return true;
}

bool AesCtr::process_inplace(uint8_t* data, size_t len) {
    return process(data, data, len);
}

// ============================================================================
// X25519 (Curve25519) - TweetNaCl-derived 64-bit field arithmetic
// ============================================================================
namespace {

using gf = int64_t[16];

static void set25519(gf r, const gf a) {
    for (int i = 0; i < 16; ++i) r[i] = a[i];
}

static void car25519(gf o) {
    for (int i = 0; i < 16; ++i) {
        o[i] += (1LL << 16);
        int64_t c = o[i] >> 16;
        o[(i + 1) * (i < 15)] += c - 1 + 37 * (c - 1) * (i == 15);
        o[i] -= c << 16;
    }
}

static void sel25519(gf p, gf q, int b) {
    int64_t c = ~(b - 1);
    for (int i = 0; i < 16; ++i) {
        int64_t t = c & (p[i] ^ q[i]);
        p[i] ^= t;
        q[i] ^= t;
    }
}

static void pack25519(uint8_t* o, const gf n) {
    gf m, t;
    for (int i = 0; i < 16; ++i) t[i] = n[i];
    car25519(t);
    car25519(t);
    car25519(t);
    for (int j = 0; j < 2; ++j) {
        m[0] = t[0] - 0xffed;
        for (int i = 1; i < 15; ++i) {
            m[i] = t[i] - 0xffff - ((m[i - 1] >> 16) & 1);
            m[i - 1] &= 0xffff;
        }
        m[15] = t[15] - 0x7fff - ((m[14] >> 16) & 1);
        int b = static_cast<int>((m[15] >> 16) & 1);
        m[14] &= 0xffff;
        sel25519(t, m, 1 - b);
    }
    for (int i = 0; i < 16; ++i) {
        o[2 * i] = static_cast<uint8_t>(t[i] & 0xff);
        o[2 * i + 1] = static_cast<uint8_t>(t[i] >> 8);
    }
}

static void unpack25519(gf o, const uint8_t* n) {
    for (int i = 0; i < 16; ++i) {
        o[i] = n[2 * i] + (static_cast<int64_t>(n[2 * i + 1]) << 8);
    }
    o[15] &= 0x7fff;
}

static void A(gf o, const gf a, const gf b) {
    for (int i = 0; i < 16; ++i) o[i] = a[i] + b[i];
}

static void Z(gf o, const gf a, const gf b) {
    for (int i = 0; i < 16; ++i) o[i] = a[i] - b[i];
}

static void M(gf o, const gf a, const gf b) {
    int64_t t[31] = {};
    for (int i = 0; i < 16; ++i) {
        for (int j = 0; j < 16; ++j) {
            t[i + j] += a[i] * b[j];
        }
    }
    for (int i = 0; i < 15; ++i) {
        t[i] += 38 * t[i + 16];
    }
    for (int i = 0; i < 16; ++i) o[i] = t[i];
    car25519(o);
    car25519(o);
}

static void S(gf o, const gf a) {
    M(o, a, a);
}

static void inv25519(gf o, const gf i) {
    gf c;
    set25519(c, i);
    for (int a = 253; a >= 0; --a) {
        S(c, c);
        if (a != 2 && a != 4) M(c, c, i);
    }
    set25519(o, c);
}

} // namespace

void x25519_scalarmult(uint8_t out[32], const uint8_t scalar[32], const uint8_t point[32]) {
    uint8_t z[32];
    std::memcpy(z, scalar, 32);
    z[0] &= 248;
    z[31] = (z[31] & 127) | 64;

    gf x, a, b, c, d, e, f;
    unpack25519(x, point);

    for (int i = 0; i < 16; ++i) {
        a[i] = 0; b[i] = x[i]; c[i] = 0; d[i] = 0;
    }
    a[0] = 1;
    d[0] = 1;

    static const gf _121665 = { 0xDB41, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

    for (int i = 254; i >= 0; --i) {
        int r = (z[i >> 3] >> (i & 7)) & 1;
        sel25519(a, b, r);
        sel25519(c, d, r);
        A(e, a, c);
        Z(a, a, c);
        A(c, b, d);
        Z(b, b, d);
        S(d, e);
        S(f, a);
        M(a, c, a);
        M(c, b, e);
        A(e, a, c);
        Z(a, a, c);
        S(b, a);
        Z(c, d, f);
        M(a, c, _121665);
        A(a, a, d);
        M(c, c, a);
        M(a, d, f);
        M(d, b, x);
        S(b, e);
        sel25519(a, b, r);
        sel25519(c, d, r);
    }
    inv25519(c, c);
    M(a, a, c);
    pack25519(out, a);
}

void x25519_scalarmult_base(uint8_t out[32], const uint8_t scalar[32]) {
    static const uint8_t basepoint[32] = { 9 };
    x25519_scalarmult(out, scalar, basepoint);
}

} // namespace ssh_tunnel
