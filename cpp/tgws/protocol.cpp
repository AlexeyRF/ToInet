#include "protocol.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace tgws {

static const uint32_t RESERVED_STARTS[] = {
    0x44414548, // "HEAD"
    0x54534F50, // "POST"
    0x20544547, // "GET "
    0xeeeeeeee,
    0xdddddddd,
    0x02010316,
    0x4954504F  // "OPTI"
};

bool parse_client_handshake(const uint8_t handshake[64], const uint8_t secret[16], ClientHandshake& out) {
    uint8_t dec_prekey[32];
    uint8_t dec_iv[16];
    std::memcpy(dec_prekey, handshake + 8, 32);
    std::memcpy(dec_iv, handshake + 40, 16);

    uint8_t hash_buf[48];
    std::memcpy(hash_buf, dec_prekey, 32);
    std::memcpy(hash_buf + 32, secret, 16);

    auto dec_key = Sha256::hash(hash_buf, 48);

    Aes256Ctr decryptor(dec_key.data(), dec_iv);
    uint8_t decrypted[64];
    decryptor.process(handshake, decrypted, 64);

    uint32_t proto_tag = *reinterpret_cast<const uint32_t*>(decrypted + 56);
    if (proto_tag != PROTO_ABRIDGED &&
        proto_tag != PROTO_INTERMEDIATE &&
        proto_tag != PROTO_PADDED_INTERMEDIATE) {
        return false;
    }

    int16_t dc_idx = *reinterpret_cast<const int16_t*>(decrypted + 60);
    out.dc_id = std::abs(static_cast<int>(dc_idx));
    out.is_media = (dc_idx < 0);
    out.proto_tag = proto_tag;
    std::memcpy(out.client_prekey_and_iv, handshake + 8, 48);
    return true;
}

std::vector<uint8_t> generate_relay_init(uint32_t proto_tag, int16_t dc_idx) {
    std::vector<uint8_t> rnd(64);
    while (true) {
        random_bytes(rnd.data(), 64);
        if (rnd[0] == 0xef) continue;

        uint32_t first4 = *reinterpret_cast<const uint32_t*>(rnd.data());
        bool match_reserved = false;
        for (uint32_t res : RESERVED_STARTS) {
            if (first4 == res) {
                match_reserved = true;
                break;
            }
        }
        if (match_reserved) continue;

        uint32_t next4 = *reinterpret_cast<const uint32_t*>(rnd.data() + 4);
        if (next4 == 0) continue;
        break;
    }

    uint8_t enc_key[32];
    uint8_t enc_iv[16];
    std::memcpy(enc_key, rnd.data() + 8, 32);
    std::memcpy(enc_iv, rnd.data() + 40, 16);

    Aes256Ctr encryptor(enc_key, enc_iv);
    uint8_t enc_full[64];
    encryptor.process(rnd.data(), enc_full, 64);

    uint8_t keystream_tail[8];
    for (int i = 0; i < 8; ++i) {
        keystream_tail[i] = enc_full[56 + i] ^ rnd[56 + i];
    }

    uint8_t tail_plain[8];
    std::memcpy(tail_plain, &proto_tag, 4);
    std::memcpy(tail_plain + 4, &dc_idx, 2);
    random_bytes(tail_plain + 6, 2);

    for (int i = 0; i < 8; ++i) {
        rnd[56 + i] = tail_plain[i] ^ keystream_tail[i];
    }

    return rnd;
}

CryptoCtx build_crypto_ctx(const uint8_t client_prekey_and_iv[48],
                           const uint8_t secret[16],
                           const uint8_t relay_init[64]) {
    CryptoCtx ctx{};

    // Client decryptor
    uint8_t clt_dec_input[48];
    std::memcpy(clt_dec_input, client_prekey_and_iv, 32);
    std::memcpy(clt_dec_input + 32, secret, 16);
    auto clt_dec_key = Sha256::hash(clt_dec_input, 48);
    ctx.clt_dec.init(clt_dec_key.data(), client_prekey_and_iv + 32);
    ctx.clt_dec.skip(64); // Fast-forward past 64-byte init

    // Client encryptor (reversed client prekey and iv)
    uint8_t clt_enc_rev[48];
    for (int i = 0; i < 48; ++i) {
        clt_enc_rev[i] = client_prekey_and_iv[47 - i];
    }
    uint8_t clt_enc_input[48];
    std::memcpy(clt_enc_input, clt_enc_rev, 32);
    std::memcpy(clt_enc_input + 32, secret, 16);
    auto clt_enc_key = Sha256::hash(clt_enc_input, 48);
    ctx.clt_enc.init(clt_enc_key.data(), clt_enc_rev + 32);

    // Telegram upstream encryptor (raw relay_init keys)
    ctx.tg_enc.init(relay_init + 8, relay_init + 40);
    ctx.tg_enc.skip(64);

    // Telegram upstream decryptor (reversed relay_init prekey and iv)
    uint8_t tg_dec_rev[48];
    for (int i = 0; i < 48; ++i) {
        tg_dec_rev[i] = relay_init[8 + 47 - i];
    }
    ctx.tg_dec.init(tg_dec_rev, tg_dec_rev + 32);

    return ctx;
}

MsgSplitter::MsgSplitter(uint32_t proto_tag) : proto(proto_tag), disabled(false) {}

size_t MsgSplitter::next_packet_len(size_t offset, size_t avail) {
    if (avail == 0) return 0;

    if (proto == PROTO_ABRIDGED) {
        uint8_t first = plain_buf[offset];
        if (first == 0x7F || first == 0xFF) {
            if (avail < 4) return 0;
            uint32_t payload_len = static_cast<uint32_t>(plain_buf[offset + 1])
                | (static_cast<uint32_t>(plain_buf[offset + 2]) << 8)
                | (static_cast<uint32_t>(plain_buf[offset + 3]) << 16);
            payload_len *= 4;
            if (payload_len == 0) return static_cast<size_t>(-1);
            return 4 + payload_len;
        } else {
            uint32_t payload_len = static_cast<uint32_t>(first & 0x7F) * 4;
            if (payload_len == 0) return static_cast<size_t>(-1);
            return 1 + payload_len;
        }
    } else { // Intermediate and Padded Intermediate
        if (avail < 4) return 0;
        uint32_t payload_len = *reinterpret_cast<const uint32_t*>(plain_buf.data() + offset) & 0x7FFFFFFF;
        if (payload_len == 0) return static_cast<size_t>(-1);
        return 4 + payload_len;
    }
}

std::vector<std::vector<uint8_t>> MsgSplitter::split(const uint8_t* cipher_data, const uint8_t* plain_data, size_t len) {
    std::vector<std::vector<uint8_t>> parts;
    if (!cipher_data || len == 0) return parts;

    if (disabled) {
        parts.emplace_back(cipher_data, cipher_data + len);
        return parts;
    }

    cipher_buf.insert(cipher_buf.end(), cipher_data, cipher_data + len);
    plain_buf.insert(plain_buf.end(), plain_data, plain_data + len);

    size_t offset = 0;
    size_t buf_len = cipher_buf.size();

    while (offset < buf_len) {
        size_t avail = buf_len - offset;
        size_t pkt_len = next_packet_len(offset, avail);

        if (pkt_len == 0) {
            break; // Incomplete packet, wait for more data
        }
        if (pkt_len == static_cast<size_t>(-1)) {
            // Protocol parse error: disable splitting and flush
            parts.emplace_back(cipher_buf.begin() + offset, cipher_buf.end());
            offset = buf_len;
            disabled = true;
            break;
        }
        if (avail < pkt_len) {
            break; // Incomplete packet
        }

        parts.emplace_back(cipher_buf.begin() + offset, cipher_buf.begin() + offset + pkt_len);
        offset += pkt_len;
    }

    if (offset > 0) {
        cipher_buf.erase(cipher_buf.begin(), cipher_buf.begin() + offset);
        plain_buf.erase(plain_buf.begin(), plain_buf.begin() + offset);
    }
    return parts;
}

std::vector<uint8_t> MsgSplitter::flush() {
    std::vector<uint8_t> tail = std::move(cipher_buf);
    cipher_buf.clear();
    plain_buf.clear();
    return tail;
}

} // namespace tgws
