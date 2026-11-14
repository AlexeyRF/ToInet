#include "config.h"
#include "crypto.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>

namespace tgws {

static const std::string EMPTY_STR = "";

const std::string& get_default_dc_ip(int dc, bool is_test) {
    static const std::map<int, std::string> DEFAULT_IPS = {
        {1, "149.154.175.50"},
        {2, "149.154.167.51"},
        {3, "149.154.175.100"},
        {4, "149.154.167.91"},
        {5, "149.154.171.5"},
        {203, "91.105.192.100"}
    };
    static const std::map<int, std::string> TEST_IPS = {
        {1, "149.154.175.10"},
        {2, "149.154.167.40"},
        {3, "149.154.175.117"}
    };
    const auto& table = is_test ? TEST_IPS : DEFAULT_IPS;
    auto it = table.find(dc);
    if (it != table.end()) return it->second;
    static const std::string fallback = "149.154.167.51";
    return fallback;
}

std::string get_ws_domain(int dc, bool is_media) {
    if (dc == 203) dc = 2;
    std::ostringstream ss;
    if (!is_media) {
        ss << "kws" << dc << ".web.telegram.org";
    } else {
        ss << "kws" << dc << "-1.web.telegram.org";
    }
    return ss.str();
}

static std::string decode_cf_domain(const std::string& s) {
    if (s.size() < 4 || s.substr(s.size() - 4) != ".com") return s;
    std::string p = s.substr(0, s.size() - 4);
    int n = 0;
    for (char c : p) {
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) ++n;
    }
    std::string res;
    for (char c : p) {
        if (c >= 'a' && c <= 'z') {
            res.push_back(static_cast<char>((c - 'a' - n + 260) % 26 + 'a'));
        } else if (c >= 'A' && c <= 'Z') {
            res.push_back(static_cast<char>((c - 'A' - n + 260) % 26 + 'A'));
        } else {
            res.push_back(c);
        }
    }
    res += ".co.uk";
    return res;
}

std::vector<std::string> get_default_cf_domains() {
    static const std::vector<std::string> ENC = {
        "virkgj.com", "vmmzovy.com", "mkuosckvso.com", "zaewayzmplad.com", "twdmbzcm.com",
        "awzwsldi.com", "clngqrflngqin.com", "tjacxbqtj.com", "bxaxtxmrw.com", "dmohrsgmohcrwb.com",
        "vwbmtmoi.com", "khgrre.com", "ulihssf.com", "tmhqsdqmfpmk.com", "xwuwoqbm.com",
        "orgcnunpj.com", "zhkuldz.com", "zypoljnslxa.com", "efabnxaowuzs.com", "zaftuzsftqdq.com"
    };
    std::vector<std::string> res;
    for (const auto& d : ENC) {
        res.push_back(decode_cf_domain(d));
    }
    return res;
}

static std::vector<std::string> split_domains(const std::string& s) {
    std::vector<std::string> res;
    std::string token;
    for (char c : s) {
        if (c == ',' || c == ';' || c == ' ' || c == '\t' || c == '\r' || c == '\n') {
            if (!token.empty()) {
                res.push_back(token);
                token.clear();
            }
        } else {
            token.push_back(c);
        }
    }
    if (!token.empty()) res.push_back(token);
    return res;
}

// Simple JSON extraction helpers for config.json
static std::string extract_json_str(const std::string& json, const std::string& key) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return "";
    pos = json.find(':', pos);
    if (pos == std::string::npos) return "";
    size_t start = json.find('\"', pos);
    if (start == std::string::npos) return "";
    size_t end = json.find('\"', start + 1);
    if (end == std::string::npos) return "";
    return json.substr(start + 1, end - start - 1);
}

static int extract_json_int(const std::string& json, const std::string& key, int default_val) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return default_val;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return default_val;
    size_t start = json.find_first_of("-0123456789", pos);
    if (start == std::string::npos) return default_val;
    size_t end = json.find_first_not_of("-0123456789", start);
    try {
        return std::stoi(json.substr(start, end - start));
    } catch (...) {
        return default_val;
    }
}

static bool extract_json_bool(const std::string& json, const std::string& key, bool default_val) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return default_val;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return default_val;
    size_t t = json.find("true", pos);
    size_t f = json.find("false", pos);
    if (t != std::string::npos && (f == std::string::npos || t < f)) return true;
    if (f != std::string::npos && (t == std::string::npos || f < t)) return false;
    return default_val;
}

static std::vector<std::string> extract_json_array_str(const std::string& json, const std::string& key) {
    std::vector<std::string> res;
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return res;
    size_t start = json.find('[', pos);
    if (start == std::string::npos) return res;
    size_t end = json.find(']', start);
    if (end == std::string::npos) return res;

    std::string arr = json.substr(start + 1, end - start - 1);
    size_t p = 0;
    while (p < arr.size()) {
        size_t s = arr.find('\"', p);
        if (s == std::string::npos) break;
        size_t e = arr.find('\"', s + 1);
        if (e == std::string::npos) break;
        res.push_back(arr.substr(s + 1, e - s - 1));
        p = e + 1;
    }
    return res;
}

static void parse_dc_ip_entry(const std::string& entry, std::map<int, std::string>& out) {
    size_t colon = entry.find(':');
    if (colon != std::string::npos) {
        try {
            int dc = std::stoi(entry.substr(0, colon));
            std::string ip = entry.substr(colon + 1);
            if (!ip.empty()) {
                out[dc] = ip;
            }
        } catch (...) {}
    }
}

bool load_config(int argc, char* argv[], ProxyConfig& cfg) {
    // 1. Defaults
    cfg.port = 1480;
    cfg.host = "127.0.0.1";
    cfg.dc_redirects[2] = "149.154.167.220";
    cfg.dc_redirects[4] = "149.154.167.220";
    cfg.buffer_size = 256 * 1024;
    cfg.pool_size = 4;
    cfg.fallback_cfproxy = true;
    cfg.cfproxy_h2_media = true;

    // 2. Load data/config.json if available
    std::string config_path = "data/config.json";
    std::ifstream f(config_path);
    if (!f.is_open()) {
        config_path = "config.json";
        f.open(config_path);
    }
    if (f.is_open()) {
        std::stringstream ss;
        ss << f.rdbuf();
        std::string json = ss.str();
        f.close();

        int p = extract_json_int(json, "tgws_port", 0);
        if (p > 0 && p <= 65535) cfg.port = p;

        std::string h = extract_json_str(json, "tgws_host");
        if (!h.empty()) cfg.host = h;

        std::string sec = extract_json_str(json, "tgws_secret");
        if (!sec.empty()) cfg.secret = sec;

        std::string ftls = extract_json_str(json, "tgws_fake_tls");
        if (!ftls.empty()) cfg.fake_tls_domain = ftls;

        std::string front = extract_json_str(json, "tgws_fronting_sni");
        if (!front.empty()) cfg.fronting_sni = front;

        cfg.verbose = extract_json_bool(json, "tgws_verbose", cfg.verbose);
        cfg.fallback_cfproxy = extract_json_bool(json, "tgws_fallback_cfproxy", cfg.fallback_cfproxy);
        cfg.cfproxy_h2_media = extract_json_bool(json, "tgws_cfproxy_h2_media", cfg.cfproxy_h2_media);

        std::string user_dom = extract_json_str(json, "tgws_cfproxy_user_domain");
        if (!user_dom.empty()) cfg.cfproxy_user_domains = split_domains(user_dom);

        std::string worker_dom = extract_json_str(json, "tgws_cfproxy_worker_domain");
        if (!worker_dom.empty()) cfg.cfproxy_worker_domains = split_domains(worker_dom);

        auto dc_ips = extract_json_array_str(json, "tgws_dc_ip");
        for (const auto& item : dc_ips) {
            parse_dc_ip_entry(item, cfg.dc_redirects);
        }
    }

    // 3. Command line overrides
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--port" && i + 1 < argc) {
            cfg.port = std::stoi(argv[++i]);
        } else if (arg == "--host" && i + 1 < argc) {
            cfg.host = argv[++i];
        } else if (arg == "--secret" && i + 1 < argc) {
            cfg.secret = argv[++i];
        } else if (arg == "--dc-ip" && i + 1 < argc) {
            parse_dc_ip_entry(argv[++i], cfg.dc_redirects);
        } else if (arg == "--fake-tls-domain" && i + 1 < argc) {
            cfg.fake_tls_domain = argv[++i];
        } else if (arg == "--cfproxy-domain" && i + 1 < argc) {
            auto doms = split_domains(argv[++i]);
            cfg.cfproxy_user_domains.insert(cfg.cfproxy_user_domains.end(), doms.begin(), doms.end());
        } else if (arg == "--cfproxy-worker-domain" && i + 1 < argc) {
            auto doms = split_domains(argv[++i]);
            cfg.cfproxy_worker_domains.insert(cfg.cfproxy_worker_domains.end(), doms.begin(), doms.end());
        } else if (arg == "--no-cfproxy") {
            cfg.fallback_cfproxy = false;
        } else if (arg == "--no-secure") {
            cfg.disable_secure = true;
        } else if (arg == "--force-test-dc") {
            cfg.force_test_dc = true;
        } else if (arg == "--pool-size" && i + 1 < argc) {
            cfg.pool_size = std::stoi(argv[++i]);
        } else if (arg == "--buf-kb" && i + 1 < argc) {
            cfg.buffer_size = std::max(4, std::stoi(argv[++i])) * 1024;
        } else if (arg == "-v" || arg == "--verbose") {
            cfg.verbose = true;
        } else if (arg == "--proxy-protocol") {
            cfg.proxy_protocol = true;
        }
    }

    // Generate random secret if not set
    if (cfg.secret.size() != 32) {
        uint8_t rand_sec[16];
        random_bytes(rand_sec, 16);
        cfg.secret = hex_encode(rand_sec, 16);
    }

    return true;
}

} // namespace tgws
