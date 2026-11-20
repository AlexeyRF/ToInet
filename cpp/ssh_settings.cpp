#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#ifndef _WINSOCK_DEPRECATED_NO_WARNINGS
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#endif

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <tlhelp32.h>
#include <commctrl.h>
#include <dwmapi.h>
#include <shellapi.h>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "shell32.lib")

// Control IDs
#define IDC_BTN_MASK_ALL     101
#define IDC_EDIT_HOST        102
#define IDC_EDIT_PORT        103
#define IDC_EDIT_USER        104
#define IDC_EDIT_PASS        105
#define IDC_EDIT_SOCKS       106
#define IDC_CHK_RECONNECT    107
#define IDC_CHK_SHARE_LAN    108
#define IDC_BTN_TOGGLE       109
#define IDC_BTN_SAVE         110
#define IDC_BTN_CLOSE        111
#define IDT_STATUS_TIMER     201

enum AppLang { LANG_RU, LANG_EN, LANG_FR };
static AppLang g_lang = LANG_RU;

struct LStr {
    const wchar_t* ru;
    const wchar_t* en;
    const wchar_t* fr;
    const wchar_t* get() const {
        if (g_lang == LANG_FR) return fr;
        if (g_lang == LANG_EN) return en;
        return ru;
    }
};

static const LStr T_WIN_TITLE      = { L"SSH SOCKS5 Туннель", L"SSH SOCKS5 Tunnel", L"Tunnel SSH SOCKS5" };
static const LStr T_HEADER_TITLE   = { L"Настройки SSH Туннеля", L"SSH Tunnel Settings", L"Paramètres du tunnel SSH" };
static const LStr T_BTN_MASK_ALL   = { L"👁 Скрыть всё", L"👁 Mask all", L"👁 Masquer tout" };
static const LStr T_BTN_SHOW_ALL   = { L"👁 Показать всё", L"👁 Show all", L"👁 Afficher tout" };

static const LStr T_GRP_SERVER     = { L"Параметры SSH сервера", L"SSH Server Credentials", L"Identifiants du serveur SSH" };
static const LStr T_LBL_HOST       = { L"Хост / IP:", L"Host / IP:", L"Hôte / IP :" };
static const LStr T_LBL_PORT       = { L"SSH Порт:", L"SSH Port:", L"Port SSH :" };
static const LStr T_LBL_USER       = { L"Логин:", L"User:", L"Utilisateur :" };
static const LStr T_LBL_PASS       = { L"Пароль:", L"Password:", L"Mot de passe :" };

static const LStr T_GRP_LOCAL      = { L"Локальный прокси (SOCKS5)", L"Local SOCKS5 Proxy", L"Proxy local SOCKS5" };
static const LStr T_LBL_SOCKS      = { L"Порт:", L"Port:", L"Port :" };
static const LStr T_CHK_RECONNECT  = { L"Автопереподключение", L"Auto reconnect", L"Reconnexion automatique" };
static const LStr T_CHK_SHARE_LAN  = { L"Раздавать в локальную сеть (0.0.0.0 вместо 127.0.0.1)", L"Share to local network (0.0.0.0 instead of 127.0.0.1)", L"Partager sur le réseau local (0.0.0.0 au lieu de 127.0.0.1)" };

static const LStr T_STATUS_DISC    = { L"⚪ Отключено", L"⚪ Disconnected", L"⚪ Déconnecté" };
static const LStr T_BTN_START      = { L"Запустить туннель", L"Start Tunnel", L"Démarrer le tunnel" };
static const LStr T_BTN_STOP       = { L"Остановить туннель", L"Stop Tunnel", L"Arrêter le tunnel" };
static const LStr T_BTN_SAVE       = { L"Сохранить", L"Save", L"Enregistrer" };
static const LStr T_BTN_CLOSE      = { L"Закрыть", L"Close", L"Fermer" };

static const LStr T_MSG_SAVED      = { L"Настройки SSH успешно сохранены!", L"SSH settings saved successfully!", L"Paramètres SSH enregistrés avec succès !" };
static const LStr T_MSG_TITLE_OK   = { L"Сохранено", L"Saved", L"Enregistré" };
static const LStr T_MSG_TITLE_WARN = { L"Предупреждение", L"Warning", L"Avertissement" };
static const LStr T_MSG_TITLE_ERR  = { L"Ошибка", L"Error", L"Erreur" };

static const LStr T_WARN_LAN_TITLE = { L"Предупреждение безопасности", L"Security Warning", L"Avertissement de sécurité" };
static const LStr T_WARN_LAN_TEXT  = {
    L"⚠️ Внимание!\n\n"
    L"Включение раздачи на 0.0.0.0 откроет доступ к вашему SOCKS5 прокси для всех устройств в локальной сети (Wi-Fi / LAN).\n"
    L"Любой компьютер, телефон или устройство в вашей сети сможет направлять трафик через ваш SSH туннель без авторизации.\n\n"
    L"Вы действительно хотите включить раздачу?",
    L"⚠️ Warning!\n\n"
    L"Enabling sharing on 0.0.0.0 will expose your SOCKS5 proxy to all devices in the local network (Wi-Fi / LAN).\n"
    L"Any computer or device in your local network will be able to route traffic through your SSH tunnel without authentication.\n\n"
    L"Are you sure you want to enable LAN sharing?",
    L"⚠️ Attention !\n\n"
    L"L'activation du partage sur 0.0.0.0 permettra à tous les appareils de votre réseau local (Wi-Fi / LAN) d'accéder à votre proxy SOCKS5.\n"
    L"N'importe quel appareil pourra acheminer du trafic sans authentification.\n\n"
    L"Voulez-vous vraiment activer le partage ?"
};

static const LStr T_ERR_NO_CRED    = { L"SSH сервер или логин не настроены. Заполните поля хоста и логина.", L"SSH host or username is not configured. Please fill in host and user.", L"Hôte SSH ou nom d'utilisateur non configuré." };
static const LStr T_ERR_NO_EXE     = { L"Файл bin/ssh_tunnel.exe не найден! Соберите проект через build.bat.", L"File bin/ssh_tunnel.exe not found! Build it via build.bat.", L"Fichier bin/ssh_tunnel.exe introuvable !" };

// Global UI Handles
static HWND g_hMainWnd = NULL;
static HWND g_hBtnMaskAll = NULL;
static HWND g_hHostEdit = NULL;
static HWND g_hPortEdit = NULL;
static HWND g_hUserEdit = NULL;
static HWND g_hPassEdit = NULL;
static HWND g_hSocksEdit = NULL;
static HWND g_hChkReconnect = NULL;
static HWND g_hChkShareLan = NULL;
static HWND g_hBtnToggle = NULL;
static HWND g_hBtnSave = NULL;
static HWND g_hBtnClose = NULL;

static HFONT g_hFontTitle = NULL;
static HFONT g_hFontNormal = NULL;
static HFONT g_hFontBold = NULL;
static HFONT g_hFontSmall = NULL;

static HBRUSH g_hBrushBg = NULL;      // #181818
static HBRUSH g_hBrushEditBg = NULL;  // #242424

static COLORREF g_colBg = RGB(24, 24, 24);
static COLORREF g_colEditBg = RGB(36, 36, 36);
static COLORREF g_colText = RGB(204, 204, 204);
static COLORREF g_colTitle = RGB(93, 173, 226);

// State & Paths
static std::wstring g_rootDir;
static std::wstring g_configPath;
static bool g_hideCredentials = true;
static bool g_isTunnelRunning = false;
static std::wstring g_statusText;
static HWND g_hoveredBtn = NULL;

std::wstring Utf8ToUtf16(const std::string& str) {
    if (str.empty()) return L"";
    int size = MultiByteToWideChar(CP_UTF8, 0, str.c_str(), (int)str.size(), NULL, 0);
    std::wstring out(size, 0);
    MultiByteToWideChar(CP_UTF8, 0, str.c_str(), (int)str.size(), &out[0], size);
    return out;
}

std::string Utf16ToUtf8(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int size = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), NULL, 0, NULL, NULL);
    std::string out(size, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), &out[0], size, NULL, NULL);
    return out;
}

void InitPaths() {
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);

    std::wstring rootCand1 = dir;
    std::wstring rootCand2 = dir + L"\\..";
    std::wstring rootCand3 = dir + L"\\..\\..";

    if (GetFileAttributesW((rootCand1 + L"\\data").c_str()) != INVALID_FILE_ATTRIBUTES) {
        g_rootDir = rootCand1;
    } else if (GetFileAttributesW((rootCand2 + L"\\data").c_str()) != INVALID_FILE_ATTRIBUTES) {
        g_rootDir = rootCand2;
    } else {
        g_rootDir = rootCand3;
    }

    wchar_t fullRoot[MAX_PATH];
    if (GetFullPathNameW(g_rootDir.c_str(), MAX_PATH, fullRoot, NULL)) {
        g_rootDir = fullRoot;
    }
    g_configPath = g_rootDir + L"\\data\\config.json";
}

// JSON helpers
static std::string ExtractJsonStr(const std::string& json, const std::string& key) {
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

static int ExtractJsonInt(const std::string& json, const std::string& key, int default_val) {
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

static bool ExtractJsonBool(const std::string& json, const std::string& key, bool default_val) {
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

static void ReplaceJsonStr(std::string& json, const std::string& key, const std::string& val) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return;
    size_t q1 = json.find('\"', pos);
    if (q1 == std::string::npos) return;
    size_t q2 = json.find('\"', q1 + 1);
    if (q2 == std::string::npos) return;
    json.replace(q1 + 1, q2 - q1 - 1, val);
}

static void ReplaceJsonInt(std::string& json, const std::string& key, int val) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return;
    size_t s = json.find_first_of("0123456789-", pos);
    if (s == std::string::npos) return;
    size_t e = json.find_first_not_of("0123456789-", s);
    std::string vstr = std::to_string(val);
    json.replace(s, e - s, vstr);
}

static void ReplaceJsonBool(std::string& json, const std::string& key, bool val) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return;
    size_t s = json.find_first_of("tf", pos);
    if (s == std::string::npos) return;
    size_t e = json.find_first_of(" ,\r\n}", s);
    std::string vstr = val ? "true" : "false";
    json.replace(s, e - s, vstr);
}

static void UpsertJsonStr(std::string& json, const std::string& key, const std::string& val) {
    if (json.find("\"" + key + "\"") != std::string::npos) {
        ReplaceJsonStr(json, key, val);
    } else {
        size_t brace = json.rfind('}');
        if (brace != std::string::npos) {
            std::string entry = ",\n  \"" + key + "\": \"" + val + "\"\n";
            json.insert(brace, entry);
        }
    }
}

static void UpsertJsonInt(std::string& json, const std::string& key, int val) {
    if (json.find("\"" + key + "\"") != std::string::npos) {
        ReplaceJsonInt(json, key, val);
    } else {
        size_t brace = json.rfind('}');
        if (brace != std::string::npos) {
            std::string entry = ",\n  \"" + key + "\": " + std::to_string(val) + "\n";
            json.insert(brace, entry);
        }
    }
}

static void UpsertJsonBool(std::string& json, const std::string& key, bool val) {
    if (json.find("\"" + key + "\"") != std::string::npos) {
        ReplaceJsonBool(json, key, val);
    } else {
        size_t brace = json.rfind('}');
        if (brace != std::string::npos) {
            std::string entry = ",\n  \"" + key + "\": " + (val ? "true" : "false") + "\n";
            json.insert(brace, entry);
        }
    }
}

// Tunnel management
bool IsProcessRunning(const wchar_t* processName) {
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return false;
    PROCESSENTRY32W pe = { sizeof(pe) };
    bool found = false;
    if (Process32FirstW(hSnap, &pe)) {
        do {
            if (_wcsicmp(pe.szExeFile, processName) == 0) {
                found = true;
                break;
            }
        } while (Process32NextW(hSnap, &pe));
    }
    CloseHandle(hSnap);
    return found;
}

bool CheckPortListening(int port) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) return false;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<u_short>(port));
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    u_long nonBlocking = 1;
    ioctlsocket(s, FIONBIO, &nonBlocking);
    int res = connect(s, (sockaddr*)&addr, sizeof(addr));
    bool open = false;
    if (res == 0) {
        open = true;
    } else {
        fd_set writeSet;
        FD_ZERO(&writeSet);
        FD_SET(s, &writeSet);
        timeval tv{ 0, 80000 }; // 80 ms
        if (select(0, NULL, &writeSet, NULL, &tv) > 0) {
            int err = 0;
            int errLen = sizeof(err);
            if (getsockopt(s, SOL_SOCKET, SO_ERROR, (char*)&err, &errLen) == 0 && err == 0) {
                open = true;
            }
        }
    }
    closesocket(s);
    return open;
}

bool IsTunnelRunning(int port) {
    return IsProcessRunning(L"ssh_tunnel.exe") || CheckPortListening(port);
}

void StopTunnel() {
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap != INVALID_HANDLE_VALUE) {
        PROCESSENTRY32W pe = { sizeof(pe) };
        if (Process32FirstW(hSnap, &pe)) {
            do {
                if (_wcsicmp(pe.szExeFile, L"ssh_tunnel.exe") == 0) {
                    HANDLE hProc = OpenProcess(PROCESS_TERMINATE, FALSE, pe.th32ProcessID);
                    if (hProc) {
                        TerminateProcess(hProc, 0);
                        CloseHandle(hProc);
                    }
                }
            } while (Process32NextW(hSnap, &pe));
        }
        CloseHandle(hSnap);
    }
}

bool StartTunnel(const std::wstring& host, int port, const std::wstring& user, const std::wstring& pass, int socksPort, bool shareLan, bool autoReconnect) {
    if (host.empty() || user.empty()) {
        MessageBoxW(g_hMainWnd, T_ERR_NO_CRED.get(), T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONWARNING);
        return false;
    }
    std::wstring exe = g_rootDir + L"\\bin\\ssh_tunnel.exe";
    if (GetFileAttributesW(exe.c_str()) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(g_hMainWnd, T_ERR_NO_EXE.get(), T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONERROR);
        return false;
    }

    std::wstring bindAddr = shareLan ? L"0.0.0.0" : L"127.0.0.1";
    std::wstring cmd = L"\"" + exe + L"\" --host \"" + host + L"\" --port " + std::to_wstring(port) +
                       L" --user \"" + user + L"\" --socks-port " + std::to_wstring(socksPort) +
                       L" --bind " + bindAddr + L" --interval 5";

    if (!pass.empty()) {
        cmd += L" --pass \"" + pass + L"\"";
    }
    if (!autoReconnect) {
        cmd += L" --no-reconnect";
    }

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = {};
    std::vector<wchar_t> cmdBuf(cmd.begin(), cmd.end());
    cmdBuf.push_back(0);

    if (CreateProcessW(NULL, cmdBuf.data(), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        return true;
    }
    return false;
}

void ApplyMasking(bool mask) {
    g_hideCredentials = mask;
    wchar_t passChar = mask ? L'•' : 0;
    SendMessageW(g_hHostEdit, EM_SETPASSWORDCHAR, (WPARAM)passChar, 0);
    SendMessageW(g_hUserEdit, EM_SETPASSWORDCHAR, (WPARAM)passChar, 0);
    SendMessageW(g_hPassEdit, EM_SETPASSWORDCHAR, (WPARAM)passChar, 0);

    InvalidateRect(g_hHostEdit, NULL, TRUE);
    InvalidateRect(g_hUserEdit, NULL, TRUE);
    InvalidateRect(g_hPassEdit, NULL, TRUE);

    SetWindowTextW(g_hBtnMaskAll, mask ? T_BTN_SHOW_ALL.get() : T_BTN_MASK_ALL.get());
}

void LoadConfigData() {
    std::ifstream file(g_configPath, std::ios::binary);
    std::string content;
    if (file.is_open()) {
        std::stringstream ss;
        ss << file.rdbuf();
        content = ss.str();
        file.close();
    }

    std::string lang = ExtractJsonStr(content, "language");
    if (lang == "fr") g_lang = LANG_FR;
    else if (lang == "en") g_lang = LANG_EN;
    else g_lang = LANG_RU;

    std::string host = ExtractJsonStr(content, "ssh_host");
    SetWindowTextW(g_hHostEdit, Utf8ToUtf16(host).c_str());

    int port = ExtractJsonInt(content, "ssh_port", 22);
    SetWindowTextW(g_hPortEdit, std::to_wstring(port).c_str());

    std::string user = ExtractJsonStr(content, "ssh_user");
    SetWindowTextW(g_hUserEdit, Utf8ToUtf16(user).c_str());

    std::string pass = ExtractJsonStr(content, "ssh_pass");
    SetWindowTextW(g_hPassEdit, Utf8ToUtf16(pass).c_str());

    int socksPort = ExtractJsonInt(content, "ssh_socks_port", 1770);
    SetWindowTextW(g_hSocksEdit, std::to_wstring(socksPort).c_str());

    bool reconnect = ExtractJsonBool(content, "ssh_auto_reconnect", true);
    SendMessageW(g_hChkReconnect, BM_SETCHECK, reconnect ? BST_CHECKED : BST_UNCHECKED, 0);

    bool shareLan = ExtractJsonBool(content, "ssh_share_lan", false);
    SendMessageW(g_hChkShareLan, BM_SETCHECK, shareLan ? BST_CHECKED : BST_UNCHECKED, 0);

    g_hideCredentials = ExtractJsonBool(content, "ssh_hide_credentials", true);
    ApplyMasking(g_hideCredentials);
}

bool SaveConfigData(bool silent) {
    wchar_t bufH[256] = {}, bufP[32] = {}, bufU[256] = {}, bufPass[256] = {}, bufS[32] = {};
    GetWindowTextW(g_hHostEdit, bufH, 256);
    GetWindowTextW(g_hPortEdit, bufP, 32);
    GetWindowTextW(g_hUserEdit, bufU, 256);
    GetWindowTextW(g_hPassEdit, bufPass, 256);
    GetWindowTextW(g_hSocksEdit, bufS, 32);

    int port = _wtoi(bufP);
    if (port <= 0 || port > 65535) port = 22;
    int socksPort = _wtoi(bufS);
    if (socksPort < 1024 || socksPort > 65535) socksPort = 1770;

    bool reconnect = (SendMessageW(g_hChkReconnect, BM_GETCHECK, 0, 0) == BST_CHECKED);
    bool shareLan = (SendMessageW(g_hChkShareLan, BM_GETCHECK, 0, 0) == BST_CHECKED);

    std::ifstream file(g_configPath, std::ios::binary);
    std::string content;
    if (file.is_open()) {
        std::stringstream ss;
        ss << file.rdbuf();
        content = ss.str();
        file.close();
    } else {
        content = "{\n}\n";
    }

    UpsertJsonStr(content, "ssh_host", Utf16ToUtf8(bufH));
    UpsertJsonInt(content, "ssh_port", port);
    UpsertJsonStr(content, "ssh_user", Utf16ToUtf8(bufU));
    UpsertJsonStr(content, "ssh_pass", Utf16ToUtf8(bufPass));
    UpsertJsonInt(content, "ssh_socks_port", socksPort);
    UpsertJsonBool(content, "ssh_auto_reconnect", reconnect);
    UpsertJsonBool(content, "ssh_share_lan", shareLan);
    UpsertJsonBool(content, "ssh_hide_credentials", g_hideCredentials);

    std::ofstream out(g_configPath, std::ios::binary | std::ios::trunc);
    if (out.is_open()) {
        out.write(content.c_str(), content.size());
        out.close();
        if (!silent) {
            MessageBoxW(g_hMainWnd, T_MSG_SAVED.get(), T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
        }
        return true;
    }
    return false;
}

void UpdateStatusUI() {
    wchar_t bufS[32] = {};
    GetWindowTextW(g_hSocksEdit, bufS, 32);
    int socksPort = _wtoi(bufS);
    if (socksPort <= 0) socksPort = 1770;

    bool running = IsTunnelRunning(socksPort);
    bool stateChanged = (running != g_isTunnelRunning);
    g_isTunnelRunning = running;

    bool shareLan = (SendMessageW(g_hChkShareLan, BM_GETCHECK, 0, 0) == BST_CHECKED);
    const wchar_t* bindHost = shareLan ? L"0.0.0.0" : L"127.0.0.1";

    if (running) {
        wchar_t buf[256];
        swprintf_s(buf, 256, (g_lang == LANG_RU) ? L"🟢 Подключено (SOCKS5 активен на %s:%d)" :
                             ((g_lang == LANG_FR) ? L"🟢 Connecté (SOCKS5 actif sur %s:%d)" :
                                                    L"🟢 Connected (SOCKS5 listening on %s:%d)"), bindHost, socksPort);
        g_statusText = buf;
        SetWindowTextW(g_hBtnToggle, T_BTN_STOP.get());
    } else {
        g_statusText = T_STATUS_DISC.get();
        SetWindowTextW(g_hBtnToggle, T_BTN_START.get());
    }

    if (g_hMainWnd) {
        RECT rc = { 14, 274, 436, 298 };
        InvalidateRect(g_hMainWnd, &rc, FALSE);
        if (stateChanged && g_hBtnToggle) {
            InvalidateRect(g_hBtnToggle, NULL, FALSE);
        }
    }
}

void ToggleTunnel() {
    SaveConfigData(true);
    wchar_t bufS[32] = {};
    GetWindowTextW(g_hSocksEdit, bufS, 32);
    int socksPort = _wtoi(bufS);
    if (socksPort <= 0) socksPort = 1770;

    if (IsTunnelRunning(socksPort)) {
        StopTunnel();
    } else {
        wchar_t bufH[256] = {}, bufP[32] = {}, bufU[256] = {}, bufPass[256] = {};
        GetWindowTextW(g_hHostEdit, bufH, 256);
        GetWindowTextW(g_hPortEdit, bufP, 32);
        GetWindowTextW(g_hUserEdit, bufU, 256);
        GetWindowTextW(g_hPassEdit, bufPass, 256);
        int port = _wtoi(bufP);
        if (port <= 0) port = 22;
        bool reconnect = (SendMessageW(g_hChkReconnect, BM_GETCHECK, 0, 0) == BST_CHECKED);
        bool shareLan = (SendMessageW(g_hChkShareLan, BM_GETCHECK, 0, 0) == BST_CHECKED);

        StartTunnel(bufH, port, bufU, bufPass, socksPort, shareLan, reconnect);
    }
    UpdateStatusUI();
}

// Subclassed button proc for hover tracking
LRESULT CALLBACK ButtonSubclassProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam, UINT_PTR uIdSubclass, DWORD_PTR dwRefData) {
    (void)dwRefData;
    switch (uMsg) {
    case WM_MOUSEMOVE:
        if (g_hoveredBtn != hWnd) {
            HWND prev = g_hoveredBtn;
            g_hoveredBtn = hWnd;
            if (prev) InvalidateRect(prev, NULL, FALSE);
            InvalidateRect(hWnd, NULL, FALSE);

            TRACKMOUSEEVENT tme = { sizeof(TRACKMOUSEEVENT), TME_LEAVE, hWnd, 0 };
            TrackMouseEvent(&tme);
        }
        break;
    case WM_MOUSELEAVE:
        if (g_hoveredBtn == hWnd) {
            g_hoveredBtn = NULL;
            InvalidateRect(hWnd, NULL, FALSE);
        }
        break;
    case WM_NCDESTROY:
        RemoveWindowSubclass(hWnd, ButtonSubclassProc, uIdSubclass);
        break;
    }
    return DefSubclassProc(hWnd, uMsg, wParam, lParam);
}

// Custom button renderer (calm, muted palette)
void DrawCustomButton(LPDRAWITEMSTRUCT dis) {
    HDC hdc = dis->hDC;
    RECT rc = dis->rcItem;
    bool isSelected = (dis->itemState & ODS_SELECTED) != 0;
    bool isHovered = (dis->hwndItem == g_hoveredBtn);

    FillRect(hdc, &rc, g_hBrushBg);

    COLORREF colBg;
    COLORREF colBorder;

    if (dis->CtlID == IDC_BTN_TOGGLE) {
        if (g_isTunnelRunning) {
            // Muted Red (Stop)
            if (isSelected)      { colBg = RGB(105, 35, 35); colBorder = RGB(135, 48, 48); }
            else if (isHovered)  { colBg = RGB(150, 55, 55); colBorder = RGB(170, 68, 68); }
            else                 { colBg = RGB(130, 45, 45); colBorder = RGB(135, 48, 48); }
        } else {
            // Muted Green (Start)
            if (isSelected)      { colBg = RGB(35, 78, 42);  colBorder = RGB(48, 100, 58); }
            else if (isHovered)  { colBg = RGB(55, 112, 65); colBorder = RGB(70, 130, 80); }
            else                 { colBg = RGB(45, 95, 55);  colBorder = RGB(48, 100, 58); }
        }
    } else if (dis->CtlID == IDC_BTN_SAVE) {
        // Muted Blue
        if (isSelected)      { colBg = RGB(24, 62, 96);  colBorder = RGB(36, 82, 126); }
        else if (isHovered)  { colBg = RGB(42, 92, 140); colBorder = RGB(52, 110, 165); }
        else                 { colBg = RGB(32, 78, 120); colBorder = RGB(36, 82, 126); }
    } else if (dis->CtlID == IDC_BTN_CLOSE) {
        // Dark Charcoal
        if (isSelected)      { colBg = RGB(36, 36, 36);  colBorder = RGB(58, 58, 58); }
        else if (isHovered)  { colBg = RGB(60, 60, 60);  colBorder = RGB(75, 75, 75); }
        else                 { colBg = RGB(46, 46, 46);  colBorder = RGB(58, 58, 58); }
    } else { // IDC_BTN_MASK_ALL
        // Compact gray
        if (isSelected)      { colBg = RGB(32, 32, 32);  colBorder = RGB(50, 50, 50); }
        else if (isHovered)  { colBg = RGB(52, 52, 52);  colBorder = RGB(72, 72, 72); }
        else                 { colBg = RGB(40, 40, 40);  colBorder = RGB(60, 60, 60); }
    }

    HBRUSH hBr = CreateSolidBrush(colBg);
    HPEN hPen = CreatePen(PS_SOLID, 1, colBorder);
    HGDIOBJ oldBr = SelectObject(hdc, hBr);
    HGDIOBJ oldPen = SelectObject(hdc, hPen);

    RoundRect(hdc, rc.left, rc.top, rc.right, rc.bottom, 6, 6);

    SelectObject(hdc, oldBr);
    SelectObject(hdc, oldPen);
    DeleteObject(hBr);
    DeleteObject(hPen);

    wchar_t text[128];
    GetWindowTextW(dis->hwndItem, text, 128);
    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(220, 220, 220));
    SelectObject(hdc, (dis->CtlID == IDC_BTN_MASK_ALL) ? g_hFontSmall : g_hFontBold);
    DrawTextW(hdc, text, -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

// Window Procedure
LRESULT CALLBACK WndProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        g_hMainWnd = hWnd;

        g_hFontTitle  = CreateFontW(-14, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontNormal = CreateFontW(-12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold   = CreateFontW(-12, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontSmall  = CreateFontW(-11, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        // Mask All Button (Top right, Y=10)
        g_hBtnMaskAll = CreateWindowExW(0, L"BUTTON", T_BTN_MASK_ALL.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            320, 10, 114, 26, hWnd, (HMENU)IDC_BTN_MASK_ALL, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnMaskAll, ButtonSubclassProc, IDC_BTN_MASK_ALL, 0);

        // Group 1 Edits: Server
        g_hHostEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL,
            92, 60, 190, 24, hWnd, (HMENU)IDC_EDIT_HOST, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hHostEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hPortEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"22",
            WS_CHILD | WS_VISIBLE | ES_NUMBER | ES_AUTOHSCROLL,
            362, 60, 60, 24, hWnd, (HMENU)IDC_EDIT_PORT, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hPortEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hUserEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL,
            92, 92, 330, 24, hWnd, (HMENU)IDC_EDIT_USER, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hUserEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hPassEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | ES_PASSWORD | ES_AUTOHSCROLL,
            92, 124, 330, 24, hWnd, (HMENU)IDC_EDIT_PASS, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hPassEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Group 2: Local SOCKS5
        g_hSocksEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"1770",
            WS_CHILD | WS_VISIBLE | ES_NUMBER | ES_AUTOHSCROLL,
            92, 194, 65, 24, hWnd, (HMENU)IDC_EDIT_SOCKS, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hSocksEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkReconnect = CreateWindowExW(0, L"BUTTON", T_CHK_RECONNECT.get(),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX,
            172, 194, 250, 24, hWnd, (HMENU)IDC_CHK_RECONNECT, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hChkReconnect, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkShareLan = CreateWindowExW(0, L"BUTTON", T_CHK_SHARE_LAN.get(),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX,
            24, 228, 398, 24, hWnd, (HMENU)IDC_CHK_SHARE_LAN, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hChkShareLan, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Bottom Buttons (Y=304, H=34)
        g_hBtnToggle = CreateWindowExW(0, L"BUTTON", T_BTN_START.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            14, 304, 162, 34, hWnd, (HMENU)IDC_BTN_TOGGLE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnToggle, ButtonSubclassProc, IDC_BTN_TOGGLE, 0);

        g_hBtnSave = CreateWindowExW(0, L"BUTTON", T_BTN_SAVE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            184, 304, 126, 34, hWnd, (HMENU)IDC_BTN_SAVE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnSave, ButtonSubclassProc, IDC_BTN_SAVE, 0);

        g_hBtnClose = CreateWindowExW(0, L"BUTTON", T_BTN_CLOSE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            318, 304, 118, 34, hWnd, (HMENU)IDC_BTN_CLOSE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnClose, ButtonSubclassProc, IDC_BTN_CLOSE, 0);

        LoadConfigData();
        UpdateStatusUI();

        SetTimer(hWnd, IDT_STATUS_TIMER, 1000, NULL);
        return 0;
    }

    case WM_TIMER: {
        if (wParam == IDT_STATUS_TIMER) {
            UpdateStatusUI();
        }
        return 0;
    }

    case WM_ERASEBKGND: {
        HDC hdc = (HDC)wParam;
        RECT rc;
        GetClientRect(hWnd, &rc);
        FillRect(hdc, &rc, g_hBrushBg);
        return 1;
    }

    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT pdis = (LPDRAWITEMSTRUCT)lParam;
        if (pdis->CtlType == ODT_BUTTON) {
            DrawCustomButton(pdis);
            return TRUE;
        }
        break;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        int code = HIWORD(wParam);

        if (id == IDC_BTN_MASK_ALL) {
            g_hideCredentials = !g_hideCredentials;
            ApplyMasking(g_hideCredentials);
            SaveConfigData(true);
        } else if (id == IDC_CHK_SHARE_LAN && code == BN_CLICKED) {
            if (SendMessageW(g_hChkShareLan, BM_GETCHECK, 0, 0) == BST_CHECKED) {
                if (MessageBoxW(hWnd, T_WARN_LAN_TEXT.get(), T_WARN_LAN_TITLE.get(), MB_YESNO | MB_ICONWARNING) != IDYES) {
                    SendMessageW(g_hChkShareLan, BM_SETCHECK, BST_UNCHECKED, 0);
                }
            }
        } else if (id == IDC_BTN_TOGGLE) {
            ToggleTunnel();
        } else if (id == IDC_BTN_SAVE) {
            SaveConfigData(false);
        } else if (id == IDC_BTN_CLOSE) {
            DestroyWindow(hWnd);
        }
        return 0;
    }

    case WM_CTLCOLORBTN:
        return (INT_PTR)g_hBrushBg;

    case WM_CTLCOLOREDIT: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, RGB(240, 240, 240));
        SetBkColor(hdc, g_colEditBg);
        return (INT_PTR)g_hBrushEditBg;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        return (INT_PTR)g_hBrushBg;
    }

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hWnd, &ps);

        // 1. Header Title
        SelectObject(hdc, g_hFontTitle);
        SetTextColor(hdc, RGB(255, 255, 255));
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 16, 14, T_HEADER_TITLE.get(), (int)wcslen(T_HEADER_TITLE.get()));

        // 2. Group 1: Server (14, 42, 436, 166)
        HPEN hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        HGDIOBJ oldPen = SelectObject(hdc, hPenBorder);
        HGDIOBJ oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));
        RoundRect(hdc, 14, 42, 436, 166, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        // Group 1 Title
        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 24, 34, T_GRP_SERVER.get(), (int)wcslen(T_GRP_SERVER.get()));

        // Group 1 Labels
        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 24, 64, T_LBL_HOST.get(), (int)wcslen(T_LBL_HOST.get()));
        TextOutW(hdc, 292, 64, T_LBL_PORT.get(), (int)wcslen(T_LBL_PORT.get()));
        TextOutW(hdc, 24, 96, T_LBL_USER.get(), (int)wcslen(T_LBL_USER.get()));
        TextOutW(hdc, 24, 128, T_LBL_PASS.get(), (int)wcslen(T_LBL_PASS.get()));

        // 3. Group 2: Local SOCKS5 (14, 176, 436, 264)
        hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        oldPen = SelectObject(hdc, hPenBorder);
        oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));
        RoundRect(hdc, 14, 176, 436, 264, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        // Group 2 Title
        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 24, 168, T_GRP_LOCAL.get(), (int)wcslen(T_GRP_LOCAL.get()));

        // Group 2 Labels
        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 24, 198, T_LBL_SOCKS.get(), (int)wcslen(T_LBL_SOCKS.get()));

        // 4. Status Line (14, 274, 436, 296)
        SelectObject(hdc, g_hFontBold);
        if (g_isTunnelRunning) {
            SetTextColor(hdc, RGB(60, 175, 85));
        } else {
            SetTextColor(hdc, RGB(136, 136, 136));
        }
        RECT rcStatus = { 14, 274, 436, 296 };
        DrawTextW(hdc, g_statusText.c_str(), -1, &rcStatus, DT_CENTER | DT_SINGLELINE);

        EndPaint(hWnd, &ps);
        return 0;
    }

    case WM_DESTROY:
        KillTimer(hWnd, IDT_STATUS_TIMER);
        if (g_hFontTitle)  DeleteObject(g_hFontTitle);
        if (g_hFontNormal) DeleteObject(g_hFontNormal);
        if (g_hFontBold)   DeleteObject(g_hFontBold);
        if (g_hFontSmall)  DeleteObject(g_hFontSmall);
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hWnd, uMsg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE, PWSTR, int nCmdShow) {
    INITCOMMONCONTROLSEX icex = { sizeof(INITCOMMONCONTROLSEX), ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES };
    InitCommonControlsEx(&icex);

    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);

    LANGID langId = GetUserDefaultUILanguage();
    WORD priLang = langId & 0xFF;
    if (priLang == 0x0C) g_lang = LANG_FR;
    else if (priLang == 0x09) g_lang = LANG_EN;
    else g_lang = LANG_RU;

    InitPaths();

    g_statusText = T_STATUS_DISC.get();
    g_hBrushBg = CreateSolidBrush(g_colBg);
    g_hBrushEditBg = CreateSolidBrush(g_colEditBg);

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetSSHSettingsWnd";

    std::wstring icoPath = g_rootDir + L"\\icon.ico";
    HICON hIcon = (HICON)LoadImageW(NULL, icoPath.c_str(), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
    if (!hIcon) {
        icoPath = g_rootDir + L"\\..\\icon.ico";
        hIcon = (HICON)LoadImageW(NULL, icoPath.c_str(), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
    }
    if (hIcon) {
        wc.hIcon = hIcon;
        wc.hIconSm = hIcon;
    }

    RegisterClassExW(&wc);

    RECT rcWin = { 0, 0, 450, 352 };
    AdjustWindowRectEx(&rcWin, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE, 0);
    int width = rcWin.right - rcWin.left;
    int height = rcWin.bottom - rcWin.top;

    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);
    int x = (screenW - width) / 2;
    int y = (screenH - height) / 2;

    HWND hWnd = CreateWindowExW(
        0, wc.lpszClassName, T_WIN_TITLE.get(),
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        x, y, width, height,
        NULL, NULL, hInstance, NULL
    );

    if (!hWnd) {
        WSACleanup();
        return 1;
    }

    BOOL darkMode = TRUE;
    DwmSetWindowAttribute(hWnd, 20, &darkMode, sizeof(darkMode));
    DwmSetWindowAttribute(hWnd, 19, &darkMode, sizeof(darkMode));
    COLORREF captionColor = RGB(24, 24, 24);
    DwmSetWindowAttribute(hWnd, 35, &captionColor, sizeof(captionColor));

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        if (msg.message == WM_KEYDOWN && msg.wParam == VK_ESCAPE) {
            DestroyWindow(hWnd);
            break;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    DeleteObject(g_hBrushBg);
    DeleteObject(g_hBrushEditBg);
    WSACleanup();
    return (int)msg.wParam;
}
