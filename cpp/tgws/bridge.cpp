#include "bridge.h"
#include <thread>
#include <vector>
#include <iostream>

namespace tgws {

Stats g_stats;

static bool send_all_socket(SOCKET s, const uint8_t* buf, size_t len) {
    size_t total = 0;
    while (total < len) {
        int r = ::send(s, reinterpret_cast<const char*>(buf) + total, static_cast<int>(len - total), 0);
        if (r <= 0) return false;
        total += r;
    }
    return true;
}

void bridge_ws_reencrypt(SOCKET client_sock,
                         bool is_fake_tls,
                         RawWebSocket& ws,
                         CryptoCtx& ctx,
                         MsgSplitter* splitter,
                         const std::string& label) {
    std::atomic<bool> closed(false);
    FakeTlsStream fake_tls(client_sock);

    // Thread 1: Client -> WS
    std::thread t_up([&]() {
        std::vector<uint8_t> in_buf(65536);
        std::vector<uint8_t> plain_buf(65536);

        while (!closed && ws.is_open()) {
            int n = 0;
            if (is_fake_tls) {
                n = fake_tls.recv(in_buf.data(), in_buf.size());
            } else {
                n = ::recv(client_sock, reinterpret_cast<char*>(in_buf.data()), static_cast<int>(in_buf.size()), 0);
            }
            if (n <= 0) break;

            g_stats.bytes_up += n;

            // Decrypt client ciphertext to plaintext
            ctx.clt_dec.process(in_buf.data(), plain_buf.data(), n);

            // Re-encrypt plaintext for Telegram upstream
            ctx.tg_enc.process(plain_buf.data(), in_buf.data(), n);

            if (splitter) {
                auto parts = splitter->split(in_buf.data(), plain_buf.data(), n);
                for (const auto& part : parts) {
                    if (!ws.send(part.data(), part.size())) {
                        closed = true;
                        break;
                    }
                }
            } else {
                if (!ws.send(in_buf.data(), n)) {
                    closed = true;
                    break;
                }
            }
        }
        if (splitter) {
            auto tail = splitter->flush();
            if (!tail.empty()) {
                ws.send(tail.data(), tail.size());
            }
        }
        closed = true;
        ws.close();
        shutdown(client_sock, SD_BOTH);
    });

    // Thread 2: WS -> Client
    std::thread t_down([&]() {
        std::vector<uint8_t> payload;
        std::vector<uint8_t> plain;

        while (!closed && ws.is_open()) {
            if (!ws.recv(payload)) break;
            size_t n = payload.size();
            if (n == 0) continue;

            g_stats.bytes_down += n;

            plain.resize(n);
            // Decrypt Telegram upstream ciphertext
            ctx.tg_dec.process(payload.data(), plain.data(), n);

            // Re-encrypt for client
            ctx.clt_enc.process(plain.data(), payload.data(), n);

            bool ok = false;
            if (is_fake_tls) {
                ok = fake_tls.send_all(payload.data(), n);
            } else {
                ok = send_all_socket(client_sock, payload.data(), n);
            }
            if (!ok) break;
        }
        closed = true;
        ws.close();
        shutdown(client_sock, SD_BOTH);
    });

    if (t_up.joinable()) t_up.join();
    if (t_down.joinable()) t_down.join();
}

void bridge_tcp_reencrypt(SOCKET client_sock,
                          bool is_fake_tls,
                          SOCKET remote_sock,
                          CryptoCtx& ctx,
                          const std::string& label) {
    std::atomic<bool> closed(false);
    FakeTlsStream fake_tls(client_sock);

    std::thread t_up([&]() {
        std::vector<uint8_t> in_buf(65536);
        std::vector<uint8_t> plain_buf(65536);

        while (!closed) {
            int n = 0;
            if (is_fake_tls) {
                n = fake_tls.recv(in_buf.data(), in_buf.size());
            } else {
                n = ::recv(client_sock, reinterpret_cast<char*>(in_buf.data()), static_cast<int>(in_buf.size()), 0);
            }
            if (n <= 0) break;

            g_stats.bytes_up += n;
            ctx.clt_dec.process(in_buf.data(), plain_buf.data(), n);
            ctx.tg_enc.process(plain_buf.data(), in_buf.data(), n);

            if (!send_all_socket(remote_sock, in_buf.data(), n)) break;
        }
        closed = true;
        shutdown(client_sock, SD_BOTH);
        shutdown(remote_sock, SD_BOTH);
    });

    std::thread t_down([&]() {
        std::vector<uint8_t> in_buf(65536);
        std::vector<uint8_t> plain_buf(65536);

        while (!closed) {
            int n = ::recv(remote_sock, reinterpret_cast<char*>(in_buf.data()), static_cast<int>(in_buf.size()), 0);
            if (n <= 0) break;

            g_stats.bytes_down += n;
            ctx.tg_dec.process(in_buf.data(), plain_buf.data(), n);
            ctx.clt_enc.process(plain_buf.data(), in_buf.data(), n);

            bool ok = false;
            if (is_fake_tls) {
                ok = fake_tls.send_all(in_buf.data(), n);
            } else {
                ok = send_all_socket(client_sock, in_buf.data(), n);
            }
            if (!ok) break;
        }
        closed = true;
        shutdown(client_sock, SD_BOTH);
        shutdown(remote_sock, SD_BOTH);
    });

    if (t_up.joinable()) t_up.join();
    if (t_down.joinable()) t_down.join();
}

} // namespace tgws
