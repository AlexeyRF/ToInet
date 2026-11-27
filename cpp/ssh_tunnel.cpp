#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#ifndef _WINSOCK_DEPRECATED_NO_WARNINGS
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#endif

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include <atomic>
#include <fstream>
#include <cstring>

#include "ssh_tunnel/ssh_crypto.h"
#include "ssh_tunnel/ssh_client.h"

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "bcrypt.lib")

namespace {

std::atomic<bool> g_stopRequested{ false };

BOOL WINAPI ConsoleHandler(DWORD signal) {
    if (signal == CTRL_C_EVENT || signal == CTRL_BREAK_EVENT || signal == CTRL_CLOSE_EVENT) {
        g_stopRequested.store(true);
        return TRUE;
    }
    return FALSE;
}

std::string WideToUtf8(const std::wstring& w) {
    if (w.empty()) return "";
    int len = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), nullptr, 0, nullptr, nullptr);
    if (len <= 0) return "";
    std::string out(len, '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), &out[0], len, nullptr, nullptr);
    return out;
}

std::vector<uint8_t> HexToBytes(const std::wstring& hex) {
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        wchar_t buf[3] = { hex[i], hex[i + 1], 0 };
        uint8_t b = static_cast<uint8_t>(wcstoul(buf, nullptr, 16));
        bytes.push_back(b);
    }
    return bytes;
}

bool DecryptPasswordWithKeyFile(const std::wstring& encPassHex, const std::wstring& keyFilePath, std::wstring& outPlainPass) {
    std::wifstream kf(keyFilePath);
    if (!kf.is_open()) return false;
    std::wstring keyHex;
    kf >> keyHex;
    kf.close();

    if (keyHex.empty() || encPassHex.empty()) return false;

    std::vector<uint8_t> encBytes = HexToBytes(encPassHex);
    std::vector<uint8_t> keyBytes = HexToBytes(keyHex);
    if (encBytes.empty() || keyBytes.empty()) return false;

    std::string decryptedUtf8(encBytes.size(), '\0');
    for (size_t i = 0; i < encBytes.size(); ++i) {
        decryptedUtf8[i] = static_cast<char>(encBytes[i] ^ keyBytes[i % keyBytes.size()]);
    }

    int wlen = MultiByteToWideChar(CP_UTF8, 0, decryptedUtf8.c_str(), static_cast<int>(decryptedUtf8.size()), nullptr, 0);
    if (wlen > 0) {
        outPlainPass.resize(wlen);
        MultiByteToWideChar(CP_UTF8, 0, decryptedUtf8.c_str(), static_cast<int>(decryptedUtf8.size()), &outPlainPass[0], wlen);
        return true;
    }
    return false;
}

bool RecvExact(SOCKET s, uint8_t* buf, size_t len) {
    size_t got = 0;
    while (got < len) {
        int r = recv(s, reinterpret_cast<char*>(buf + got), static_cast<int>(len - got), 0);
        if (r <= 0) return false;
        got += static_cast<size_t>(r);
    }
    return true;
}

bool SendExact(SOCKET s, const uint8_t* buf, size_t len) {
    size_t sent = 0;
    while (sent < len) {
        int r = send(s, reinterpret_cast<const char*>(buf + sent), static_cast<int>(len - sent), 0);
        if (r <= 0) return false;
        sent += static_cast<size_t>(r);
    }
    return true;
}

void HandleSocks5Client(SOCKET client_sock, std::string orig_ip, uint16_t orig_port, ssh_tunnel::SshClient* ssh) {
    DWORD timeout_ms = 15000;
    setsockopt(client_sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
    BOOL nodelay = TRUE;
    setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&nodelay), sizeof(nodelay));

    // 1. SOCKS5 Greeting: VER (1) | NMETHODS (1) | METHODS (NMETHODS)
    uint8_t hdr[2];
    if (!RecvExact(client_sock, hdr, 2) || hdr[0] != 0x05) {
        closesocket(client_sock);
        return;
    }
    uint8_t nmethods = hdr[1];
    std::vector<uint8_t> methods(nmethods);
    if (nmethods > 0 && !RecvExact(client_sock, methods.data(), nmethods)) {
        closesocket(client_sock);
        return;
    }

    uint8_t auth_reply[2] = { 0x05, 0x00 }; // No authentication
    if (!SendExact(client_sock, auth_reply, 2)) {
        closesocket(client_sock);
        return;
    }

    // 2. SOCKS5 Request: VER | CMD | RSV | ATYP | DST.ADDR | DST.PORT
    uint8_t req[4];
    if (!RecvExact(client_sock, req, 4) || req[0] != 0x05) {
        closesocket(client_sock);
        return;
    }

    uint8_t cmd = req[1];
    uint8_t atyp = req[3];
    if (cmd != 0x01) { // Only CONNECT supported
        uint8_t err_reply[10] = { 0x05, 0x07, 0x00, 0x01, 0, 0, 0, 0, 0, 0 };
        SendExact(client_sock, err_reply, 10);
        closesocket(client_sock);
        return;
    }

    std::string dest_host;
    if (atyp == 0x01) { // IPv4
        uint8_t ip4[4];
        if (!RecvExact(client_sock, ip4, 4)) { closesocket(client_sock); return; }
        char buf[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, ip4, buf, sizeof(buf));
        dest_host = buf;
    } else if (atyp == 0x03) { // Domain name
        uint8_t dlen = 0;
        if (!RecvExact(client_sock, &dlen, 1) || dlen == 0) { closesocket(client_sock); return; }
        std::vector<char> dbuf(dlen);
        if (!RecvExact(client_sock, reinterpret_cast<uint8_t*>(dbuf.data()), dlen)) { closesocket(client_sock); return; }
        dest_host.assign(dbuf.begin(), dbuf.end());
    } else if (atyp == 0x04) { // IPv6
        uint8_t ip6[16];
        if (!RecvExact(client_sock, ip6, 16)) { closesocket(client_sock); return; }
        char buf[INET6_ADDRSTRLEN];
        inet_ntop(AF_INET6, ip6, buf, sizeof(buf));
        dest_host = buf;
    } else {
        uint8_t err_reply[10] = { 0x05, 0x08, 0x00, 0x01, 0, 0, 0, 0, 0, 0 };
        SendExact(client_sock, err_reply, 10);
        closesocket(client_sock);
        return;
    }

    uint8_t port_be[2];
    if (!RecvExact(client_sock, port_be, 2)) {
        closesocket(client_sock);
        return;
    }
    uint16_t dest_port = static_cast<uint16_t>((port_be[0] << 8) | port_be[1]);

    // Remove receive timeout for long-lived proxied connection
    DWORD zero_timeout = 0;
    setsockopt(client_sock, SOL_SOCKET, SO_RCVTIMEO, reinterpret_cast<const char*>(&zero_timeout), sizeof(zero_timeout));

    auto ch = ssh->open_direct_tcpip(dest_host, dest_port, orig_ip, orig_port, client_sock);
    if (!ch) {
        uint8_t err_reply[10] = { 0x05, 0x05, 0x00, 0x01, 0, 0, 0, 0, 0, 0 };
        SendExact(client_sock, err_reply, 10);
        closesocket(client_sock);
        return;
    }

    uint8_t ok_reply[10] = { 0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0 };
    if (!SendExact(client_sock, ok_reply, 10)) {
        ssh->close_channel(ch);
        closesocket(client_sock);
        return;
    }

    // Forward client -> SSH channel
    std::vector<uint8_t> buf(32768);
    while (!g_stopRequested.load() && ssh->is_connected()) {
        int r = recv(client_sock, reinterpret_cast<char*>(buf.data()), static_cast<int>(buf.size()), 0);
        if (r <= 0) break;
        if (!ssh->send_channel_data(ch, buf.data(), static_cast<size_t>(r))) {
            break;
        }
    }

    ssh->send_channel_eof(ch);
    ssh->close_channel(ch);
    closesocket(client_sock);
}

SOCKET CreateSocksListener(const std::string& bind_addr, int port) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) return INVALID_SOCKET;

    BOOL reuse = TRUE;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&reuse), sizeof(reuse));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<u_short>(port));
    if (inet_pton(AF_INET, bind_addr.c_str(), &addr.sin_addr) != 1) {
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    }

    if (bind(s, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR ||
        listen(s, SOMAXCONN) == SOCKET_ERROR) {
        closesocket(s);
        return INVALID_SOCKET;
    }
    return s;
}

bool RunSelfTest() {
    // RFC 7748 Section 6.1 X25519 test vector
    const uint8_t alice_priv[32] = {
        0x77, 0x07, 0x6d, 0x0a, 0x73, 0x18, 0xa5, 0x7d,
        0x3c, 0x16, 0xc1, 0x72, 0x51, 0xb2, 0x66, 0x45,
        0xdf, 0x4c, 0x2f, 0x87, 0xeb, 0xc0, 0x99, 0x2a,
        0xb1, 0x77, 0xfb, 0xa5, 0x1d, 0xb9, 0x2c, 0x2a
    };
    const uint8_t expected_pub[32] = {
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a
    };
    uint8_t actual_pub[32]{};
    ssh_tunnel::x25519_scalarmult_base(actual_pub, alice_priv);
    if (std::memcmp(actual_pub, expected_pub, 32) != 0) {
        std::wcerr << L"[SELF-TEST] X25519 basepoint test FAILED\n";
        return false;
    }

    // AES-256-CTR roundtrip test
    uint8_t key[32]{};
    uint8_t iv[16]{};
    ssh_tunnel::random_bytes(key, sizeof(key));
    ssh_tunnel::random_bytes(iv, sizeof(iv));
    const char* msg = "ToInet-MAX native C++ SSH-2 tunnel crypto self-test!";
    size_t len = std::strlen(msg);
    std::vector<uint8_t> buf(msg, msg + len);

    ssh_tunnel::AesCtr enc, dec;
    if (!enc.init(key, sizeof(key), iv) || !dec.init(key, sizeof(key), iv)) {
        std::wcerr << L"[SELF-TEST] AesCtr init FAILED\n";
        return false;
    }
    enc.process_inplace(buf.data(), buf.size());
    dec.process_inplace(buf.data(), buf.size());
    if (std::memcmp(buf.data(), msg, len) != 0) {
        std::wcerr << L"[SELF-TEST] AesCtr roundtrip FAILED\n";
        return false;
    }

    // HMAC-SHA256 test
    ssh_tunnel::HmacContext hmac;
    uint8_t mac1[32]{}, mac2[32]{};
    if (!hmac.init(ssh_tunnel::HashAlg::SHA256, key, sizeof(key)) ||
        !hmac.compute(1, buf.data(), buf.size(), mac1) ||
        !hmac.compute(1, buf.data(), buf.size(), mac2) ||
        !ssh_tunnel::constant_time_eq(mac1, mac2, 32)) {
        std::wcerr << L"[SELF-TEST] HMAC-SHA256 test FAILED\n";
        return false;
    }

    std::wcout << L"[SELF-TEST] All crypto checks PASSED (X25519 RFC7748, AES-256-CTR, HMAC-SHA256)\n";
    return true;
}

struct SSHConfig {
    std::wstring host;
    int port{ 22 };
    std::wstring user;
    std::wstring pass;
    std::wstring encPass;
    std::wstring keyFile;
    std::wstring bindAddress{ L"127.0.0.1" };
    int socksPort{ 1770 };
    bool autoReconnect{ true };
    int reconnectInterval{ 5 };
};

void PrintHelp() {
    std::wcout << L"ToInet Native C++ SSH-2 SOCKS5 Tunnel Service\n"
               << L"Usage:\n"
               << L"  ssh_tunnel.exe --host <host> --port <port> --user <user> [options]\n\n"
               << L"Options:\n"
               << L"  --host <string>         Remote SSH server host/IP\n"
               << L"  --port <int>            Remote SSH server port (default: 22)\n"
               << L"  --user <string>         SSH username\n"
               << L"  --pass <string>         SSH password\n"
               << L"  --enc-pass <hex>        Encrypted SSH password (hex-encoded)\n"
               << L"  --key-file <path>       One-time decryption key file path\n"
               << L"  --socks-port <int>      Local SOCKS5 port (default: 1770)\n"
               << L"  --bind <string>         Local bind IP (default: 127.0.0.1, or 0.0.0.0 for LAN sharing)\n"
               << L"  --share                 Shortcut for --bind 0.0.0.0\n"
               << L"  --no-reconnect          Disable auto-reconnect on disconnect\n"
               << L"  --interval <int>        Reconnect interval in seconds (default: 5)\n"
               << L"  --self-test             Run built-in crypto self-test and exit\n"
               << L"  --help                  Show this help message\n";
}

} // namespace

int wmain(int argc, wchar_t* argv[]) {
    SSHConfig config;

    for (int i = 1; i < argc; ++i) {
        std::wstring arg = argv[i];
        if (arg == L"--help" || arg == L"-h") {
            PrintHelp();
            return 0;
        } else if (arg == L"--self-test") {
            return RunSelfTest() ? 0 : 1;
        } else if (arg == L"--host" && i + 1 < argc) {
            config.host = argv[++i];
        } else if (arg == L"--port" && i + 1 < argc) {
            config.port = _wtoi(argv[++i]);
        } else if (arg == L"--user" && i + 1 < argc) {
            config.user = argv[++i];
        } else if (arg == L"--pass" && i + 1 < argc) {
            config.pass = argv[++i];
        } else if (arg == L"--enc-pass" && i + 1 < argc) {
            config.encPass = argv[++i];
        } else if (arg == L"--key-file" && i + 1 < argc) {
            config.keyFile = argv[++i];
        } else if (arg == L"--socks-port" && i + 1 < argc) {
            config.socksPort = _wtoi(argv[++i]);
        } else if (arg == L"--bind" && i + 1 < argc) {
            config.bindAddress = argv[++i];
        } else if (arg == L"--share") {
            config.bindAddress = L"0.0.0.0";
        } else if (arg == L"--no-reconnect") {
            config.autoReconnect = false;
        } else if (arg == L"--interval" && i + 1 < argc) {
            config.reconnectInterval = _wtoi(argv[++i]);
        }
    }

    if (config.host.empty()) {
        wchar_t envHost[512];
        if (GetEnvironmentVariableW(L"TOINET_SSH_HOST", envHost, 512) > 0) {
            config.host = envHost;
        }
    }
    if (config.user.empty()) {
        wchar_t envUser[512];
        if (GetEnvironmentVariableW(L"TOINET_SSH_USER", envUser, 512) > 0) {
            config.user = envUser;
        }
    }
    if (config.pass.empty() && !config.encPass.empty() && !config.keyFile.empty()) {
        std::wstring decrypted;
        if (DecryptPasswordWithKeyFile(config.encPass, config.keyFile, decrypted)) {
            config.pass = decrypted;
            DeleteFileW(config.keyFile.c_str());
            config.keyFile.clear();
        } else {
            std::wcerr << L"[ERROR] Failed to decrypt password using key-file: " << config.keyFile << std::endl;
        }
    }
    if (config.pass.empty()) {
        wchar_t envPass[1024];
        if (GetEnvironmentVariableW(L"TOINET_SSH_PASS", envPass, 1024) > 0) {
            config.pass = envPass;
        }
    }

    if (config.host.empty() || config.user.empty()) {
        std::wcerr << L"[ERROR] Missing SSH host or user. Specify --host and --user (and --pass).\n";
        PrintHelp();
        return 1;
    }

    SetConsoleCtrlHandler(ConsoleHandler, TRUE);

    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);

    std::string hostUtf8 = WideToUtf8(config.host);
    std::string userUtf8 = WideToUtf8(config.user);
    std::string passUtf8 = WideToUtf8(config.pass);
    std::string bindUtf8 = WideToUtf8(config.bindAddress);

    std::wcout << L"[INFO] Starting native C++ SSH-2 Tunnel to " << config.user << L"@" << config.host << L":" << config.port
               << L" -> SOCKS5 " << config.bindAddress << L":" << config.socksPort << std::endl;

    while (!g_stopRequested.load()) {
        std::wcout << L"[STATUS] CONNECTING" << std::endl;

        ssh_tunnel::SshClient ssh;
        std::string err;
        if (!ssh.connect_and_auth(hostUtf8, config.port, userUtf8, passUtf8, err)) {
            std::cerr << "[STATUS] ERROR: " << err << std::endl;
            if (!config.autoReconnect || g_stopRequested.load()) break;
            std::wcout << L"[INFO] Waiting " << config.reconnectInterval << L"s before reconnecting..." << std::endl;
            for (int i = 0; i < config.reconnectInterval * 10 && !g_stopRequested.load(); ++i) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            continue;
        }

        SOCKET listen_sock = CreateSocksListener(bindUtf8, config.socksPort);
        if (listen_sock == INVALID_SOCKET) {
            std::wcerr << L"[STATUS] ERROR: Failed to bind SOCKS5 listener on " << config.bindAddress << L":" << config.socksPort << std::endl;
            ssh.disconnect();
            if (!config.autoReconnect || g_stopRequested.load()) break;
            for (int i = 0; i < config.reconnectInterval * 10 && !g_stopRequested.load(); ++i) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            continue;
        }

        ssh.start_session_threads();
        std::wcout << L"[STATUS] CONNECTED " << config.bindAddress << L":" << config.socksPort << std::endl;

        while (!g_stopRequested.load() && ssh.is_connected()) {
            fd_set readfds;
            FD_ZERO(&readfds);
            FD_SET(listen_sock, &readfds);
            timeval tv{ 0, 200000 }; // 200 ms poll for stop/disconnect
            int sel = select(0, &readfds, nullptr, nullptr, &tv);
            if (sel > 0 && FD_ISSET(listen_sock, &readfds)) {
                sockaddr_in client_addr{};
                int addrlen = sizeof(client_addr);
                SOCKET cs = accept(listen_sock, reinterpret_cast<sockaddr*>(&client_addr), &addrlen);
                if (cs != INVALID_SOCKET) {
                    char ipbuf[INET_ADDRSTRLEN] = "127.0.0.1";
                    inet_ntop(AF_INET, &client_addr.sin_addr, ipbuf, sizeof(ipbuf));
                    uint16_t cport = ntohs(client_addr.sin_port);
                    std::thread(HandleSocks5Client, cs, std::string(ipbuf), cport, &ssh).detach();
                }
            }
        }

        closesocket(listen_sock);
        ssh.disconnect();

        std::wcout << L"[STATUS] DISCONNECTED" << std::endl;

        if (g_stopRequested.load() || !config.autoReconnect) {
            break;
        }

        std::wcout << L"[INFO] Waiting " << config.reconnectInterval << L"s before reconnecting..." << std::endl;
        for (int i = 0; i < config.reconnectInterval * 10 && !g_stopRequested.load(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    std::wcout << L"[STATUS] STOPPED" << std::endl;
    WSACleanup();
    return 0;
}
