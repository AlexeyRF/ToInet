#pragma once

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace tgws {

struct ProxyConfig {
    int port = 1480;
    std::string host = "127.0.0.1";
    std::string secret;
    std::map<int, std::string> dc_redirects;
    std::string fake_tls_domain;
    std::string fronting_sni;
    int buffer_size = 256 * 1024;
    int pool_size = 4;
    bool fallback_cfproxy = true;
    bool cfproxy_h2_media = true;
    std::vector<std::string> cfproxy_user_domains;
    std::vector<std::string> cfproxy_worker_domains;
    bool disable_secure = false;
    bool force_test_dc = false;
    bool verbose = false;
    bool proxy_protocol = false;
};

// Default Telegram DC IP addresses
const std::string& get_default_dc_ip(int dc, bool is_test);

// WebSocket hostname for DC (e.g. kws2.web.telegram.org)
std::string get_ws_domain(int dc, bool is_media);

// Decodes the built-in Cloudflare fallback domains
std::vector<std::string> get_default_cf_domains();

// Loads configuration from data/config.json and overrides with command line arguments
bool load_config(int argc, char* argv[], ProxyConfig& cfg);

} // namespace tgws
