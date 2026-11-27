#include "ssh_client.h"
#include <cstring>
#include <sstream>
#include <algorithm>
#include <chrono>

namespace ssh_tunnel {

namespace {

// SSH Message Numbers (RFC 4253 / 4252 / 4254)
constexpr uint8_t SSH_MSG_DISCONNECT                = 1;
constexpr uint8_t SSH_MSG_IGNORE                    = 2;
constexpr uint8_t SSH_MSG_UNIMPLEMENTED             = 3;
constexpr uint8_t SSH_MSG_DEBUG                     = 4;
constexpr uint8_t SSH_MSG_SERVICE_REQUEST           = 5;
constexpr uint8_t SSH_MSG_SERVICE_ACCEPT            = 6;
constexpr uint8_t SSH_MSG_EXT_INFO                  = 7;
constexpr uint8_t SSH_MSG_KEXINIT                   = 20;
constexpr uint8_t SSH_MSG_NEWKEYS                   = 21;
constexpr uint8_t SSH_MSG_KEX_ECDH_INIT             = 30;
constexpr uint8_t SSH_MSG_KEX_ECDH_REPLY            = 31;
constexpr uint8_t SSH_MSG_USERAUTH_REQUEST          = 50;
constexpr uint8_t SSH_MSG_USERAUTH_FAILURE          = 51;
constexpr uint8_t SSH_MSG_USERAUTH_SUCCESS          = 52;
constexpr uint8_t SSH_MSG_USERAUTH_BANNER           = 53;
constexpr uint8_t SSH_MSG_USERAUTH_INFO_REQUEST     = 60;
constexpr uint8_t SSH_MSG_USERAUTH_INFO_RESPONSE    = 61;
constexpr uint8_t SSH_MSG_GLOBAL_REQUEST            = 80;
constexpr uint8_t SSH_MSG_REQUEST_SUCCESS           = 81;
constexpr uint8_t SSH_MSG_REQUEST_FAILURE           = 82;
constexpr uint8_t SSH_MSG_CHANNEL_OPEN              = 90;
constexpr uint8_t SSH_MSG_CHANNEL_OPEN_CONFIRMATION = 91;
constexpr uint8_t SSH_MSG_CHANNEL_OPEN_FAILURE      = 92;
constexpr uint8_t SSH_MSG_CHANNEL_WINDOW_ADJUST     = 93;
constexpr uint8_t SSH_MSG_CHANNEL_DATA              = 94;
constexpr uint8_t SSH_MSG_CHANNEL_EXTENDED_DATA     = 95;
constexpr uint8_t SSH_MSG_CHANNEL_EOF               = 96;
constexpr uint8_t SSH_MSG_CHANNEL_CLOSE             = 97;
constexpr uint8_t SSH_MSG_CHANNEL_REQUEST           = 98;
constexpr uint8_t SSH_MSG_CHANNEL_SUCCESS           = 99;
constexpr uint8_t SSH_MSG_CHANNEL_FAILURE           = 100;

constexpr uint32_t INITIAL_WINDOW_SIZE = 2 * 1024 * 1024;
constexpr uint32_t MAX_PACKET_SIZE     = 32768;

class ByteWriter {
public:
    std::vector<uint8_t> buf;

    void write_u8(uint8_t v) { buf.push_back(v); }

    void write_u32(uint32_t v) {
        buf.push_back(static_cast<uint8_t>((v >> 24) & 0xFF));
        buf.push_back(static_cast<uint8_t>((v >> 16) & 0xFF));
        buf.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
        buf.push_back(static_cast<uint8_t>(v & 0xFF));
    }

    void write_bytes(const void* data, size_t len) {
        const uint8_t* p = static_cast<const uint8_t*>(data);
        buf.insert(buf.end(), p, p + len);
    }

    void write_string(const void* data, size_t len) {
        write_u32(static_cast<uint32_t>(len));
        write_bytes(data, len);
    }

    void write_string(const std::string& s) {
        write_string(s.data(), s.size());
    }

    void write_mpint(const uint8_t* big_endian_unsigned, size_t len) {
        size_t start = 0;
        while (start < len && big_endian_unsigned[start] == 0) {
            ++start;
        }
        if (start == len) {
            write_u32(0);
            return;
        }
        bool need_pad = (big_endian_unsigned[start] & 0x80) != 0;
        write_u32(static_cast<uint32_t>(len - start + (need_pad ? 1 : 0)));
        if (need_pad) write_u8(0);
        write_bytes(big_endian_unsigned + start, len - start);
    }
};

class ByteReader {
public:
    ByteReader(const uint8_t* data, size_t len) : data_(data), len_(len), pos_(0) {}

    size_t remaining() const { return len_ - pos_; }

    bool read_u8(uint8_t& out) {
        if (remaining() < 1) return false;
        out = data_[pos_++];
        return true;
    }

    bool read_u32(uint32_t& out) {
        if (remaining() < 4) return false;
        out = (static_cast<uint32_t>(data_[pos_]) << 24) |
              (static_cast<uint32_t>(data_[pos_ + 1]) << 16) |
              (static_cast<uint32_t>(data_[pos_ + 2]) << 8) |
              static_cast<uint32_t>(data_[pos_ + 3]);
        pos_ += 4;
        return true;
    }

    bool read_string(std::string& out) {
        uint32_t slen = 0;
        if (!read_u32(slen) || remaining() < slen) return false;
        out.assign(reinterpret_cast<const char*>(data_ + pos_), slen);
        pos_ += slen;
        return true;
    }

    bool read_bytes_vec(std::vector<uint8_t>& out) {
        uint32_t slen = 0;
        if (!read_u32(slen) || remaining() < slen) return false;
        out.assign(data_ + pos_, data_ + pos_ + slen);
        pos_ += slen;
        return true;
    }

    bool skip(size_t n) {
        if (remaining() < n) return false;
        pos_ += n;
        return true;
    }

private:
    const uint8_t* data_;
    size_t len_;
    size_t pos_;
};

static std::string negotiate_alg(const std::string& client_list, const std::string& server_list) {
    std::vector<std::string> server_algs;
    std::stringstream ss_s(server_list);
    std::string item;
    while (std::getline(ss_s, item, ',')) {
        if (!item.empty()) server_algs.push_back(item);
    }

    std::stringstream ss_c(client_list);
    while (std::getline(ss_c, item, ',')) {
        if (std::find(server_algs.begin(), server_algs.end(), item) != server_algs.end()) {
            return item;
        }
    }
    return "";
}

static std::vector<uint8_t> derive_key(const std::vector<uint8_t>& k_mpint,
                                       const std::vector<uint8_t>& h,
                                       char letter,
                                       const std::vector<uint8_t>& session_id,
                                       size_t needed_len) {
    std::vector<uint8_t> out;
    ByteWriter w;
    w.write_bytes(k_mpint.data(), k_mpint.size());
    w.write_bytes(h.data(), h.size());
    w.write_u8(static_cast<uint8_t>(letter));
    w.write_bytes(session_id.data(), session_id.size());

    std::vector<uint8_t> k1 = hash_data(HashAlg::SHA256, w.buf.data(), w.buf.size());
    out.insert(out.end(), k1.begin(), k1.end());

    while (out.size() < needed_len) {
        ByteWriter w2;
        w2.write_bytes(k_mpint.data(), k_mpint.size());
        w2.write_bytes(h.data(), h.size());
        w2.write_bytes(out.data(), out.size());
        std::vector<uint8_t> kn = hash_data(HashAlg::SHA256, w2.buf.data(), w2.buf.size());
        out.insert(out.end(), kn.begin(), kn.end());
    }
    out.resize(needed_len);
    return out;
}

static bool send_all_socket(SOCKET s, const uint8_t* data, size_t len) {
    size_t sent = 0;
    while (sent < len) {
        int r = send(s, reinterpret_cast<const char*>(data + sent), static_cast<int>(len - sent), 0);
        if (r <= 0) return false;
        sent += static_cast<size_t>(r);
    }
    return true;
}

} // namespace

SshClient::SshClient() = default;

SshClient::~SshClient() {
    disconnect();
}

bool SshClient::send_raw(const uint8_t* data, size_t len) {
    return send_all_socket(sock_, data, len);
}

bool SshClient::recv_raw(uint8_t* data, size_t len) {
    size_t recvd = 0;
    while (recvd < len) {
        int r = recv(sock_, reinterpret_cast<char*>(data + recvd), static_cast<int>(len - recvd), 0);
        if (r <= 0) return false;
        recvd += static_cast<size_t>(r);
    }
    return true;
}

bool SshClient::send_packet(const std::vector<uint8_t>& payload) {
    std::lock_guard<std::mutex> lock(send_mutex_);
    if (sock_ == INVALID_SOCKET) return false;

    size_t block_size = send_encrypted_ ? 16 : 8;
    size_t unpadded = 5 + payload.size();
    size_t pad_len = block_size - (unpadded % block_size);
    if (pad_len < 4) pad_len += block_size;

    uint32_t packet_len = static_cast<uint32_t>(1 + payload.size() + pad_len);
    std::vector<uint8_t> pkt(4 + packet_len);
    pkt[0] = static_cast<uint8_t>((packet_len >> 24) & 0xFF);
    pkt[1] = static_cast<uint8_t>((packet_len >> 16) & 0xFF);
    pkt[2] = static_cast<uint8_t>((packet_len >> 8) & 0xFF);
    pkt[3] = static_cast<uint8_t>(packet_len & 0xFF);
    pkt[4] = static_cast<uint8_t>(pad_len);
    if (!payload.empty()) {
        std::memcpy(pkt.data() + 5, payload.data(), payload.size());
    }
    random_bytes(pkt.data() + 5 + payload.size(), pad_len);

    std::vector<uint8_t> mac;
    if (send_encrypted_ && send_mac_.mac_size() > 0) {
        mac.resize(send_mac_.mac_size());
        if (!send_mac_.compute(send_seq_, pkt.data(), pkt.size(), mac.data())) {
            return false;
        }
    }

    if (send_encrypted_) {
        if (!send_cipher_.process_inplace(pkt.data(), pkt.size())) {
            return false;
        }
    }

    if (!mac.empty()) {
        pkt.insert(pkt.end(), mac.begin(), mac.end());
    }

    bool ok = send_raw(pkt.data(), pkt.size());
    if (ok) {
        send_seq_++;
    }
    return ok;
}

bool SshClient::recv_packet(std::vector<uint8_t>& out_payload) {
    while (true) {
        size_t block_size = recv_encrypted_ ? 16 : 8;
        std::vector<uint8_t> first_block(block_size);
        if (!recv_raw(first_block.data(), block_size)) return false;

        if (recv_encrypted_) {
            if (!recv_cipher_.process_inplace(first_block.data(), block_size)) return false;
        }

        uint32_t packet_len = (static_cast<uint32_t>(first_block[0]) << 24) |
                              (static_cast<uint32_t>(first_block[1]) << 16) |
                              (static_cast<uint32_t>(first_block[2]) << 8) |
                              static_cast<uint32_t>(first_block[3]);

        if (packet_len < 2 || packet_len > 512 * 1024) return false;

        size_t total_len = 4 + static_cast<size_t>(packet_len);
        if (total_len < block_size || (total_len % block_size) != 0) return false;

        std::vector<uint8_t> pkt(total_len);
        std::memcpy(pkt.data(), first_block.data(), block_size);
        if (total_len > block_size) {
            if (!recv_raw(pkt.data() + block_size, total_len - block_size)) return false;
            if (recv_encrypted_) {
                if (!recv_cipher_.process_inplace(pkt.data() + block_size, total_len - block_size)) return false;
            }
        }

        if (recv_encrypted_ && recv_mac_.mac_size() > 0) {
            std::vector<uint8_t> wire_mac(recv_mac_.mac_size());
            std::vector<uint8_t> calc_mac(recv_mac_.mac_size());
            if (!recv_raw(wire_mac.data(), wire_mac.size())) return false;
            if (!recv_mac_.compute(recv_seq_, pkt.data(), pkt.size(), calc_mac.data())) return false;
            if (!constant_time_eq(wire_mac.data(), calc_mac.data(), wire_mac.size())) return false;
        }

        recv_seq_++;

        uint8_t pad_len = pkt[4];
        if (pad_len < 4 || static_cast<size_t>(pad_len) + 1 > packet_len) return false;

        size_t payload_len = packet_len - 1 - pad_len;
        out_payload.assign(pkt.begin() + 5, pkt.begin() + 5 + payload_len);

        if (!out_payload.empty()) {
            uint8_t msg = out_payload[0];
            if (msg == SSH_MSG_IGNORE || msg == SSH_MSG_DEBUG || msg == SSH_MSG_UNIMPLEMENTED) {
                continue;
            }
        }
        return true;
    }
}

bool SshClient::perform_version_exchange(std::string& v_c, std::string& v_s, std::string& out_error) {
    v_c = "SSH-2.0-ToInetSSH_1.0";
    std::string send_banner = v_c + "\r\n";
    if (!send_raw(reinterpret_cast<const uint8_t*>(send_banner.data()), send_banner.size())) {
        out_error = "Failed to send SSH version banner";
        return false;
    }

    for (int line_num = 0; line_num < 32; ++line_num) {
        std::string line;
        char c = 0;
        while (line.size() < 255) {
            if (!recv_raw(reinterpret_cast<uint8_t*>(&c), 1)) {
                out_error = "Connection closed during SSH version exchange";
                return false;
            }
            if (c == '\n') break;
            if (c != '\r') line.push_back(c);
        }
        if (line.rfind("SSH-2.0-", 0) == 0 || line.rfind("SSH-1.99-", 0) == 0) {
            v_s = line;
            return true;
        }
    }
    out_error = "Invalid or missing SSH-2.0 server banner";
    return false;
}

bool SshClient::perform_kex(const std::string& v_c, const std::string& v_s, std::string& out_error) {
    const std::string kex_algs = "curve25519-sha256,curve25519-sha256@libssh.org";
    const std::string host_key_algs = "ssh-ed25519,rsa-sha2-512,rsa-sha2-256,ssh-rsa";
    const std::string enc_algs = "aes256-ctr,aes128-ctr";
    const std::string mac_algs = "hmac-sha2-256,hmac-sha2-512,hmac-sha1";
    const std::string comp_algs = "none";

    uint8_t cookie[16];
    random_bytes(cookie, 16);

    ByteWriter kex_c;
    kex_c.write_u8(SSH_MSG_KEXINIT);
    kex_c.write_bytes(cookie, 16);
    kex_c.write_string(kex_algs);
    kex_c.write_string(host_key_algs);
    kex_c.write_string(enc_algs);
    kex_c.write_string(enc_algs);
    kex_c.write_string(mac_algs);
    kex_c.write_string(mac_algs);
    kex_c.write_string(comp_algs);
    kex_c.write_string(comp_algs);
    kex_c.write_string("");
    kex_c.write_string("");
    kex_c.write_u8(0); // first_kex_packet_follows = false
    kex_c.write_u32(0);

    std::vector<uint8_t> i_c = kex_c.buf;
    if (!send_packet(i_c)) {
        out_error = "Failed to send KEXINIT";
        return false;
    }

    std::vector<uint8_t> i_s;
    if (!recv_packet(i_s) || i_s.empty() || i_s[0] != SSH_MSG_KEXINIT) {
        out_error = "Expected SSH_MSG_KEXINIT from server";
        return false;
    }

    ByteReader r(i_s.data() + 1, i_s.size() - 1);
    std::string srv_kex, srv_host, srv_enc_c2s, srv_enc_s2c, srv_mac_c2s, srv_mac_s2c, srv_comp_c2s, srv_comp_s2c;
    if (!r.skip(16) || !r.read_string(srv_kex) || !r.read_string(srv_host) ||
        !r.read_string(srv_enc_c2s) || !r.read_string(srv_enc_s2c) ||
        !r.read_string(srv_mac_c2s) || !r.read_string(srv_mac_s2c) ||
        !r.read_string(srv_comp_c2s) || !r.read_string(srv_comp_s2c)) {
        out_error = "Malformed server KEXINIT";
        return false;
    }

    std::string chosen_kex = negotiate_alg(kex_algs, srv_kex);
    std::string chosen_enc_c2s = negotiate_alg(enc_algs, srv_enc_c2s);
    std::string chosen_enc_s2c = negotiate_alg(enc_algs, srv_enc_s2c);
    std::string chosen_mac_c2s = negotiate_alg(mac_algs, srv_mac_c2s);
    std::string chosen_mac_s2c = negotiate_alg(mac_algs, srv_mac_s2c);

    if (chosen_kex.empty() || chosen_enc_c2s.empty() || chosen_enc_s2c.empty() ||
        chosen_mac_c2s.empty() || chosen_mac_s2c.empty()) {
        out_error = "No common SSH algorithms (kex=" + srv_kex + ", enc=" + srv_enc_c2s + ", mac=" + srv_mac_c2s + ")";
        return false;
    }

    // Generate ephemeral X25519 keypair
    uint8_t priv[32], q_c[32];
    random_bytes(priv, 32);
    x25519_scalarmult_base(q_c, priv);

    ByteWriter ecdh_init;
    ecdh_init.write_u8(SSH_MSG_KEX_ECDH_INIT);
    ecdh_init.write_string(q_c, 32);
    if (!send_packet(ecdh_init.buf)) {
        out_error = "Failed to send KEX_ECDH_INIT";
        return false;
    }

    std::vector<uint8_t> ecdh_reply;
    if (!recv_packet(ecdh_reply) || ecdh_reply.empty() || ecdh_reply[0] != SSH_MSG_KEX_ECDH_REPLY) {
        out_error = "Expected SSH_MSG_KEX_ECDH_REPLY";
        return false;
    }

    ByteReader rr(ecdh_reply.data() + 1, ecdh_reply.size() - 1);
    std::vector<uint8_t> k_s, q_s, sig_h;
    if (!rr.read_bytes_vec(k_s) || !rr.read_bytes_vec(q_s) || !rr.read_bytes_vec(sig_h) || q_s.size() != 32) {
        out_error = "Malformed KEX_ECDH_REPLY";
        return false;
    }

    uint8_t shared_secret[32];
    x25519_scalarmult(shared_secret, priv, q_s.data());

    // Check for all-zero shared secret (low-order point)
    uint8_t zero_check = 0;
    for (int i = 0; i < 32; ++i) zero_check |= shared_secret[i];
    if (zero_check == 0) {
        out_error = "Invalid X25519 shared secret";
        return false;
    }

    ByteWriter k_mpint_w;
    k_mpint_w.write_mpint(shared_secret, 32);
    const std::vector<uint8_t>& k_mpint = k_mpint_w.buf;

    // Exchange hash H = SHA256(V_C || V_S || I_C || I_S || K_S || Q_C || Q_S || K)
    ByteWriter hw;
    hw.write_string(v_c);
    hw.write_string(v_s);
    hw.write_string(i_c.data(), i_c.size());
    hw.write_string(i_s.data(), i_s.size());
    hw.write_string(k_s.data(), k_s.size());
    hw.write_string(q_c, 32);
    hw.write_string(q_s.data(), q_s.size());
    hw.write_bytes(k_mpint.data(), k_mpint.size());

    std::vector<uint8_t> h = hash_data(HashAlg::SHA256, hw.buf.data(), hw.buf.size());
    if (session_id_.empty()) {
        session_id_ = h;
    }

    // Exchange NEWKEYS
    if (!send_packet({ SSH_MSG_NEWKEYS })) {
        out_error = "Failed to send NEWKEYS";
        return false;
    }

    std::vector<uint8_t> nk;
    if (!recv_packet(nk) || nk.empty() || nk[0] != SSH_MSG_NEWKEYS) {
        out_error = "Expected SSH_MSG_NEWKEYS";
        return false;
    }

    auto mac_info = [](const std::string& name, HashAlg& alg, size_t& len) {
        if (name == "hmac-sha2-512") { alg = HashAlg::SHA512; len = 64; }
        else if (name == "hmac-sha1") { alg = HashAlg::SHA1; len = 20; }
        else { alg = HashAlg::SHA256; len = 32; }
    };

    size_t enc_len_c2s = (chosen_enc_c2s == "aes256-ctr") ? 32 : 16;
    size_t enc_len_s2c = (chosen_enc_s2c == "aes256-ctr") ? 32 : 16;
    HashAlg mac_alg_c2s, mac_alg_s2c;
    size_t mac_len_c2s, mac_len_s2c;
    mac_info(chosen_mac_c2s, mac_alg_c2s, mac_len_c2s);
    mac_info(chosen_mac_s2c, mac_alg_s2c, mac_len_s2c);

    auto iv_c2s  = derive_key(k_mpint, h, 'A', session_id_, 16);
    auto iv_s2c  = derive_key(k_mpint, h, 'B', session_id_, 16);
    auto key_c2s = derive_key(k_mpint, h, 'C', session_id_, enc_len_c2s);
    auto key_s2c = derive_key(k_mpint, h, 'D', session_id_, enc_len_s2c);
    auto mkey_c2s = derive_key(k_mpint, h, 'E', session_id_, mac_len_c2s);
    auto mkey_s2c = derive_key(k_mpint, h, 'F', session_id_, mac_len_s2c);

    if (!send_cipher_.init(key_c2s.data(), key_c2s.size(), iv_c2s.data()) ||
        !recv_cipher_.init(key_s2c.data(), key_s2c.size(), iv_s2c.data()) ||
        !send_mac_.init(mac_alg_c2s, mkey_c2s.data(), mkey_c2s.size()) ||
        !recv_mac_.init(mac_alg_s2c, mkey_s2c.data(), mkey_s2c.size())) {
        out_error = "Failed to initialize session cipher/MAC";
        return false;
    }

    send_encrypted_ = true;
    recv_encrypted_ = true;
    return true;
}

bool SshClient::perform_auth(const std::string& user, const std::string& password, std::string& out_error) {
    ByteWriter svc;
    svc.write_u8(SSH_MSG_SERVICE_REQUEST);
    svc.write_string("ssh-userauth");
    if (!send_packet(svc.buf)) {
        out_error = "Failed to request ssh-userauth service";
        return false;
    }

    std::vector<uint8_t> resp;
    while (true) {
        if (!recv_packet(resp) || resp.empty()) {
            out_error = "Connection closed waiting for SERVICE_ACCEPT";
            return false;
        }
        if (resp[0] == SSH_MSG_EXT_INFO) continue;
        if (resp[0] == SSH_MSG_SERVICE_ACCEPT) break;
        out_error = "Unexpected packet waiting for SERVICE_ACCEPT";
        return false;
    }

    // Try password authentication first
    ByteWriter auth;
    auth.write_u8(SSH_MSG_USERAUTH_REQUEST);
    auth.write_string(user);
    auth.write_string("ssh-connection");
    auth.write_string("password");
    auth.write_u8(0); // FALSE
    auth.write_string(password);

    if (!send_packet(auth.buf)) {
        out_error = "Failed to send password auth request";
        return false;
    }

    bool tried_kbd = false;
    while (true) {
        if (!recv_packet(resp) || resp.empty()) {
            out_error = "Connection closed during authentication";
            return false;
        }
        uint8_t msg = resp[0];
        if (msg == SSH_MSG_USERAUTH_BANNER || msg == SSH_MSG_EXT_INFO) {
            continue;
        }
        if (msg == SSH_MSG_USERAUTH_SUCCESS) {
            return true;
        }
        if (msg == SSH_MSG_USERAUTH_FAILURE) {
            ByteReader fr(resp.data() + 1, resp.size() - 1);
            std::string methods;
            fr.read_string(methods);
            if (!tried_kbd && methods.find("keyboard-interactive") != std::string::npos) {
                tried_kbd = true;
                ByteWriter kbd;
                kbd.write_u8(SSH_MSG_USERAUTH_REQUEST);
                kbd.write_string(user);
                kbd.write_string("ssh-connection");
                kbd.write_string("keyboard-interactive");
                kbd.write_string(""); // language tag
                kbd.write_string(""); // submethods
                if (!send_packet(kbd.buf)) {
                    out_error = "Failed to send keyboard-interactive auth request";
                    return false;
                }
                continue;
            }
            out_error = "Authentication failed (allowed methods: " + methods + ")";
            return false;
        }
        if (msg == SSH_MSG_USERAUTH_INFO_REQUEST) {
            ByteReader ir(resp.data() + 1, resp.size() - 1);
            std::string name, instr, lang;
            uint32_t num_prompts = 0;
            if (!ir.read_string(name) || !ir.read_string(instr) || !ir.read_string(lang) || !ir.read_u32(num_prompts)) {
                out_error = "Malformed USERAUTH_INFO_REQUEST";
                return false;
            }
            ByteWriter iresp;
            iresp.write_u8(SSH_MSG_USERAUTH_INFO_RESPONSE);
            iresp.write_u32(num_prompts);
            for (uint32_t i = 0; i < num_prompts; ++i) {
                iresp.write_string(password);
            }
            if (!send_packet(iresp.buf)) {
                out_error = "Failed to send USERAUTH_INFO_RESPONSE";
                return false;
            }
            continue;
        }
        out_error = "Unexpected packet during authentication";
        return false;
    }
}

bool SshClient::connect_and_auth(const std::string& host, int port,
                                 const std::string& user, const std::string& password,
                                 std::string& out_error) {
    disconnect();

    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    addrinfo* result = nullptr;
    std::string port_str = std::to_string(port);
    if (getaddrinfo(host.c_str(), port_str.c_str(), &hints, &result) != 0 || !result) {
        out_error = "DNS resolution failed for " + host;
        return false;
    }

    SOCKET s = INVALID_SOCKET;
    for (addrinfo* ptr = result; ptr != nullptr; ptr = ptr->ai_next) {
        s = socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol);
        if (s == INVALID_SOCKET) continue;

        DWORD timeout_ms = 10000;
        setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
        setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));

        if (connect(s, ptr->ai_addr, static_cast<int>(ptr->ai_addrlen)) == 0) {
            break;
        }
        closesocket(s);
        s = INVALID_SOCKET;
    }
    freeaddrinfo(result);

    if (s == INVALID_SOCKET) {
        out_error = "TCP connection failed to " + host + ":" + port_str;
        return false;
    }

    // Remove blocking timeouts for long-lived tunnel session; enable TCP_NODELAY
    DWORD zero_timeout = 0;
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&zero_timeout), sizeof(zero_timeout));
    setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, reinterpret_cast<const char*>(&zero_timeout), sizeof(zero_timeout));
    BOOL nodelay = TRUE;
    setsockopt(s, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));

    sock_ = s;
    send_seq_ = 0;
    recv_seq_ = 0;
    send_encrypted_ = false;
    recv_encrypted_ = false;
    session_id_.clear();
    missed_keepalives_ = 0;

    std::string v_c, v_s;
    if (!perform_version_exchange(v_c, v_s, out_error) ||
        !perform_kex(v_c, v_s, out_error) ||
        !perform_auth(user, password, out_error)) {
        closesocket(sock_);
        sock_ = INVALID_SOCKET;
        return false;
    }

    connected_.store(true);
    return true;
}

void SshClient::start_session_threads() {
    stop_threads_.store(false);
    reader_thread_ = std::thread(&SshClient::reader_loop, this);
    keepalive_thread_ = std::thread(&SshClient::keepalive_loop, this);
}

void SshClient::disconnect() {
    connected_.store(false);
    stop_threads_.store(true);

    if (sock_ != INVALID_SOCKET) {
        shutdown(sock_, SD_BOTH);
        closesocket(sock_);
        sock_ = INVALID_SOCKET;
    }

    {
        std::lock_guard<std::mutex> lock(channels_mutex_);
        for (auto& kv : channels_) {
            auto& ch = kv.second;
            std::lock_guard<std::mutex> clock(ch->mu);
            ch->closed = true;
            ch->open_failed = true;
            if (ch->client_sock != INVALID_SOCKET) {
                shutdown(ch->client_sock, SD_BOTH);
                closesocket(ch->client_sock);
                ch->client_sock = INVALID_SOCKET;
            }
            ch->cv.notify_all();
        }
        channels_.clear();
    }

    if (reader_thread_.joinable()) reader_thread_.join();
    if (keepalive_thread_.joinable()) keepalive_thread_.join();
}

void SshClient::keepalive_loop() {
    while (!stop_threads_.load() && connected_.load()) {
        for (int i = 0; i < 150 && !stop_threads_.load() && connected_.load(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if (stop_threads_.load() || !connected_.load()) break;

        if (missed_keepalives_.fetch_add(1) >= 3) {
            connected_.store(false);
            if (sock_ != INVALID_SOCKET) {
                shutdown(sock_, SD_BOTH);
                closesocket(sock_);
                sock_ = INVALID_SOCKET;
            }
            break;
        }

        ByteWriter ka;
        ka.write_u8(SSH_MSG_GLOBAL_REQUEST);
        ka.write_string("keepalive@openssh.com");
        ka.write_u8(1); // want_reply = true
        if (!send_packet(ka.buf)) {
            connected_.store(false);
            break;
        }
    }
}

void SshClient::reader_loop() {
    std::vector<uint8_t> payload;
    while (!stop_threads_.load() && connected_.load()) {
        if (!recv_packet(payload)) {
            break;
        }
        if (!payload.empty()) {
            handle_packet(payload);
        }
    }
    connected_.store(false);

    std::lock_guard<std::mutex> lock(channels_mutex_);
    for (auto& kv : channels_) {
        auto& ch = kv.second;
        std::lock_guard<std::mutex> clock(ch->mu);
        ch->closed = true;
        ch->open_failed = true;
        if (ch->client_sock != INVALID_SOCKET) {
            shutdown(ch->client_sock, SD_BOTH);
        }
        ch->cv.notify_all();
    }
}

void SshClient::handle_packet(const std::vector<uint8_t>& payload) {
    uint8_t msg = payload[0];
    ByteReader r(payload.data() + 1, payload.size() - 1);

    switch (msg) {
        case SSH_MSG_DISCONNECT: {
            connected_.store(false);
            break;
        }
        case SSH_MSG_GLOBAL_REQUEST: {
            std::string req_name;
            uint8_t want_reply = 0;
            if (r.read_string(req_name) && r.read_u8(want_reply) && want_reply) {
                send_packet({ SSH_MSG_REQUEST_FAILURE });
            }
            break;
        }
        case SSH_MSG_REQUEST_SUCCESS:
        case SSH_MSG_REQUEST_FAILURE: {
            missed_keepalives_.store(0);
            break;
        }
        case SSH_MSG_CHANNEL_OPEN_CONFIRMATION: {
            uint32_t recipient = 0, sender = 0, init_win = 0, max_pkt = 0;
            if (!r.read_u32(recipient) || !r.read_u32(sender) ||
                !r.read_u32(init_win) || !r.read_u32(max_pkt)) break;

            std::shared_ptr<SshChannel> ch;
            {
                std::lock_guard<std::mutex> lock(channels_mutex_);
                auto it = channels_.find(recipient);
                if (it != channels_.end()) ch = it->second;
            }
            if (ch) {
                std::lock_guard<std::mutex> clock(ch->mu);
                ch->remote_id = sender;
                ch->remote_window = init_win;
                ch->remote_max_packet = (max_pkt > 0 && max_pkt < MAX_PACKET_SIZE) ? max_pkt : MAX_PACKET_SIZE;
                ch->open_confirmed = true;
                ch->cv.notify_all();
            }
            break;
        }
        case SSH_MSG_CHANNEL_OPEN_FAILURE: {
            uint32_t recipient = 0;
            if (!r.read_u32(recipient)) break;
            std::shared_ptr<SshChannel> ch;
            {
                std::lock_guard<std::mutex> lock(channels_mutex_);
                auto it = channels_.find(recipient);
                if (it != channels_.end()) {
                    ch = it->second;
                    channels_.erase(it);
                }
            }
            if (ch) {
                std::lock_guard<std::mutex> clock(ch->mu);
                ch->open_failed = true;
                ch->closed = true;
                ch->cv.notify_all();
            }
            break;
        }
        case SSH_MSG_CHANNEL_WINDOW_ADJUST: {
            uint32_t recipient = 0, add_bytes = 0;
            if (!r.read_u32(recipient) || !r.read_u32(add_bytes)) break;
            std::shared_ptr<SshChannel> ch;
            {
                std::lock_guard<std::mutex> lock(channels_mutex_);
                auto it = channels_.find(recipient);
                if (it != channels_.end()) ch = it->second;
            }
            if (ch) {
                std::lock_guard<std::mutex> clock(ch->mu);
                ch->remote_window += add_bytes;
                ch->cv.notify_all();
            }
            break;
        }
        case SSH_MSG_CHANNEL_DATA: {
            uint32_t recipient = 0;
            std::vector<uint8_t> data;
            if (!r.read_u32(recipient) || !r.read_bytes_vec(data)) break;

            std::shared_ptr<SshChannel> ch;
            {
                std::lock_guard<std::mutex> lock(channels_mutex_);
                auto it = channels_.find(recipient);
                if (it != channels_.end()) ch = it->second;
            }
            if (!ch) break;

            SOCKET cs = INVALID_SOCKET;
            uint32_t win_adjust = 0;
            {
                std::lock_guard<std::mutex> clock(ch->mu);
                if (ch->closed || ch->client_sock == INVALID_SOCKET) break;
                cs = ch->client_sock;
                if (ch->local_window >= data.size()) {
                    ch->local_window -= static_cast<uint32_t>(data.size());
                } else {
                    ch->local_window = 0;
                }
                if (ch->local_window < INITIAL_WINDOW_SIZE / 2) {
                    win_adjust = INITIAL_WINDOW_SIZE - ch->local_window;
                    ch->local_window += win_adjust;
                }
            }

            if (!data.empty() && !send_all_socket(cs, data.data(), data.size())) {
                close_channel(ch);
                break;
            }

            if (win_adjust > 0) {
                ByteWriter wa;
                wa.write_u8(SSH_MSG_CHANNEL_WINDOW_ADJUST);
                wa.write_u32(ch->remote_id);
                wa.write_u32(win_adjust);
                send_packet(wa.buf);
            }
            break;
        }
        case SSH_MSG_CHANNEL_EOF: {
            uint32_t recipient = 0;
            if (!r.read_u32(recipient)) break;
            std::shared_ptr<SshChannel> ch;
            {
                std::lock_guard<std::mutex> lock(channels_mutex_);
                auto it = channels_.find(recipient);
                if (it != channels_.end()) ch = it->second;
            }
            if (ch) {
                std::lock_guard<std::mutex> clock(ch->mu);
                if (ch->client_sock != INVALID_SOCKET) {
                    shutdown(ch->client_sock, SD_SEND);
                }
            }
            break;
        }
        case SSH_MSG_CHANNEL_CLOSE: {
            uint32_t recipient = 0;
            if (!r.read_u32(recipient)) break;
            std::shared_ptr<SshChannel> ch;
            {
                std::lock_guard<std::mutex> lock(channels_mutex_);
                auto it = channels_.find(recipient);
                if (it != channels_.end()) {
                    ch = it->second;
                    channels_.erase(it);
                }
            }
            if (ch) {
                bool need_close_reply = false;
                uint32_t rid = 0;
                {
                    std::lock_guard<std::mutex> clock(ch->mu);
                    ch->closed = true;
                    if (!ch->close_sent && ch->open_confirmed) {
                        ch->close_sent = true;
                        need_close_reply = true;
                        rid = ch->remote_id;
                    }
                    if (ch->client_sock != INVALID_SOCKET) {
                        shutdown(ch->client_sock, SD_BOTH);
                    }
                    ch->cv.notify_all();
                }
                if (need_close_reply) {
                    ByteWriter cw;
                    cw.write_u8(SSH_MSG_CHANNEL_CLOSE);
                    cw.write_u32(rid);
                    send_packet(cw.buf);
                }
            }
            break;
        }
        default:
            break;
    }
}

std::shared_ptr<SshChannel> SshClient::open_direct_tcpip(
    const std::string& dest_host, uint16_t dest_port,
    const std::string& orig_host, uint16_t orig_port,
    SOCKET client_sock) {
    if (!connected_.load()) return nullptr;

    auto ch = std::make_shared<SshChannel>();
    ch->client_sock = client_sock;
    ch->local_window = INITIAL_WINDOW_SIZE;

    {
        std::lock_guard<std::mutex> lock(channels_mutex_);
        ch->local_id = next_channel_id_++;
        channels_[ch->local_id] = ch;
    }

    ByteWriter w;
    w.write_u8(SSH_MSG_CHANNEL_OPEN);
    w.write_string("direct-tcpip");
    w.write_u32(ch->local_id);
    w.write_u32(INITIAL_WINDOW_SIZE);
    w.write_u32(MAX_PACKET_SIZE);
    w.write_string(dest_host);
    w.write_u32(dest_port);
    w.write_string(orig_host);
    w.write_u32(orig_port);

    if (!send_packet(w.buf)) {
        std::lock_guard<std::mutex> lock(channels_mutex_);
        channels_.erase(ch->local_id);
        return nullptr;
    }

    std::unique_lock<std::mutex> clock(ch->mu);
    bool ok = ch->cv.wait_for(clock, std::chrono::seconds(15), [&]() {
        return ch->open_confirmed || ch->open_failed || ch->closed || !connected_.load();
    });

    if (!ok || !ch->open_confirmed || ch->open_failed || ch->closed) {
        clock.unlock();
        std::lock_guard<std::mutex> lock(channels_mutex_);
        channels_.erase(ch->local_id);
        return nullptr;
    }
    return ch;
}

bool SshClient::send_channel_data(const std::shared_ptr<SshChannel>& ch, const uint8_t* data, size_t len) {
    size_t offset = 0;
    while (offset < len) {
        uint32_t chunk = 0;
        uint32_t rid = 0;
        {
            std::unique_lock<std::mutex> clock(ch->mu);
            ch->cv.wait(clock, [&]() {
                return ch->remote_window > 0 || ch->closed || !connected_.load();
            });
            if (ch->closed || !connected_.load()) return false;

            size_t avail = std::min<size_t>(len - offset, ch->remote_window);
            avail = std::min<size_t>(avail, ch->remote_max_packet);
            chunk = static_cast<uint32_t>(avail);
            ch->remote_window -= chunk;
            rid = ch->remote_id;
        }

        ByteWriter w;
        w.write_u8(SSH_MSG_CHANNEL_DATA);
        w.write_u32(rid);
        w.write_string(data + offset, chunk);
        if (!send_packet(w.buf)) return false;
        offset += chunk;
    }
    return true;
}

void SshClient::send_channel_eof(const std::shared_ptr<SshChannel>& ch) {
    uint32_t rid = 0;
    {
        std::lock_guard<std::mutex> clock(ch->mu);
        if (ch->eof_sent || ch->closed || !ch->open_confirmed) return;
        ch->eof_sent = true;
        rid = ch->remote_id;
    }
    ByteWriter w;
    w.write_u8(SSH_MSG_CHANNEL_EOF);
    w.write_u32(rid);
    send_packet(w.buf);
}

void SshClient::close_channel(const std::shared_ptr<SshChannel>& ch) {
    bool need_send = false;
    uint32_t rid = 0;
    {
        std::lock_guard<std::mutex> clock(ch->mu);
        ch->closed = true;
        if (!ch->close_sent && ch->open_confirmed) {
            ch->close_sent = true;
            need_send = true;
            rid = ch->remote_id;
        }
        ch->cv.notify_all();
    }
    if (need_send) {
        ByteWriter w;
        w.write_u8(SSH_MSG_CHANNEL_CLOSE);
        w.write_u32(rid);
        send_packet(w.buf);
    }
    {
        std::lock_guard<std::mutex> lock(channels_mutex_);
        channels_.erase(ch->local_id);
    }
}

} // namespace ssh_tunnel
