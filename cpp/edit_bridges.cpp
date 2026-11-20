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
#include <cctype>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "shell32.lib")

// Control IDs
#define IDC_BRIDGES_EDIT    101
#define IDC_BTN_ADD         102
#define IDC_BTN_REPLACE     103
#define IDC_BTN_UPDATE      104
#define IDC_BTN_CONFIG      105
#define IDC_BTN_CLEAR       106

// Action Dialog Control IDs
#define IDC_ACT_ADD         201
#define IDC_ACT_REPLACE     202
#define IDC_ACT_LEAVE       203

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

static const LStr T_WIN_TITLE         = { L"Менеджер Tor мостов", L"Tor Bridge Manager", L"Gestionnaire de ponts Tor" };
static const LStr T_HEADER            = { L"Менеджер Tor мостов", L"Tor Bridge Manager", L"Gestionnaire de ponts Tor" };
static const LStr T_COUNT_PREFIX      = { L"Загружено мостов: ", L"Bridges loaded: ", L"Ponts chargés : " };
static const LStr T_FILE_STATUS       = { L"Файл: bridges.txt", L"File: bridges.txt", L"Fichier : bridges.txt" };
static const LStr T_EDITOR_LABEL      = { L"Введите мосты (каждый с новой строки):", L"Enter bridges (one per line):", L"Entrez les ponts (un par ligne) :" };

static const LStr T_BTN_ADD           = { L"Добавить мосты", L"Add bridges", L"Ajouter des ponts" };
static const LStr T_BTN_REPLACE       = { L"Заменить мосты", L"Replace bridges", L"Remplacer les ponts" };
static const LStr T_BTN_UPDATE        = { L"Обновить конфигурацию", L"Update configuration", L"Mettre à jour la configuration" };
static const LStr T_BTN_CONFIG        = { L"Настроить конфигурацию", L"Configure Tor", L"Configurer Tor" };
static const LStr T_BTN_CLEAR         = { L"Очистить поле ввода", L"Clear input field", L"Effacer le champ de saisie" };

static const LStr T_STATUS_READY      = { L"Готов к работе", L"Ready", L"Prêt" };
static const LStr T_STATUS_EMPTY      = { L"Поле ввода пусто", L"Input field is empty", L"Le champ de saisie est vide" };
static const LStr T_STATUS_CLEARED    = { L"Поле ввода очищено", L"Input field cleared", L"Champ de saisie effacé" };
static const LStr T_STATUS_TORRC_DEL  = { L"Файл torrc успешно удален", L"File torrc deleted successfully", L"Fichier torrc supprimé avec succès" };
static const LStr T_STATUS_TORRC_NF   = { L"Файл torrc не найден", L"File torrc not found", L"Fichier torrc introuvable" };
static const LStr T_STATUS_MAESTRO_RUN= { L"Программа maestro.pyw запущена", L"Maestro program launched", L"Programme maestro.pyw lancé" };
static const LStr T_STATUS_MAESTRO_NF = { L"Файл maestro.pyw не найден", L"File maestro.pyw not found", L"Fichier maestro.pyw introuvable" };

static const LStr T_MSG_TITLE_INFO    = { L"Информация", L"Information", L"Information" };
static const LStr T_MSG_TITLE_CONF    = { L"Подтверждение", L"Confirmation", L"Confirmation" };
static const LStr T_MSG_TITLE_WARN    = { L"Пустой ввод", L"Warning", L"Avertissement" };
static const LStr T_MSG_TITLE_ERR     = { L"Ошибка", L"Error", L"Erreur" };
static const LStr T_MSG_TITLE_OK      = { L"Успех", L"Success", L"Succès" };

static const LStr T_ERR_EMPTY_ADD     = { L"Введите текст для добавления", L"Enter text to add", L"Entrez du texte à ajouter" };
static const LStr T_ERR_EMPTY_REP     = { L"Введите текст для замены", L"Enter text to replace", L"Entrez du texte pour remplacer" };
static const LStr T_ERR_NO_VALID_ADD  = { L"Не найдено валидных мостов для добавления", L"No valid bridges found to add", L"Aucun pont valide trouvé à ajouter" };
static const LStr T_ERR_NO_VALID_REP  = { L"Не найдено валидных мостов для замены", L"No valid bridges found to replace", L"Aucun pont valide trouvé pour remplacer" };
static const LStr T_INFO_ALL_EXIST    = { L"Все мосты уже существуют в файле", L"All bridges already exist in the file", L"Tous les ponts existent déjà dans le fichier" };

static const LStr T_CONF_CLEAR        = { L"Вы уверены, что хотите очистить поле ввода?", L"Are you sure you want to clear the input field?", L"Voulez-vous vraiment effacer le champ de saisie ?" };

// Action Dialog
static const LStr T_ACT_TITLE         = { L"Выбор действия", L"Choose Action", L"Choix de l'action" };
static const LStr T_ACT_HEAD          = { L"Внесены изменения в мосты", L"Bridge Changes Detected", L"Modifications apportées aux ponts" };
static const LStr T_ACT_DESC          = { L"Были внесены изменения в список мостов.\nВыберите действие перед запуском конфигуратора:", L"Changes were made to the bridges list.\nChoose an action before launching configurator:", L"Des modifications ont été apportées à la liste des ponts.\nChoisissez une action avant de lancer le configurateur :" };
static const LStr T_ACT_BTN_ADD       = { L"Добавить мосты", L"Add bridges", L"Ajouter des ponts" };
static const LStr T_ACT_BTN_REP       = { L"Заменить мосты", L"Replace bridges", L"Remplacer les ponts" };
static const LStr T_ACT_BTN_LEAVE     = { L"Оставить как есть", L"Leave as is", L"Laisser tel quel" };

// Global UI Handles
static HWND g_hMainWnd = NULL;
static HWND g_hEdit = NULL;
static HWND g_hBtnAdd = NULL;
static HWND g_hBtnReplace = NULL;
static HWND g_hBtnUpdate = NULL;
static HWND g_hBtnConfig = NULL;
static HWND g_hBtnClear = NULL;

static HFONT g_hFontTitle = NULL;
static HFONT g_hFontNormal = NULL;
static HFONT g_hFontBold = NULL;
static HFONT g_hFontMono = NULL;
static HFONT g_hFontSmall = NULL;

static HBRUSH g_hBrushBg = NULL;      // #181818
static HBRUSH g_hBrushPanel = NULL;   // #1E1E1E
static HBRUSH g_hBrushEditBg = NULL;  // #242424

static COLORREF g_colBg = RGB(24, 24, 24);
static COLORREF g_colPanel = RGB(30, 30, 30);
static COLORREF g_colEditBg = RGB(36, 36, 36);
static COLORREF g_colText = RGB(224, 224, 224);
static COLORREF g_colAccentGreen = RGB(65, 140, 80);

// Paths & State
static std::wstring g_rootDir;
static std::wstring g_dataDir;
static std::wstring g_bridgesPath;
static std::wstring g_torrcPath;
static std::wstring g_maestroPath;
static std::wstring g_configPath;

static bool g_changesMade = false;
static int g_bridgesCount = 0;
static std::wstring g_statusMsg;
static HWND g_hoveredBtn = NULL;

enum ActionChoice { ACT_NONE = 0, ACT_ADD, ACT_REPLACE, ACT_LEAVE, ACT_CANCEL };
static ActionChoice g_actionResult = ACT_NONE;

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

static std::string Trim(const std::string& s) {
    size_t start = s.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return "";
    size_t end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

static std::wstring TrimW(const std::wstring& s) {
    size_t start = s.find_first_not_of(L" \t\r\n");
    if (start == std::wstring::npos) return L"";
    size_t end = s.find_last_not_of(L" \t\r\n");
    return s.substr(start, end - start + 1);
}

// Path initialization
void InitPaths() {
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);

    // Check if running from bin/ or cpp/ or root
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

    g_dataDir = g_rootDir + L"\\data";
    g_bridgesPath = g_dataDir + L"\\bridges.txt";
    g_torrcPath = g_dataDir + L"\\torrc";
    g_configPath = g_dataDir + L"\\config.json";
    g_maestroPath = g_rootDir + L"\\ui\\maestro.pyw";
}

// Language preference loading
void LoadLanguagePreference() {
    std::ifstream file(g_configPath, std::ios::binary);
    if (!file.is_open()) return;
    std::stringstream ss;
    ss << file.rdbuf();
    std::string content = ss.str();
    file.close();

    size_t posLang = content.find("\"language\"");
    if (posLang != std::string::npos) {
        size_t col = content.find(':', posLang);
        if (col != std::string::npos) {
            size_t q1 = content.find('\"', col);
            size_t q2 = (q1 != std::string::npos) ? content.find('\"', q1 + 1) : std::string::npos;
            if (q1 != std::string::npos && q2 != std::string::npos) {
                std::string lval = content.substr(q1 + 1, q2 - q1 - 1);
                if (lval == "fr") g_lang = LANG_FR;
                else if (lval == "en") g_lang = LANG_EN;
                else if (lval == "ru") g_lang = LANG_RU;
            }
        }
    }
}

void SetStatus(const std::wstring& msg) {
    g_statusMsg = msg;
    if (g_hMainWnd) {
        RECT rc = { 0, 538, 704, 566 };
        InvalidateRect(g_hMainWnd, &rc, FALSE);
    }
}

// Extract valid bridges from text
std::vector<std::string> GetValidBridges(const std::wstring& textW) {
    std::vector<std::string> bridges;
    std::string text = Utf16ToUtf8(textW);
    std::stringstream ss(text);
    std::string line;
    while (std::getline(ss, line)) {
        std::string trimmed = Trim(line);
        if (!trimmed.empty() && trimmed[0] != '#') {
            bridges.push_back(trimmed);
        }
    }
    return bridges;
}

// Load existing bridges from data/bridges.txt
void LoadExistingBridges() {
    g_bridgesCount = 0;
    std::ifstream f(g_bridgesPath, std::ios::binary);
    if (f.is_open()) {
        std::string line;
        while (std::getline(f, line)) {
            std::string t = Trim(line);
            if (!t.empty()) g_bridgesCount++;
        }
        f.close();
        if (g_bridgesCount > 0) {
            wchar_t buf[256];
            swprintf_s(buf, 256, (g_lang == LANG_RU) ? L"Загружено %d мостов из bridges.txt" :
                                ((g_lang == LANG_FR) ? L"%d ponts chargés depuis bridges.txt" :
                                                       L"Loaded %d bridges from bridges.txt"), g_bridgesCount);
            SetStatus(buf);
        } else {
            SetStatus(T_STATUS_READY.get());
        }
    } else {
        SetStatus(T_STATUS_READY.get());
    }
    if (g_hMainWnd) {
        RECT rc = { 20, 60, 684, 98 };
        InvalidateRect(g_hMainWnd, &rc, FALSE);
    }
}

// Clear tor cache files in data/ safely
void ClearTorCache() {
    WIN32_FIND_DATAW ffd;
    std::wstring searchPattern = g_dataDir + L"\\*";
    HANDLE hFind = FindFirstFileW(searchPattern.c_str(), &ffd);
    if (hFind == INVALID_HANDLE_VALUE) return;

    do {
        if (wcscmp(ffd.cFileName, L".") == 0 || wcscmp(ffd.cFileName, L"..") == 0) continue;

        std::wstring name = ffd.cFileName;
        std::wstring fullPath = g_dataDir + L"\\" + name;

        // Never touch geoip, bridges.txt, config files, user data!
        if (wcsncmp(name.c_str(), L"cached-", 7) == 0 ||
            _wcsicmp(name.c_str(), L"lock") == 0 ||
            _wcsicmp(name.c_str(), L"state") == 0) {
            DeleteFileW(fullPath.c_str());
        }
    } while (FindNextFileW(hFind, &ffd));

    FindClose(hFind);
}

// Button actions
void AddBridges() {
    int len = GetWindowTextLengthW(g_hEdit);
    if (len == 0) {
        MessageBoxW(g_hMainWnd, T_ERR_EMPTY_ADD.get(), T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
        return;
    }
    std::vector<wchar_t> buf(len + 1);
    GetWindowTextW(g_hEdit, buf.data(), len + 1);
    auto bridges = GetValidBridges(buf.data());
    if (bridges.empty()) {
        MessageBoxW(g_hMainWnd, T_ERR_NO_VALID_ADD.get(), T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
        return;
    }

    // Read existing
    std::vector<std::string> existing;
    std::ifstream fin(g_bridgesPath, std::ios::binary);
    if (fin.is_open()) {
        std::string line;
        while (std::getline(fin, line)) {
            std::string t = Trim(line);
            if (!t.empty()) existing.push_back(t);
        }
        fin.close();
    }

    std::vector<std::string> newBridges;
    for (const auto& b : bridges) {
        if (std::find(existing.begin(), existing.end(), b) == existing.end() &&
            std::find(newBridges.begin(), newBridges.end(), b) == newBridges.end()) {
            newBridges.push_back(b);
        }
    }

    if (newBridges.empty()) {
        MessageBoxW(g_hMainWnd, T_INFO_ALL_EXIST.get(), T_MSG_TITLE_INFO.get(), MB_OK | MB_ICONINFORMATION);
        return;
    }

    // Append to bridges.txt
    std::ofstream fout(g_bridgesPath, std::ios::binary | std::ios::app);
    if (!fout.is_open()) {
        MessageBoxW(g_hMainWnd, L"Failed to open bridges.txt for writing", T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONERROR);
        return;
    }
    for (const auto& b : newBridges) {
        fout << b << "\n";
    }
    fout.close();

    g_changesMade = true;
    SetWindowTextW(g_hEdit, L"");
    LoadExistingBridges();
    ClearTorCache();

    wchar_t msgBuf[256];
    swprintf_s(msgBuf, 256, (g_lang == LANG_RU) ? L"Добавлено %d новых мостов" :
                           ((g_lang == LANG_FR) ? L"%d nouveaux ponts ajoutés" :
                                                  L"Added %d new bridges"), (int)newBridges.size());
    MessageBoxW(g_hMainWnd, msgBuf, T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
    SetStatus(msgBuf);
}

void ReplaceBridges() {
    int len = GetWindowTextLengthW(g_hEdit);
    if (len == 0) {
        MessageBoxW(g_hMainWnd, T_ERR_EMPTY_REP.get(), T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
        return;
    }
    std::vector<wchar_t> buf(len + 1);
    GetWindowTextW(g_hEdit, buf.data(), len + 1);
    auto bridges = GetValidBridges(buf.data());
    if (bridges.empty()) {
        MessageBoxW(g_hMainWnd, T_ERR_NO_VALID_REP.get(), T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
        return;
    }

    wchar_t confirmBuf[512];
    swprintf_s(confirmBuf, 512, (g_lang == LANG_RU) ? L"Вы уверены, что хотите заменить всё содержимое файла %s?\nБудет добавлено %d мостов." :
                               ((g_lang == LANG_FR) ? L"Voulez-vous vraiment remplacer le contenu de %s ?\n%d ponts seront ajoutés." :
                                                      L"Are you sure you want to replace all contents of %s?\n%d bridges will be added."),
               g_bridgesPath.c_str(), (int)bridges.size());

    if (MessageBoxW(g_hMainWnd, confirmBuf, T_MSG_TITLE_CONF.get(), MB_YESNO | MB_ICONQUESTION) != IDYES) {
        return;
    }

    std::ofstream fout(g_bridgesPath, std::ios::binary | std::ios::trunc);
    if (!fout.is_open()) {
        MessageBoxW(g_hMainWnd, L"Failed to open bridges.txt for writing", T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONERROR);
        return;
    }
    for (const auto& b : bridges) {
        fout << b << "\n";
    }
    fout.close();

    g_changesMade = true;
    SetWindowTextW(g_hEdit, L"");
    LoadExistingBridges();
    ClearTorCache();

    wchar_t okBuf[256];
    swprintf_s(okBuf, 256, (g_lang == LANG_RU) ? L"Содержимое файла успешно заменено. Добавлено %d мостов." :
                          ((g_lang == LANG_FR) ? L"Contenu remplacé avec succès. %d ponts ajoutés." :
                                                 L"File contents successfully replaced. Added %d bridges."), (int)bridges.size());
    MessageBoxW(g_hMainWnd, okBuf, T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
    SetStatus(okBuf);
}

void UpdateConfig() {
    if (GetFileAttributesW(g_torrcPath.c_str()) != INVALID_FILE_ATTRIBUTES) {
        wchar_t prompt[512];
        swprintf_s(prompt, 512, (g_lang == LANG_RU) ? L"Вы уверены, что хотите удалить файл %s?" :
                                ((g_lang == LANG_FR) ? L"Voulez-vous vraiment supprimer le fichier %s ?" :
                                                       L"Are you sure you want to delete file %s?"), g_torrcPath.c_str());

        if (MessageBoxW(g_hMainWnd, prompt, T_MSG_TITLE_CONF.get(), MB_YESNO | MB_ICONQUESTION) == IDYES) {
            DeleteFileW(g_torrcPath.c_str());
            SetStatus(T_STATUS_TORRC_DEL.get());
            MessageBoxW(g_hMainWnd, T_STATUS_TORRC_DEL.get(), T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
        }
    } else {
        wchar_t info[512];
        swprintf_s(info, 512, (g_lang == LANG_RU) ? L"Файл %s не существует в папке data" :
                              ((g_lang == LANG_FR) ? L"Le fichier %s n'existe pas dans data" :
                                                     L"File %s does not exist in data"), g_torrcPath.c_str());
        MessageBoxW(g_hMainWnd, info, T_MSG_TITLE_INFO.get(), MB_OK | MB_ICONINFORMATION);
        SetStatus(T_STATUS_TORRC_NF.get());
    }
}

void LaunchMaestro() {
    std::wstring maestroExe = g_rootDir + L"\\bin\\maestro.exe";
    std::wstring maestroPyw = g_maestroPath;

    bool launched = false;
    if (GetFileAttributesW(maestroExe.c_str()) != INVALID_FILE_ATTRIBUTES) {
        HINSTANCE hInst = ShellExecuteW(NULL, L"open", maestroExe.c_str(), NULL, NULL, SW_SHOWNORMAL);
        launched = ((INT_PTR)hInst > 32);
    }

    if (!launched && GetFileAttributesW(maestroPyw.c_str()) != INVALID_FILE_ATTRIBUTES) {
        HINSTANCE hInst = ShellExecuteW(NULL, L"open", maestroPyw.c_str(), NULL, NULL, SW_SHOWNORMAL);
        launched = ((INT_PTR)hInst > 32);

        if (!launched) {
            // Try pythonw or python
            std::wstring cmd = L"pythonw.exe \"" + maestroPyw + L"\"";
            STARTUPINFOW si = { sizeof(si) };
            PROCESS_INFORMATION pi = {};
            std::vector<wchar_t> cmdBuf(cmd.begin(), cmd.end());
            cmdBuf.push_back(0);
            if (CreateProcessW(NULL, cmdBuf.data(), NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
                CloseHandle(pi.hProcess);
                CloseHandle(pi.hThread);
                launched = true;
            }
        }
    }

    if (launched) {
        SetStatus(T_STATUS_MAESTRO_RUN.get());
        MessageBoxW(g_hMainWnd, T_STATUS_MAESTRO_RUN.get(), T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
    } else {
        SetStatus(T_STATUS_MAESTRO_NF.get());
        wchar_t warn[512];
        swprintf_s(warn, 512, (g_lang == LANG_RU) ? L"Файл maestro.pyw не найден в %s" :
                              ((g_lang == LANG_FR) ? L"Fichier maestro.pyw introuvable dans %s" :
                                                     L"File maestro.pyw not found in %s"), maestroPyw.c_str());
        MessageBoxW(g_hMainWnd, warn, T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
    }
}

// Action Dialog Callback
LRESULT CALLBACK ActionDlgProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_ERASEBKGND: {
        HDC hdc = (HDC)wParam;
        RECT rc;
        GetClientRect(hWnd, &rc);
        FillRect(hdc, &rc, g_hBrushBg);
        return 1;
    }
    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT dis = (LPDRAWITEMSTRUCT)lParam;
        if (dis->CtlType == ODT_BUTTON) {
            HDC hdc = dis->hDC;
            RECT rc = dis->rcItem;
            bool isSelected = (dis->itemState & ODS_SELECTED) != 0;
            bool isHovered = (dis->hwndItem == g_hoveredBtn);

            FillRect(hdc, &rc, g_hBrushBg);

            COLORREF colBg;
            COLORREF colBorder;
            if (dis->CtlID == IDC_ACT_ADD) {
                if (isSelected)      { colBg = RGB(35, 78, 42);  colBorder = RGB(48, 100, 58); }
                else if (isHovered)  { colBg = RGB(55, 112, 65); colBorder = RGB(70, 130, 80); }
                else                 { colBg = RGB(45, 95, 55);  colBorder = RGB(48, 100, 58); }
            } else if (dis->CtlID == IDC_ACT_REPLACE) {
                if (isSelected)      { colBg = RGB(105, 35, 35); colBorder = RGB(135, 48, 48); }
                else if (isHovered)  { colBg = RGB(150, 55, 55); colBorder = RGB(170, 68, 68); }
                else                 { colBg = RGB(130, 45, 45); colBorder = RGB(135, 48, 48); }
            } else { // IDC_ACT_LEAVE
                if (isSelected)      { colBg = RGB(24, 62, 96);  colBorder = RGB(36, 82, 126); }
                else if (isHovered)  { colBg = RGB(42, 92, 140); colBorder = RGB(52, 110, 165); }
                else                 { colBg = RGB(32, 78, 120); colBorder = RGB(36, 82, 126); }
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
            return TRUE;
        }
        break;
    }
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hWnd, &ps);

        RECT rcClient;
        GetClientRect(hWnd, &rcClient);

        // Header Title (Orange)
        SelectObject(hdc, g_hFontTitle);
        SetTextColor(hdc, RGB(255, 152, 0));
        SetBkMode(hdc, TRANSPARENT);
        RECT rcHead = { 20, 16, rcClient.right - 20, 42 };
        DrawTextW(hdc, T_ACT_HEAD.get(), -1, &rcHead, DT_CENTER | DT_SINGLELINE);

        // Description
        SelectObject(hdc, g_hFontNormal);
        SetTextColor(hdc, g_colText);
        RECT rcDesc = { 20, 48, rcClient.right - 20, 105 };
        DrawTextW(hdc, T_ACT_DESC.get(), -1, &rcDesc, DT_CENTER | DT_WORDBREAK);

        EndPaint(hWnd, &ps);
        return 0;
    }
    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == IDC_ACT_ADD) {
            g_actionResult = ACT_ADD;
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        } else if (id == IDC_ACT_REPLACE) {
            g_actionResult = ACT_REPLACE;
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        } else if (id == IDC_ACT_LEAVE) {
            g_actionResult = ACT_LEAVE;
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        }
        return 0;
    }
    case WM_CLOSE:
        if (g_actionResult == ACT_NONE) g_actionResult = ACT_CANCEL;
        return 0;
    }
    return DefWindowProcW(hWnd, uMsg, wParam, lParam);
}

// Subclass for hover buttons
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

// Subclass for Edit box to display placeholder
LRESULT CALLBACK EditSubclassProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam, UINT_PTR uIdSubclass, DWORD_PTR dwRefData) {
    (void)dwRefData;
    LRESULT lr = DefSubclassProc(hWnd, uMsg, wParam, lParam);
    if (uMsg == WM_PAINT) {
        if (GetWindowTextLengthW(hWnd) == 0 && GetFocus() != hWnd) {
            HDC hdc = GetDC(hWnd);
            RECT rc;
            GetClientRect(hWnd, &rc);
            InflateRect(&rc, -5, -4);
            SelectObject(hdc, g_hFontMono);
            SetTextColor(hdc, RGB(120, 120, 120));
            SetBkMode(hdc, TRANSPARENT);
            const wchar_t* placeholder = L"Пример:\r\nobfs4 192.95.36.142:443 2C5BED3F2B2D4F2A8F0B5E6D9C8A7B4E5F6A7B8 cert=...\r\nobfs4 193.11.166.194:443 1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B cert=...";
            DrawTextW(hdc, placeholder, -1, &rc, DT_LEFT | DT_TOP | DT_WORDBREAK);
            ReleaseDC(hWnd, hdc);
        }
    } else if (uMsg == WM_SETFOCUS || uMsg == WM_KILLFOCUS) {
        InvalidateRect(hWnd, NULL, TRUE);
    } else if (uMsg == WM_NCDESTROY) {
        RemoveWindowSubclass(hWnd, EditSubclassProc, uIdSubclass);
    }
    return lr;
}

ActionChoice ShowActionDialog(HWND hParent) {
    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = ActionDlgProc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetActionDlgClass";
    RegisterClassExW(&wc);

    int w = 460;
    int h = 205;
    RECT rcParent;
    GetWindowRect(hParent, &rcParent);
    int x = rcParent.left + (rcParent.right - rcParent.left - w) / 2;
    int y = rcParent.top + (rcParent.bottom - rcParent.top - h) / 2;

    HWND hDlg = CreateWindowExW(
        WS_EX_DLGMODALFRAME,
        L"ToInetActionDlgClass",
        T_ACT_TITLE.get(),
        WS_POPUP | WS_CAPTION | WS_SYSMENU,
        x, y, w, h,
        hParent, NULL, GetModuleHandle(NULL), NULL
    );

    if (!hDlg) return ACT_CANCEL;

    BOOL darkMode = TRUE;
    DwmSetWindowAttribute(hDlg, 20, &darkMode, sizeof(darkMode));
    DwmSetWindowAttribute(hDlg, 19, &darkMode, sizeof(darkMode));
    COLORREF captionColor = RGB(24, 24, 24);
    DwmSetWindowAttribute(hDlg, 35, &captionColor, sizeof(captionColor));

    // Create 3 Action Buttons
    HWND btnAdd = CreateWindowExW(0, L"BUTTON", T_ACT_BTN_ADD.get(),
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        20, 116, 130, 36, hDlg, (HMENU)IDC_ACT_ADD, GetModuleHandle(NULL), NULL);
    SetWindowSubclass(btnAdd, ButtonSubclassProc, IDC_ACT_ADD, 0);

    HWND btnRep = CreateWindowExW(0, L"BUTTON", T_ACT_BTN_REP.get(),
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        165, 116, 130, 36, hDlg, (HMENU)IDC_ACT_REPLACE, GetModuleHandle(NULL), NULL);
    SetWindowSubclass(btnRep, ButtonSubclassProc, IDC_ACT_REPLACE, 0);

    HWND btnLeave = CreateWindowExW(0, L"BUTTON", T_ACT_BTN_LEAVE.get(),
        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
        310, 116, 130, 36, hDlg, (HMENU)IDC_ACT_LEAVE, GetModuleHandle(NULL), NULL);
    SetWindowSubclass(btnLeave, ButtonSubclassProc, IDC_ACT_LEAVE, 0);

    ShowWindow(hDlg, SW_SHOW);
    UpdateWindow(hDlg);
    EnableWindow(hParent, FALSE);

    g_actionResult = ACT_NONE;
    MSG msg;
    while (g_actionResult == ACT_NONE && GetMessageW(&msg, NULL, 0, 0)) {
        if (msg.message == WM_KEYDOWN && msg.wParam == VK_ESCAPE) {
            g_actionResult = ACT_CANCEL;
            break;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    EnableWindow(hParent, TRUE);
    SetForegroundWindow(hParent);
    DestroyWindow(hDlg);
    UnregisterClassW(L"ToInetActionDlgClass", GetModuleHandle(NULL));

    return g_actionResult;
}

bool HasUnsavedInput() {
    int len = GetWindowTextLengthW(g_hEdit);
    if (len == 0) return false;
    std::vector<wchar_t> buf(len + 1);
    GetWindowTextW(g_hEdit, buf.data(), len + 1);
    auto bridges = GetValidBridges(buf.data());
    return !bridges.empty();
}

void ConfigureTor() {
    if (GetFileAttributesW(g_torrcPath.c_str()) != INVALID_FILE_ATTRIBUTES) {
        DeleteFileW(g_torrcPath.c_str());
    }

    if (g_changesMade || HasUnsavedInput()) {
        ActionChoice act = ShowActionDialog(g_hMainWnd);
        if (act == ACT_CANCEL) return;
        if (act == ACT_ADD) AddBridges();
        else if (act == ACT_REPLACE) ReplaceBridges();
    }

    LaunchMaestro();
}

void ClearInputText() {
    if (MessageBoxW(g_hMainWnd, T_CONF_CLEAR.get(), T_MSG_TITLE_CONF.get(), MB_YESNO | MB_ICONQUESTION) == IDYES) {
        SetWindowTextW(g_hEdit, L"");
        SetStatus(T_STATUS_CLEARED.get());
    }
}

void OnTextChanged() {
    int len = GetWindowTextLengthW(g_hEdit);
    if (len > 0) {
        std::vector<wchar_t> buf(len + 1);
        GetWindowTextW(g_hEdit, buf.data(), len + 1);
        auto bridges = GetValidBridges(buf.data());
        int count = (int)bridges.size();
        if (count > 0) {
            wchar_t msg[256];
            swprintf_s(msg, 256, (g_lang == LANG_RU) ? L"В поле ввода: %d мостов (не сохранено)" :
                                 ((g_lang == LANG_FR) ? L"Dans le champ : %d ponts (non enregistré)" :
                                                        L"In input field: %d bridges (unsaved)"), count);
            SetStatus(msg);
            return;
        }
    }
    SetStatus(T_STATUS_EMPTY.get());
}

// Custom button renderer
void DrawCustomButton(LPDRAWITEMSTRUCT dis) {
    HDC hdc = dis->hDC;
    RECT rc = dis->rcItem;
    bool isSelected = (dis->itemState & ODS_SELECTED) != 0;
    bool isHovered = (dis->hwndItem == g_hoveredBtn);

    FillRect(hdc, &rc, g_hBrushBg);

    COLORREF colBg;
    COLORREF colBorder;
    if (dis->CtlID == IDC_BTN_ADD) {
        if (isSelected)      { colBg = RGB(35, 78, 42);  colBorder = RGB(48, 100, 58); }
        else if (isHovered)  { colBg = RGB(55, 112, 65); colBorder = RGB(70, 130, 80); }
        else                 { colBg = RGB(45, 95, 55);  colBorder = RGB(48, 100, 58); }
    } else if (dis->CtlID == IDC_BTN_REPLACE) {
        if (isSelected)      { colBg = RGB(105, 35, 35); colBorder = RGB(135, 48, 48); }
        else if (isHovered)  { colBg = RGB(150, 55, 55); colBorder = RGB(170, 68, 68); }
        else                 { colBg = RGB(130, 45, 45); colBorder = RGB(135, 48, 48); }
    } else if (dis->CtlID == IDC_BTN_UPDATE) {
        if (isSelected)      { colBg = RGB(110, 65, 18); colBorder = RGB(140, 85, 24); }
        else if (isHovered)  { colBg = RGB(155, 96, 28); colBorder = RGB(175, 110, 32); }
        else                 { colBg = RGB(135, 82, 22); colBorder = RGB(140, 85, 24); }
    } else if (dis->CtlID == IDC_BTN_CONFIG) {
        if (isSelected)      { colBg = RGB(24, 62, 96);  colBorder = RGB(36, 82, 126); }
        else if (isHovered)  { colBg = RGB(42, 92, 140); colBorder = RGB(52, 110, 165); }
        else                 { colBg = RGB(32, 78, 120); colBorder = RGB(36, 82, 126); }
    } else { // IDC_BTN_CLEAR
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

        g_hFontTitle  = CreateFontW(-20, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontNormal = CreateFontW(-13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold   = CreateFontW(-13, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontMono   = CreateFontW(-13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, FIXED_PITCH | FF_MODERN, L"Consolas");
        g_hFontSmall  = CreateFontW(-11, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        // Multiline Edit Control (X=20, Y=132, W=664, H=298)
        g_hEdit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL,
            20, 132, 664, 298, hWnd, (HMENU)IDC_BRIDGES_EDIT, GetModuleHandle(NULL), NULL);
        SendMessageW(g_hEdit, WM_SETFONT, (WPARAM)g_hFontMono, TRUE);
        SetWindowSubclass(g_hEdit, EditSubclassProc, IDC_BRIDGES_EDIT, 0);

        // Buttons (Y=442, H=34)
        g_hBtnAdd = CreateWindowExW(0, L"BUTTON", T_BTN_ADD.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            20, 442, 150, 34, hWnd, (HMENU)IDC_BTN_ADD, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnAdd, ButtonSubclassProc, IDC_BTN_ADD, 0);

        g_hBtnReplace = CreateWindowExW(0, L"BUTTON", T_BTN_REPLACE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            180, 442, 150, 34, hWnd, (HMENU)IDC_BTN_REPLACE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnReplace, ButtonSubclassProc, IDC_BTN_REPLACE, 0);

        g_hBtnUpdate = CreateWindowExW(0, L"BUTTON", T_BTN_UPDATE.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            342, 442, 170, 34, hWnd, (HMENU)IDC_BTN_UPDATE, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnUpdate, ButtonSubclassProc, IDC_BTN_UPDATE, 0);

        g_hBtnConfig = CreateWindowExW(0, L"BUTTON", T_BTN_CONFIG.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            522, 442, 162, 34, hWnd, (HMENU)IDC_BTN_CONFIG, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnConfig, ButtonSubclassProc, IDC_BTN_CONFIG, 0);

        // Clear button (Y=488, H=30, Centered)
        g_hBtnClear = CreateWindowExW(0, L"BUTTON", T_BTN_CLEAR.get(),
            WS_CHILD | WS_VISIBLE | BS_OWNERDRAW,
            262, 488, 180, 30, hWnd, (HMENU)IDC_BTN_CLEAR, GetModuleHandle(NULL), NULL);
        SetWindowSubclass(g_hBtnClear, ButtonSubclassProc, IDC_BTN_CLEAR, 0);

        LoadExistingBridges();
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
        if (id == IDC_BRIDGES_EDIT && code == EN_CHANGE) {
            OnTextChanged();
        } else if (id == IDC_BTN_ADD) {
            AddBridges();
        } else if (id == IDC_BTN_REPLACE) {
            ReplaceBridges();
        } else if (id == IDC_BTN_UPDATE) {
            UpdateConfig();
        } else if (id == IDC_BTN_CONFIG) {
            ConfigureTor();
        } else if (id == IDC_BTN_CLEAR) {
            ClearInputText();
        }
        return 0;
    }

    case WM_CTLCOLORBTN:
        return (INT_PTR)g_hBrushBg;

    case WM_CTLCOLOREDIT: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, RGB(224, 224, 224));
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
        SetTextColor(hdc, g_colAccentGreen);
        SetBkMode(hdc, TRANSPARENT);
        RECT rcTitle = { 20, 14, 684, 44 };
        DrawTextW(hdc, T_HEADER.get(), -1, &rcTitle, DT_CENTER | DT_SINGLELINE);

        // Underline
        HPEN hPenGreen = CreatePen(PS_SOLID, 2, g_colAccentGreen);
        HGDIOBJ oldPen = SelectObject(hdc, hPenGreen);
        MoveToEx(hdc, 20, 48, NULL);
        LineTo(hdc, 684, 48);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenGreen);

        // 2. Info Panel (20, 60, 684, 98)
        HPEN hPenBorder = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        oldPen = SelectObject(hdc, hPenBorder);
        HGDIOBJ oldBr = SelectObject(hdc, g_hBrushPanel);
        RoundRect(hdc, 20, 60, 684, 98, 6, 6);
        SelectObject(hdc, oldBr);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenBorder);

        // Info Panel Texts
        SelectObject(hdc, g_hFontNormal);
        SetBkMode(hdc, TRANSPARENT);
        SetTextColor(hdc, RGB(160, 160, 160));
        wchar_t countBuf[128];
        swprintf_s(countBuf, 128, L"%s%d", T_COUNT_PREFIX.get(), g_bridgesCount);
        TextOutW(hdc, 34, 72, countBuf, (int)wcslen(countBuf));

        SetTextColor(hdc, RGB(136, 136, 136));
        TextOutW(hdc, 560, 72, T_FILE_STATUS.get(), (int)wcslen(T_FILE_STATUS.get()));

        // 3. Editor Label (20, 110)
        SelectObject(hdc, g_hFontBold);
        SetTextColor(hdc, g_colText);
        TextOutW(hdc, 20, 110, T_EDITOR_LABEL.get(), (int)wcslen(T_EDITOR_LABEL.get()));

        // 4. Status Bar (0, 538, 704, 566)
        RECT rcStatus = { 0, 538, 704, 566 };
        FillRect(hdc, &rcStatus, g_hBrushPanel);

        HPEN hPenStatus = CreatePen(PS_SOLID, 1, RGB(51, 51, 51));
        oldPen = SelectObject(hdc, hPenStatus);
        MoveToEx(hdc, 0, 538, NULL);
        LineTo(hdc, 704, 538);
        SelectObject(hdc, oldPen);
        DeleteObject(hPenStatus);

        SelectObject(hdc, g_hFontSmall);
        SetTextColor(hdc, RGB(150, 150, 150));
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 16, 545, g_statusMsg.c_str(), (int)g_statusMsg.size());

        EndPaint(hWnd, &ps);
        return 0;
    }

    case WM_DESTROY:
        if (g_hFontTitle)  DeleteObject(g_hFontTitle);
        if (g_hFontNormal) DeleteObject(g_hFontNormal);
        if (g_hFontBold)   DeleteObject(g_hFontBold);
        if (g_hFontMono)   DeleteObject(g_hFontMono);
        if (g_hFontSmall)  DeleteObject(g_hFontSmall);
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
    LoadLanguagePreference();

    g_statusMsg = T_STATUS_READY.get();

    g_hBrushBg = CreateSolidBrush(g_colBg);
    g_hBrushPanel = CreateSolidBrush(g_colPanel);
    g_hBrushEditBg = CreateSolidBrush(g_colEditBg);

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetEditBridgesWnd";

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

    RECT rcWin = { 0, 0, 704, 566 };
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
    DeleteObject(g_hBrushPanel);
    DeleteObject(g_hBrushEditBg);
    return (int)msg.wParam;
}
