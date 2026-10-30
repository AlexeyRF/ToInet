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

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "shell32.lib")

// Control IDs
#define IDC_PROXI_EDIT    101
#define IDC_PROXI_BROWSE  102
#define IDC_PROXI_CLEAR   103
#define IDC_EXT_EDIT      104
#define IDC_EXT_ADD       105
#define IDC_EXT_CLEAR     106
#define IDC_BTN_SAVE      107
#define IDC_BTN_CANCEL    108

enum AppLang { LANG_RU, LANG_EN, LANG_FR };
static AppLang g_lang = LANG_RU;

// Translations
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

static const LStr T_WIN_TITLE   = { L"Пути программ", L"Program Paths", L"Chemins des programmes" };
static const LStr T_GRP_PROXI   = { L"Проксификатор", L"Proxifier", L"Proxificateur" };
static const LStr T_LBL_PROXI   = { L"Путь к исполняемому файлу Proxifier.exe:", L"Path to Proxifier.exe:", L"Chemin vers Proxifier.exe :" };
static const LStr T_BTN_BROWSE  = { L"Обзор...", L"Browse...", L"Parcourir..." };
static const LStr T_BTN_CLEAR   = { L"Очистить", L"Clear", L"Effacer" };

static const LStr T_GRP_EXT     = { L"Дополнительные программы", L"External Programs", L"Programmes additionnels" };
static const LStr T_LBL_EXT     = { L"Пути к программам (по одной на строку):", L"Paths to programs (one per line):", L"Chemins des programmes (un par ligne) :" };
static const LStr T_BTN_ADD     = { L"➕ Добавить файл...", L"➕ Add file...", L"➕ Ajouter un fichier..." };
static const LStr T_BTN_EXT_CLR = { L"🗑 Очистить список", L"🗑 Clear list", L"🗑 Vider la liste" };

static const LStr T_BTN_SAVE    = { L"💾 Сохранить", L"💾 Save", L"💾 Enregistrer" };
static const LStr T_BTN_CANCEL  = { L"Отмена", L"Cancel", L"Annuler" };
static const LStr T_MSG_SAVED   = { L"Настройки путей программ успешно сохранены!", L"Program paths saved successfully!", L"Paramètres des chemins enregistrés avec succès !" };
static const LStr T_MSG_TITLE   = { L"Успех", L"Success", L"Succès" };

// Global UI Handles & Brushes
static HWND g_hMainWnd = NULL;
static HWND g_hProxiEdit = NULL;
static HWND g_hExtEdit = NULL;
static HWND g_hBtnProxiBrowse = NULL;
static HWND g_hBtnProxiClear = NULL;
static HWND g_hBtnExtAdd = NULL;
static HWND g_hBtnExtClear = NULL;
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

// Hover tracking
static HWND g_hoveredBtn = NULL;

// Helper: UTF-8 <-> UTF-16
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

// Find data/config.json
std::wstring GetConfigFilePath() {
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);

    // Try parent directory if running inside bin/
    std::wstring p1 = dir + L"\\..\\data\\config.json";
    if (GetFileAttributesW(p1.c_str()) != INVALID_FILE_ATTRIBUTES) return p1;

    // Try same directory/data
    std::wstring p2 = dir + L"\\data\\config.json";
    if (GetFileAttributesW(p2.c_str()) != INVALID_FILE_ATTRIBUTES) return p2;

    return p1;
}

// Simple JSON extraction and saving
void LoadConfigData(std::wstring& proxiApp, std::wstring& extPrograms) {
    g_configPath = GetConfigFilePath();
    std::ifstream file(g_configPath, std::ios::binary);
    if (!file.is_open()) return;

    std::stringstream ss;
    ss << file.rdbuf();
    std::string content = ss.str();
    file.close();

    // 1. Detect language
    size_t posLang = content.find("\"language\"");
    if (posLang != std::string::npos) {
        size_t col = content.find(":", posLang);
        if (col != std::string::npos) {
            size_t q1 = content.find("\"", col);
            size_t q2 = (q1 != std::string::npos) ? content.find("\"", q1 + 1) : std::string::npos;
            if (q1 != std::string::npos && q2 != std::string::npos) {
                std::string lval = content.substr(q1 + 1, q2 - q1 - 1);
                if (lval == "fr") g_lang = LANG_FR;
                else if (lval == "en") g_lang = LANG_EN;
                else if (lval == "ru") g_lang = LANG_RU;
            }
        }
    }

    // 2. Extract proxification_app
    size_t posProxi = content.find("\"proxification_app\"");
    if (posProxi != std::string::npos) {
        size_t col = content.find(":", posProxi);
        if (col != std::string::npos) {
            size_t q1 = content.find("\"", col);
            size_t q2 = (q1 != std::string::npos) ? content.find("\"", q1 + 1) : std::string::npos;
            if (q1 != std::string::npos && q2 != std::string::npos) {
                std::string raw = content.substr(q1 + 1, q2 - q1 - 1);
                std::string unesc;
                for (size_t i = 0; i < raw.size(); ++i) {
                    if (raw[i] == '\\' && i + 1 < raw.size()) {
                        unesc += raw[i + 1];
                        i++;
                    } else {
                        unesc += raw[i];
                    }
                }
                proxiApp = Utf8ToUtf16(unesc);
            }
        }
    }

    // 3. Extract ext_programs
    size_t posExt = content.find("\"ext_programs\"");
    if (posExt != std::string::npos) {
        size_t b1 = content.find("[", posExt);
        size_t b2 = (b1 != std::string::npos) ? content.find("]", b1) : std::string::npos;
        if (b1 != std::string::npos && b2 != std::string::npos) {
            std::string arr = content.substr(b1 + 1, b2 - b1 - 1);
            std::wstring result;
            size_t cur = 0;
            while (cur < arr.size()) {
                size_t q1 = arr.find("\"", cur);
                if (q1 == std::string::npos) break;
                size_t q2 = arr.find("\"", q1 + 1);
                if (q2 == std::string::npos) break;
                std::string item = arr.substr(q1 + 1, q2 - q1 - 1);
                std::string unesc;
                for (size_t i = 0; i < item.size(); ++i) {
                    if (item[i] == '\\' && i + 1 < item.size()) {
                        unesc += item[i + 1];
                        i++;
                    } else {
                        unesc += item[i];
                    }
                }
                if (!result.empty()) result += L"\r\n";
                result += Utf8ToUtf16(unesc);
                cur = q2 + 1;
            }
            extPrograms = result;
        }
    }
}

// Escape JSON string
std::string EscapeJson(const std::string& in) {
    std::string out;
    for (char c : in) {
        if (c == '\\') out += "\\\\";
        else if (c == '\"') out += "\\\"";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') continue;
        else if (c == '\t') out += "\\t";
        else out += c;
    }
    return out;
}

bool SaveConfigData(const std::wstring& proxiApp, const std::wstring& extPrograms) {
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

    std::string utf8Proxi = Utf16ToUtf8(proxiApp);
    std::string proxiLine = "\"proxification_app\": \"" + EscapeJson(utf8Proxi) + "\"";

    // Split external programs lines
    std::vector<std::string> progs;
    std::wstring curLine;
    for (wchar_t c : extPrograms) {
        if (c == L'\r' || c == L'\n') {
            if (!curLine.empty()) {
                progs.push_back(Utf16ToUtf8(curLine));
                curLine.clear();
            }
        } else {
            curLine += c;
        }
    }
    if (!curLine.empty()) progs.push_back(Utf16ToUtf8(curLine));

    std::string extBlock = "\"ext_programs\": [\n";
    for (size_t i = 0; i < progs.size(); ++i) {
        extBlock += "    \"" + EscapeJson(progs[i]) + "\"";
        if (i + 1 < progs.size()) extBlock += ",";
        extBlock += "\n";
    }
    extBlock += "  ]";

    // Update proxification_app
    size_t posP = content.find("\"proxification_app\"");
    if (posP != std::string::npos) {
        size_t endLine = content.find("\n", posP);
        if (endLine == std::string::npos) endLine = content.size();
        bool hasComma = (content.find(",", posP) < endLine);
        content.replace(posP, endLine - posP, "  " + proxiLine + (hasComma ? "," : ""));
    } else {
        size_t brace = content.find("{");
        if (brace != std::string::npos) {
            content.insert(brace + 1, "\n  " + proxiLine + ",");
        }
    }

    // Update ext_programs
    size_t posE = content.find("\"ext_programs\"");
    if (posE != std::string::npos) {
        size_t b1 = content.find("[", posE);
        size_t b2 = (b1 != std::string::npos) ? content.find("]", b1) : std::string::npos;
        if (b1 != std::string::npos && b2 != std::string::npos) {
            size_t nextEnd = b2 + 1;
            bool hasComma = (nextEnd < content.size() && content[nextEnd] == ',');
            if (hasComma) nextEnd++;
            content.replace(posE, nextEnd - posE, "  " + extBlock + (hasComma ? "," : ""));
        }
    } else {
        size_t brace = content.find("{");
        if (brace != std::string::npos) {
            content.insert(brace + 1, "\n  " + extBlock + ",");
        }
    }

    std::ofstream out(g_configPath, std::ios::binary | std::ios::trunc);
    if (!out.is_open()) return false;
    out.write(content.c_str(), content.size());
    out.close();
    return true;
}

// Owner draw button renderer
void DrawCustomButton(LPDRAWITEMSTRUCT dis) {
    HDC hdc = dis->hDC;
    RECT rc = dis->rcItem;
    bool isSelected = (dis->itemState & ODS_SELECTED) != 0;
    bool isHovered = (dis->hwndItem == g_hoveredBtn);
    bool isPrimary = (dis->CtlID == IDC_BTN_SAVE);

    // 1. Fill entire button client rectangle with parent window background #181818 first!
    // This eliminates any white / default dialog color in the 4 rounded corners!
    FillRect(hdc, &rc, g_hBrushBg);

    // 2. Select button fill and border color
    COLORREF colBg;
    if (isPrimary) {
        if (isSelected) colBg = RGB(0, 90, 158);
        else if (isHovered) colBg = RGB(16, 132, 216);
        else colBg = RGB(0, 120, 212);
    } else {
        if (isSelected) colBg = RGB(32, 32, 32);
        else if (isHovered) colBg = RGB(56, 56, 56);
        else colBg = RGB(45, 45, 45);
    }

    HBRUSH hBr = CreateSolidBrush(colBg);
    HPEN hPen = CreatePen(PS_SOLID, 1, isPrimary ? colBg : (isHovered ? RGB(85, 85, 85) : RGB(61, 61, 61)));
    HGDIOBJ oldBr = SelectObject(hdc, hBr);
    HGDIOBJ oldPen = SelectObject(hdc, hPen);

    // 3. Draw rounded button
    RoundRect(hdc, rc.left, rc.top, rc.right, rc.bottom, 6, 6);

    SelectObject(hdc, oldBr);
    SelectObject(hdc, oldPen);
    DeleteObject(hBr);
    DeleteObject(hPen);

    // 4. Draw button text
    wchar_t text[128];
    GetWindowTextW(dis->hwndItem, text, 128);
    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(255, 255, 255));
    SelectObject(hdc, g_hFontNormal);
    DrawTextW(hdc, text, -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
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

// Window Procedure
LRESULT CALLBACK WndProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        g_hMainWnd = hWnd;

        // Fonts
        g_hFontNormal = CreateFontW(-13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold   = CreateFontW(-13, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontSmall  = CreateFontW(-11, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        // Load config
        std::wstring proxiApp, extPrograms;
        LoadConfigData(proxiApp, extPrograms);

        // Proxifier Edit (Y=56)
        g_hProxiEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", proxiApp.c_str(),
            WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL,
            24, 56, 330, 26, hWnd, (HMENU)IDC_PROXI_EDIT, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hProxiEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Browse Proxifier
        g_hBtnProxiBrowse = CreateWindowExW(0, L"BUTTON", T_BTN_BROWSE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            360, 56, 72, 26, hWnd, (HMENU)IDC_PROXI_BROWSE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnProxiBrowse, ButtonSubclassProc, IDC_PROXI_BROWSE, 0);

        // Clear Proxifier
        g_hBtnProxiClear = CreateWindowExW(0, L"BUTTON", T_BTN_CLEAR.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            438, 56, 60, 26, hWnd, (HMENU)IDC_PROXI_CLEAR, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnProxiClear, ButtonSubclassProc, IDC_PROXI_CLEAR, 0);

        // External Programs Edit (Multiline, Y=160, height=230)
        g_hExtEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", extPrograms.c_str(),
            WS_CHILD | WS_VISIBLE | ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL,
            24, 160, 474, 230, hWnd, (HMENU)IDC_EXT_EDIT, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hExtEdit, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Add File (Y=400)
        g_hBtnExtAdd = CreateWindowExW(0, L"BUTTON", T_BTN_ADD.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            24, 400, 140, 28, hWnd, (HMENU)IDC_EXT_ADD, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnExtAdd, ButtonSubclassProc, IDC_EXT_ADD, 0);

        // Clear External List (Y=400)
        g_hBtnExtClear = CreateWindowExW(0, L"BUTTON", T_BTN_EXT_CLR.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            172, 400, 130, 28, hWnd, (HMENU)IDC_EXT_CLEAR, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnExtClear, ButtonSubclassProc, IDC_EXT_CLEAR, 0);

        // Save Button (Primary Blue, Y=455)
        g_hBtnSave = CreateWindowExW(0, L"BUTTON", T_BTN_SAVE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            260, 455, 115, 32, hWnd, (HMENU)IDC_BTN_SAVE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnSave, ButtonSubclassProc, IDC_BTN_SAVE, 0);

        // Cancel Button (Gray, Y=455)
        g_hBtnCancel = CreateWindowExW(0, L"BUTTON", T_BTN_CANCEL.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            383, 455, 115, 32, hWnd, (HMENU)IDC_BTN_CANCEL, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnCancel, ButtonSubclassProc, IDC_BTN_CANCEL, 0);

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
        if (id == IDC_PROXI_BROWSE) {
            wchar_t szFile[MAX_PATH] = L"";
            OPENFILENAMEW ofn = { sizeof(OPENFILENAMEW) };
            ofn.hwndOwner = hWnd;
            ofn.lpstrFilter = L"Executables (*.exe)\0*.exe\0All Files (*.*)\0*.*\0";
            ofn.lpstrFile = szFile;
            ofn.nMaxFile = MAX_PATH;
            ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST;
            if (GetOpenFileNameW(&ofn)) {
                SetWindowTextW(g_hProxiEdit, szFile);
            }
        }
        else if (id == IDC_PROXI_CLEAR) {
            SetWindowTextW(g_hProxiEdit, L"");
        }
        else if (id == IDC_EXT_ADD) {
            wchar_t szFile[MAX_PATH] = L"";
            OPENFILENAMEW ofn = { sizeof(OPENFILENAMEW) };
            ofn.hwndOwner = hWnd;
            ofn.lpstrFilter = L"Executables (*.exe;*.bat;*.cmd)\0*.exe;*.bat;*.cmd\0All Files (*.*)\0*.*\0";
            ofn.lpstrFile = szFile;
            ofn.nMaxFile = MAX_PATH;
            ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST;
            if (GetOpenFileNameW(&ofn)) {
                int len = GetWindowTextLengthW(g_hExtEdit);
                std::vector<wchar_t> buf(len + 1);
                GetWindowTextW(g_hExtEdit, buf.data(), len + 1);
                std::wstring text = buf.data();
                if (!text.empty() && text.back() != L'\n') text += L"\r\n";
                text += szFile;
                SetWindowTextW(g_hExtEdit, text.c_str());
            }
        }
        else if (id == IDC_EXT_CLEAR) {
            SetWindowTextW(g_hExtEdit, L"");
        }
        else if (id == IDC_BTN_SAVE) {
            int lenP = GetWindowTextLengthW(g_hProxiEdit);
            std::vector<wchar_t> bufP(lenP + 1);
            GetWindowTextW(g_hProxiEdit, bufP.data(), lenP + 1);

            int lenE = GetWindowTextLengthW(g_hExtEdit);
            std::vector<wchar_t> bufE(lenE + 1);
            GetWindowTextW(g_hExtEdit, bufE.data(), lenE + 1);

            if (SaveConfigData(bufP.data(), bufE.data())) {
                MessageBoxW(hWnd, T_MSG_SAVED.get(), T_MSG_TITLE.get(), MB_OK | MB_ICONINFORMATION);
                DestroyWindow(hWnd);
            } else {
                MessageBoxW(hWnd, L"Error saving config.json", L"Error", MB_OK | MB_ICONERROR);
            }
        }
        else if (id == IDC_BTN_CANCEL) {
            DestroyWindow(hWnd);
        }
        return 0;
    }

    case WM_CTLCOLORBTN: {
        return (INT_PTR)g_hBrushBg;
    }

    case WM_CTLCOLOREDIT: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, RGB(255, 255, 255));
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

        // Group 1: Proxifier (Top=12, Bottom=96)
        HPEN hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        HGDIOBJ oldPen = SelectObject(hdc, hPenBorder);
        HGDIOBJ oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));

        RoundRect(hdc, 12, 12, 508, 96, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        // Group 1 Title (breaks border cleanly with opaque background)
        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 22, 4, T_GRP_PROXI.get(), (int)wcslen(T_GRP_PROXI.get()));

        // Group 1 Label (Y=30)
        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 24, 30, T_LBL_PROXI.get(), (int)wcslen(T_LBL_PROXI.get()));

        // Group 2: External Programs (Top=112, Bottom=440)
        hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        oldPen = SelectObject(hdc, hPenBorder);
        oldBr = SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));

        RoundRect(hdc, 12, 112, 508, 440, 8, 8);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        // Group 2 Title (breaks border cleanly with opaque background)
        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colTitle);
        SetBkMode(hdc, OPAQUE);
        SetBkColor(hdc, g_colBg);
        TextOutW(hdc, 22, 104, T_GRP_EXT.get(), (int)wcslen(T_GRP_EXT.get()));

        // Group 2 Label (Y=132)
        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 24, 132, T_LBL_EXT.get(), (int)wcslen(T_LBL_EXT.get()));

        EndPaint(hWnd, &ps);
        return 0;
    }

    case WM_DESTROY:
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

    // Initial system language check
    LANGID langId = GetUserDefaultUILanguage();
    WORD priLang = langId & 0xFF;
    if (priLang == 0x0C) g_lang = LANG_FR;
    else if (priLang == 0x09) g_lang = LANG_EN;
    else g_lang = LANG_RU;

    // Load config to check manual language preference
    std::wstring p, e;
    LoadConfigData(p, e);

    g_hBrushBg = CreateSolidBrush(g_colBg);
    g_hBrushEditBg = CreateSolidBrush(g_colEditBg);

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetProgPathsWnd";

    // Load icon
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);
    std::wstring icoPath = dir + L"\\..\\icon.ico";
    HICON hIcon = (HICON)LoadImageW(NULL, icoPath.c_str(), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
    if (!hIcon) {
        icoPath = dir + L"\\icon.ico";
        hIcon = (HICON)LoadImageW(NULL, icoPath.c_str(), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
    }
    if (hIcon) {
        wc.hIcon = hIcon;
        wc.hIconSm = hIcon;
    }

    RegisterClassExW(&wc);

    // Window dimensions (528 x 540)
    int width = 528;
    int height = 540;
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

    // Dark Title Bar via DWM API
    BOOL darkMode = TRUE;
    DwmSetWindowAttribute(hWnd, 20, &darkMode, sizeof(darkMode)); // DWMWA_USE_IMMERSIVE_DARK_MODE
    DwmSetWindowAttribute(hWnd, 19, &darkMode, sizeof(darkMode));
    COLORREF captionColor = RGB(24, 24, 24);
    DwmSetWindowAttribute(hWnd, 35, &captionColor, sizeof(captionColor)); // DWMWA_CAPTION_COLOR

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
