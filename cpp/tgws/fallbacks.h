#pragma once

#include "protocol.h"
#include "websocket.h"
#include "config.h"
#include <winsock2.h>
#include <string>
#include <vector>

namespace tgws {

class FallbackManager {
public:
    explicit FallbackManager(const ProxyConfig& cfg);

    // Attempts fallbacks in order (CF Worker -> CF Proxy -> Tor SOCKS5 -> Direct TCP)
    bool execute_fallback(SOCKET client_sock,
                          bool is_fake_tls,
                          const std::vector<uint8_t>& relay_init,
                          int dc, bool is_test_dc, bool is_media,
                          CryptoCtx& ctx, MsgSplitter* splitter,
                          uint32_t proto_tag,
                          const std::string& label);

private:
    const ProxyConfig& config;
    std::vector<std::string> cf_domains;

    bool try_cf_worker(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                       int dc, bool is_media, const std::string& dst, CryptoCtx& ctx, MsgSplitter* splitter, const std::string& label);

    bool try_cf_proxy(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                      int dc, bool is_media, CryptoCtx& ctx, MsgSplitter* splitter, const std::string& label);

    bool try_tor_socks5(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                        int dc, const std::string& dst, int port, CryptoCtx& ctx, const std::string& label);

    bool try_direct_tcp(SOCKET client_sock, bool is_fake_tls, const std::vector<uint8_t>& relay_init,
                        int dc, const std::string& dst, int port, CryptoCtx& ctx, const std::string& label);
};

} // namespace tgws
