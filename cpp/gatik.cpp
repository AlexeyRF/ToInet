#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <atomic>
#include <chrono>
#include <cstring>
#include <fstream>
#include <algorithm>

#pragma comment(lib, "ws2_32.lib")

static std::atomic<bool> g_running(true);
static std::atomic<int64_t> g_global_upload_mode_until(0);

static const size_t UPLOAD_THRESHOLD = 1024;
static const size_t BUFFER_SIZE = 16384;

static std::string g_listen_host = "127.0.0.1";
static int g_listen_port = 1777;

static std::string g_download_proxy_host = "127.0.0.1";
static int g_download_proxy_port = 9853; // TOR

static std::string g_upload_proxy_host = "127.0.0.1";
static int g_upload_proxy_port = 1480;   // TGWS

int64_t get_current_time_sec() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
}

BOOL WINAPI ConsoleCtrlHandler(DWORD ctrl_type) {
    if (ctrl_type == CTRL_C_EVENT || ctrl_type == CTRL_CLOSE_EVENT || ctrl_type == CTRL_BREAK_EVENT) {
        g_running = false;
        return TRUE;
    }
    return FALSE;
}

bool recv_exact(SOCKET s, uint8_t* buf, size_t len) {
    size_t total = 0;
    while (total < len) {
        int r = recv(s, reinterpret_cast<char*>(buf + total), static_cast<int>(len - total), 0);
        if (r <= 0) {
            return false;
        }
        total += static_cast<size_t>(r);
    }
    return true;
}

bool send_all(SOCKET s, const uint8_t* buf, size_t len) {
    size_t total = 0;
    while (total < len) {
        int r = send(s, reinterpret_cast<const char*>(buf + total), static_cast<int>(len - total), 0);
        if (r <= 0) {
            return false;
        }
        total += static_cast<size_t>(r);
    }
    return true;
}

SOCKET connect_to(const std::string& host, int port) {
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        return INVALID_SOCKET;
    }

    // Disable Nagle's algorithm for lower latency
    int nodelay = 1;
    setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));

    sockaddr_in addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<u_short>(port));
    inet_pton(AF_INET, host.c_str(), &addr.sin_addr);

    if (connect(sock, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR) {
        closesocket(sock);
        return INVALID_SOCKET;
    }
    return sock;
}

void forward_traffic(SOCKET src, SOCKET dst, bool is_upload, bool is_client_to_server, size_t initial_bytes) {
    std::vector<uint8_t> buffer(BUFFER_SIZE);
    size_t bytes_transferred = initial_bytes;

    while (g_running) {
        int n = recv(src, reinterpret_cast<char*>(buffer.data()), static_cast<int>(buffer.size()), 0);
        if (n <= 0) {
            break;
        }

        if (!send_all(dst, buffer.data(), static_cast<size_t>(n))) {
            break;
        }

        bytes_transferred += static_cast<size_t>(n);

        if (is_client_to_server) {
            int64_t now = get_current_time_sec();
            // If routed via TOR but client sends > 64KB, abort so Telegram reconnects to TGWS
            if (!is_upload && bytes_transferred > 65536) {
                std::cout << "[Gatik] Heavy upload detected (" << bytes_transferred 
                          << " bytes) on TOR line! Aborting to trigger TGWS reconnect...\n";
                g_global_upload_mode_until.store(now + 15);
                break;
            }
            if (is_upload && bytes_transferred > 65536) {
                int64_t cur = g_global_upload_mode_until.load();
                int64_t target = now + 15;
                if (target > cur) {
                    g_global_upload_mode_until.store(target);
                }
            }
        }
    }

    shutdown(src, SD_BOTH);
    shutdown(dst, SD_BOTH);
}

void handle_client(SOCKET client_sock) {
    int nodelay = 1;
    setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));

    // 1. SOCKS5 Handshake
    uint8_t hdr[2];
    if (!recv_exact(client_sock, hdr, 2) || hdr[0] != 5) {
        closesocket(client_sock);
        return;
    }
    uint8_t nmethods = hdr[1];
    std::vector<uint8_t> methods(nmethods);
    if (!recv_exact(client_sock, methods.data(), nmethods)) {
        closesocket(client_sock);
        return;
    }

    // Handshake response: No authentication required
    uint8_t hs_reply[2] = {0x05, 0x00};
    if (!send_all(client_sock, hs_reply, 2)) {
        closesocket(client_sock);
        return;
    }

    // 2. CONNECT Request
    uint8_t req_hdr[4];
    if (!recv_exact(client_sock, req_hdr, 4)) {
        closesocket(client_sock);
        return;
    }
    if (req_hdr[0] != 5 || req_hdr[1] != 1) { // Only CONNECT supported
        closesocket(client_sock);
        return;
    }

    uint8_t atyp = req_hdr[3];
    std::vector<uint8_t> dst_addr_bytes;
    std::string dst_display;

    if (atyp == 1) { // IPv4
        dst_addr_bytes.resize(4);
        if (!recv_exact(client_sock, dst_addr_bytes.data(), 4)) {
            closesocket(client_sock);
            return;
        }
        dst_display = std::to_string(dst_addr_bytes[0]) + "." +
                      std::to_string(dst_addr_bytes[1]) + "." +
                      std::to_string(dst_addr_bytes[2]) + "." +
                      std::to_string(dst_addr_bytes[3]);
    } else if (atyp == 3) { // Domain
        uint8_t dlen = 0;
        if (!recv_exact(client_sock, &dlen, 1)) {
            closesocket(client_sock);
            return;
        }
        dst_addr_bytes.resize(dlen);
        if (!recv_exact(client_sock, dst_addr_bytes.data(), dlen)) {
            closesocket(client_sock);
            return;
        }
        dst_display = std::string(reinterpret_cast<char*>(dst_addr_bytes.data()), dlen);
    } else if (atyp == 4) { // IPv6
        dst_addr_bytes.resize(16);
        if (!recv_exact(client_sock, dst_addr_bytes.data(), 16)) {
            closesocket(client_sock);
            return;
        }
        dst_display = "[IPv6]";
    } else {
        closesocket(client_sock);
        return;
    }

    uint8_t dst_port_bytes[2];
    if (!recv_exact(client_sock, dst_port_bytes, 2)) {
        closesocket(client_sock);
        return;
    }
    uint16_t dst_port = (static_cast<uint16_t>(dst_port_bytes[0]) << 8) | dst_port_bytes[1];

    // 3. Early SUCCESS reply to client
    // Telegram will now immediately send the first data packet
    uint8_t success_reply[10] = {0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
    if (!send_all(client_sock, success_reply, 10)) {
        closesocket(client_sock);
        return;
    }

    // 4. Intercept first packet from client
    std::vector<uint8_t> first_chunk(BUFFER_SIZE);
    int r = recv(client_sock, reinterpret_cast<char*>(first_chunk.data()), static_cast<int>(first_chunk.size()), 0);
    if (r <= 0) {
        closesocket(client_sock);
        return;
    }
    first_chunk.resize(static_cast<size_t>(r));

    // Wait slightly (up to 100ms) if chunk is small to assemble full payload if sent in fragments
    while (first_chunk.size() < UPLOAD_THRESHOLD) {
        timeval tv;
        tv.tv_sec = 0;
        tv.tv_usec = 100000; // 100ms
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(client_sock, &fds);
        int sel = select(0, &fds, NULL, NULL, &tv);
        if (sel <= 0) {
            break;
        }
        uint8_t tmp[BUFFER_SIZE];
        int more = recv(client_sock, reinterpret_cast<char*>(tmp), sizeof(tmp), 0);
        if (more <= 0) {
            break;
        }
        first_chunk.insert(first_chunk.end(), tmp, tmp + more);
    }

    // 5. Routing Decision
    int64_t now = get_current_time_sec();
    bool is_upload = (first_chunk.size() > UPLOAD_THRESHOLD) || (now < g_global_upload_mode_until.load());

    std::string upstream_host = is_upload ? g_upload_proxy_host : g_download_proxy_host;
    int upstream_port = is_upload ? g_upload_proxy_port : g_download_proxy_port;
    std::string route_label = is_upload ? "UPLOAD (TGWS)" : "DOWNLOAD (TOR)";

    std::cout << "[Gatik] Connect to " << dst_display << ":" << dst_port 
              << " | First chunk: " << first_chunk.size() << " bytes -> " << route_label << "\n";

    // 6. Connect to upstream proxy
    SOCKET upstream_sock = connect_to(upstream_host, upstream_port);
    if (upstream_sock == INVALID_SOCKET) {
        std::cerr << "[Gatik] Failed to connect to upstream " << upstream_host << ":" << upstream_port << "\n";
        closesocket(client_sock);
        return;
    }

    // Upstream Handshake
    uint8_t up_hs[3] = {0x05, 0x01, 0x00};
    if (!send_all(upstream_sock, up_hs, 3)) {
        closesocket(upstream_sock);
        closesocket(client_sock);
        return;
    }
    uint8_t up_hs_resp[2];
    if (!recv_exact(upstream_sock, up_hs_resp, 2) || up_hs_resp[0] != 5 || up_hs_resp[1] != 0) {
        closesocket(upstream_sock);
        closesocket(client_sock);
        return;
    }

    // Upstream CONNECT request
    std::vector<uint8_t> up_req = {0x05, 0x01, 0x00, atyp};
    if (atyp == 3) {
        up_req.push_back(static_cast<uint8_t>(dst_addr_bytes.size()));
    }
    up_req.insert(up_req.end(), dst_addr_bytes.begin(), dst_addr_bytes.end());
    up_req.push_back(dst_port_bytes[0]);
    up_req.push_back(dst_port_bytes[1]);

    if (!send_all(upstream_sock, up_req.data(), up_req.size())) {
        closesocket(upstream_sock);
        closesocket(client_sock);
        return;
    }

    // Upstream CONNECT response
    uint8_t up_resp_hdr[4];
    if (!recv_exact(upstream_sock, up_resp_hdr, 4) || up_resp_hdr[1] != 0) {
        closesocket(upstream_sock);
        closesocket(client_sock);
        return;
    }

    uint8_t bnd_atyp = up_resp_hdr[3];
    if (bnd_atyp == 1) {
        uint8_t bnd[6];
        recv_exact(upstream_sock, bnd, 6);
    } else if (bnd_atyp == 3) {
        uint8_t len = 0;
        if (recv_exact(upstream_sock, &len, 1)) {
            std::vector<uint8_t> bnd(len + 2);
            recv_exact(upstream_sock, bnd.data(), bnd.size());
        }
    } else if (bnd_atyp == 4) {
        uint8_t bnd[18];
        recv_exact(upstream_sock, bnd, 18);
    }

    // 7. Send the intercepted first packet to upstream
    if (!send_all(upstream_sock, first_chunk.data(), first_chunk.size())) {
        closesocket(upstream_sock);
        closesocket(client_sock);
        return;
    }

    // 8. Bidirectional Forwarding
    std::thread t_up(forward_traffic, client_sock, upstream_sock, is_upload, true, first_chunk.size());
    std::thread t_down(forward_traffic, upstream_sock, client_sock, is_upload, false, 0);

    if (t_up.joinable()) t_up.join();
    if (t_down.joinable()) t_down.join();

    closesocket(upstream_sock);
    closesocket(client_sock);
}

void load_config_if_available() {
    std::vector<std::string> candidate_paths = {
        "config.json",
        "../config.json",
        "../../config.json"
    };

    for (const auto& path : candidate_paths) {
        std::ifstream file(path);
        if (file.is_open()) {
            std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
            // Basic JSON value extraction without heavy dependencies
            auto extract_int = [&](const std::string& key, int default_val) -> int {
                auto pos = content.find("\"" + key + "\"");
                if (pos != std::string::npos) {
                    auto colon = content.find(":", pos);
                    if (colon != std::string::npos) {
                        size_t start = colon + 1;
                        while (start < content.size() && (content[start] == ' ' || content[start] == '\t')) start++;
                        size_t end = start;
                        while (end < content.size() && (content[end] >= '0' && content[end] <= '9')) end++;
                        if (end > start) {
                            try {
                                return std::stoi(content.substr(start, end - start));
                            } catch (...) {}
                        }
                    }
                }
                return default_val;
            };

            auto extract_str = [&](const std::string& key, const std::string& default_val) -> std::string {
                auto pos = content.find("\"" + key + "\"");
                if (pos != std::string::npos) {
                    auto colon = content.find(":", pos);
                    if (colon != std::string::npos) {
                        auto q1 = content.find("\"", colon);
                        if (q1 != std::string::npos) {
                            auto q2 = content.find("\"", q1 + 1);
                            if (q2 != std::string::npos) {
                                return content.substr(q1 + 1, q2 - q1 - 1);
                            }
                        }
                    }
                }
                return default_val;
            };

            g_download_proxy_port = extract_int("tor_socks_port", g_download_proxy_port);
            g_upload_proxy_port = extract_int("tgws_port", g_upload_proxy_port);
            g_upload_proxy_host = extract_str("tgws_host", g_upload_proxy_host);
            break;
        }
    }
}

int main(int argc, char* argv[]) {
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCtrlHandler(ConsoleCtrlHandler, TRUE);

    load_config_if_available();

    // CLI overrides
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--port" && i + 1 < argc) {
            g_listen_port = std::stoi(argv[++i]);
        } else if (arg == "--tor-port" && i + 1 < argc) {
            g_download_proxy_port = std::stoi(argv[++i]);
        } else if (arg == "--tgws-port" && i + 1 < argc) {
            g_upload_proxy_port = std::stoi(argv[++i]);
        } else if (arg == "--tgws-host" && i + 1 < argc) {
            g_upload_proxy_host = argv[++i];
        }
    }

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[Gatik] WSAStartup failed\n";
        return 1;
    }

    SOCKET listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock == INVALID_SOCKET) {
        std::cerr << "[Gatik] socket() failed\n";
        WSACleanup();
        return 1;
    }

    int reuse = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&reuse), sizeof(reuse));

    sockaddr_in server_addr;
    std::memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(static_cast<u_short>(g_listen_port));
    inet_pton(AF_INET, g_listen_host.c_str(), &server_addr.sin_addr);

    if (bind(listen_sock, reinterpret_cast<sockaddr*>(&server_addr), sizeof(server_addr)) == SOCKET_ERROR) {
        int err = WSAGetLastError();
        if (err == WSAEADDRINUSE || err == 10048) {
            std::cout << "[Gatik] Port " << g_listen_port << " already in use, exiting.\n";
        } else {
            std::cerr << "[Gatik] bind() failed with error " << err << "\n";
        }
        closesocket(listen_sock);
        WSACleanup();
        return 0;
    }

    if (listen(listen_sock, SOMAXCONN) == SOCKET_ERROR) {
        std::cerr << "[Gatik] listen() failed\n";
        closesocket(listen_sock);
        WSACleanup();
        return 1;
    }

    std::cout << "[Gatik] SOCKS5 Router started: " << g_listen_host << ":" << g_listen_port << "\n";
    std::cout << "[Gatik] TOR line: " << g_download_proxy_host << ":" << g_download_proxy_port 
              << " | TGWS line: " << g_upload_proxy_host << ":" << g_upload_proxy_port << "\n";

    // Non-blocking accept check so we can exit on g_running = false
    while (g_running) {
        timeval tv;
        tv.tv_sec = 1;
        tv.tv_usec = 0;
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(listen_sock, &fds);

        int sel = select(0, &fds, NULL, NULL, &tv);
        if (sel > 0 && FD_ISSET(listen_sock, &fds)) {
            SOCKET client_sock = accept(listen_sock, NULL, NULL);
            if (client_sock != INVALID_SOCKET) {
                std::thread(handle_client, client_sock).detach();
            }
        }
    }

    closesocket(listen_sock);
    WSACleanup();
    std::cout << "[Gatik] Stopped.\n";
    return 0;
}
