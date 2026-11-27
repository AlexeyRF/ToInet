#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include <cstdint>
#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <condition_variable>
#include <unordered_map>
#include <atomic>
#include <thread>

#include "ssh_crypto.h"

namespace ssh_tunnel {

struct SshChannel {
    uint32_t local_id{ 0 };
    uint32_t remote_id{ 0 };
    uint32_t local_window{ 2 * 1024 * 1024 };
    uint32_t remote_window{ 0 };
    uint32_t remote_max_packet{ 32768 };

    SOCKET client_sock{ INVALID_SOCKET };

    std::mutex mu;
    std::condition_variable cv;
    bool open_confirmed{ false };
    bool open_failed{ false };
    bool eof_sent{ false };
    bool close_sent{ false };
    bool closed{ false };
};

class SshClient {
public:
    SshClient();
    ~SshClient();

    SshClient(const SshClient&) = delete;
    SshClient& operator=(const SshClient&) = delete;

    // Connect, perform SSH-2 handshake + KEX + userauth
    bool connect_and_auth(const std::string& host, int port,
                          const std::string& user, const std::string& password,
                          std::string& out_error);

    // Start background reader and keepalive threads
    void start_session_threads();

    // Disconnect and clean up all channels
    void disconnect();

    bool is_connected() const { return connected_.load(); }

    // Open a direct-tcpip forwarding channel for a SOCKS5 client socket
    std::shared_ptr<SshChannel> open_direct_tcpip(
        const std::string& dest_host, uint16_t dest_port,
        const std::string& orig_host, uint16_t orig_port,
        SOCKET client_sock);

    // Send data from local SOCKS5 client into the SSH channel (handles windowing)
    bool send_channel_data(const std::shared_ptr<SshChannel>& ch, const uint8_t* data, size_t len);

    // Send EOF / CLOSE on channel
    void send_channel_eof(const std::shared_ptr<SshChannel>& ch);
    void close_channel(const std::shared_ptr<SshChannel>& ch);

private:
    SOCKET sock_{ INVALID_SOCKET };
    std::atomic<bool> connected_{ false };
    std::atomic<bool> stop_threads_{ false };

    std::mutex send_mutex_;
    uint32_t send_seq_{ 0 };
    uint32_t recv_seq_{ 0 };

    bool send_encrypted_{ false };
    bool recv_encrypted_{ false };
    AesCtr send_cipher_;
    AesCtr recv_cipher_;
    HmacContext send_mac_;
    HmacContext recv_mac_;

    std::vector<uint8_t> session_id_;

    std::mutex channels_mutex_;
    uint32_t next_channel_id_{ 0 };
    std::unordered_map<uint32_t, std::shared_ptr<SshChannel>> channels_;

    std::atomic<int> missed_keepalives_{ 0 };
    std::thread reader_thread_;
    std::thread keepalive_thread_;

    bool send_raw(const uint8_t* data, size_t len);
    bool recv_raw(uint8_t* data, size_t len);
    bool send_packet(const std::vector<uint8_t>& payload);
    bool recv_packet(std::vector<uint8_t>& out_payload);

    bool perform_version_exchange(std::string& v_c, std::string& v_s, std::string& out_error);
    bool perform_kex(const std::string& v_c, const std::string& v_s, std::string& out_error);
    bool perform_auth(const std::string& user, const std::string& password, std::string& out_error);

    void reader_loop();
    void keepalive_loop();
    void handle_packet(const std::vector<uint8_t>& payload);
};

} // namespace ssh_tunnel
