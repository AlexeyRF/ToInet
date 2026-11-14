#pragma once

#include "protocol.h"
#include "websocket.h"
#include "fake_tls.h"
#include <winsock2.h>
#include <atomic>
#include <string>

namespace tgws {

struct Stats {
    std::atomic<uint64_t> connections_total{0};
    std::atomic<int64_t>  connections_active{0};
    std::atomic<uint64_t> pool_hits{0};
    std::atomic<uint64_t> pool_misses{0};
    std::atomic<uint64_t> bytes_up{0};
    std::atomic<uint64_t> bytes_down{0};
};

extern Stats g_stats;

// Re-encryption bridge between client socket and upstream RawWebSocket
void bridge_ws_reencrypt(SOCKET client_sock,
                         bool is_fake_tls,
                         RawWebSocket& ws,
                         CryptoCtx& ctx,
                         MsgSplitter* splitter,
                         const std::string& label);

// Re-encryption bridge between client socket and remote TCP socket (used for Tor/TCP fallback)
void bridge_tcp_reencrypt(SOCKET client_sock,
                          bool is_fake_tls,
                          SOCKET remote_sock,
                          CryptoCtx& ctx,
                          const std::string& label);

} // namespace tgws
