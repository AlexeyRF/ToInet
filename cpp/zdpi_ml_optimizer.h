#pragma once

#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif

#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <string>
#include <vector>
#include <regex>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <fstream>
#include <sstream>
#include <set>
#include <map>
#include <iomanip>
#include <chrono>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

namespace ZDPI_ML {

// 25 Standard Feature Names
inline const std::vector<std::string> FEATURE_NAMES = {
    "has_fake",
    "fake_ttl",
    "fake_tmpl_google",
    "fake_tmpl_kyber",
    "fake_tmpl_rutracker",
    "fake_tmpl_other",
    "has_split",
    "split_pos_midsld",
    "split_pos_sniext",
    "split_pos_sld",
    "split_pos_sni",
    "split_pos_num",
    "has_disorder",
    "disorder_pos_midsld",
    "disorder_pos_num",
    "has_tlsrec",
    "tlsrec_pos_midsld",
    "tlsrec_pos_sniext",
    "has_multisplit",
    "has_oob",
    "has_quic_drop",
    "has_fake_sni",
    "has_http_mods",
    "has_auto_detect",
    "num_stages"
};

// String utility functions
inline std::string trim(const std::string& str) {
    size_t first = str.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    size_t last = str.find_last_not_of(" \t\r\n");
    return str.substr(first, (last - first + 1));
}

inline std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

inline std::string escape_json_str(const std::string& str) {
    std::string out;
    out.reserve(str.size() + 8);
    for (char c : str) {
        if (c == '"') out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c == '\t') out += "\\t";
        else out += c;
    }
    return out;
}

// Extract normalized 25-feature vector from strategy command line
inline std::vector<double> extract_features(const std::string& strategy_str) {
    std::string s = to_lower(trim(strategy_str));
    std::vector<double> feat(25, 0.0);

    // 1. Fake
    if (s.find("--dpi-desync") != std::string::npos && s.find("fake") != std::string::npos) {
        feat[0] = 1.0;
    } else if (s.find("-f") != std::string::npos || s.find("--fake") != std::string::npos) {
        feat[0] = 1.0;
    }

    // Fake TTL
    std::smatch m;
    std::regex ttl_re(R"((?:--dpi-desync-ttl|--ttl|-t)\s*=?\s*(\d+))");
    if (std::regex_search(s, m, ttl_re)) {
        try { feat[1] = std::stod(m[1].str()); } catch (...) { feat[1] = 3.0; }
    } else if (feat[0] > 0.0) {
        feat[1] = 3.0;
    }

    // Fake templates
    if (s.find("google") != std::string::npos) feat[2] = 1.0;
    if (s.find("kyber") != std::string::npos) feat[3] = 1.0;
    if (s.find("rutracker") != std::string::npos) feat[4] = 1.0;
    if (s.find("-f-") != std::string::npos || s.find("--fake -") != std::string::npos ||
        s.find("fake-data") != std::string::npos || s.find("0x") != std::string::npos) {
        feat[5] = 1.0;
    }

    // 2. Split
    if (s.find("split") != std::string::npos || s.find("-s") != std::string::npos) {
        feat[6] = 1.0;
    }
    if (s.find("midsld") != std::string::npos) feat[7] = 1.0;
    if (s.find("sniext") != std::string::npos) feat[8] = 1.0;
    if (s.find("endsld") != std::string::npos || std::regex_search(s, std::regex(R"(\bsld\b)"))) {
        feat[9] = 1.0;
    }
    if (s.find("+s") != std::string::npos || std::regex_search(s, std::regex(R"(\bsni\b)"))) {
        feat[10] = 1.0;
    }
    std::regex split_num_re(R"((?:split-pos|split|-s)\s*=?\s*(\d+))");
    if (std::regex_search(s, m, split_num_re)) {
        try { feat[11] = std::stod(m[1].str()); } catch (...) {}
    }

    // 3. Disorder
    if (s.find("disorder") != std::string::npos || s.find("-d") != std::string::npos) {
        feat[12] = 1.0;
        if (s.find("midsld") != std::string::npos) feat[13] = 1.0;
        std::regex d_num_re(R"((?:-d|disorder)\s*=?\s*(\d+))");
        if (std::regex_search(s, m, d_num_re)) {
            try { feat[14] = std::stod(m[1].str()); } catch (...) {}
        }
    }

    // 4. TLS Record
    if (s.find("tlsrec") != std::string::npos || s.find("-r") != std::string::npos) {
        feat[15] = 1.0;
        if (s.find("midsld") != std::string::npos) feat[16] = 1.0;
        if (s.find("sniext") != std::string::npos) feat[17] = 1.0;
    }

    // 5. Multisplit
    size_t s_count = 0;
    size_t pos = 0;
    while ((pos = s.find("-s", pos)) != std::string::npos) {
        s_count++;
        pos += 2;
    }
    bool comma_in_split_pos = false;
    if (s.find("split-pos") != std::string::npos) {
        std::regex sp_re(R"(split-pos\s*=?\s*([^\s]+))");
        if (std::regex_search(s, m, sp_re)) {
            if (m[1].str().find(',') != std::string::npos) {
                comma_in_split_pos = true;
            }
        }
    }
    if (s.find("multisplit") != std::string::npos || s_count > 1 || comma_in_split_pos) {
        feat[18] = 1.0;
    }

    // 6. OOB
    if (s.find("oob") != std::string::npos || s.find("-o") != std::string::npos) {
        feat[19] = 1.0;
    }

    // 7. QUIC drop
    if (s.find("--quic-drop") != std::string::npos || s.find("--drop-quic") != std::string::npos ||
        s.find("-q 1") != std::string::npos || s.find("-qr") != std::string::npos) {
        feat[20] = 1.0;
    }

    // 8. Fake SNI
    if (s.find("--dpi-desync-fake-sni") != std::string::npos || s.find("--fake-sni") != std::string::npos ||
        s.find("-n ") != std::string::npos) {
        feat[21] = 1.0;
    }

    // 9. HTTP mods
    if (s.find("-m") != std::string::npos || s.find("--mod-http") != std::string::npos) {
        feat[22] = 1.0;
    }

    // 10. Auto detect
    if (s.find("-a") != std::string::npos || s.find("--auto") != std::string::npos) {
        feat[23] = 1.0;
    }

    // Stages count
    std::regex stage_re(R"(-[sdfroq]\b|--dpi-desync\b)");
    auto stage_begin = std::sregex_iterator(s.begin(), s.end(), stage_re);
    auto stage_end = std::sregex_iterator();
    size_t stages = std::distance(stage_begin, stage_end);
    feat[24] = static_cast<double>(stages < 1 ? 1 : stages);

    return feat;
}

// Data structures
struct HistoryEntry {
    std::string strategy;
    double overall_pct = 0.0;
    double priority_pct = 0.0;
    double score = 0.0;
    int success_count = 0;
    int total_sites = 0;
    double timestamp = 0.0;
    std::vector<double> features;
};

struct GeneratedStrategy {
    std::string strategy;
    double predicted_score = 0.0;
    std::vector<double> features;
    std::string reason;
};

// Lightweight JSON parser for history files
namespace JsonHelper {
    enum class Type { Null, Bool, Number, String, Array, Object };

    struct Value {
        Type type = Type::Null;
        bool b = false;
        double n = 0.0;
        std::string s;
        std::vector<Value> a;
        std::vector<std::pair<std::string, Value>> o;

        const Value* find(const std::string& key) const {
            if (type != Type::Object) return nullptr;
            for (const auto& kv : o) {
                if (kv.first == key) return &kv.second;
            }
            return nullptr;
        }

        std::string get_string(const std::string& key, const std::string& def = "") const {
            const Value* v = find(key);
            return (v && v->type == Type::String) ? v->s : def;
        }

        double get_number(const std::string& key, double def = 0.0) const {
            const Value* v = find(key);
            return (v && v->type == Type::Number) ? v->n : def;
        }

        int get_int(const std::string& key, int def = 0) const {
            return static_cast<int>(get_number(key, def));
        }

        std::vector<double> get_double_array(const std::string& key) const {
            std::vector<double> res;
            const Value* v = find(key);
            if (v && v->type == Type::Array) {
                for (const auto& elem : v->a) {
                    if (elem.type == Type::Number) {
                        res.push_back(elem.n);
                    }
                }
            }
            return res;
        }
    };

    class Parser {
        const std::string& src;
        size_t pos = 0;

        void skip_ws() {
            while (pos < src.size() && (src[pos] == ' ' || src[pos] == '\t' || src[pos] == '\r' || src[pos] == '\n')) {
                pos++;
            }
        }

        char peek() {
            skip_ws();
            return (pos < src.size()) ? src[pos] : '\0';
        }

        char get() {
            skip_ws();
            return (pos < src.size()) ? src[pos++] : '\0';
        }

    public:
        Parser(const std::string& text) : src(text) {}

        bool parse(Value& out) {
            skip_ws();
            char c = peek();
            if (c == '[') return parse_array(out);
            if (c == '{') return parse_object(out);
            if (c == '"') return parse_string(out);
            if (c == 't' || c == 'f') return parse_bool(out);
            if (c == 'n') return parse_null(out);
            if (isdigit((unsigned char)c) || c == '-') return parse_number(out);
            return false;
        }

    private:
        bool parse_string(Value& out) {
            if (get() != '"') return false;
            std::string res;
            while (pos < src.size()) {
                char ch = src[pos++];
                if (ch == '"') {
                    out.type = Type::String;
                    out.s = std::move(res);
                    return true;
                }
                if (ch == '\\' && pos < src.size()) {
                    char esc = src[pos++];
                    if (esc == '"') res += '"';
                    else if (esc == '\\') res += '\\';
                    else if (esc == '/') res += '/';
                    else if (esc == 'b') res += '\b';
                    else if (esc == 'f') res += '\f';
                    else if (esc == 'n') res += '\n';
                    else if (esc == 'r') res += '\r';
                    else if (esc == 't') res += '\t';
                    else if (esc == 'u' && pos + 4 <= src.size()) {
                        pos += 4;
                        res += '?';
                    } else {
                        res += esc;
                    }
                } else {
                    res += ch;
                }
            }
            return false;
        }

        bool parse_number(Value& out) {
            size_t start = pos;
            if (pos < src.size() && src[pos] == '-') pos++;
            while (pos < src.size() && (isdigit((unsigned char)src[pos]) || src[pos] == '.' || src[pos] == 'e' || src[pos] == 'E' || src[pos] == '+' || src[pos] == '-')) {
                pos++;
            }
            try {
                out.type = Type::Number;
                out.n = std::stod(src.substr(start, pos - start));
                return true;
            } catch (...) {
                return false;
            }
        }

        bool parse_bool(Value& out) {
            if (src.compare(pos, 4, "true") == 0) {
                pos += 4;
                out.type = Type::Bool;
                out.b = true;
                return true;
            }
            if (src.compare(pos, 5, "false") == 0) {
                pos += 5;
                out.type = Type::Bool;
                out.b = false;
                return true;
            }
            return false;
        }

        bool parse_null(Value& out) {
            if (src.compare(pos, 4, "null") == 0) {
                pos += 4;
                out.type = Type::Null;
                return true;
            }
            return false;
        }

        bool parse_array(Value& out) {
            if (get() != '[') return false;
            out.type = Type::Array;
            out.a.clear();
            if (peek() == ']') {
                get();
                return true;
            }
            while (pos < src.size()) {
                Value elem;
                if (!parse(elem)) return false;
                out.a.push_back(std::move(elem));
                char sep = get();
                if (sep == ']') return true;
                if (sep != ',') return false;
            }
            return false;
        }

        bool parse_object(Value& out) {
            if (get() != '{') return false;
            out.type = Type::Object;
            out.o.clear();
            if (peek() == '}') {
                get();
                return true;
            }
            while (pos < src.size()) {
                Value keyVal;
                if (!parse_string(keyVal)) return false;
                if (get() != ':') return false;
                Value val;
                if (!parse(val)) return false;
                out.o.emplace_back(std::move(keyVal.s), std::move(val));
                char sep = get();
                if (sep == '}') return true;
                if (sep != ',') return false;
            }
            return false;
        }
    };
}

// ZDPIMLOptimizer Class
class ZDPIMLOptimizer {
public:
    std::string history_file;
    std::vector<HistoryEntry> history;
    std::vector<std::pair<std::string, double>> top_features;

    ZDPIMLOptimizer(const std::string& custom_history_file = "") {
        if (!custom_history_file.empty()) {
            history_file = custom_history_file;
        } else {
            history_file = resolve_default_history_path();
        }
        load_history();
        train_model();
    }

    static std::string resolve_default_history_path() {
        // Look in probable project locations
        const std::vector<std::string> candidates = {
            "ui\\zdpi_ml_history.json",
            "ui/zdpi_ml_history.json",
            "zdpi_ml_history.json",
            "data\\zdpi_ml_history.json"
        };
        for (const auto& c : candidates) {
            std::ifstream f(c);
            if (f.good()) return c;
        }

#ifdef _WIN32
        // Look near executable
        char exePath[MAX_PATH];
        if (GetModuleFileNameA(NULL, exePath, MAX_PATH)) {
            std::string dir = exePath;
            size_t slash = dir.find_last_of("\\/");
            if (slash != std::string::npos) dir = dir.substr(0, slash);

            std::vector<std::string> relCands = {
                dir + "\\..\\ui\\zdpi_ml_history.json",
                dir + "\\ui\\zdpi_ml_history.json",
                dir + "\\zdpi_ml_history.json"
            };
            for (const auto& rc : relCands) {
                std::ifstream f(rc);
                if (f.good()) return rc;
            }
        }

        const char* appdata = getenv("APPDATA");
        if (appdata) {
            std::string appCand = std::string(appdata) + "\\ToInet-MAX\\zdpi_ml_history.json";
            std::ifstream f(appCand);
            if (f.good()) return appCand;
        }
#endif
        return "ui\\zdpi_ml_history.json";
    }

    bool load_history() {
        history.clear();
        std::ifstream file(history_file);
        if (!file.is_open()) {
            return false;
        }
        std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        file.close();

        JsonHelper::Value root;
        JsonHelper::Parser parser(content);
        if (!parser.parse(root) || root.type != JsonHelper::Type::Array) {
            return false;
        }

        for (const auto& item : root.a) {
            if (item.type != JsonHelper::Type::Object) continue;
            HistoryEntry e;
            e.strategy = trim(item.get_string("strategy"));
            if (e.strategy.empty()) continue;

            e.overall_pct = item.get_number("overall_pct");
            e.priority_pct = item.get_number("priority_pct");
            e.score = item.get_number("score");
            e.success_count = item.get_int("success_count");
            e.total_sites = item.get_int("total_sites");
            e.timestamp = item.get_number("timestamp");
            e.features = item.get_double_array("features");

            if (e.features.size() != 25) {
                e.features = extract_features(e.strategy);
            }
            history.push_back(std::move(e));
        }
        return true;
    }

    bool save_history() const {
        std::ofstream file(history_file);
        if (!file.is_open()) return false;

        file << "[\n";
        for (size_t i = 0; i < history.size(); ++i) {
            const auto& e = history[i];
            file << "  {\n";
            file << "    \"strategy\": \"" << escape_json_str(e.strategy) << "\",\n";
            file << "    \"overall_pct\": " << std::fixed << std::setprecision(4) << e.overall_pct << ",\n";
            file << "    \"priority_pct\": " << std::fixed << std::setprecision(4) << e.priority_pct << ",\n";
            file << "    \"score\": " << std::fixed << std::setprecision(4) << e.score << ",\n";
            file << "    \"success_count\": " << e.success_count << ",\n";
            file << "    \"total_sites\": " << e.total_sites << ",\n";
            file << "    \"timestamp\": " << std::fixed << std::setprecision(2) << e.timestamp << ",\n";
            file << "    \"features\": [\n";
            for (size_t j = 0; j < e.features.size(); ++j) {
                file << "      " << std::fixed << std::setprecision(1) << e.features[j];
                if (j + 1 < e.features.size()) file << ",";
                file << "\n";
            }
            file << "    ]\n";
            file << "  }";
            if (i + 1 < history.size()) file << ",";
            file << "\n";
        }
        file << "]\n";
        file.close();
        return true;
    }

    void add_result(const std::string& strategy_raw, double overall_pct, double priority_pct,
                    int success_count, int total_sites) {
        std::string strategy = trim(strategy_raw);
        if (strategy.empty()) return;

        double score = (0.7 * priority_pct) + (0.3 * overall_pct);
        auto now = std::chrono::duration_cast<std::chrono::duration<double>>(
            std::chrono::system_clock::now().time_since_epoch()).count();

        for (auto& item : history) {
            if (item.strategy == strategy) {
                item.overall_pct = overall_pct;
                item.priority_pct = priority_pct;
                item.score = score;
                item.success_count = success_count;
                item.total_sites = total_sites;
                item.timestamp = now;
                save_history();
                train_model();
                return;
            }
        }

        HistoryEntry entry;
        entry.strategy = strategy;
        entry.overall_pct = overall_pct;
        entry.priority_pct = priority_pct;
        entry.score = score;
        entry.success_count = success_count;
        entry.total_sites = total_sites;
        entry.timestamp = now;
        entry.features = extract_features(strategy);

        history.push_back(std::move(entry));
        save_history();
        train_model();
    }

    bool train_model() {
        if (history.size() < 2) {
            top_features.clear();
            return false;
        }

        const size_t n = history.size();
        double sum_y = 0.0;
        for (const auto& h : history) sum_y += h.score;
        double avg_y = sum_y / static_cast<double>(n);

        double var_y = 0.0;
        for (const auto& h : history) {
            double diff = h.score - avg_y;
            var_y += diff * diff;
        }

        if (var_y <= 1e-9) {
            top_features.clear();
            return false;
        }

        std::vector<std::pair<std::string, double>> correlations;
        for (size_t j = 0; j < FEATURE_NAMES.size(); ++j) {
            double sum_c = 0.0;
            for (const auto& h : history) sum_c += h.features[j];
            double avg_c = sum_c / static_cast<double>(n);

            double var_c = 0.0;
            double cov = 0.0;
            for (const auto& h : history) {
                double diff_c = h.features[j] - avg_c;
                double diff_y = h.score - avg_y;
                var_c += diff_c * diff_c;
                cov += diff_c * diff_y;
            }

            if (var_c > 1e-9) {
                double r = cov / std::sqrt(var_c * var_y);
                correlations.emplace_back(FEATURE_NAMES[j], (r > 0.0 ? r : 0.0));
            } else {
                correlations.emplace_back(FEATURE_NAMES[j], 0.0);
            }
        }

        double total_r = 0.0;
        for (const auto& c : correlations) total_r += c.second;

        top_features.clear();
        if (total_r > 0.0) {
            for (auto& c : correlations) {
                c.second /= total_r;
            }
            std::sort(correlations.begin(), correlations.end(),
                      [](const auto& a, const auto& b) { return a.second > b.second; });

            for (const auto& c : correlations) {
                if (c.second > 0.03 && top_features.size() < 5) {
                    top_features.push_back(c);
                }
            }
        }
        return true;
    }

    double predict_score(const std::string& strategy) const {
        if (history.empty()) return 50.0;

        std::vector<double> feat = extract_features(strategy);
        double total_weighted_score = 0.0;
        double total_weight = 0.0;

        for (const auto& item : history) {
            double dist_sq = 0.0;
            for (size_t i = 0; i < 25; ++i) {
                double diff = feat[i] - item.features[i];
                dist_sq += diff * diff;
            }
            double dist = std::sqrt(dist_sq);
            double weight = 1.0 / (1.0 + dist);
            total_weighted_score += item.score * weight;
            total_weight += weight;
        }

        if (total_weight > 0.0) {
            double pred = total_weighted_score / total_weight;
            if (pred < 0.0) pred = 0.0;
            if (pred > 100.0) pred = 100.0;
            return pred;
        }
        return 50.0;
    }

    std::string explain_recommendation(const std::string& strategy) const {
        std::vector<std::string> reasons;
        if (strategy.find("midsld") != std::string::npos) {
            reasons.push_back("Маркер midsld (обход SNI-фильтров)");
        }
        if (strategy.find("kyber") != std::string::npos) {
            reasons.push_back("Kyber Fake (проходит DPI ТСПУ)");
        } else if (strategy.find("google") != std::string::npos) {
            reasons.push_back("Google Fake (высокая совместимость)");
        }
        if (strategy.find("--quic-drop") != std::string::npos) {
            reasons.push_back("QUIC-Drop (ускорение YouTube 4K)");
        }
        std::regex ttl_reg(R"(ttl=[234]|t [234])");
        if (std::regex_search(strategy, ttl_reg)) {
            reasons.push_back("Оптимальный TTL (2-4)");
        }
        if (strategy.find("tlsrec") != std::string::npos) {
            reasons.push_back("TLS-Record расщепление");
        }
        if (reasons.empty()) {
            reasons.push_back("Комбинация параметров с высоким рейтингом");
        }

        std::string result;
        for (size_t i = 0; i < reasons.size(); ++i) {
            result += reasons[i];
            if (i + 1 < reasons.size()) result += ", ";
        }
        return result;
    }

    std::vector<GeneratedStrategy> generate_ai_strategies(
        int count = 10,
        const std::vector<std::string>& existing_list = {}) const
    {
        std::set<std::string> existing(existing_list.begin(), existing_list.end());
        for (const auto& item : history) {
            existing.insert(item.strategy);
        }

        const std::vector<std::string> modes = {
            "fake,split2", "fake,disorder2", "fake,multisplit", "fakedsplit",
            "fake,tlsrec", "tlsrec", "fakeddisorder"
        };
        const std::vector<std::string> positions = {
            "midsld", "sniext", "sld", "sni", "1", "2", "3", "1,midsld", "1,sniext,midsld"
        };
        const std::vector<std::string> fakes = {"google", "kyber", "rutracker"};
        const std::vector<int> ttls = {2, 3, 4, 5, 8};
        const std::vector<std::string> quic_opts = {"--quic-drop", ""};

        std::set<std::string> candidates;

        // 1. Recombine from top-performing historical strategies
        std::vector<HistoryEntry> sorted_history = history;
        std::sort(sorted_history.begin(), sorted_history.end(),
                  [](const auto& a, const auto& b) { return a.score > b.score; });

        size_t top_n = std::min(static_cast<size_t>(5), sorted_history.size());
        for (size_t i = 0; i < top_n; ++i) {
            std::string strat = sorted_history[i].strategy;

            // Mutate TTL
            for (int new_ttl : {2, 3, 4, 5}) {
                std::string mut1 = std::regex_replace(strat, std::regex(R"(--dpi-desync-ttl=\d+)"), "--dpi-desync-ttl=" + std::to_string(new_ttl));
                std::string mut2 = std::regex_replace(mut1, std::regex(R"(-t\s*\d+)"), "-t " + std::to_string(new_ttl));
                candidates.insert(trim(mut2));
            }

            // Mutate fake template
            for (const auto& new_tmpl : fakes) {
                std::string mut = std::regex_replace(strat, std::regex(R"(--dpi-desync-fake-tls=\w+)"), "--dpi-desync-fake-tls=" + new_tmpl);
                candidates.insert(trim(mut));
            }

            // Mutate midsld
            if (strat.find("midsld") == std::string::npos && strat.find("--dpi-desync-split-pos=") != std::string::npos) {
                std::string mut = std::regex_replace(strat, std::regex(R"(--dpi-desync-split-pos=[^\s]+)"), "--dpi-desync-split-pos=midsld");
                candidates.insert(trim(mut));
            }

            // Mutate quic-drop
            if (strat.find("--quic-drop") == std::string::npos) {
                candidates.insert(trim(strat + " --quic-drop"));
            }
        }

        // 2. Parametric synthesis of Zapret & ByeDPI strategies
        for (const auto& m : modes) {
            for (const auto& p : positions) {
                for (const auto& f : fakes) {
                    for (int t : ttls) {
                        for (const auto& q : quic_opts) {
                            std::string q_str = q.empty() ? "" : (" " + q);
                            std::string cmd = "--dpi-desync=" + m + " --dpi-desync-split-pos=" + p +
                                              " --dpi-desync-fake-tls=" + f + " --dpi-desync-ttl=" +
                                              std::to_string(t) + q_str;
                            candidates.insert(trim(cmd));
                        }
                    }
                }
            }
        }

        // 3. ByeDPI-style syntax combinations
        for (const auto& p : {"midsld", "sniext", "1+s", "2+s", "3+s"}) {
            for (int t : {3, 4, 5}) {
                for (const auto& q : {"--quic-drop", ""}) {
                    std::string q_str = std::string(q).empty() ? "" : (" " + std::string(q));
                    candidates.insert(trim("-s " + std::string(p) + " -f " + std::string(p) + " -r " + std::string(p) + " -t " + std::to_string(t) + q_str));
                    candidates.insert(trim("-d " + std::string(p) + " -f 1 -t " + std::to_string(t) + q_str));
                    candidates.insert(trim("-s 1 -d " + std::string(p) + " -f -1 -t " + std::to_string(t) + q_str));
                }
            }
        }

        // Filter novel candidates & score
        std::vector<GeneratedStrategy> scored;
        scored.reserve(candidates.size());

        for (const auto& cand : candidates) {
            if (existing.find(cand) != existing.end()) continue;
            GeneratedStrategy gs;
            gs.strategy = cand;
            gs.predicted_score = std::round(predict_score(cand) * 10.0) / 10.0;
            gs.features = extract_features(cand);
            gs.reason = explain_recommendation(cand);
            scored.push_back(std::move(gs));
        }

        std::sort(scored.begin(), scored.end(),
                  [](const auto& a, const auto& b) { return a.predicted_score > b.predicted_score; });

        if (scored.size() > static_cast<size_t>(count)) {
            scored.resize(count);
        }
        return scored;
    }
};

} // namespace ZDPI_ML
