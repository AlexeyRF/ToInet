#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <dwmapi.h>
#include <uxtheme.h>
#include <vssym32.h>
#include <shellapi.h>

#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "uxtheme.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "shell32.lib")

#pragma comment(linker,"\"/manifestdependency:type='win32' name='Microsoft.Windows.Common-Controls' version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

// Languages
enum Lang { LANG_RU = 0, LANG_EN, LANG_FR };
static Lang g_lang = LANG_RU;

struct LStr {
    const wchar_t* ru;
    const wchar_t* en;
    const wchar_t* fr;
};

static const wchar_t* Tr(const LStr& s) {
    if (g_lang == LANG_FR && s.fr) return s.fr;
    if (g_lang == LANG_EN && s.en) return s.en;
    return s.ru;
}

// Translations
static const LStr T_WIN_TITLE           = { L"Настройки автозапуска", L"Autostart Settings", L"Paramètres de démarrage" };
static const LStr T_GROUP_TOOLS         = { L"Инструменты для автозапуска", L"Tools to autostart", L"Outils au démarrage" };
static const LStr T_GROUP_PARAMS        = { L"Параметры запуска Windows и Tor", L"Startup & Tor Options", L"Options de démarrage et Tor" };

static const LStr T_TOOL_BYEDPI         = { L"zDPI (Обход DPI)", L"zDPI (DPI Bypass)", L"zDPI (Contournement DPI)" };
static const LStr T_TOOL_TOR            = { L"Tor (Onion/Мосты)", L"Tor (Onion/Bridges)", L"Tor (Onion/Ponts)" };
static const LStr T_TOOL_OPERA          = { L"Opera Proxy (VPN)", L"Opera Proxy (VPN)", L"Opera Proxy (VPN)" };
static const LStr T_TOOL_SSH            = { L"SSH Туннель (SOCKS5)", L"SSH Tunnel (SOCKS5)", L"Tunnel SSH (SOCKS5)" };
static const LStr T_TOOL_TGWS           = { L"Telegram WS Proxy", L"Telegram WS Proxy", L"Proxy Telegram WS" };
static const LStr T_TOOL_PROXIFIER      = { L"Внешний Proxifier (режим EMPTY)", L"External Proxifier (EMPTY mode)", L"Proxifier externe (mode EMPTY)" };
static const LStr T_TOOL_EXT            = { L"Доп. программы", L"External Programs", L"Programmes additionnels" };

static const LStr T_APP_AUTOSTART       = { L"Запускать ToInet-MAX при старте Windows", L"Start ToInet-MAX on Windows startup", L"Démarrer ToInet-MAX avec Windows" };
static const LStr T_AUTO_LAST           = { L"Подключать последний режим при запуске", L"Connect last mode on start", L"Reconnecter le dernier mode au démarrage" };
static const LStr T_TORRC_LABEL         = { L"Действие с torrc:", L"Action with torrc:", L"Action pour torrc :" };

static const LStr T_TORRC_OPT_NONE      = { L"Не трогать (None)", L"Do nothing (None)", L"Ne rien faire (None)" };
static const LStr T_TORRC_OPT_BRIDGES   = { L"Обновлять мосты", L"Update bridges only", L"Mettre à jour les ponts" };
static const LStr T_TORRC_OPT_FULL      = { L"Полное пересоздание", L"Full recreation", L"Recréation complète" };

static const LStr T_BTN_SAVE            = { L"Сохранить", L"Save", L"Enregistrer" };
static const LStr T_BTN_CANCEL          = { L"Отмена", L"Cancel", L"Annuler" };

static const LStr T_WARN_TITLE          = { L"Внимание", L"Warning", L"Attention" };
static const LStr T_TGWS_WARN           = {
    L"Павел Дуров признан в России экстремистом и не известно какие меры будут приняты в отношении телеграмма, поэтому вместо tgws стоит использовать tor или opera proxy. Включить автозапуск tgws?",
    L"Pavel Durov is recognized as an extremist in Russia and it is unknown what measures will be taken against Telegram, so instead of tgws you should use tor or opera proxy. Enable tgws autostart?",
    L"Pavel Durov est reconnu comme extrémiste en Russie et les mesures contre Telegram sont incertaines, il est donc recommandé d'utiliser Tor ou Opera proxy à la place de tgws. Activer le démarrage de tgws ?"
};

static const LStr T_MSG_SUCCESS_TITLE   = { L"Успех", L"Success", L"Succès" };
static const LStr T_MSG_SUCCESS         = { L"Настройки автозапуска сохранены.", L"Autostart settings saved.", L"Paramètres de démarrage enregistrés." };
static const LStr T_MSG_ERROR_TITLE     = { L"Ошибка", L"Error", L"Erreur" };
static const LStr T_MSG_ERROR_AUTORUN   = { L"Не удалось настроить автозапуск в реестре.", L"Failed to set autorun in registry.", L"Échec de la configuration du démarrage dans le registre." };

// Control IDs
#define IDC_CHK_BYEDPI       201
#define IDC_CHK_TOR          202
#define IDC_CHK_OPERA        203
#define IDC_CHK_SSH          204
#define IDC_CHK_TGWS         205
#define IDC_CHK_PROXIFIER    206
#define IDC_CHK_EXT          207

#define IDC_CHK_APP_AUTO     210
#define IDC_CHK_AUTO_LAST    211
#define IDC_COMBO_TORRC      212

#define IDC_BTN_SAVE         220
#define IDC_BTN_CANCEL       221

// UI Elements
static HWND g_hMainWnd = NULL;
static HWND g_hChkByeDPI = NULL;
static HWND g_hChkTor = NULL;
static HWND g_hChkOpera = NULL;
static HWND g_hChkSSH = NULL;
static HWND g_hChkTGWS = NULL;
static HWND g_hChkProxifier = NULL;
static HWND g_hChkExt = NULL;

static HWND g_hChkAppAuto = NULL;
static HWND g_hChkAutoLast = NULL;
static HWND g_hComboTorrc = NULL;

static HWND g_hBtnSave = NULL;
static HWND g_hBtnCancel = NULL;

static HFONT g_hFontNormal = NULL;
static HFONT g_hFontBold = NULL;

static HBRUSH g_hBrushBg = NULL;      // #181818
static HBRUSH g_hBrushEditBg = NULL;  // #242424

static COLORREF g_colBg = RGB(24, 24, 24);
static COLORREF g_colText = RGB(224, 224, 224);
static COLORREF g_colTitle = RGB(93, 173, 226);

static std::wstring g_rootDir;
static std::wstring g_configPath;
static HWND g_hoveredBtn = NULL;

static bool g_initialAppAuto = false;

// UTF conversions
static std::wstring Utf8ToUtf16(const std::string& str) {
    if (str.empty()) return L"";
    int size = MultiByteToWideChar(CP_UTF8, 0, str.c_str(), (int)str.size(), NULL, 0);
    std::wstring out(size, 0);
    MultiByteToWideChar(CP_UTF8, 0, str.c_str(), (int)str.size(), &out[0], size);
    return out;
}

static std::string Utf16ToUtf8(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int size = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), NULL, 0, NULL, NULL);
    std::string out(size, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), &out[0], size, NULL, NULL);
    return out;
}

static void InitPaths() {
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);

    std::wstring rootCand1 = dir;
    std::wstring rootCand2 = dir + L"\\..";

    DWORD attr1 = GetFileAttributesW((rootCand1 + L"\\data\\config.json").c_str());
    if (attr1 != INVALID_FILE_ATTRIBUTES) {
        g_rootDir = rootCand1;
    } else {
        g_rootDir = rootCand2;
    }

    wchar_t fullRoot[MAX_PATH];
    GetFullPathNameW(g_rootDir.c_str(), MAX_PATH, fullRoot, NULL);
    g_rootDir = fullRoot;
    g_configPath = g_rootDir + L"\\data\\config.json";
}

// JSON helpers
static std::string ExtractJsonStr(const std::string& json, const std::string& key, const std::string& defVal = "") {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return defVal;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return defVal;
    pos = json.find('\"', pos);
    if (pos == std::string::npos) return defVal;
    size_t endPos = json.find('\"', pos + 1);
    if (endPos == std::string::npos) return defVal;
    return json.substr(pos + 1, endPos - pos - 1);
}

static bool ExtractJsonBool(const std::string& json, const std::string& key, bool defVal = false) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return defVal;
    pos = json.find(':', pos);
    if (pos == std::string::npos) return defVal;
    size_t tPos = json.find("true", pos);
    size_t fPos = json.find("false", pos);
    size_t nextComma = json.find_first_of(",}\n\r", pos);
    if (tPos != std::string::npos && tPos < nextComma) return true;
    if (fPos != std::string::npos && fPos < nextComma) return false;
    return defVal;
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

static void UpsertJsonToolsArray(std::string& json, const std::vector<std::string>& tools) {
    std::string arrStr = "[\n";
    for (size_t i = 0; i < tools.size(); ++i) {
        arrStr += "    \"" + tools[i] + "\"";
        if (i + 1 < tools.size()) arrStr += ",";
        arrStr += "\n";
    }
    arrStr += "  ]";

    std::string key = "\"autostart_tools\"";
    size_t pos = json.find(key);
    if (pos != std::string::npos) {
        size_t colon = json.find(':', pos);
        if (colon != std::string::npos) {
            size_t bOpen = json.find('[', colon);
            if (bOpen != std::string::npos) {
                size_t bClose = json.find(']', bOpen);
                if (bClose != std::string::npos) {
                    json.replace(bOpen, bClose - bOpen + 1, arrStr);
                    return;
                }
            }
        }
    }

    size_t brace = json.rfind('}');
    if (brace != std::string::npos) {
        std::string entry = ",\n  \"autostart_tools\": " + arrStr + "\n";
        json.insert(brace, entry);
    }
}

static bool ToolInArray(const std::string& json, const std::string& toolName) {
    std::string key = "\"autostart_tools\"";
    size_t pos = json.find(key);
    if (pos == std::string::npos) {
        // Default tools if not present: byedpi, tor, opera, vless, tgws, ext
        if (toolName == "byedpi" || toolName == "tor" || toolName == "opera" || 
            toolName == "tgws" || toolName == "ext") return true;
        return false;
    }
    size_t colon = json.find(':', pos);
    if (colon == std::string::npos) return false;
    size_t bOpen = json.find('[', colon);
    if (bOpen == std::string::npos) return false;
    size_t bClose = json.find(']', bOpen);
    if (bClose == std::string::npos) return false;
    std::string arrBlock = json.substr(bOpen, bClose - bOpen + 1);
    return arrBlock.find("\"" + toolName + "\"") != std::string::npos;
}

// Autorun Registry Helper
static bool SetAutoRun(bool enable) {
    HKEY hKey;
    LONG res = RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_SET_VALUE, &hKey);
    if (res != ERROR_SUCCESS) return false;

    if (enable) {
        std::wstring exeTarget = g_rootDir + L"\\ToInet-MAX.exe";
        std::wstring target;
        if (GetFileAttributesW(exeTarget.c_str()) != INVALID_FILE_ATTRIBUTES) {
            target = exeTarget;
        } else {
            std::wstring batPath = g_rootDir + L"\\launch.bat";
            if (GetFileAttributesW(batPath.c_str()) == INVALID_FILE_ATTRIBUTES) {
                // Create launch.bat
                std::ofstream bat(batPath, std::ios::binary);
                if (bat.is_open()) {
                    bat << "@echo off\r\ncd /d \"%~dp0\"\r\nstart /b pythonw \"%~dp0main.pyw\"\r\n";
                    bat.close();
                }
            }
            target = batPath;
        }
        res = RegSetValueExW(hKey, L"ToInet-MAX", 0, REG_SZ, (const BYTE*)target.c_str(), (DWORD)((target.length() + 1) * sizeof(wchar_t)));
    } else {
        res = RegDeleteValueW(hKey, L"ToInet-MAX");
        if (res == ERROR_FILE_NOT_FOUND) res = ERROR_SUCCESS;
    }

    RegCloseKey(hKey);
    return (res == ERROR_SUCCESS);
}

// Load Settings from config.json
static void LoadSettings() {
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

    // Checkboxes
    SendMessageW(g_hChkByeDPI, BM_SETCHECK, ToolInArray(content, "byedpi") ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkTor, BM_SETCHECK, ToolInArray(content, "tor") ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkOpera, BM_SETCHECK, ToolInArray(content, "opera") ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkSSH, BM_SETCHECK, ToolInArray(content, "ssh") ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkTGWS, BM_SETCHECK, ToolInArray(content, "tgws") ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkProxifier, BM_SETCHECK, ToolInArray(content, "proxifier") ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkExt, BM_SETCHECK, ToolInArray(content, "ext") ? BST_CHECKED : BST_UNCHECKED, 0);

    g_initialAppAuto = ExtractJsonBool(content, "auto_start", false);
    SendMessageW(g_hChkAppAuto, BM_SETCHECK, g_initialAppAuto ? BST_CHECKED : BST_UNCHECKED, 0);

    bool autoLast = ExtractJsonBool(content, "auto_connect_last_mode", false);
    SendMessageW(g_hChkAutoLast, BM_SETCHECK, autoLast ? BST_CHECKED : BST_UNCHECKED, 0);

    // Torrc combo
    std::string torrcVal = ExtractJsonStr(content, "recreate_torrc", "none");
    if (torrcVal.empty()) {
        bool bVal = ExtractJsonBool(content, "recreate_torrc", false);
        torrcVal = bVal ? "full" : "none";
    }

    if (torrcVal == "true" || torrcVal == "full") {
        SendMessageW(g_hComboTorrc, CB_SETCURSEL, 2, 0);
    } else if (torrcVal == "false" || torrcVal == "bridges") {
        SendMessageW(g_hComboTorrc, CB_SETCURSEL, 1, 0);
    } else {
        SendMessageW(g_hComboTorrc, CB_SETCURSEL, 0, 0);
    }
}

// Save Settings
static void SaveSettings() {
    std::ifstream file(g_configPath, std::ios::binary);
    std::string content;
    if (file.is_open()) {
        std::stringstream ss;
        ss << file.rdbuf();
        content = ss.str();
        file.close();
    } else {
        content = "{\n}";
    }

    // Tools
    std::vector<std::string> tools;
    if (SendMessageW(g_hChkByeDPI, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("byedpi");
    if (SendMessageW(g_hChkTor, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("tor");
    if (SendMessageW(g_hChkOpera, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("opera");
    if (SendMessageW(g_hChkSSH, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("ssh");
    if (SendMessageW(g_hChkTGWS, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("tgws");
    if (SendMessageW(g_hChkProxifier, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("proxifier");
    if (SendMessageW(g_hChkExt, BM_GETCHECK, 0, 0) == BST_CHECKED) tools.push_back("ext");

    UpsertJsonToolsArray(content, tools);

    bool autoLast = (SendMessageW(g_hChkAutoLast, BM_GETCHECK, 0, 0) == BST_CHECKED);
    UpsertJsonBool(content, "auto_connect_last_mode", autoLast);

    int torrcIdx = (int)SendMessageW(g_hComboTorrc, CB_GETCURSEL, 0, 0);
    std::string torrcStr = "none";
    if (torrcIdx == 1) torrcStr = "bridges";
    else if (torrcIdx == 2) torrcStr = "full";
    UpsertJsonStr(content, "recreate_torrc", torrcStr);

    bool newAppAuto = (SendMessageW(g_hChkAppAuto, BM_GETCHECK, 0, 0) == BST_CHECKED);
    if (newAppAuto != g_initialAppAuto) {
        if (!SetAutoRun(newAppAuto)) {
            MessageBoxW(g_hMainWnd, Tr(T_MSG_ERROR_AUTORUN), Tr(T_MSG_ERROR_TITLE), MB_OK | MB_ICONWARNING);
        } else {
            g_initialAppAuto = newAppAuto;
        }
    }
    UpsertJsonBool(content, "auto_start", newAppAuto);

    std::ofstream out(g_configPath, std::ios::binary);
    if (out.is_open()) {
        out << content;
        out.close();
    }

    MessageBoxW(g_hMainWnd, Tr(T_MSG_SUCCESS), Tr(T_MSG_SUCCESS_TITLE), MB_OK | MB_ICONINFORMATION);
    DestroyWindow(g_hMainWnd);
}

// Window Procedure
static LRESULT CALLBACK WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_CREATE: {
        g_hMainWnd = hWnd;

        // Fonts
        g_hFontNormal = CreateFontW(16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
            DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
            DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold = CreateFontW(16, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
            DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
            DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        // 1. GroupBox: Tools (Left: 14, Top: 10, Width: 412, Height: 145)
        HWND hGrpTools = CreateWindowExW(0, L"BUTTON", Tr(T_GROUP_TOOLS),
            WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
            14, 10, 412, 145, hWnd, NULL, NULL, NULL);
        SendMessageW(hGrpTools, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);

        // Checkboxes in 2 columns:
        // Col 0: X = 28, Width = 190
        // Col 1: X = 222, Width = 195
        g_hChkByeDPI = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_BYEDPI),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            28, 32, 190, 22, hWnd, (HMENU)IDC_CHK_BYEDPI, NULL, NULL);
        SendMessageW(g_hChkByeDPI, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkTor = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_TOR),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            222, 32, 195, 22, hWnd, (HMENU)IDC_CHK_TOR, NULL, NULL);
        SendMessageW(g_hChkTor, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkOpera = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_OPERA),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            28, 58, 190, 22, hWnd, (HMENU)IDC_CHK_OPERA, NULL, NULL);
        SendMessageW(g_hChkOpera, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkSSH = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_SSH),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            222, 58, 195, 22, hWnd, (HMENU)IDC_CHK_SSH, NULL, NULL);
        SendMessageW(g_hChkSSH, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkTGWS = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_TGWS),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            28, 84, 190, 22, hWnd, (HMENU)IDC_CHK_TGWS, NULL, NULL);
        SendMessageW(g_hChkTGWS, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkProxifier = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_PROXIFIER),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            222, 84, 195, 22, hWnd, (HMENU)IDC_CHK_PROXIFIER, NULL, NULL);
        SendMessageW(g_hChkProxifier, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkExt = CreateWindowExW(0, L"BUTTON", Tr(T_TOOL_EXT),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            28, 110, 190, 22, hWnd, (HMENU)IDC_CHK_EXT, NULL, NULL);
        SendMessageW(g_hChkExt, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // 2. GroupBox: Params (Left: 14, Top: 165, Width: 412, Height: 140)
        HWND hGrpParams = CreateWindowExW(0, L"BUTTON", Tr(T_GROUP_PARAMS),
            WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
            14, 165, 412, 140, hWnd, NULL, NULL, NULL);
        SendMessageW(hGrpParams, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);

        g_hChkAppAuto = CreateWindowExW(0, L"BUTTON", Tr(T_APP_AUTOSTART),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            28, 188, 380, 22, hWnd, (HMENU)IDC_CHK_APP_AUTO, NULL, NULL);
        SendMessageW(g_hChkAppAuto, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hChkAutoLast = CreateWindowExW(0, L"BUTTON", Tr(T_AUTO_LAST),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP,
            28, 216, 380, 22, hWnd, (HMENU)IDC_CHK_AUTO_LAST, NULL, NULL);
        SendMessageW(g_hChkAutoLast, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Torrc row
        HWND hTorrcLbl = CreateWindowExW(0, L"STATIC", Tr(T_TORRC_LABEL),
            WS_CHILD | WS_VISIBLE | SS_LEFT,
            28, 252, 130, 20, hWnd, NULL, NULL, NULL);
        SendMessageW(hTorrcLbl, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hComboTorrc = CreateWindowExW(0, L"COMBOBOX", L"",
            WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_TABSTOP,
            165, 248, 240, 120, hWnd, (HMENU)IDC_COMBO_TORRC, NULL, NULL);
        SendMessageW(g_hComboTorrc, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        SendMessageW(g_hComboTorrc, CB_ADDSTRING, 0, (LPARAM)Tr(T_TORRC_OPT_NONE));
        SendMessageW(g_hComboTorrc, CB_ADDSTRING, 0, (LPARAM)Tr(T_TORRC_OPT_BRIDGES));
        SendMessageW(g_hComboTorrc, CB_ADDSTRING, 0, (LPARAM)Tr(T_TORRC_OPT_FULL));
        SendMessageW(g_hComboTorrc, CB_SETCURSEL, 0, 0);

        // 3. Action Buttons (Calm theme)
        g_hBtnSave = CreateWindowExW(0, L"BUTTON", Tr(T_BTN_SAVE),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_TABSTOP,
            205, 320, 110, 32, hWnd, (HMENU)IDC_BTN_SAVE, NULL, NULL);

        g_hBtnCancel = CreateWindowExW(0, L"BUTTON", Tr(T_BTN_CANCEL),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_TABSTOP,
            325, 320, 100, 32, hWnd, (HMENU)IDC_BTN_CANCEL, NULL, NULL);

        // Enable Dark Mode on controls
        SetWindowTheme(hGrpTools, L"DarkMode_Explorer", NULL);
        SetWindowTheme(hGrpParams, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkByeDPI, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkTor, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkOpera, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkSSH, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkTGWS, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkProxifier, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkExt, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkAppAuto, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hChkAutoLast, L"DarkMode_Explorer", NULL);
        SetWindowTheme(g_hComboTorrc, L"DarkMode_CFD", NULL);

        LoadSettings();
        return 0;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        int code = HIWORD(wParam);

        if (id == IDC_CHK_TGWS && code == BN_CLICKED) {
            LRESULT state = SendMessageW(g_hChkTGWS, BM_GETCHECK, 0, 0);
            if (state == BST_CHECKED) {
                int res = MessageBoxW(hWnd, Tr(T_TGWS_WARN), Tr(T_WARN_TITLE), MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2);
                if (res != IDYES) {
                    SendMessageW(g_hChkTGWS, BM_SETCHECK, BST_UNCHECKED, 0);
                }
            }
        }
        else if (id == IDC_BTN_SAVE) {
            SaveSettings();
        }
        else if (id == IDC_BTN_CANCEL) {
            DestroyWindow(hWnd);
        }
        return 0;
    }

    case WM_CTLCOLORDLG:
        return (LRESULT)g_hBrushBg;

    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLORBTN: {
        HDC hdc = (HDC)wParam;
        HWND hCtrl = (HWND)lParam;
        SetBkMode(hdc, TRANSPARENT);

        // Groupbox headers highlight
        LONG_PTR style = GetWindowLongPtrW(hCtrl, GWL_STYLE);
        if ((style & BS_GROUPBOX) == BS_GROUPBOX) {
            SetTextColor(hdc, g_colTitle);
        } else {
            SetTextColor(hdc, g_colText);
        }
        return (LRESULT)g_hBrushBg;
    }

    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT dis = (LPDRAWITEMSTRUCT)lParam;
        if (dis->CtlType == ODT_BUTTON) {
            bool isHover = (dis->hwndItem == g_hoveredBtn);
            bool isDown = (dis->itemState & ODS_SELECTED);

            COLORREF bgCol;
            COLORREF borderCol = RGB(60, 60, 60);

            if (dis->CtlID == IDC_BTN_SAVE) {
                // Calm steel blue: normal (32, 78, 120), hover (42, 92, 140)
                if (isDown) bgCol = RGB(25, 62, 98);
                else if (isHover) bgCol = RGB(42, 92, 140);
                else bgCol = RGB(32, 78, 120);
                borderCol = RGB(55, 105, 155);
            } else {
                // Cancel: calm dark charcoal (46, 46, 46), hover (60, 60, 60)
                if (isDown) bgCol = RGB(36, 36, 36);
                else if (isHover) bgCol = RGB(60, 60, 60);
                else bgCol = RGB(46, 46, 46);
                borderCol = RGB(65, 65, 65);
            }

            HBRUSH hBr = CreateSolidBrush(bgCol);
            HPEN hPen = CreatePen(PS_SOLID, 1, borderCol);
            HGDIOBJ oldBr = SelectObject(dis->hDC, hBr);
            HGDIOBJ oldPen = SelectObject(dis->hDC, hPen);

            RoundRect(dis->hDC, dis->rcItem.left, dis->rcItem.top, dis->rcItem.right, dis->rcItem.bottom, 6, 6);

            SelectObject(dis->hDC, oldBr);
            SelectObject(dis->hDC, oldPen);
            DeleteObject(hBr);
            DeleteObject(hPen);

            // Draw text
            wchar_t text[128] = { 0 };
            GetWindowTextW(dis->hwndItem, text, 128);
            SetBkMode(dis->hDC, TRANSPARENT);
            SetTextColor(dis->hDC, RGB(220, 220, 220));
            SelectObject(dis->hDC, g_hFontNormal);
            DrawTextW(dis->hDC, text, -1, &dis->rcItem, DT_CENTER | DT_VCENTER | DT_SINGLELINE);

            return TRUE;
        }
        break;
    }

    case WM_SETCURSOR: {
        HWND hTarget = (HWND)wParam;
        if (hTarget == g_hBtnSave || hTarget == g_hBtnCancel) {
            if (g_hoveredBtn != hTarget) {
                HWND old = g_hoveredBtn;
                g_hoveredBtn = hTarget;
                if (old) InvalidateRect(old, NULL, TRUE);
                InvalidateRect(g_hoveredBtn, NULL, TRUE);

                TRACKMOUSEEVENT tme = { sizeof(TRACKMOUSEEVENT), TME_LEAVE, hWnd, 0 };
                TrackMouseEvent(&tme);
            }
        }
        break;
    }

    case WM_MOUSELEAVE: {
        if (g_hoveredBtn) {
            HWND old = g_hoveredBtn;
            g_hoveredBtn = NULL;
            InvalidateRect(old, NULL, TRUE);
        }
        break;
    }

    case WM_DESTROY:
        if (g_hFontNormal) DeleteObject(g_hFontNormal);
        if (g_hFontBold) DeleteObject(g_hFontBold);
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hWnd, msg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE, LPWSTR, int) {
    InitCommonControls();
    InitPaths();

    // Read language from config before window creation to set title
    std::ifstream cfg(g_configPath, std::ios::binary);
    if (cfg.is_open()) {
        std::stringstream ss;
        ss << cfg.rdbuf();
        std::string content = ss.str();
        std::string lang = ExtractJsonStr(content, "language");
        if (lang == "fr") g_lang = LANG_FR;
        else if (lang == "en") g_lang = LANG_EN;
        else g_lang = LANG_RU;
        cfg.close();
    }

    g_hBrushBg = CreateSolidBrush(g_colBg);
    g_hBrushEditBg = CreateSolidBrush(RGB(36, 36, 36));

    WNDCLASSEXW wc = { 0 };
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"ToInetAutostartSettingsClass";
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;

    std::wstring iconPath = g_rootDir + L"\\icon.ico";
    HICON hIcon = (HICON)LoadImageW(NULL, iconPath.c_str(), IMAGE_ICON, 32, 32, LR_LOADFROMFILE);
    if (hIcon) {
        wc.hIcon = hIcon;
        wc.hIconSm = hIcon;
    }

    RegisterClassExW(&wc);

    RECT rc = { 0, 0, 440, 370 };
    AdjustWindowRect(&rc, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE);
    int winWidth = rc.right - rc.left;
    int winHeight = rc.bottom - rc.top;

    int posX = (GetSystemMetrics(SM_CXSCREEN) - winWidth) / 2;
    int posY = (GetSystemMetrics(SM_CYSCREEN) - winHeight) / 2;

    HWND hWnd = CreateWindowExW(
        0, wc.lpszClassName, Tr(T_WIN_TITLE),
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        posX, posY, winWidth, winHeight,
        NULL, NULL, hInstance, NULL
    );

    if (!hWnd) return 0;

    // Apply DWM Dark Mode
    BOOL darkMode = TRUE;
    DwmSetWindowAttribute(hWnd, 20, &darkMode, sizeof(darkMode)); // DWMWA_USE_IMMERSIVE_DARK_MODE
    DwmSetWindowAttribute(hWnd, 19, &darkMode, sizeof(darkMode));
    COLORREF capCol = 0x00181818;
    DwmSetWindowAttribute(hWnd, 35, &capCol, sizeof(capCol));     // DWMWA_CAPTION_COLOR

    ShowWindow(hWnd, SW_SHOW);
    UpdateWindow(hWnd);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        if (!IsDialogMessageW(hWnd, &msg)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    if (g_hBrushBg) DeleteObject(g_hBrushBg);
    if (g_hBrushEditBg) DeleteObject(g_hBrushEditBg);
    if (hIcon) DestroyIcon(hIcon);

    return 0;
}
