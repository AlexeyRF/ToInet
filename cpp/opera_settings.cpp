#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <commctrl.h>
#include <dwmapi.h>
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
#pragma comment(lib, "shell32.lib")

// Control IDs
#define IDC_COMBO_REGION     101
#define IDC_COMBO_POLICY     102
#define IDC_EDIT_RAW         103
#define IDC_CHK_POOL         104
#define IDC_EDIT_POOL_SIZE   105
#define IDC_BTN_SAVE         106
#define IDC_BTN_CANCEL       107

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

static const LStr T_WIN_TITLE        = { L"Настройки Opera Proxy", L"Opera Proxy Settings", L"Paramètres Opera Proxy" };
static const LStr T_HEADER_TITLE     = { L"Настройки Opera Proxy", L"Opera Proxy Settings", L"Paramètres Opera Proxy" };

static const LStr T_GRP_BASIC        = { L"Основные параметры", L"Basic Parameters", L"Paramètres de base" };
static const LStr T_LBL_REGION       = { L"Регион (Страна):", L"Region (Country):", L"Région (Pays):" };
static const LStr T_LBL_POLICY       = { L"Выбор сервера:", L"Server Selection:", L"Sélection du serveur:" };

static const LStr T_GRP_ADV          = { L"Дополнительные аргументы (для продвинутых)", L"Additional Arguments (Advanced)", L"Arguments additionnels (Avancé)" };
static const LStr T_GRP_POOL         = { L"Пул прокси (Load Balancing)", L"Proxy Pool (Load Balancing)", L"Pool de proxies (Équilibrage de charge)" };
static const LStr T_CHK_POOL         = { L"Включить пул (запуск нескольких экземпляров)", L"Enable Pool (Run multiple instances)", L"Activer le pool (plusieurs instances)" };
static const LStr T_LBL_COUNT        = { L"Количество:", L"Count:", L"Nombre:" };

static const LStr T_BTN_CANCEL       = { L"Отмена", L"Cancel", L"Annuler" };
static const LStr T_BTN_SAVE         = { L"Сохранить и Применить", L"Save and Apply", L"Enregistrer et appliquer" };

static const LStr T_MSG_TITLE_OK     = { L"Успех", L"Success", L"Succès" };
static const LStr T_MSG_SAVED        = {
    L"Настройки сохранены. Если Opera Proxy запущен, пожалуйста, перезапустите его.",
    L"Settings saved. If Opera Proxy is running, please restart it.",
    L"Paramètres enregistrés. Si Opera Proxy est en cours d'exécution, veuillez le redémarrer."
};

// Global UI Handles
static HWND g_hMainWnd = NULL;
static HWND g_hComboRegion = NULL;
static HWND g_hComboPolicy = NULL;
static HWND g_hEditRaw = NULL;
static HWND g_hChkPool = NULL;
static HWND g_hEditPoolSize = NULL;
static HWND g_hBtnSave = NULL;
static HWND g_hBtnCancel = NULL;

static HFONT g_hFontTitle = NULL;
static HFONT g_hFontNormal = NULL;
static HFONT g_hFontBold = NULL;

static HBRUSH g_hBrushBg = NULL;      // #181818
static HBRUSH g_hBrushEditBg = NULL;  // #242424

static COLORREF g_colBg = RGB(24, 24, 24);
static COLORREF g_colEditBg = RGB(36, 36, 36);
static COLORREF g_colText = RGB(208, 208, 208);
static COLORREF g_colTitle = RGB(93, 173, 226);

static std::wstring g_rootDir;
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

static std::string StringReplaceAll(std::string str, const std::string& from, const std::string& to) {
    size_t start_pos = 0;
    while((start_pos = str.find(from, start_pos)) != std::string::npos) {
        str.replace(start_pos, from.length(), to);
        start_pos += to.length();
    }
    return str;
}

void LoadSettings() {
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

    bool poolEnabled = ExtractJsonBool(content, "opera_pool_enabled", false);
    int poolSize = ExtractJsonInt(content, "opera_pool_size", 3);
    if (poolSize < 2 || poolSize > 10) poolSize = 3;

    SendMessageW(g_hChkPool, BM_SETCHECK, poolEnabled ? BST_CHECKED : BST_UNCHECKED, 0);
    SetWindowTextW(g_hEditPoolSize, std::to_wstring(poolSize).c_str());
    EnableWindow(g_hEditPoolSize, poolEnabled ? TRUE : FALSE);

    std::string params = ExtractJsonStr(content, "opera_params");
    if (!params.empty()) {
        // Region
        if (params.find("-country EU") != std::string::npos) SendMessageW(g_hComboRegion, CB_SETCURSEL, 0, 0);
        else if (params.find("-country AM") != std::string::npos) SendMessageW(g_hComboRegion, CB_SETCURSEL, 1, 0);
        else if (params.find("-country AS") != std::string::npos) SendMessageW(g_hComboRegion, CB_SETCURSEL, 2, 0);
        else if (params.find("-country ALL") != std::string::npos) SendMessageW(g_hComboRegion, CB_SETCURSEL, 3, 0);

        // Policy
        if (params.find("-server-selection fastest") != std::string::npos) SendMessageW(g_hComboPolicy, CB_SETCURSEL, 0, 0);
        else if (params.find("-server-selection random") != std::string::npos) SendMessageW(g_hComboPolicy, CB_SETCURSEL, 1, 0);
        else if (params.find("-server-selection first") != std::string::npos) SendMessageW(g_hComboPolicy, CB_SETCURSEL, 2, 0);

        std::vector<std::string> known = {
            "-bind-address 127.0.0.1:1785", "-socks-mode", "-verbosity 20",
            "-country EU", "-country AM", "-country AS", "-country ALL",
            "-server-selection fastest", "-server-selection random", "-server-selection first"
        };
        std::string adv = params;
        for (const auto& k : known) {
            adv = StringReplaceAll(adv, k, "");
        }
        // Normalize spaces
        std::stringstream ssAdv(adv);
        std::string token, cleanAdv;
        while (ssAdv >> token) {
            if (!cleanAdv.empty()) cleanAdv += " ";
            cleanAdv += token;
        }
        SetWindowTextW(g_hEditRaw, Utf8ToUtf16(cleanAdv).c_str());
    } else {
        SendMessageW(g_hComboRegion, CB_SETCURSEL, 0, 0); // EU
        SendMessageW(g_hComboPolicy, CB_SETCURSEL, 1, 0); // random
    }
}

void SaveSettings() {
    int regIdx = (int)SendMessageW(g_hComboRegion, CB_GETCURSEL, 0, 0);
    const char* regStr = "EU";
    if (regIdx == 1) regStr = "AM";
    else if (regIdx == 2) regStr = "AS";
    else if (regIdx == 3) regStr = "ALL";

    int polIdx = (int)SendMessageW(g_hComboPolicy, CB_GETCURSEL, 0, 0);
    const char* polStr = "random";
    if (polIdx == 0) polStr = "fastest";
    else if (polIdx == 2) polStr = "first";

    wchar_t bufAdv[512] = {};
    GetWindowTextW(g_hEditRaw, bufAdv, 512);
    std::string adv = Utf16ToUtf8(bufAdv);

    std::string newParams = "-bind-address 127.0.0.1:1785 -verbosity 20 -country " + std::string(regStr) + " -server-selection " + std::string(polStr);
    if (!adv.empty()) {
        newParams += " " + adv;
    }

    bool poolEnabled = (SendMessageW(g_hChkPool, BM_GETCHECK, 0, 0) == BST_CHECKED);
    wchar_t bufSize[16] = {};
    GetWindowTextW(g_hEditPoolSize, bufSize, 16);
    int poolSize = _wtoi(bufSize);
    if (poolSize < 2) poolSize = 2;
    if (poolSize > 10) poolSize = 10;

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

    UpsertJsonStr(content, "opera_params", newParams);
    UpsertJsonBool(content, "opera_pool_enabled", poolEnabled);
    UpsertJsonInt(content, "opera_pool_size", poolSize);

    std::ofstream out(g_configPath, std::ios::binary | std::ios::trunc);
    if (out.is_open()) {
        out.write(content.c_str(), content.size());
        out.close();
    }

    MessageBoxW(g_hMainWnd, T_MSG_SAVED.get(), T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
    DestroyWindow(g_hMainWnd);
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

    if (dis->CtlID == IDC_BTN_SAVE) {
        // Muted Blue
        if (isSelected)      { colBg = RGB(24, 62, 96);  colBorder = RGB(36, 82, 126); }
        else if (isHovered)  { colBg = RGB(42, 92, 140); colBorder = RGB(52, 110, 165); }
        else                 { colBg = RGB(32, 78, 120); colBorder = RGB(36, 82, 126); }
    } else { // IDC_BTN_CANCEL
        // Dark Charcoal
        if (isSelected)      { colBg = RGB(36, 36, 36);  colBorder = RGB(58, 58, 58); }
        else if (isHovered)  { colBg = RGB(60, 60, 60);  colBorder = RGB(75, 75, 75); }
        else                 { colBg = RGB(46, 46, 46);  colBorder = RGB(58, 58, 58); }
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
    SelectObject(hdc, g_hFontBold);
    DrawTextW(hdc, text, -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

// Window Procedure
LRESULT CALLBACK WndProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        g_hMainWnd = hWnd;

        g_hFontTitle  = CreateFontW(-16, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontNormal = CreateFontW(-12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold   = CreateFontW(-12, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        // Group 1 Controls: Basic
        g_hComboRegion = CreateWindowExW(0, L"COMBOBOX", L"",
            WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL,
            160, 68, 316, 160, hWnd, (HMENU)IDC_COMBO_REGION, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hComboRegion, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);
        SendMessageW(g_hComboRegion, CB_ADDSTRING, 0, (LPARAM)L"EU (Европа)");
        SendMessageW(g_hComboRegion, CB_ADDSTRING, 0, (LPARAM)L"AM (Америка)");
        SendMessageW(g_hComboRegion, CB_ADDSTRING, 0, (LPARAM)L"AS (Азия)");
        SendMessageW(g_hComboRegion, CB_ADDSTRING, 0, (LPARAM)L"ALL (Любой)");
        SendMessageW(g_hComboRegion, CB_SETCURSEL, 0, 0);

        g_hComboPolicy = CreateWindowExW(0, L"COMBOBOX", L"",
            WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL,
            160, 102, 316, 160, hWnd, (HMENU)IDC_COMBO_POLICY, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hComboPolicy, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);
        SendMessageW(g_hComboPolicy, CB_ADDSTRING, 0, (LPARAM)L"fastest (Самый быстрый)");
        SendMessageW(g_hComboPolicy, CB_ADDSTRING, 0, (LPARAM)L"random (Случайный)");
        SendMessageW(g_hComboPolicy, CB_ADDSTRING, 0, (LPARAM)L"first (Первый)");
        SendMessageW(g_hComboPolicy, CB_SETCURSEL, 1, 0);

        // Group 2 Controls: Advanced Raw Params
        g_hEditRaw = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL,
            28, 180, 448, 26, hWnd, (HMENU)IDC_EDIT_RAW, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hEditRaw, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Group 3 Controls: Pool
        g_hChkPool = CreateWindowExW(0, L"BUTTON", T_CHK_POOL.get(),
            WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX,
            28, 256, 320, 24, hWnd, (HMENU)IDC_CHK_POOL, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hChkPool, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        g_hEditPoolSize = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"3",
            WS_CHILD | WS_VISIBLE | ES_NUMBER | ES_CENTER,
            430, 256, 46, 24, hWnd, (HMENU)IDC_EDIT_POOL_SIZE, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hEditPoolSize, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Bottom Buttons (Y=326, H=32)
        g_hBtnCancel = CreateWindowExW(0, L"BUTTON", T_BTN_CANCEL.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            176, 326, 120, 32, hWnd, (HMENU)IDC_BTN_CANCEL, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnCancel, ButtonSubclassProc, IDC_BTN_CANCEL, 0);

        g_hBtnSave = CreateWindowExW(0, L"BUTTON", T_BTN_SAVE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            306, 326, 182, 32, hWnd, (HMENU)IDC_BTN_SAVE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnSave, ButtonSubclassProc, IDC_BTN_SAVE, 0);

        LoadSettings();
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

        if (id == IDC_CHK_POOL && code == BN_CLICKED) {
            bool checked = (SendMessageW(g_hChkPool, BM_GETCHECK, 0, 0) == BST_CHECKED);
            EnableWindow(g_hEditPoolSize, checked ? TRUE : FALSE);
        } else if (id == IDC_BTN_SAVE) {
            SaveSettings();
        } else if (id == IDC_BTN_CANCEL) {
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
        RECT rcTitle = { 0, 12, 504, 36 };
        DrawTextW(hdc, T_HEADER_TITLE.get(), -1, &rcTitle, DT_CENTER | DT_SINGLELINE);

        // 2. Group 1: Basic (16, 46, 488, 142)
        HPEN hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        HGDIOBJ oldPen = SelectObject(hdc, hPenBorder);
        HGDIOBJ oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));
        RoundRect(hdc, 16, 46, 488, 142, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 26, 38, T_GRP_BASIC.get(), (int)wcslen(T_GRP_BASIC.get()));

        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 28, 72, T_LBL_REGION.get(), (int)wcslen(T_LBL_REGION.get()));
        TextOutW(hdc, 28, 106, T_LBL_POLICY.get(), (int)wcslen(T_LBL_POLICY.get()));

        // 3. Group 2: Advanced (16, 156, 488, 222)
        hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        oldPen = SelectObject(hdc, hPenBorder);
        oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));
        RoundRect(hdc, 16, 156, 488, 222, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 26, 148, T_GRP_ADV.get(), (int)wcslen(T_GRP_ADV.get()));

        // 4. Group 3: Pool (16, 236, 488, 302)
        hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        oldPen = SelectObject(hdc, hPenBorder);
        oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));
        RoundRect(hdc, 16, 236, 488, 302, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 26, 228, T_GRP_POOL.get(), (int)wcslen(T_GRP_POOL.get()));

        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 356, 260, T_LBL_COUNT.get(), (int)wcslen(T_LBL_COUNT.get()));

        EndPaint(hWnd, &ps);
        return 0;
    }

    case WM_DESTROY:
        if (g_hFontTitle)  DeleteObject(g_hFontTitle);
        if (g_hFontNormal) DeleteObject(g_hFontNormal);
        if (g_hFontBold)   DeleteObject(g_hFontBold);
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hWnd, uMsg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE, PWSTR, int nCmdShow) {
    INITCOMMONCONTROLSEX icex = { sizeof(INITCOMMONCONTROLSEX), ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES };
    InitCommonControlsEx(&icex);

    LANGID langId = GetUserDefaultUILanguage();
    WORD priLang = langId & 0xFF;
    if (priLang == 0x0C) g_lang = LANG_FR;
    else if (priLang == 0x09) g_lang = LANG_EN;
    else g_lang = LANG_RU;

    InitPaths();

    g_hBrushBg = CreateSolidBrush(g_colBg);
    g_hBrushEditBg = CreateSolidBrush(g_colEditBg);

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetOperaSettingsWnd";

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

    RECT rcWin = { 0, 0, 504, 376 };
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

    if (!hWnd) return 1;

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
    return (int)msg.wParam;
}
