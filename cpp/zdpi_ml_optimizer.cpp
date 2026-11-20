#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif

#ifndef NOMINMAX
#define NOMINMAX
#endif

#include "zdpi_ml_optimizer.h"
#include <iostream>
#include <iomanip>
#include <fstream>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

using namespace ZDPI_ML;

static void print_usage(const char* prog) {
    std::cout << "zDPI Machine Learning Strategy Optimizer (C++ Engine)\n";
    std::cout << "Usage: " << prog << " <command> [options/arguments]\n\n";
    std::cout << "Commands:\n";
    std::cout << "  predict \"<strategy>\"                     Predict bypass score (0.0 - 100.0)\n";
    std::cout << "  generate [count=10] [existing_file]      Synthesize and rank novel AI strategies\n";
    std::cout << "  add \"<strat>\" <overall%> <pri%> <ok> <all> Record test outcome to history\n";
    std::cout << "  train                                    Train model & print top features\n";
    std::cout << "  top-features                             Display top correlated bypass features\n";
    std::cout << "  explain \"<strategy>\"                     Display explanation for strategy ranking\n";
    std::cout << "  features \"<strategy>\"                    Print 25 numerical features for strategy\n";
    std::cout << "  benchmark                                Run self-test and accuracy verification\n";
}

int main(int argc, char* argv[]) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif

    if (argc < 2) {
        print_usage(argv[0]);
        std::cout << "\n--- Current Model Status ---\n";
        ZDPIMLOptimizer opt;
        std::cout << "History file: " << opt.history_file << "\n";
        std::cout << "Trained records: " << opt.history.size() << "\n";
        if (!opt.top_features.empty()) {
            std::cout << "Top Correlated Features:\n";
            for (const auto& tf : opt.top_features) {
                std::cout << "  - " << std::left << std::setw(22) << tf.first
                          << ": " << std::fixed << std::setprecision(1) << (tf.second * 100.0) << "%\n";
            }
        }
        return 0;
    }

    std::string cmd = to_lower(argv[1]);

    if (cmd == "predict") {
        if (argc < 3) {
            std::cerr << "Error: Missing strategy argument for predict.\n";
            return 1;
        }
        std::string strategy = argv[2];
        ZDPIMLOptimizer opt;
        double score = opt.predict_score(strategy);
        std::cout << std::fixed << std::setprecision(1) << score << "\n";
        return 0;
    }

    if (cmd == "explain") {
        if (argc < 3) {
            std::cerr << "Error: Missing strategy argument for explain.\n";
            return 1;
        }
        std::string strategy = argv[2];
        ZDPIMLOptimizer opt;
        std::cout << opt.explain_recommendation(strategy) << "\n";
        return 0;
    }

    if (cmd == "features") {
        if (argc < 3) {
            std::cerr << "Error: Missing strategy argument for features.\n";
            return 1;
        }
        std::string strategy = argv[2];
        auto feat = extract_features(strategy);
        for (size_t i = 0; i < FEATURE_NAMES.size(); ++i) {
            std::cout << "  " << std::left << std::setw(22) << FEATURE_NAMES[i]
                      << ": " << std::fixed << std::setprecision(1) << feat[i] << "\n";
        }
        return 0;
    }

    if (cmd == "generate") {
        int count = 10;
        if (argc >= 3) {
            try { count = std::max(1, std::stoi(argv[2])); } catch (...) {}
        }
        std::vector<std::string> existing;
        if (argc >= 4) {
            std::ifstream ef(argv[3]);
            if (ef.is_open()) {
                std::string line;
                while (std::getline(ef, line)) {
                    std::string t = trim(line);
                    if (!t.empty() && t[0] != '#') {
                        existing.push_back(t);
                    }
                }
            }
        }

        ZDPIMLOptimizer opt;
        auto generated = opt.generate_ai_strategies(count, existing);

        std::cout << "[\n";
        for (size_t i = 0; i < generated.size(); ++i) {
            const auto& g = generated[i];
            std::cout << "  {\n";
            std::cout << "    \"strategy\": \"" << escape_json_str(g.strategy) << "\",\n";
            std::cout << "    \"predicted_score\": " << std::fixed << std::setprecision(1) << g.predicted_score << ",\n";
            std::cout << "    \"reason\": \"" << escape_json_str(g.reason) << "\"\n";
            std::cout << "  }";
            if (i + 1 < generated.size()) std::cout << ",";
            std::cout << "\n";
        }
        std::cout << "]\n";
        return 0;
    }

    if (cmd == "add") {
        if (argc < 7) {
            std::cerr << "Usage: " << argv[0] << " add \"<strat>\" <overall%> <pri%> <ok_cnt> <tot_cnt>\n";
            return 1;
        }
        std::string strategy = argv[2];
        double overall_pct = std::stod(argv[3]);
        double pri_pct = std::stod(argv[4]);
        int ok_cnt = std::stoi(argv[5]);
        int tot_cnt = std::stoi(argv[6]);

        ZDPIMLOptimizer opt;
        opt.add_result(strategy, overall_pct, pri_pct, ok_cnt, tot_cnt);
        std::cout << "Successfully added/updated strategy in " << opt.history_file << "\n";
        return 0;
    }

    if (cmd == "train") {
        ZDPIMLOptimizer opt;
        bool ok = opt.train_model();
        if (!ok) {
            std::cout << "Insufficient data to train model (need >= 2 records).\n";
            return 1;
        }
        std::cout << "Model trained successfully on " << opt.history.size() << " historical test records.\n";
        std::cout << "Top Correlated Features:\n";
        for (const auto& tf : opt.top_features) {
            std::cout << "  - " << std::left << std::setw(22) << tf.first
                      << ": " << std::fixed << std::setprecision(1) << (tf.second * 100.0) << "%\n";
        }
        return 0;
    }

    if (cmd == "top-features") {
        ZDPIMLOptimizer opt;
        for (const auto& tf : opt.top_features) {
            std::cout << tf.first << "\t" << std::fixed << std::setprecision(4) << tf.second << "\n";
        }
        return 0;
    }

    if (cmd == "benchmark") {
        std::cout << "Running zDPI ML Optimizer Benchmark...\n";
        ZDPIMLOptimizer opt;
        std::cout << "Loaded " << opt.history.size() << " records from " << opt.history_file << "\n";

        // Verification of feature extraction consistency
        int mismatches = 0;
        for (const auto& item : opt.history) {
            auto re_extracted = extract_features(item.strategy);
            for (size_t i = 0; i < 25; ++i) {
                if (std::abs(re_extracted[i] - item.features[i]) > 1e-4) {
                    mismatches++;
                }
            }
        }
        std::cout << "Feature consistency checks: "
                  << (mismatches == 0 ? "100% MATCH" : (std::to_string(mismatches) + " mismatches")) << "\n";

        // Performance benchmark
        auto t0 = std::chrono::high_resolution_clock::now();
        const int iterations = 10000;
        const std::string test_strat = "--dpi-desync=fake,split2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=kyber --dpi-desync-ttl=3 --quic-drop";
        double dummy = 0.0;
        for (int i = 0; i < iterations; ++i) {
            dummy += opt.predict_score(test_strat);
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        double elapsed_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        std::cout << iterations << " predictions completed in " << std::fixed << std::setprecision(2) << elapsed_ms << " ms ("
                  << (elapsed_ms / iterations * 1000.0) << " us / prediction)\n";

        auto gen = opt.generate_ai_strategies(5);
        std::cout << "Generated " << gen.size() << " top candidate strategies:\n";
        for (size_t i = 0; i < gen.size(); ++i) {
            std::cout << "  " << (i + 1) << ". [" << std::fixed << std::setprecision(1) << gen[i].predicted_score << "%] "
                      << gen[i].strategy << " (" << gen[i].reason << ")\n";
        }
        return 0;
    }

    std::cerr << "Unknown command: " << argv[1] << "\n";
    print_usage(argv[0]);
    return 1;
}
