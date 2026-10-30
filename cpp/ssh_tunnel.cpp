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
#include <sstream>
#include <vector>
#include <chrono>
#include <thread>
#include <atomic>
#include <csignal>
#include <fstream>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "advapi32.lib")

static std::vector<uint8_t> HexToBytes(const std::wstring& hex) {
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        wchar_t buf[3] = { hex[i], hex[i + 1], 0 };
        uint8_t b = static_cast<uint8_t>(wcstoul(buf, nullptr, 16));
        bytes.push_back(b);
    }
    return bytes;
}

static bool DecryptPasswordWithKeyFile(const std::wstring& encPassHex, const std::wstring& keyFilePath, std::wstring& outPlainPass) {
    std::wifstream kf(keyFilePath);
    if (!kf.is_open()) return false;
    std::wstring keyHex;
    kf >> keyHex;
    kf.close();

    if (keyHex.empty() || encPassHex.empty()) return false;

    std::vector<uint8_t> encBytes = HexToBytes(encPassHex);
    std::vector<uint8_t> keyBytes = HexToBytes(keyHex);

    if (encBytes.empty() || keyBytes.empty()) return false;

    std::string decryptedUtf8;
    decryptedUtf8.resize(encBytes.size());
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

static std::atomic<bool> g_stopRequested{ false };

static BOOL WINAPI ConsoleHandler(DWORD signal) {
    if (signal == CTRL_C_EVENT || signal == CTRL_BREAK_EVENT || signal == CTRL_CLOSE_EVENT) {
        g_stopRequested.store(true);
        return TRUE;
    }
    return FALSE;
}



static std::wstring FindSshExecutable() {
    wchar_t sysDir[MAX_PATH];
    if (GetSystemDirectoryW(sysDir, MAX_PATH)) {
        std::wstring candidate = std::wstring(sysDir) + L"\\OpenSSH\\ssh.exe";
        DWORD attr = GetFileAttributesW(candidate.c_str());
        if (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
            return candidate;
        }
    }

    wchar_t pathBuf[MAX_PATH];
    if (SearchPathW(NULL, L"ssh.exe", NULL, MAX_PATH, pathBuf, NULL) > 0) {
        return std::wstring(pathBuf);
    }

    return L"ssh.exe";
}

static bool CheckPortAvailable(int port) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) return false;

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<u_short>(port));
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    u_long nonBlocking = 1;
    ioctlsocket(s, FIONBIO, &nonBlocking);

    int res = connect(s, reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
    bool open = false;

    if (res == 0) {
        open = true;
    } else {
        fd_set writeSet;
        FD_ZERO(&writeSet);
        FD_SET(s, &writeSet);
        timeval tv{ 0, 150000 }; // 150 ms
        if (select(0, nullptr, &writeSet, nullptr, &tv) > 0) {
            int err = 0;
            int errLen = sizeof(err);
            if (getsockopt(s, SOL_SOCKET, SO_ERROR, reinterpret_cast<char*>(&err), &errLen) == 0 && err == 0) {
                open = true;
            }
        }
    }

    closesocket(s);
    return open;
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

static void PrintHelp() {
    std::wcout << L"ToInet SSH SOCKS5 Tunnel Service\n"
               << L"Usage:\n"
               << L"  ssh_tunnel.exe --host <host> --port <port> --user <user> [options]\n\n"
               << L"Options:\n"
               << L"  --host <string>         Remote SSH server host/IP\n"
               << L"  --port <int>            Remote SSH server port (default: 22)\n"
               << L"  --user <string>         SSH username\n"
               << L"  --pass <string>         SSH plaintext password (legacy)\n"
               << L"  --enc-pass <hex>        Encrypted SSH password (hex-encoded)\n"
               << L"  --key-file <path>       One-time decryption key file path\n"
               << L"  --socks-port <int>      Local SOCKS5 port (default: 1770)\n"
               << L"  --bind <string>         Local bind IP (default: 127.0.0.1, or 0.0.0.0 for LAN sharing)\n"
               << L"  --share                 Shortcut for --bind 0.0.0.0\n"
               << L"  --no-reconnect          Disable auto-reconnect on disconnect\n"
               << L"  --interval <int>        Reconnect interval in seconds (default: 5)\n"
               << L"  --askpass               Internal helper for OpenSSH SSH_ASKPASS\n"
               << L"  --help                  Show this help message\n";
}

int wmain(int argc, wchar_t* argv[]) {
    // 1. Check for askpass mode
    for (int i = 1; i < argc; ++i) {
        if (_wcsicmp(argv[i], L"--askpass") == 0) {
            // Retrieve password from environment variable
            wchar_t envPass[1024];
            DWORD len = GetEnvironmentVariableW(L"TOINET_SSH_PASS", envPass, 1024);
            if (len > 0) {
                std::wcout << envPass << L"\n";
            }
            return 0;
        }
    }

    SSHConfig config;

    for (int i = 1; i < argc; ++i) {
        std::wstring arg = argv[i];
        if (arg == L"--help" || arg == L"-h") {
            PrintHelp();
            return 0;
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

    // Job Object for clean process tree termination
    HANDLE hJob = CreateJobObjectW(NULL, NULL);
    if (hJob) {
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION jeli{};
        jeli.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(hJob, JobObjectExtendedLimitInformation, &jeli, sizeof(jeli));
    }

    std::wstring sshExe = FindSshExecutable();
    wchar_t currentExe[MAX_PATH];
    GetModuleFileNameW(NULL, currentExe, MAX_PATH);

    // Configure AskPass
    std::wstring askpassCmd = L"\"" + std::wstring(currentExe) + L"\" --askpass";
    SetEnvironmentVariableW(L"SSH_ASKPASS", askpassCmd.c_str());
    SetEnvironmentVariableW(L"SSH_ASKPASS_REQUIRE", L"force");
    SetEnvironmentVariableW(L"DISPLAY", L":0");
    SetEnvironmentVariableW(L"TOINET_SSH_PASS", config.pass.c_str());

    std::wcout << L"[INFO] Starting SSH Tunnel to " << config.user << L"@" << config.host << L":" << config.port
               << L" -> SOCKS5 " << config.bindAddress << L":" << config.socksPort << std::endl;

    while (!g_stopRequested.load()) {
        std::wcout << L"[STATUS] CONNECTING" << std::endl;

        std::wostringstream cmd;
        cmd << L"\"" << sshExe << L"\""
            << L" -N"
            << L" -D " << config.bindAddress << L":" << config.socksPort
            << L" -p " << config.port;

        if (config.bindAddress == L"0.0.0.0" || config.bindAddress == L"*") {
            cmd << L" -o GatewayPorts=yes";
        }

        cmd << L" -o StrictHostKeyChecking=no"
            << L" -o UserKnownHostsFile=NUL"
            << L" -o ExitOnForwardFailure=yes"
            << L" -o ServerAliveInterval=15"
            << L" -o ServerAliveCountMax=3"
            << L" -o PreferredAuthentications=password"
            << L" " << config.user << L"@" << config.host;

        std::wstring cmdStr = cmd.str();
        std::vector<wchar_t> cmdBuf(cmdStr.begin(), cmdStr.end());
        cmdBuf.push_back(L'\0');

        STARTUPINFOW si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};

        BOOL success = CreateProcessW(
            NULL,
            cmdBuf.data(),
            NULL,
            NULL,
            FALSE,
            CREATE_NO_WINDOW,
            NULL,
            NULL,
            &si,
            &pi
        );

        if (!success) {
            std::wcerr << L"[STATUS] ERROR: Failed to execute ssh.exe (" << GetLastError() << L")" << std::endl;
            if (!config.autoReconnect || g_stopRequested.load()) break;
            std::this_thread::sleep_for(std::chrono::seconds(config.reconnectInterval));
            continue;
        }

        if (hJob) {
            AssignProcessToJobObject(hJob, pi.hProcess);
        }

        bool wasConnected = false;
        int checkCount = 0;
        uint64_t connectTime = 0;

        while (!g_stopRequested.load()) {
            DWORD exitCode = 0;
            if (!GetExitCodeProcess(pi.hProcess, &exitCode) || exitCode != STILL_ACTIVE) {
                std::wcout << L"[STATUS] DISCONNECTED (ssh exited with code " << exitCode << L")" << std::endl;
                break;
            }

            bool portListening = CheckPortAvailable(config.socksPort);

            if (portListening && !wasConnected) {
                wasConnected = true;
                connectTime = GetTickCount64();
                std::wcout << L"[STATUS] CONNECTED 127.0.0.1:" << config.socksPort << std::endl;
                if (!config.keyFile.empty()) {
                    DeleteFileW(config.keyFile.c_str());
                }
            } else if (!portListening && wasConnected) {
                wasConnected = false;
                std::wcout << L"[STATUS] CONNECTING" << std::endl;
            } else if (!portListening && !wasConnected) {
                checkCount++;
                if (checkCount > 40) { // ~8 seconds timeout
                    std::wcerr << L"[STATUS] ERROR: SSH session timeout (port not opened)" << std::endl;
                    break;
                }
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(200));
        }

        if (pi.hProcess) {
            TerminateProcess(pi.hProcess, 0);
            WaitForSingleObject(pi.hProcess, 1000);
            CloseHandle(pi.hProcess);
        }
        if (pi.hThread) {
            CloseHandle(pi.hThread);
        }

        if (g_stopRequested.load() || !config.autoReconnect) {
            break;
        }

        std::wcout << L"[INFO] Waiting " << config.reconnectInterval << L"s before reconnecting..." << std::endl;
        for (int i = 0; i < config.reconnectInterval * 10 && !g_stopRequested.load(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    std::wcout << L"[STATUS] STOPPED" << std::endl;

    if (hJob) {
        CloseHandle(hJob);
    }
    WSACleanup();
    return 0;
}
