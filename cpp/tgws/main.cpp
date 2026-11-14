#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <atomic>
#include <chrono>

#include "crypto.h"
#include "tls_socket.h"
#include "websocket.h"
#include "fake_tls.h"
#include "protocol.h"
#include "config.h"
#include "pool.h"
#include "fallbacks.h"
#include "bridge.h"

#pragma comment(lib, "ws2_32.lib")

namespace tgws {

static std::atomic<bool> g_server_running(true);

static BOOL WINAPI ConsoleHandler(DWORD ctrlType) {
    if (ctrlType == CTRL_C_EVENT || ctrlType == CTRL_CLOSE_EVENT || ctrlType == CTRL_BREAK_EVENT) {
        g_server_running = false;
        return TRUE;
    }
    return FALSE;
}

static void handle_client(SOCKET client_sock,
                          sockaddr_in client_addr,
                          const ProxyConfig& cfg,
                          const uint8_t secret_bytes[16],
                          WsPool& ws_pool,
                          FallbackManager& fallback_mgr) {
    g_stats.connections_total++;
    g_stats.connections_active++;

    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &client_addr.sin_addr, ip_str, INET_ADDRSTRLEN);
    std::string label = std::string(ip_str) + ":" + std::to_string(ntohs(client_addr.sin_port));

    // Socket optimization
    int nodelay = 1;
    setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));
    int buf_sz = cfg.buffer_size;
    setsockopt(client_sock, SOL_SOCKET, SO_RCVBUF, reinterpret_cast<const char*>(&buf_sz), sizeof(buf_sz));
    setsockopt(client_sock, SOL_SOCKET, SO_SNDBUF, reinterpret_cast<const char*>(&buf_sz), sizeof(buf_sz));

    DWORD timeout_ms = 10000;
    setsockopt(client_sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));

    bool is_fake_tls = false;
    uint8_t handshake[64];
    size_t handshake_len = 0;

    // Check first byte for Fake TLS handshake
    uint8_t first_byte = 0;
    int r = ::recv(client_sock, reinterpret_cast<char*>(&first_byte), 1, 0);
    if (r <= 0) {
        closesocket(client_sock);
        g_stats.connections_active--;
        return;
    }

    if (!cfg.fake_tls_domain.empty() && first_byte == TLS_RECORD_HANDSHAKE) {
        // Read remaining TLS record header (4 bytes: version, length)
        uint8_t hdr_rest[4];
        if (::recv(client_sock, reinterpret_cast<char*>(hdr_rest), 4, 0) != 4) {
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }

        uint16_t record_len = (static_cast<uint16_t>(hdr_rest[2]) << 8) | hdr_rest[3];
        std::vector<uint8_t> client_hello(5 + record_len);
        client_hello[0] = first_byte;
        std::memcpy(client_hello.data() + 1, hdr_rest, 4);

        size_t b_read = 0;
        while (b_read < record_len) {
            int n = ::recv(client_sock, reinterpret_cast<char*>(client_hello.data()) + 5 + b_read,
                           static_cast<int>(record_len - b_read), 0);
            if (n <= 0) break;
            b_read += n;
        }

        if (b_read != record_len) {
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }

        FakeTlsResult tls_res = verify_client_hello(client_hello.data(), client_hello.size(), secret_bytes);
        if (!tls_res.valid) {
            if (cfg.verbose) {
                std::cout << "[" << label << "] Fake TLS verify failed -> proxying to masking domain: "
                          << cfg.fake_tls_domain << std::endl;
            }
            proxy_to_masking_domain(client_sock, cfg.fake_tls_domain, client_hello.data(), client_hello.size());
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }

        // Build & send ServerHello response
        auto server_hello = build_server_hello(secret_bytes, tls_res.client_random.data(), tls_res.session_id.data());
        ::send(client_sock, reinterpret_cast<const char*>(server_hello.data()), static_cast<int>(server_hello.size()), 0);

        is_fake_tls = true;
        FakeTlsStream tls_stream(client_sock);
        if (!tls_stream.recv_exact(handshake, 64)) {
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }
    } else if (!cfg.fake_tls_domain.empty() && first_byte != TLS_RECORD_HANDSHAKE) {
        // Non-TLS byte with Fake TLS enabled -> HTTP 301 Redirect to masking domain
        std::string redir = "HTTP/1.1 301 Moved Permanently\r\n"
                            "Location: https://" + cfg.fake_tls_domain + "/\r\n"
                            "Content-Length: 0\r\n"
                            "Connection: close\r\n\r\n";
        ::send(client_sock, redir.data(), static_cast<int>(redir.size()), 0);
        closesocket(client_sock);
        g_stats.connections_active--;
        return;
    } else {
        // Plain obfuscated2 handshake
        handshake[0] = first_byte;
        size_t h_read = 1;
        while (h_read < 64) {
            int n = ::recv(client_sock, reinterpret_cast<char*>(handshake) + h_read, static_cast<int>(64 - h_read), 0);
            if (n <= 0) break;
            h_read += n;
        }
        if (h_read != 64) {
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }
    }

    ClientHandshake client_hs{};
    if (!parse_client_handshake(handshake, secret_bytes, client_hs)) {
        if (cfg.verbose) {
            std::cout << "[" << label << "] Bad handshake (invalid secret or unknown protocol)" << std::endl;
        }
        closesocket(client_sock);
        g_stats.connections_active--;
        return;
    }

    int dc = client_hs.dc_id;
    bool is_test_dc = cfg.force_test_dc || (dc >= 10000);
    if (dc >= 10000) dc -= 10000;

    int16_t dc_idx = client_hs.is_media ? -static_cast<int16_t>(dc) : static_cast<int16_t>(dc);
    auto relay_init = generate_relay_init(client_hs.proto_tag, dc_idx);
    auto crypto_ctx = build_crypto_ctx(client_hs.client_prekey_and_iv, secret_bytes, relay_init.data());

    MsgSplitter splitter(client_hs.proto_tag);

    if (cfg.verbose) {
        std::cout << "[" << label << "] Handshake OK: DC" << dc
                  << (client_hs.is_media ? " media" : "")
                  << " proto=0x" << std::hex << client_hs.proto_tag << std::dec << std::endl;
    }

    // Reset socket timeout to 0 (infinite) for streaming session
    timeout_ms = 0;
    setsockopt(client_sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));

    // Try pre-warmed connection from pool
    auto ws = ws_pool.get(dc, client_hs.is_media, is_test_dc);
    if (ws) {
        g_stats.pool_hits++;
        if (cfg.verbose) {
            std::cout << "[" << label << "] WS Pool hit for DC" << dc << std::endl;
        }
        if (ws->send(relay_init.data(), relay_init.size())) {
            bridge_ws_reencrypt(client_sock, is_fake_tls, *ws, crypto_ctx, &splitter, label);
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }
    }

    // Direct WS connect
    std::string target_ip;
    auto it = cfg.dc_redirects.find(dc);
    if (it != cfg.dc_redirects.end() && !it->second.empty()) {
        target_ip = it->second;
    } else {
        target_ip = get_default_dc_ip(dc, is_test_dc);
    }

    std::string domain = get_ws_domain(dc, client_hs.is_media);
    std::string path = is_test_dc ? "/apiws_test" : "/apiws";

    RawWebSocket direct_ws;
    if (direct_ws.connect(target_ip, 443, domain, path, domain, true, 8)) {
        if (cfg.verbose) {
            std::cout << "[" << label << "] Direct WS connected to DC" << dc << " (" << target_ip << ")" << std::endl;
        }
        if (direct_ws.send(relay_init.data(), relay_init.size())) {
            bridge_ws_reencrypt(client_sock, is_fake_tls, direct_ws, crypto_ctx, &splitter, label);
            closesocket(client_sock);
            g_stats.connections_active--;
            return;
        }
    }

    // Fallbacks
    g_stats.pool_misses++;
    if (cfg.verbose) {
        std::cout << "[" << label << "] Direct WS unavailable -> trying fallbacks..." << std::endl;
    }

    fallback_mgr.execute_fallback(client_sock, is_fake_tls, relay_init, dc, is_test_dc, client_hs.is_media,
                                  crypto_ctx, &splitter, client_hs.proto_tag, label);

    closesocket(client_sock);
    g_stats.connections_active--;
}

} // namespace tgws

int main(int argc, char* argv[]) {
    using namespace tgws;

    ProxyConfig cfg;
    load_config(argc, argv, cfg);

    uint8_t secret_bytes[16];
    if (!hex_decode(cfg.secret, secret_bytes, 16)) {
        std::cerr << "Invalid 32-hex secret: " << cfg.secret << std::endl;
        return 1;
    }

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "WSAStartup failed" << std::endl;
        return 1;
    }

    SOCKET listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock == INVALID_SOCKET) {
        std::cerr << "Failed to create socket: " << WSAGetLastError() << std::endl;
        return 1;
    }

    int reuse = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&reuse), sizeof(reuse));

    sockaddr_in bind_addr{};
    bind_addr.sin_family = AF_INET;
    bind_addr.sin_port = htons(static_cast<u_short>(cfg.port));
    inet_pton(AF_INET, cfg.host.c_str(), &bind_addr.sin_addr);

    if (bind(listen_sock, reinterpret_cast<sockaddr*>(&bind_addr), sizeof(bind_addr)) == SOCKET_ERROR) {
        std::cerr << "Failed to bind to " << cfg.host << ":" << cfg.port << " (Error " << WSAGetLastError() << ")" << std::endl;
        closesocket(listen_sock);
        return 1;
    }

    if (listen(listen_sock, SOMAXCONN) == SOCKET_ERROR) {
        std::cerr << "Failed to listen: " << WSAGetLastError() << std::endl;
        closesocket(listen_sock);
        return 1;
    }

    SetConsoleCtrlHandler(ConsoleHandler, TRUE);

    WsPool ws_pool;
    ws_pool.init(&cfg);
    ws_pool.warmup();

    FallbackManager fallback_mgr(cfg);

    std::string link_host = (cfg.host == "0.0.0.0") ? "127.0.0.1" : cfg.host;
    std::string dd_link = "tg://proxy?server=" + link_host + "&port=" + std::to_string(cfg.port) + "&secret=dd" + cfg.secret;
    std::string ee_link;
    if (!cfg.fake_tls_domain.empty()) {
        ee_link = "tg://proxy?server=" + link_host + "&port=" + std::to_string(cfg.port) + "&secret=ee" + cfg.secret + hex_encode(cfg.fake_tls_domain.data(), cfg.fake_tls_domain.size());
    }

    std::cout << "============================================================" << std::endl;
    std::cout << "  Telegram MTProto WS Bridge Proxy (C++ Native)" << std::endl;
    std::cout << "  Listening on:   " << cfg.host << ":" << cfg.port << std::endl;
    std::cout << "  Secret:         " << cfg.secret << std::endl;
    if (!cfg.fake_tls_domain.empty()) {
        std::cout << "  Fake TLS:       " << cfg.fake_tls_domain << std::endl;
    }
    std::cout << "  Target DC IPs:" << std::endl;
    for (const auto& pair : cfg.dc_redirects) {
        std::cout << "    DC" << pair.first << ": " << pair.second << std::endl;
    }
    std::cout << "  CF Fallback:    " << (cfg.fallback_cfproxy ? "enabled" : "disabled") << std::endl;
    std::cout << "============================================================" << std::endl;
    std::cout << "  Connect Link:" << std::endl;
    std::cout << "    " << (!ee_link.empty() ? ee_link : dd_link) << std::endl;
    std::cout << "============================================================" << std::endl;

    while (g_server_running) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(listen_sock, &read_fds);

        timeval tv{ 1, 0 };
        int sel = select(0, &read_fds, nullptr, nullptr, &tv);
        if (sel <= 0) continue;

        sockaddr_in client_addr{};
        int addr_len = sizeof(client_addr);
        SOCKET client_sock = accept(listen_sock, reinterpret_cast<sockaddr*>(&client_addr), &addr_len);
        if (client_sock == INVALID_SOCKET) continue;

        std::thread([=, &cfg, &ws_pool, &fallback_mgr]() {
            handle_client(client_sock, client_addr, cfg, secret_bytes, ws_pool, fallback_mgr);
        }).detach();
    }

    std::cout << "\nStopping TGWS server..." << std::endl;
    closesocket(listen_sock);
    ws_pool.stop();
    WSACleanup();
    return 0;
}
