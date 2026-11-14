#include "fallbacks.h"
#include "bridge.h"
#include <iostream>
#include <ws2tcpip.h>

namespace tgws {

FallbackManager::FallbackManager(const ProxyConfig& cfg) : config(cfg) {
    if (!config.cfproxy_user_domains.empty()) {
        cf_domains = config.cfproxy_user_domains;
    } else {
        cf_domains = get_default_cf_domains();
    }
}

bool FallbackManager::execute_fallback(SOCKET client_sock,
                                      bool is_fake_tls,
                                      const std::vector<uint8_t>& relay_init,
                                      int dc, bool is_test_dc, bool is_media,
                                      CryptoCtx& ctx, MsgSplitter* splitter,
                                      uint32_t proto_tag,
                                      const std::string& label) {
    std::string fallback_dst = get_default_dc_ip(dc, is_test_dc);

    // 1. Cloudflare Worker fallback
    if (!config.cfproxy_worker_domains.empty() && !fallback_dst.empty()) {
        if (try_cf_worker(client_sock, is_fake_tls, relay_init, dc, is_media, fallback_dst, ctx, splitter, label)) {
            return true;
        }
    }

    // 2. Cloudflare Proxy fallback
    if (config.fallback_cfproxy && !is_test_dc) {
        if (try_cf_proxy(client_sock, is_fake_tls, relay_init, dc, is_media, ctx, splitter, label)) {
            return true;
        }
    }

    // 3. Tor SOCKS5 fallback
    if (!fallback_dst.empty()) {
        if (try_tor_socks5(client_sock, is_fake_tls, relay_init, dc, fallback_dst, 443, ctx, label)) {
            return true;
        }
    }

    // 4. Direct TCP fallback
    if (!fallback_dst.empty()) {
        if (try_direct_tcp(client_sock, is_fake_tls, relay_init, dc, fallback_dst, 443, ctx, label)) {
            return true;
        }
    }

    return false;
}

bool FallbackManager::try_cf_worker(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                                    int dc, bool is_media, const std::string& dst, CryptoCtx& ctx, MsgSplitter* splitter,
                                    const std::string& label) {
    for (const auto& worker : config.cfproxy_worker_domains) {
        std::string path = "/apiws?dst=" + dst + "&dc=" + std::to_string(dc);
        RawWebSocket ws;
        int port = config.disable_secure ? 80 : 443;
        bool secure = !config.disable_secure;

        if (ws.connect(worker, port, worker, path, worker, secure, 8)) {
            if (config.verbose) {
                std::cout << "[" << label << "] Connected via CF worker: " << worker << std::endl;
            }
            if (ws.send(relay_init.data(), relay_init.size())) {
                bridge_ws_reencrypt(client_sock, is_fake_tls, ws, ctx, splitter, label);
                return true;
            }
        }
    }
    return false;
}

bool FallbackManager::try_cf_proxy(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                                   int dc, bool is_media, CryptoCtx& ctx, MsgSplitter* splitter,
                                   const std::string& label) {
    int port = config.disable_secure ? 80 : 443;
    bool secure = !config.disable_secure;

    for (const auto& base_dom : cf_domains) {
        std::string domain = "kws" + std::to_string(dc) + "." + base_dom;
        RawWebSocket ws;

        if (ws.connect(domain, port, domain, "/apiws", domain, secure, 6)) {
            if (config.verbose) {
                std::cout << "[" << label << "] Connected via CF proxy: " << domain << std::endl;
            }
            if (ws.send(relay_init.data(), relay_init.size())) {
                bridge_ws_reencrypt(client_sock, is_fake_tls, ws, ctx, splitter, label);
                return true;
            }
        }
    }
    return false;
}

bool FallbackManager::try_tor_socks5(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                                     int dc, const std::string& dst, int port, CryptoCtx& ctx,
                                     const std::string& label) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) return false;

    sockaddr_in tor_addr{};
    tor_addr.sin_family = AF_INET;
    tor_addr.sin_port = htons(9853); // Default Tor SOCKS5 port in ToInet
    inet_pton(AF_INET, "127.0.0.1", &tor_addr.sin_addr);

    if (::connect(s, reinterpret_cast<sockaddr*>(&tor_addr), sizeof(tor_addr)) != 0) {
        closesocket(s);
        return false;
    }

    // SOCKS5 Handshake
    uint8_t greeting[] = { 0x05, 0x01, 0x00 };
    if (::send(s, reinterpret_cast<char*>(greeting), 3, 0) != 3) {
        closesocket(s);
        return false;
    }

    uint8_t g_resp[2];
    if (::recv(s, reinterpret_cast<char*>(g_resp), 2, 0) != 2 || g_resp[0] != 0x05 || g_resp[1] != 0x00) {
        closesocket(s);
        return false;
    }

    // Connect request
    std::vector<uint8_t> req = { 0x05, 0x01, 0x00 };
    in_addr dst_in{};
    if (inet_pton(AF_INET, dst.c_str(), &dst_in) == 1) {
        req.push_back(0x01); // IPv4
        const uint8_t* p = reinterpret_cast<const uint8_t*>(&dst_in);
        req.insert(req.end(), p, p + 4);
    } else {
        req.push_back(0x03); // Domain name
        req.push_back(static_cast<uint8_t>(dst.size()));
        req.insert(req.end(), dst.begin(), dst.end());
    }
    uint16_t p16 = htons(static_cast<uint16_t>(port));
    req.push_back(static_cast<uint8_t>(p16 & 0xFF));
    req.push_back(static_cast<uint8_t>((p16 >> 8) & 0xFF));

    if (::send(s, reinterpret_cast<char*>(req.data()), static_cast<int>(req.size()), 0) <= 0) {
        closesocket(s);
        return false;
    }

    uint8_t c_resp[10];
    int r = ::recv(s, reinterpret_cast<char*>(c_resp), 10, 0);
    if (r < 10 || c_resp[1] != 0x00) {
        closesocket(s);
        return false;
    }

    if (config.verbose) {
        std::cout << "[" << label << "] Connected via TOR fallback to " << dst << ":" << port << std::endl;
    }

    if (::send(s, reinterpret_cast<const char*>(relay_init.data()), static_cast<int>(relay_init.size()), 0) <= 0) {
        closesocket(s);
        return false;
    }

    bridge_tcp_reencrypt(client_sock, is_fake_tls, s, ctx, label);
    closesocket(s);
    return true;
}

bool FallbackManager::try_direct_tcp(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                                     int dc, const std::string& dst, int port, CryptoCtx& ctx,
                                     const std::string& label) {
    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    addrinfo* res = nullptr;
    std::string port_str = std::to_string(port);

    if (getaddrinfo(dst.c_str(), port_str.c_str(), &hints, &res) != 0) return false;

    SOCKET s = INVALID_SOCKET;
    for (addrinfo* ptr = res; ptr != nullptr; ptr = ptr->ai_next) {
        s = socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol);
        if (s == INVALID_SOCKET) continue;

        int nodelay = 1;
        setsockopt(s, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));

        if (::connect(s, ptr->ai_addr, static_cast<int>(ptr->ai_addrlen)) == 0) {
            break;
        }
        closesocket(s);
        s = INVALID_SOCKET;
    }
    freeaddrinfo(res);
    if (s == INVALID_SOCKET) return false;

    if (config.verbose) {
        std::cout << "[" << label << "] Connected via Direct TCP fallback to " << dst << ":" << port << std::endl;
    }

    if (::send(s, reinterpret_cast<const char*>(relay_init.data()), static_cast<int>(relay_init.size()), 0) <= 0) {
        closesocket(s);
        return false;
    }

    bridge_tcp_reencrypt(client_sock, is_fake_tls, s, ctx, label);
    closesocket(s);
    return true;
}

} // namespace tgws
