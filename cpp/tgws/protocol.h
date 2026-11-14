#pragma once

#include <cstdint>
#include <vector>
#include "crypto.h"

namespace tgws {

constexpr uint32_t PROTO_ABRIDGED = 0xefefefef;
constexpr uint32_t PROTO_INTERMEDIATE = 0xeeeeeeee;
constexpr uint32_t PROTO_PADDED_INTERMEDIATE = 0xdddddddd;

struct ClientHandshake {
    int dc_id = 0;
    bool is_media = false;
    uint32_t proto_tag = 0;
    uint8_t client_prekey_and_iv[48]; // prekey (32) + iv (16)
};

// Parses 64-byte client obfuscated2 handshake using MTProto secret
bool parse_client_handshake(const uint8_t handshake[64], const uint8_t secret[16], ClientHandshake& out);

// Generates 64-byte relay_init for upstream Telegram connection
std::vector<uint8_t> generate_relay_init(uint32_t proto_tag, int16_t dc_idx);

// Crypto context containing 4 bidirectional AES-256-CTR ciphers
struct CryptoCtx {
    Aes256Ctr clt_dec; // decrypt from client
    Aes256Ctr clt_enc; // encrypt to client
    Aes256Ctr tg_enc;  // encrypt to telegram
    Aes256Ctr tg_dec;  // decrypt from telegram
};

CryptoCtx build_crypto_ctx(const uint8_t client_prekey_and_iv[48],
                           const uint8_t secret[16],
                           const uint8_t relay_init[64]);

// Splits TCP stream into individual MTProto transport packets for WebSocket framing
class MsgSplitter {
public:
    explicit MsgSplitter(uint32_t proto_tag);

    // Feeds chunk (ciphertext) and plain (decrypted plaintext) and returns individual packets
    std::vector<std::vector<uint8_t>> split(const uint8_t* cipher_data, const uint8_t* plain_data, size_t len);

    // Flushes leftover buffer as final packet
    std::vector<uint8_t> flush();

private:
    uint32_t proto;
    std::vector<uint8_t> cipher_buf;
    std::vector<uint8_t> plain_buf;
    bool disabled;

    size_t next_packet_len(size_t offset, size_t avail);
};

} // namespace tgws
