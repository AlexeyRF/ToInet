#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <commctrl.h>
#include <commdlg.h>
#include <dwmapi.h>
#include <shellapi.h>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "shell32.lib")

// Control IDs
#define IDC_HOST_EDIT       101
#define IDC_PORT_EDIT       102
#define IDC_DC_EDIT         103
#define IDC_SECRET_EDIT     104
#define IDC_FAKETLS_EDIT    105
#define IDC_FRONTING_EDIT   106
#define IDC_CHK_VERBOSE     107
#define IDC_CHK_CFPROXY     108
#define IDC_CHK_H2          109
#define IDC_CF_USER_EDIT    110
#define IDC_CF_WORKER_EDIT  111
#define IDC_BTN_SAVE        112
#define IDC_BTN_CANCEL      113
#define IDC_BTN_GEN_SECRET  114

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

static const LStr T_WIN_TITLE   = { L"Настройки TGWS Proxy", L"TGWS Proxy Settings", L"Paramètres TGWS Proxy" };
static const LStr T_LBL_HOST    = { L"IP-адрес прокси:", L"Proxy IP address:", L"Adresse IP du proxy :" };
static const LStr T_LBL_PORT    = { L"Порт прокси:", L"Proxy port:", L"Port du proxy :" };
static const LStr T_LBL_DC      = { L"DC → IP маппинги (формат DC:IP по одному на строку):", L"DC → IP mappings (DC:IP format, one per line):", L"Mappages DC → IP (un par ligne) :" };
static const LStr T_LBL_SECRET  = { L"MTProto Секрет (32 hex символа):", L"MTProto Secret (32 hex chars):", L"Secret MTProto (32 caractères hex) :" };
static const LStr T_BTN_GEN_SEC = { L"🎲 Сгенерировать", L"🎲 Generate", L"🎲 Générer" };
static const LStr T_LBL_FAKETLS = { L"Fake TLS Домен (например, google.com):", L"Fake TLS Domain (e.g. google.com):", L"Domaine Fake TLS (ex. google.com) :" };
static const LStr T_LBL_FRONT   = { L"Domain Fronting SNI (устарело):", L"Domain Fronting SNI (obsolete):", L"Domain Fronting SNI (obsolète) :" };
static const LStr T_CHK_VERBOSE = { L"Подробное логирование (verbose)", L"Verbose logging", L"Journalisation détaillée" };
static const LStr T_CHK_CFPROXY = { L"Включить Cloudflare Proxy (запасной канал)", L"Enable Cloudflare Proxy fallback", L"Activer le proxy Cloudflare de secours" };
static const LStr T_CHK_H2      = { L"Мультиплексирование медиа (HTTP/2)", L"Media multiplexing (HTTP/2)", L"Multiplexage média (HTTP/2)" };
static const LStr T_LBL_CF_USER = { L"Свои домены CF Proxy (через запятую):", L"Custom CF Proxy domains (comma-separated):", L"Domaines CF Proxy personnalisés :" };
static const LStr T_LBL_CF_WORK = { L"Свои домены CF Worker (через запятую):", L"Custom CF Worker domains (comma-separated):", L"Domaines CF Worker personnalisés :" };
static const LStr T_BTN_SAVE    = { L"💾 Сохранить", L"💾 Save", L"💾 Enregistrer" };
static const LStr T_BTN_CANCEL  = { L"Отмена", L"Cancel", L"Annuler" };
static const LStr T_MSG_SAVED   = { L"Настройки TGWS Proxy успешно сохранены!\nПожалуйста, перезапустите TGWS для применения изменений.", L"TGWS settings saved successfully!\nPlease restart TGWS to apply changes.", L"Paramètres enregistrés avec succès !" };
static const LStr T_MSG_TITLE   = { L"Успех", L"Success", L"Succès" };
static const LStr T_ERR_PORT    = { L"Порт должен быть числом от 1 до 65535", L"Port must be a number from 1 to 65535", L"Le port doit être compris entre 1 et 65535" };
static const LStr T_ERR_SECRET  = { L"Секрет должен состоять ровно из 32 шестнадцатеричных символов (0-9, a-f)", L"Secret must be exactly 32 hex characters (0-9, a-f)", L"Le secret doit comporter 32 caractères hexadécimaux" };

// Global UI Handles
static HWND g_hMainWnd = NULL;
static HWND g_hHostEdit = NULL;
static HWND g_hPortEdit = NULL;
static HWND g_hDcEdit = NULL;
static HWND g_hSecretEdit = NULL;
static HWND g_hFakeTlsEdit = NULL;
static HWND g_hFrontingEdit = NULL;
static HWND g_hChkVerbose = NULL;
static HWND g_hChkCfProxy = NULL;
static HWND g_hChkH2 = NULL;
static HWND g_hCfUserEdit = NULL;
static HWND g_hCfWorkerEdit = NULL;
static HWND g_hBtnGenSec = NULL;
static HWND g_hBtnSave = NULL;
static HWND g_hBtnCancel = NULL;

static HFONT g_hFontNormal = NULL;
static HFONT g_hFontBold = NULL;
static HFONT g_hFontSmall = NULL;

static HBRUSH g_hBrushBg = NULL;      // #181818
static HBRUSH g_hBrushEditBg = NULL;  // #242424
static COLORREF g_colBg = RGB(24, 24, 24);
static COLORREF g_colEditBg = RGB(36, 36, 36);
static COLORREF g_colText = RGB(224, 224, 224);
static COLORREF g_colTitle = RGB(93, 173, 226);

static std::wstring g_configPath;
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

std::wstring GetConfigFilePath() {
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);

    std::wstring p1 = dir + L"\\..\\data\\config.json";
    if (GetFileAttributesW(p1.c_str()) != INVALID_FILE_ATTRIBUTES) return p1;

    std::wstring p2 = dir + L"\\data\\config.json";
    if (GetFileAttributesW(p2.c_str()) != INVALID_FILE_ATTRIBUTES) return p2;

    return p1;
}

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

static std::vector<std::string> ExtractJsonArrStr(const std::string& json, const std::string& key) {
    std::vector<std::string> res;
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return res;
    size_t start = json.find('[', pos);
    if (start == std::string::npos) return res;
    size_t end = json.find(']', start);
    if (end == std::string::npos) return res;

    std::string arr = json.substr(start + 1, end - start - 1);
    size_t p = 0;
    while (p < arr.size()) {
        size_t s = arr.find('\"', p);
        if (s == std::string::npos) break;
        size_t e = arr.find('\"', s + 1);
        if (e == std::string::npos) break;
        res.push_back(arr.substr(s + 1, e - s - 1));
        p = e + 1;
    }
    return res;
}

static std::string GenerateRandomSecret() {
    static const char hex_digits[] = "0123456789abcdef";
    std::string sec;
    sec.resize(32);
    for (int i = 0; i < 32; ++i) {
        sec[i] = hex_digits[rand() % 16];
    }
    return sec;
}

void LoadAndPopulateFields() {
    g_configPath = GetConfigFilePath();
    std::ifstream file(g_configPath, std::ios::binary);
    std::string content;
    if (file.is_open()) {
        std::stringstream ss;
        ss << file.rdbuf();
        content = ss.str();
        file.close();
    }

    // Language detection
    std::string lang = ExtractJsonStr(content, "language");
    if (lang == "en") g_lang = LANG_EN;
    else if (lang == "fr") g_lang = LANG_FR;
    else g_lang = LANG_RU;

    std::string host = ExtractJsonStr(content, "tgws_host");
    if (host.empty()) host = "127.0.0.1";
    SetWindowTextW(g_hHostEdit, Utf8ToUtf16(host).c_str());

    int port = ExtractJsonInt(content, "tgws_port", 1480);
    SetWindowTextW(g_hPortEdit, std::to_wstring(port).c_str());

    auto dcs = ExtractJsonArrStr(content, "tgws_dc_ip");
    if (dcs.empty()) {
        dcs = { "2:149.154.167.220", "4:149.154.167.220" };
    }
    std::wstring dcText;
    for (size_t i = 0; i < dcs.size(); ++i) {
        dcText += Utf8ToUtf16(dcs[i]);
        if (i + 1 < dcs.size()) dcText += L"\r\n";
    }
    SetWindowTextW(g_hDcEdit, dcText.c_str());

    std::string secret = ExtractJsonStr(content, "tgws_secret");
    if (secret.empty()) secret = GenerateRandomSecret();
    SetWindowTextW(g_hSecretEdit, Utf8ToUtf16(secret).c_str());

    std::string fakeTls = ExtractJsonStr(content, "tgws_fake_tls");
    SetWindowTextW(g_hFakeTlsEdit, Utf8ToUtf16(fakeTls).c_str());

    std::string fronting = ExtractJsonStr(content, "tgws_fronting_sni");
    SetWindowTextW(g_hFrontingEdit, Utf8ToUtf16(fronting).c_str());

    SendMessageW(g_hChkVerbose, BM_SETCHECK, ExtractJsonBool(content, "tgws_verbose", false) ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkCfProxy, BM_SETCHECK, ExtractJsonBool(content, "tgws_fallback_cfproxy", true) ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(g_hChkH2, BM_SETCHECK, ExtractJsonBool(content, "tgws_cfproxy_h2_media", true) ? BST_CHECKED : BST_UNCHECKED, 0);

    std::string cfUser = ExtractJsonStr(content, "tgws_cfproxy_user_domain");
    SetWindowTextW(g_hCfUserEdit, Utf8ToUtf16(cfUser).c_str());

    std::string cfWorker = ExtractJsonStr(content, "tgws_cfproxy_worker_domain");
    SetWindowTextW(g_hCfWorkerEdit, Utf8ToUtf16(cfWorker).c_str());
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

static void ReplaceJsonArrStr(std::string& json, const std::string& key, const std::vector<std::string>& arr) {
    std::string search = "\"" + key + "\"";
    size_t pos = json.find(search);
    if (pos == std::string::npos) return;
    size_t start = json.find('[', pos);
    if (start == std::string::npos) return;
    size_t end = json.find(']', start);
    if (end == std::string::npos) return;

    std::string repl = "[\n";
    for (size_t i = 0; i < arr.size(); ++i) {
        repl += "    \"" + arr[i] + "\"";
        if (i + 1 < arr.size()) repl += ",";
        repl += "\n";
    }
    repl += "  ]";
    json.replace(start, end - start + 1, repl);
}

bool SaveConfig() {
    wchar_t buf[2048];

    GetWindowTextW(g_hPortEdit, buf, 16);
    int port = 0;
    try {
        port = std::stoi(buf);
    } catch (...) {}
    if (port < 1 || port > 65535) {
        MessageBoxW(g_hMainWnd, T_ERR_PORT.get(), L"Error", MB_ICONERROR);
        return false;
    }

    GetWindowTextW(g_hSecretEdit, buf, 128);
    std::wstring secW = buf;
    if (secW.size() != 32) {
        MessageBoxW(g_hMainWnd, T_ERR_SECRET.get(), L"Error", MB_ICONERROR);
        return false;
    }
    for (wchar_t c : secW) {
        if (!((c >= L'0' && c <= L'9') || (c >= L'a' && c <= L'f') || (c >= L'A' && c <= L'F'))) {
            MessageBoxW(g_hMainWnd, T_ERR_SECRET.get(), L"Error", MB_ICONERROR);
            return false;
        }
    }

    GetWindowTextW(g_hHostEdit, buf, 256);
    std::string host = Utf16ToUtf8(buf);

    GetWindowTextW(g_hFakeTlsEdit, buf, 512);
    std::string fakeTls = Utf16ToUtf8(buf);

    GetWindowTextW(g_hFrontingEdit, buf, 512);
    std::string fronting = Utf16ToUtf8(buf);

    bool verbose = (SendMessageW(g_hChkVerbose, BM_GETCHECK, 0, 0) == BST_CHECKED);
    bool cfProxy = (SendMessageW(g_hChkCfProxy, BM_GETCHECK, 0, 0) == BST_CHECKED);
    bool h2 = (SendMessageW(g_hChkH2, BM_GETCHECK, 0, 0) == BST_CHECKED);

    GetWindowTextW(g_hCfUserEdit, buf, 512);
    std::string cfUser = Utf16ToUtf8(buf);

    GetWindowTextW(g_hCfWorkerEdit, buf, 512);
    std::string cfWorker = Utf16ToUtf8(buf);

    int dcLen = GetWindowTextLengthW(g_hDcEdit);
    std::vector<wchar_t> dcBuf(dcLen + 1);
    GetWindowTextW(g_hDcEdit, dcBuf.data(), dcLen + 1);
    std::wstring dcW = dcBuf.data();

    std::vector<std::string> dcs;
    std::wstring line;
    std::wstringstream wss(dcW);
    while (std::getline(wss, line)) {
        while (!line.empty() && (line.back() == L'\r' || line.back() == L' ' || line.back() == L'\t')) {
            line.pop_back();
        }
        size_t start = line.find_first_not_of(L" \t");
        if (start != std::wstring::npos) line = line.substr(start);
        if (!line.empty()) {
            dcs.push_back(Utf16ToUtf8(line));
        }
    }

    std::ifstream file(g_configPath, std::ios::binary);
    std::string content;
    if (file.is_open()) {
        std::stringstream ss;
        ss << file.rdbuf();
        content = ss.str();
        file.close();
    }

    ReplaceJsonStr(content, "tgws_host", host);
    ReplaceJsonInt(content, "tgws_port", port);
    ReplaceJsonStr(content, "tgws_secret", Utf16ToUtf8(secW));
    ReplaceJsonStr(content, "tgws_fake_tls", fakeTls);
    ReplaceJsonStr(content, "tgws_fronting_sni", fronting);
    ReplaceJsonBool(content, "tgws_verbose", verbose);
    ReplaceJsonBool(content, "tgws_fallback_cfproxy", cfProxy);
    ReplaceJsonBool(content, "tgws_cfproxy_h2_media", h2);
    ReplaceJsonStr(content, "tgws_cfproxy_user_domain", cfUser);
    ReplaceJsonStr(content, "tgws_cfproxy_worker_domain", cfWorker);
    ReplaceJsonArrStr(content, "tgws_dc_ip", dcs);

    std::ofstream out(g_configPath, std::ios::binary);
    if (!out.is_open()) return false;
    out.write(content.data(), content.size());
    out.close();

    MessageBoxW(g_hMainWnd, T_MSG_SAVED.get(), T_MSG_TITLE.get(), MB_ICONINFORMATION);
    return true;
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
    switch (message) {
    case WM_CREATE: {
        // Dark Title Bar
        BOOL dark = TRUE;
        DwmSetWindowAttribute(hWnd, DWMWA_USE_IMMERSIVE_DARK_MODE, &dark, sizeof(dark));

        g_hBrushBg = CreateSolidBrush(g_colBg);
        g_hBrushEditBg = CreateSolidBrush(g_colEditBg);

        g_hFontNormal = CreateFontW(-14, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold = CreateFontW(-14, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontSmall = CreateFontW(-12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        int y = 20;
        int leftCol = 25;
        int colW = 530;

        // Host & Port (same line)
        CreateWindowW(L"STATIC", T_LBL_HOST.get(), WS_VISIBLE | WS_CHILD, leftCol, y, 200, 18, hWnd, NULL, NULL, NULL);
        CreateWindowW(L"STATIC", T_LBL_PORT.get(), WS_VISIBLE | WS_CHILD, leftCol + 350, y, 180, 18, hWnd, NULL, NULL, NULL);
        y += 22;

        g_hHostEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL, leftCol, y, 330, 26, hWnd, (HMENU)IDC_HOST_EDIT, NULL, NULL);
        g_hPortEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL | ES_NUMBER, leftCol + 350, y, 180, 26, hWnd, (HMENU)IDC_PORT_EDIT, NULL, NULL);
        y += 34;

        // Secret with Generate Button
        CreateWindowW(L"STATIC", T_LBL_SECRET.get(), WS_VISIBLE | WS_CHILD, leftCol, y, 350, 18, hWnd, NULL, NULL, NULL);
        y += 22;
        g_hSecretEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL, leftCol, y, 380, 26, hWnd, (HMENU)IDC_SECRET_EDIT, NULL, NULL);
        g_hBtnGenSec = CreateWindowW(L"BUTTON", T_BTN_GEN_SEC.get(), WS_VISIBLE | WS_CHILD | BS_OWNERDRAW, leftCol + 390, y, 140, 26, hWnd, (HMENU)IDC_BTN_GEN_SECRET, NULL, NULL);
        y += 34;

        // DC Mappings (multiline)
        CreateWindowW(L"STATIC", T_LBL_DC.get(), WS_VISIBLE | WS_CHILD, leftCol, y, colW, 18, hWnd, NULL, NULL, NULL);
        y += 22;
        g_hDcEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | WS_VSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN, leftCol, y, colW, 70, hWnd, (HMENU)IDC_DC_EDIT, NULL, NULL);
        y += 78;

        // Fake TLS & Fronting
        CreateWindowW(L"STATIC", T_LBL_FAKETLS.get(), WS_VISIBLE | WS_CHILD, leftCol, y, colW, 18, hWnd, NULL, NULL, NULL);
        y += 22;
        g_hFakeTlsEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL, leftCol, y, colW, 26, hWnd, (HMENU)IDC_FAKETLS_EDIT, NULL, NULL);
        y += 34;

        CreateWindowW(L"STATIC", T_LBL_FRONT.get(), WS_VISIBLE | WS_CHILD, leftCol, y, colW, 18, hWnd, NULL, NULL, NULL);
        y += 22;
        g_hFrontingEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL, leftCol, y, colW, 26, hWnd, (HMENU)IDC_FRONTING_EDIT, NULL, NULL);
        y += 34;

        // Checkboxes
        g_hChkVerbose = CreateWindowW(L"BUTTON", T_CHK_VERBOSE.get(), WS_VISIBLE | WS_CHILD | BS_AUTOCHECKBOX, leftCol, y, colW, 22, hWnd, (HMENU)IDC_CHK_VERBOSE, NULL, NULL);
        y += 26;
        g_hChkCfProxy = CreateWindowW(L"BUTTON", T_CHK_CFPROXY.get(), WS_VISIBLE | WS_CHILD | BS_AUTOCHECKBOX, leftCol, y, colW, 22, hWnd, (HMENU)IDC_CHK_CFPROXY, NULL, NULL);
        y += 26;
        g_hChkH2 = CreateWindowW(L"BUTTON", T_CHK_H2.get(), WS_VISIBLE | WS_CHILD | BS_AUTOCHECKBOX, leftCol, y, colW, 22, hWnd, (HMENU)IDC_CHK_H2, NULL, NULL);
        y += 32;

        // CF User & Worker domains
        CreateWindowW(L"STATIC", T_LBL_CF_USER.get(), WS_VISIBLE | WS_CHILD, leftCol, y, colW, 18, hWnd, NULL, NULL, NULL);
        y += 22;
        g_hCfUserEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL, leftCol, y, colW, 26, hWnd, (HMENU)IDC_CF_USER_EDIT, NULL, NULL);
        y += 34;

        CreateWindowW(L"STATIC", T_LBL_CF_WORK.get(), WS_VISIBLE | WS_CHILD, leftCol, y, colW, 18, hWnd, NULL, NULL, NULL);
        y += 22;
        g_hCfWorkerEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_VISIBLE | WS_CHILD | ES_AUTOHSCROLL, leftCol, y, colW, 26, hWnd, (HMENU)IDC_CF_WORKER_EDIT, NULL, NULL);
        y += 45;

        // Buttons: Save & Cancel
        g_hBtnSave = CreateWindowW(L"BUTTON", T_BTN_SAVE.get(), WS_VISIBLE | WS_CHILD | BS_OWNERDRAW, leftCol + 230, y, 140, 34, hWnd, (HMENU)IDC_BTN_SAVE, NULL, NULL);
        g_hBtnCancel = CreateWindowW(L"BUTTON", T_BTN_CANCEL.get(), WS_VISIBLE | WS_CHILD | BS_OWNERDRAW, leftCol + 390, y, 140, 34, hWnd, (HMENU)IDC_BTN_CANCEL, NULL, NULL);

        // Apply fonts
        EnumChildWindows(hWnd, [](HWND child, LPARAM) -> BOOL {
            SendMessageW(child, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);
            return TRUE;
        }, 0);

        SendMessageW(g_hBtnSave, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);
        SendMessageW(g_hBtnCancel, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);
        SendMessageW(g_hBtnGenSec, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

        LoadAndPopulateFields();
        return 0;
    }
    case WM_CTLCOLORSTATIC: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, g_colText);
        SetBkColor(hdc, g_colBg);
        return (LRESULT)g_hBrushBg;
    }
    case WM_CTLCOLOREDIT: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, RGB(255, 255, 255));
        SetBkColor(hdc, g_colEditBg);
        return (LRESULT)g_hBrushEditBg;
    }
    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT dis = (LPDRAWITEMSTRUCT)lParam;
        bool isHovered = (dis->hwndItem == g_hoveredBtn);
        bool isSelected = (dis->itemState & ODS_SELECTED);

        COLORREF bgCol = isSelected ? RGB(30, 80, 140) : (isHovered ? RGB(50, 50, 50) : RGB(36, 36, 36));
        COLORREF borderCol = isSelected ? RGB(93, 173, 226) : (isHovered ? RGB(90, 90, 90) : RGB(60, 60, 60));

        HBRUSH br = CreateSolidBrush(bgCol);
        FillRect(dis->hDC, &dis->rcItem, br);
        DeleteObject(br);

        HPEN pen = CreatePen(PS_SOLID, 1, borderCol);
        HGDIOBJ oldPen = SelectObject(dis->hDC, pen);
        HGDIOBJ oldBr = SelectObject(dis->hDC, GetStockObject(HOLLOW_BRUSH));
        RoundRect(dis->hDC, dis->rcItem.left, dis->rcItem.top, dis->rcItem.right, dis->rcItem.bottom, 4, 4);
        SelectObject(dis->hDC, oldPen);
        SelectObject(dis->hDC, oldBr);
        DeleteObject(pen);

        wchar_t text[128];
        GetWindowTextW(dis->hwndItem, text, 128);
        SetBkMode(dis->hDC, TRANSPARENT);
        SetTextColor(dis->hDC, RGB(240, 240, 240));
        DrawTextW(dis->hDC, text, -1, &dis->rcItem, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
        return TRUE;
    }
    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == IDC_BTN_GEN_SECRET) {
            std::string sec = GenerateRandomSecret();
            SetWindowTextW(g_hSecretEdit, Utf8ToUtf16(sec).c_str());
        } else if (id == IDC_BTN_SAVE) {
            if (SaveConfig()) {
                DestroyWindow(hWnd);
            }
        } else if (id == IDC_BTN_CANCEL) {
            DestroyWindow(hWnd);
        }
        return 0;
    }
    case WM_DESTROY: {
        if (g_hBrushBg) DeleteObject(g_hBrushBg);
        if (g_hBrushEditBg) DeleteObject(g_hBrushEditBg);
        if (g_hFontNormal) DeleteObject(g_hFontNormal);
        if (g_hFontBold) DeleteObject(g_hFontBold);
        if (g_hFontSmall) DeleteObject(g_hFontSmall);
        PostQuitMessage(0);
        return 0;
    }
    }
    return DefWindowProcW(hWnd, message, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE, LPWSTR, int nCmdShow) {
    WNDCLASSEXW wcex{};
    wcex.cbSize = sizeof(WNDCLASSEXW);
    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WndProc;
    wcex.hInstance = hInstance;
    wcex.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcex.hbrBackground = CreateSolidBrush(g_colBg);
    wcex.lpszClassName = L"TGWS_Settings_Class";

    RegisterClassExW(&wcex);

    int w = 600;
    int h = 670;
    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);
    int x = (screenW - w) / 2;
    int y = (screenH - h) / 2;

    g_hMainWnd = CreateWindowW(L"TGWS_Settings_Class", T_WIN_TITLE.get(),
                               WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                               x, y, w, h, NULL, NULL, hInstance, NULL);

    if (!g_hMainWnd) return 1;

    ShowWindow(g_hMainWnd, nCmdShow);
    UpdateWindow(g_hMainWnd);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return (int)msg.wParam;
}
