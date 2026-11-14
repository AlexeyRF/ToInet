#include "pool.h"
#include <iostream>

namespace tgws {

WsPool::WsPool() : config(nullptr), running(false) {}

WsPool::~WsPool() {
    stop();
}

void WsPool::init(const ProxyConfig* cfg) {
    stop();
    config = cfg;
    running = true;
    worker_thread = std::thread(&WsPool::worker_loop, this);
}

void WsPool::stop() {
    running = false;
    if (worker_thread.joinable()) {
        worker_thread.join();
    }
    std::lock_guard<std::mutex> lock(mtx);
    pool.clear();
}

std::unique_ptr<RawWebSocket> WsPool::create_connection(const PoolKey& key) {
    if (!config || config->pool_size <= 0) return nullptr;

    std::string target_ip;
    auto it = config->dc_redirects.find(key.dc);
    if (it != config->dc_redirects.end() && !it->second.empty()) {
        target_ip = it->second;
    } else {
        target_ip = get_default_dc_ip(key.dc, key.is_test);
    }

    std::string domain = get_ws_domain(key.dc, key.is_media);
    std::string path = key.is_test ? "/apiws_test" : "/apiws";

    auto ws = std::make_unique<RawWebSocket>();
    // Connects to target_ip:443 with TLS and SNI=domain
    if (ws->connect(target_ip, 443, domain, path, domain, true, 8)) {
        return ws;
    }
    return nullptr;
}

void WsPool::warmup() {
    if (!config || config->pool_size <= 0) return;
    for (const auto& pair : config->dc_redirects) {
        int dc = pair.first;
        PoolKey key{ dc, false, config->force_test_dc };
        auto ws = create_connection(key);
        if (ws) {
            std::lock_guard<std::mutex> lock(mtx);
            pool[key].push_back({ std::move(ws), std::chrono::steady_clock::now() });
        }
    }
}

std::unique_ptr<RawWebSocket> WsPool::get(int dc, bool is_media, bool is_test) {
    if (!config || config->pool_size <= 0) return nullptr;
    PoolKey key{ dc, is_media, is_test };
    auto now = std::chrono::steady_clock::now();

    std::lock_guard<std::mutex> lock(mtx);
    auto it = pool.find(key);
    if (it != pool.end()) {
        auto& dq = it->second;
        while (!dq.empty()) {
            auto item = std::move(dq.front());
            dq.pop_front();

            auto age = std::chrono::duration_cast<std::chrono::seconds>(now - item.created_at).count();
            if (age < 120 && item.ws && item.ws->is_open()) {
                return std::move(item.ws);
            }
        }
    }
    return nullptr;
}

void WsPool::worker_loop() {
    while (running) {
        // Sleep in 1-second intervals up to 5 seconds
        for (int i = 0; i < 5 && running; ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        if (!running || !config || config->pool_size <= 0) continue;

        auto now = std::chrono::steady_clock::now();

        // 1. Purge stale connections (> 120s)
        {
            std::lock_guard<std::mutex> lock(mtx);
            for (auto& pair : pool) {
                auto& dq = pair.second;
                auto it = dq.begin();
                while (it != dq.end()) {
                    auto age = std::chrono::duration_cast<std::chrono::seconds>(now - it->created_at).count();
                    if (age >= 120 || !it->ws || !it->ws->is_open()) {
                        it = dq.erase(it);
                    } else {
                        ++it;
                    }
                }
            }
        }

        // 2. Refill active pools
        for (const auto& pair : config->dc_redirects) {
            if (!running) break;
            int dc = pair.first;
            PoolKey key{ dc, false, config->force_test_dc };

            size_t count = 0;
            {
                std::lock_guard<std::mutex> lock(mtx);
                count = pool[key].size();
            }

            if (count < static_cast<size_t>(config->pool_size)) {
                auto ws = create_connection(key);
                if (ws) {
                    std::lock_guard<std::mutex> lock(mtx);
                    pool[key].push_back({ std::move(ws), std::chrono::steady_clock::now() });
                }
            }
        }
    }
}

} // namespace tgws
