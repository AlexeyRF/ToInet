#pragma once

#include "websocket.h"
#include "config.h"
#include <map>
#include <deque>
#include <memory>
#include <mutex>
#include <thread>
#include <atomic>
#include <chrono>

namespace tgws {

struct PoolKey {
    int dc;
    bool is_media;
    bool is_test;

    bool operator<(const PoolKey& o) const {
        if (dc != o.dc) return dc < o.dc;
        if (is_media != o.is_media) return is_media < o.is_media;
        return is_test < o.is_test;
    }
};

struct PooledItem {
    std::unique_ptr<RawWebSocket> ws;
    std::chrono::steady_clock::time_point created_at;
};

class WsPool {
public:
    WsPool();
    ~WsPool();

    void init(const ProxyConfig* cfg);
    void warmup();
    void stop();

    // Returns an idle pre-warmed WebSocket connection, or nullptr if none available
    std::unique_ptr<RawWebSocket> get(int dc, bool is_media, bool is_test);

private:
    const ProxyConfig* config;
    std::mutex mtx;
    std::map<PoolKey, std::deque<PooledItem>> pool;
    std::atomic<bool> running;
    std::thread worker_thread;

    void worker_loop();
    std::unique_ptr<RawWebSocket> create_connection(const PoolKey& key);
};

} // namespace tgws
