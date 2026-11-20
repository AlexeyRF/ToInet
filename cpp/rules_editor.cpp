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
#include <uxtheme.h>
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
#pragma comment(lib, "shell32.lib")

#pragma comment(linker,"\"/manifestdependency:type='win32' name='Microsoft.Windows.Common-Controls' version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

// Control IDs
#define IDC_LIST_RULES        101
#define IDC_BTN_ADD_RULE      102
#define IDC_BTN_ADD_PROXY     103
#define IDC_BTN_EDIT_RULE     104
#define IDC_BTN_DEL_RULE      105
#define IDC_BTN_UP            106
#define IDC_BTN_DOWN          107
#define IDC_BTN_CANCEL        108
#define IDC_BTN_SAVE          109

// SingleRuleDialog Controls
#define IDC_DLG_NAME          201
#define IDC_DLG_APPS          202
#define IDC_DLG_TARGETS       203
#define IDC_DLG_PORTS         204
#define IDC_DLG_ACTION        205
#define IDC_DLG_ENABLED       206
#define IDC_DLG_OK            207
#define IDC_DLG_CANCEL        208

// AddProxyDialog Controls
#define IDC_PRX_LABEL         301
#define IDC_PRX_PROTO         302
#define IDC_PRX_HOST          303
#define IDC_PRX_PORT          304
#define IDC_PRX_ADD           305
#define IDC_PRX_CANCEL        306

enum AppLang { LANG_RU, LANG_EN, LANG_FR };
static AppLang g_lang = LANG_RU;

struct LStr {
    const wchar_t* ru;
    const wchar_t* en;
    const wchar_t* fr;
    const wchar_t* get() const {
        if (g_lang == LANG_FR && fr) return fr;
        if (g_lang == LANG_EN && en) return en;
        return ru;
    }
};

static const LStr T_WIN_TITLE           = { L"Правила маршрутизации (Toinet.ppx)", L"Routing Rules (Toinet.ppx)", L"Règles de routage (Toinet.ppx)" };
static const LStr T_HEADER_NOTE         = {
    L"Правила маршрутизации трафика (приоритет сверху вниз). Синхронизируются с Proxifier и Sing-box TUN.",
    L"Traffic routing rules (processed top-down). Synchronized with Proxifier and Sing-box TUN.",
    L"Règles de routage du trafic (traitées de haut en bas). Synchronisées avec Proxifier et Sing-box TUN."
};

static const LStr T_COL_NAME            = { L"Имя правила", L"Rule Name", L"Nom de la règle" };
static const LStr T_COL_APPS            = { L"Приложения", L"Applications", L"Applications" };
static const LStr T_COL_TARGETS         = { L"Целевые хосты", L"Target Hosts", L"Hôtes cibles" };
static const LStr T_COL_PORTS           = { L"Порты", L"Ports", L"Ports" };
static const LStr T_COL_ACTION          = { L"Действие", L"Action", L"Action" };

static const LStr T_BTN_ADD_RULE        = { L"Добавить правило...", L"Add Rule...", L"Ajouter règle..." };
static const LStr T_BTN_ADD_PROXY       = { L"Добавить прокси...", L"Add Proxy...", L"Ajouter proxy..." };
static const LStr T_BTN_EDIT            = { L"Редактировать...", L"Edit...", L"Modifier..." };
static const LStr T_BTN_DELETE          = { L"Удалить", L"Delete", L"Supprimer" };
static const LStr T_BTN_UP              = { L"▲ Вверх", L"▲ Up", L"▲ Haut" };
static const LStr T_BTN_DOWN            = { L"▼ Вниз", L"▼ Down", L"▼ Bas" };
static const LStr T_BTN_CANCEL          = { L"Отмена", L"Cancel", L"Annuler" };
static const LStr T_BTN_SAVE            = { L"Сохранить", L"Save", L"Enregistrer" };

static const LStr T_MSG_TITLE_OK        = { L"Успех", L"Success", L"Succès" };
static const LStr T_MSG_TITLE_WARN      = { L"Внимание", L"Warning", L"Attention" };
static const LStr T_MSG_TITLE_ERR       = { L"Ошибка", L"Error", L"Erreur" };
static const LStr T_MSG_TITLE_CONF      = { L"Подтверждение", L"Confirmation", L"Confirmation" };

static const LStr T_MSG_SAVED           = { L"Правила успешно сохранены в Toinet.ppx!", L"Rules successfully saved to Toinet.ppx!", L"Règles enregistrées avec succès dans Toinet.ppx !" };
static const LStr T_WARN_DEFAULT_DEL    = { L"Правило 'Default' нельзя удалить.", L"Cannot delete 'Default' rule.", L"Impossible de supprimer la règle 'Default'." };
static const LStr T_WARN_DEL_PROMPT     = { L"Удалить выбранное правило?", L"Delete selected rule?", L"Supprimer la règle sélectionnée ?" };

// Single Rule Dialog translations
static const LStr T_DLG_RULE_TITLE_NEW  = { L"Добавить правило маршрутизации", L"Add Routing Rule", L"Ajouter une règle de routage" };
static const LStr T_DLG_RULE_TITLE_EDIT = { L"Редактирование правила", L"Edit Routing Rule", L"Modifier la règle de routage" };
static const LStr T_DLG_LBL_NAME        = { L"Название правила:", L"Rule Name:", L"Nom de la règle :" };
static const LStr T_DLG_LBL_APPS        = { L"Приложения (через точку с запятой или 'Any'):", L"Applications (semicolon separated or 'Any'):", L"Applications (séparées par ';' ou 'Any') :" };
static const LStr T_DLG_LBL_TARGETS     = { L"Целевые хосты (через точку с запятой или 'Any'):", L"Target Hosts (semicolon separated or 'Any'):", L"Hôtes cibles (séparés par ';' ou 'Any') :" };
static const LStr T_DLG_LBL_PORTS       = { L"Порты (например, 80; 443 или 'Any'):", L"Ports (e.g. 80; 443 or 'Any'):", L"Ports (ex. 80; 443 ou 'Any') :" };
static const LStr T_DLG_LBL_ACTION      = { L"Действие маршрутизации:", L"Routing Action:", L"Action de routage :" };
static const LStr T_DLG_CHK_ENABLED     = { L"Правило активно (включено)", L"Rule Enabled", L"Règle activée" };
static const LStr T_DLG_BTN_OK          = { L"Сохранить", L"Save", L"Enregistrer" };
static const LStr T_DLG_BTN_CANCEL      = { L"Отмена", L"Cancel", L"Annuler" };
static const LStr T_DLG_ERR_NAME        = { L"Укажите название правила.", L"Please enter rule name.", L"Veuillez entrer le nom de la règle." };

static const LStr T_ACT_DIRECT          = { L"Direct (Напрямую, без прокси)", L"Direct (No proxy)", L"Direct (Sans proxy)" };
static const LStr T_ACT_BLOCK           = { L"Block (Блокировать трафик)", L"Block (Drop traffic)", L"Bloquer (Rejeter le trafic)" };

// Add Proxy Dialog translations
static const LStr T_PRX_TITLE           = { L"Добавить прокси-сервер", L"Add Proxy Server", L"Ajouter un serveur proxy" };
static const LStr T_PRX_LBL_NAME        = { L"Название / Метка:", L"Label / Name:", L"Étiquette / Nom :" };
static const LStr T_PRX_LBL_PROTO       = { L"Протокол:", L"Protocol:", L"Protocole :" };
static const LStr T_PRX_LBL_HOST        = { L"Адрес хоста (IP или домен):", L"Host Address (IP or domain):", L"Adresse d'hôte (IP ou domaine) :" };
static const LStr T_PRX_LBL_PORT        = { L"Порт:", L"Port:", L"Port :" };
static const LStr T_PRX_BTN_ADD         = { L"Добавить", L"Add", L"Ajouter" };
static const LStr T_PRX_BTN_CANCEL      = { L"Отмена", L"Cancel", L"Annuler" };
static const LStr T_PRX_ERR_EMPTY       = { L"Укажите название и адрес хоста прокси!", L"Please provide proxy label and host address!", L"Veuillez indiquer le nom et l'hôte du proxy !" };
static const LStr T_PRX_SUCCESS_TITLE   = { L"Прокси добавлен", L"Proxy Added", L"Proxy ajouté" };

struct ProxyItem {
    std::wstring id;
    std::wstring type;
    std::wstring label;
    std::wstring address;
    std::wstring port;
    std::wstring options;
};

struct RuleItem {
    std::wstring name;
    bool enabled{ true };
    std::wstring actionKey;   // "Direct", "Block", "Proxy:100"
    std::wstring actionLabel;
    std::wstring apps;
    std::wstring targets;
    std::wstring ports;
};

static HWND g_hMainWnd = NULL;
static HWND g_hListView = NULL;
static HWND g_hBtnAddRule = NULL;
static HWND g_hBtnAddProxy = NULL;
static HWND g_hBtnEdit = NULL;
static HWND g_hBtnDelete = NULL;
static HWND g_hBtnUp = NULL;
static HWND g_hBtnDown = NULL;
static HWND g_hBtnCancel = NULL;
static HWND g_hBtnSave = NULL;

static HFONT g_hFontNormal = NULL;
static HFONT g_hFontBold = NULL;
static HFONT g_hFontSmall = NULL;

static HBRUSH g_hBrushBg = NULL;      // #181818
static HBRUSH g_hBrushEditBg = NULL;  // #242424

static COLORREF g_colBg = RGB(24, 24, 24);
static COLORREF g_colEditBg = RGB(36, 36, 36);
static COLORREF g_colText = RGB(220, 220, 220);

static std::wstring g_rootDir;
static std::wstring g_ppxPath;
static std::wstring g_ppxOriginalPrefix;

static std::vector<ProxyItem> g_proxies;
static std::vector<RuleItem> g_rules;
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

static std::wstring TrimW(const std::wstring& s) {
    size_t start = s.find_first_not_of(L" \t\r\n");
    if (start == std::wstring::npos) return L"";
    size_t end = s.find_last_not_of(L" \t\r\n");
    return s.substr(start, end - start + 1);
}

static std::wstring ExtractTagContent(const std::wstring& xml, const std::wstring& tag, size_t startPos = 0, size_t* outEndPos = nullptr) {
    std::wstring openTag = L"<" + tag;
    size_t s = xml.find(openTag, startPos);
    if (s == std::wstring::npos) return L"";
    size_t closeBracket = xml.find(L">", s);
    if (closeBracket == std::wstring::npos) return L"";
    if (xml[closeBracket - 1] == L'/') {
        if (outEndPos) *outEndPos = closeBracket + 1;
        return L"";
    }
    std::wstring closeTag = L"</" + tag + L">";
    size_t e = xml.find(closeTag, closeBracket + 1);
    if (e == std::wstring::npos) return L"";
    if (outEndPos) *outEndPos = e + closeTag.length();
    return xml.substr(closeBracket + 1, e - closeBracket - 1);
}

static std::wstring ExtractAttribute(const std::wstring& tagStr, const std::wstring& attrName) {
    std::wstring search = attrName + L"=\"";
    size_t p = tagStr.find(search);
    if (p == std::wstring::npos) return L"";
    p += search.length();
    size_t endQ = tagStr.find(L"\"", p);
    if (endQ == std::wstring::npos) return L"";
    return tagStr.substr(p, endQ - p);
}

std::wstring GetActionLabel(const std::wstring& actionKey) {
    if (actionKey == L"Direct") return (g_lang == LANG_RU) ? L"Direct (Прямое)" : L"Direct";
    if (actionKey == L"Block") return (g_lang == LANG_RU) ? L"Block (Блокировка)" : L"Block";
    if (actionKey.rfind(L"Proxy:", 0) == 0) {
        std::wstring pid = actionKey.substr(6);
        for (const auto& p : g_proxies) {
            if (p.id == pid) {
                return L"Proxy " + p.type + L" (" + p.label + L")";
            }
        }
        return L"Proxy (" + pid + L")";
    }
    return actionKey;
}

void ApplyFontToAllChildren(HWND hWnd, HFONT hFont) {
    EnumChildWindows(hWnd, [](HWND hChild, LPARAM lp) -> BOOL {
        SendMessageW(hChild, WM_SETFONT, (WPARAM)lp, TRUE);
        return TRUE;
    }, (LPARAM)hFont);
}

void InitPathsAndLang() {
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::wstring dir = exePath;
    size_t lastSlash = dir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) dir = dir.substr(0, lastSlash);

    std::wstring rootCand1 = dir;
    std::wstring rootCand2 = dir + L"\\..";
    std::wstring rootCand3 = dir + L"\\..\\..";

    if (GetFileAttributesW((rootCand1 + L"\\Toinet.ppx").c_str()) != INVALID_FILE_ATTRIBUTES) {
        g_rootDir = rootCand1;
    } else if (GetFileAttributesW((rootCand2 + L"\\Toinet.ppx").c_str()) != INVALID_FILE_ATTRIBUTES) {
        g_rootDir = rootCand2;
    } else {
        g_rootDir = rootCand3;
    }

    wchar_t fullRoot[MAX_PATH];
    if (GetFullPathNameW(g_rootDir.c_str(), MAX_PATH, fullRoot, NULL)) {
        g_rootDir = fullRoot;
    }
    g_ppxPath = g_rootDir + L"\\Toinet.ppx";

    // Read language setting from config.json
    std::wstring cfgPath = g_rootDir + L"\\data\\config.json";
    std::ifstream cfg(cfgPath, std::ios::binary);
    std::string lang = "ru";
    if (cfg.is_open()) {
        std::stringstream ss;
        ss << cfg.rdbuf();
        std::string content = ss.str();
        cfg.close();

        std::string search = "\"language\"";
        size_t pos = content.find(search);
        if (pos != std::string::npos) {
            pos = content.find(':', pos);
            if (pos != std::string::npos) {
                size_t q1 = content.find('\"', pos);
                if (q1 != std::string::npos) {
                    size_t q2 = content.find('\"', q1 + 1);
                    if (q2 != std::string::npos) {
                        lang = content.substr(q1 + 1, q2 - q1 - 1);
                    }
                }
            }
        }
    }
    if (lang == "fr") g_lang = LANG_FR;
    else if (lang == "en") g_lang = LANG_EN;
    else g_lang = LANG_RU;
}

bool LoadPPX() {
    g_proxies.clear();
    g_rules.clear();

    std::ifstream file(g_ppxPath, std::ios::binary);
    if (!file.is_open()) return false;

    std::stringstream ss;
    ss << file.rdbuf();
    file.close();

    std::wstring xml = Utf8ToUtf16(ss.str());

    // Save prefix up to <ProxyList>
    size_t pProxyList = xml.find(L"<ProxyList");
    if (pProxyList != std::wstring::npos) {
        g_ppxOriginalPrefix = xml.substr(0, pProxyList);
    } else {
        g_ppxOriginalPrefix = L"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<ProxifierProfile version=\"102\" platform=\"Windows\" product_id=\"0\" product_minver=\"400\">\n\t<Options>\n\t</Options>\n\t";
    }

    // 1. Parse Proxies
    size_t pProxyListEnd = xml.find(L"</ProxyList>", pProxyList);
    if (pProxyList != std::wstring::npos && pProxyListEnd != std::wstring::npos) {
        size_t cur = pProxyList + 10;
        while (cur < pProxyListEnd) {
            size_t proxyStart = xml.find(L"<Proxy", cur);
            if (proxyStart == std::wstring::npos || proxyStart >= pProxyListEnd) break;
            size_t proxyEnd = xml.find(L"</Proxy>", proxyStart);
            if (proxyEnd == std::wstring::npos || proxyEnd > pProxyListEnd) break;

            std::wstring block = xml.substr(proxyStart, (proxyEnd + 8) - proxyStart);
            size_t tagClose = block.find(L">");
            std::wstring openTag = block.substr(0, tagClose + 1);

            ProxyItem p;
            p.id = ExtractAttribute(openTag, L"id");
            p.type = ExtractAttribute(openTag, L"type");
            if (p.type.empty()) p.type = L"SOCKS5";
            p.options = TrimW(ExtractTagContent(block, L"Options"));
            if (p.options.empty()) p.options = L"48";
            p.port = TrimW(ExtractTagContent(block, L"Port"));
            if (p.port.empty()) p.port = L"1080";
            p.address = TrimW(ExtractTagContent(block, L"Address"));
            if (p.address.empty()) p.address = L"127.0.0.1";
            p.label = TrimW(ExtractTagContent(block, L"Label"));
            if (p.label.empty()) p.label = L"Proxy_" + p.id;

            g_proxies.push_back(p);
            cur = proxyEnd + 8;
        }
    }

    // 2. Parse Rules
    size_t pRuleList = xml.find(L"<RuleList", pProxyListEnd);
    size_t pRuleListEnd = xml.find(L"</RuleList>", pRuleList);
    if (pRuleList != std::wstring::npos && pRuleListEnd != std::wstring::npos) {
        size_t cur = pRuleList + 9;
        while (cur < pRuleListEnd) {
            size_t ruleStart = xml.find(L"<Rule", cur);
            if (ruleStart == std::wstring::npos || ruleStart >= pRuleListEnd) break;
            size_t ruleEnd = xml.find(L"</Rule>", ruleStart);
            if (ruleEnd == std::wstring::npos || ruleEnd > pRuleListEnd) break;

            std::wstring block = xml.substr(ruleStart, (ruleEnd + 7) - ruleStart);
            size_t tagClose = block.find(L">");
            std::wstring openTag = block.substr(0, tagClose + 1);

            RuleItem r;
            std::wstring enStr = ExtractAttribute(openTag, L"enabled");
            r.enabled = (_wcsicmp(enStr.c_str(), L"false") != 0);

            r.name = TrimW(ExtractTagContent(block, L"Name"));
            r.apps = TrimW(ExtractTagContent(block, L"Applications"));
            if (r.apps.empty()) r.apps = L"Any";
            r.targets = TrimW(ExtractTagContent(block, L"Targets"));
            if (r.targets.empty()) r.targets = L"Any";
            r.ports = TrimW(ExtractTagContent(block, L"Ports"));
            if (r.ports.empty()) r.ports = L"Any";

            size_t pAct = block.find(L"<Action");
            if (pAct != std::wstring::npos) {
                size_t actClose = block.find(L">", pAct);
                std::wstring actTag = block.substr(pAct, actClose - pAct + 1);
                std::wstring actType = ExtractAttribute(actTag, L"type");
                if (_wcsicmp(actType.c_str(), L"Proxy") == 0) {
                    std::wstring pid = TrimW(ExtractTagContent(block, L"Action"));
                    r.actionKey = L"Proxy:" + pid;
                } else if (_wcsicmp(actType.c_str(), L"Block") == 0) {
                    r.actionKey = L"Block";
                } else {
                    r.actionKey = L"Direct";
                }
            } else {
                r.actionKey = L"Direct";
            }
            r.actionLabel = GetActionLabel(r.actionKey);
            g_rules.push_back(r);
            cur = ruleEnd + 7;
        }
    }
    return true;
}

bool SavePPX() {
    std::wstring outXml = g_ppxOriginalPrefix;
    if (outXml.empty()) {
        outXml = L"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<ProxifierProfile version=\"102\" platform=\"Windows\" product_id=\"0\" product_minver=\"400\">\n\t<Options>\n\t</Options>\n\t";
    }

    outXml += L"<ProxyList>\n";
    for (const auto& p : g_proxies) {
        outXml += L"\t\t<Proxy id=\"" + p.id + L"\" type=\"" + p.type + L"\">\n";
        outXml += L"\t\t\t<Options>" + p.options + L"</Options>\n";
        outXml += L"\t\t\t<Port>" + p.port + L"</Port>\n";
        outXml += L"\t\t\t<Address>" + p.address + L"</Address>\n";
        outXml += L"\t\t\t<Label>" + p.label + L"</Label>\n";
        outXml += L"\t\t</Proxy>\n";
    }
    outXml += L"\t</ProxyList>\n";
    outXml += L"\t<ChainList />\n";
    outXml += L"\t<RuleList>\n";
    for (const auto& r : g_rules) {
        outXml += L"\t\t<Rule enabled=\"" + std::wstring(r.enabled ? L"true" : L"false") + L"\">\n";
        if (r.actionKey.rfind(L"Proxy:", 0) == 0) {
            std::wstring pid = r.actionKey.substr(6);
            outXml += L"\t\t\t<Action type=\"Proxy\">" + pid + L"</Action>\n";
        } else if (r.actionKey == L"Block") {
            outXml += L"\t\t\t<Action type=\"Block\" />\n";
        } else {
            outXml += L"\t\t\t<Action type=\"Direct\" />\n";
        }
        if (!r.targets.empty() && r.targets != L"Any") {
            outXml += L"\t\t\t<Targets>" + r.targets + L"</Targets>\n";
        }
        if (!r.apps.empty() && r.apps != L"Any") {
            outXml += L"\t\t\t<Applications>" + r.apps + L"</Applications>\n";
        }
        if (!r.ports.empty() && r.ports != L"Any") {
            outXml += L"\t\t\t<Ports>" + r.ports + L"</Ports>\n";
        }
        outXml += L"\t\t\t<Name>" + (r.name.empty() ? L"Rule" : r.name) + L"</Name>\n";
        outXml += L"\t\t</Rule>\n";
    }
    outXml += L"\t</RuleList>\n";
    outXml += L"</ProxifierProfile>\n";

    std::ofstream file(g_ppxPath, std::ios::binary);
    if (!file.is_open()) return false;
    std::string utf8 = Utf16ToUtf8(outXml);
    file.write(utf8.c_str(), utf8.size());
    file.close();
    return true;
}

void PopulateListView() {
    ListView_DeleteAllItems(g_hListView);

    for (size_t i = 0; i < g_rules.size(); ++i) {
        const auto& r = g_rules[i];
        LVITEMW lvi = {};
        lvi.mask = LVIF_TEXT;
        lvi.iItem = (int)i;
        lvi.iSubItem = 0;
        lvi.pszText = const_cast<wchar_t*>(r.name.c_str());
        ListView_InsertItem(g_hListView, &lvi);

        std::wstring appsDisp = r.apps;
        std::replace(appsDisp.begin(), appsDisp.end(), L'\n', L' ');
        std::wstring targetsDisp = r.targets;
        std::replace(targetsDisp.begin(), targetsDisp.end(), L'\n', L' ');
        std::wstring portsDisp = r.ports;
        std::replace(portsDisp.begin(), portsDisp.end(), L'\n', L' ');

        ListView_SetItemText(g_hListView, (int)i, 1, const_cast<wchar_t*>(appsDisp.c_str()));
        ListView_SetItemText(g_hListView, (int)i, 2, const_cast<wchar_t*>(targetsDisp.c_str()));
        ListView_SetItemText(g_hListView, (int)i, 3, const_cast<wchar_t*>(portsDisp.c_str()));
        ListView_SetItemText(g_hListView, (int)i, 4, const_cast<wchar_t*>(r.actionLabel.c_str()));

        ListView_SetCheckState(g_hListView, (int)i, r.enabled);
    }
}

// Dialog Button Drawing Helper
static void DrawCustomDialogButton(LPDRAWITEMSTRUCT dis, HWND hHovered) {
    HDC hdc = dis->hDC;
    RECT rc = dis->rcItem;
    bool isSelected = (dis->itemState & ODS_SELECTED) != 0;
    bool isHovered = (dis->hwndItem == hHovered);

    FillRect(hdc, &rc, g_hBrushBg);

    COLORREF colBg;
    COLORREF colBorder;

    if (dis->CtlID == IDC_DLG_OK || dis->CtlID == IDC_PRX_ADD) {
        // Calm steel blue
        if (isSelected)      { colBg = RGB(24, 62, 96);  colBorder = RGB(36, 82, 126); }
        else if (isHovered)  { colBg = RGB(42, 92, 140); colBorder = RGB(52, 110, 165); }
        else                 { colBg = RGB(32, 78, 120); colBorder = RGB(36, 82, 126); }
    } else {
        // Calm dark charcoal
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

    wchar_t text[128] = { 0 };
    GetWindowTextW(dis->hwndItem, text, 128);
    SetBkMode(hdc, TRANSPARENT);
    SetTextColor(hdc, RGB(220, 220, 220));
    SelectObject(hdc, g_hFontNormal);
    DrawTextW(hdc, text, -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

// Single Rule Dialog Procedure
static RuleItem g_dlgRule;
static bool g_dlgRuleAccepted = false;
static HWND g_hDlgName = NULL, g_hDlgApps = NULL, g_hDlgTargets = NULL, g_hDlgPorts = NULL;
static HWND g_hDlgAction = NULL, g_hDlgEnabled = NULL, g_hDlgBtnOk = NULL, g_hDlgBtnCancel = NULL;
static HWND g_hDlgHoveredBtn = NULL;

LRESULT CALLBACK SingleRuleDlgProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        // 1. Name
        CreateWindowExW(0, L"STATIC", T_DLG_LBL_NAME.get(), WS_CHILD | WS_VISIBLE, 20, 16, 470, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hDlgName = CreateWindowExW(0, L"EDIT", g_dlgRule.name.c_str(), WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL | WS_TABSTOP, 20, 36, 470, 26, hWnd, (HMENU)IDC_DLG_NAME, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hDlgName, L"DarkMode_CFD", NULL);

        // 2. Apps
        CreateWindowExW(0, L"STATIC", T_DLG_LBL_APPS.get(), WS_CHILD | WS_VISIBLE, 20, 68, 470, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hDlgApps = CreateWindowExW(0, L"EDIT", g_dlgRule.apps.c_str(), WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL | WS_TABSTOP, 20, 88, 470, 26, hWnd, (HMENU)IDC_DLG_APPS, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hDlgApps, L"DarkMode_CFD", NULL);

        // 3. Targets
        CreateWindowExW(0, L"STATIC", T_DLG_LBL_TARGETS.get(), WS_CHILD | WS_VISIBLE, 20, 120, 470, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hDlgTargets = CreateWindowExW(0, L"EDIT", g_dlgRule.targets.c_str(), WS_CHILD | WS_VISIBLE | WS_BORDER | ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, 20, 140, 470, 85, hWnd, (HMENU)IDC_DLG_TARGETS, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hDlgTargets, L"DarkMode_CFD", NULL);

        // 4. Ports
        CreateWindowExW(0, L"STATIC", T_DLG_LBL_PORTS.get(), WS_CHILD | WS_VISIBLE, 20, 232, 470, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hDlgPorts = CreateWindowExW(0, L"EDIT", g_dlgRule.ports.c_str(), WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL | WS_TABSTOP, 20, 252, 470, 26, hWnd, (HMENU)IDC_DLG_PORTS, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hDlgPorts, L"DarkMode_CFD", NULL);

        // 5. Action
        CreateWindowExW(0, L"STATIC", T_DLG_LBL_ACTION.get(), WS_CHILD | WS_VISIBLE, 20, 284, 470, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hDlgAction = CreateWindowExW(0, L"COMBOBOX", L"", WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, 20, 304, 470, 180, hWnd, (HMENU)IDC_DLG_ACTION, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hDlgAction, L"DarkMode_CFD", NULL);

        SendMessageW(g_hDlgAction, CB_ADDSTRING, 0, (LPARAM)T_ACT_DIRECT.get());
        SendMessageW(g_hDlgAction, CB_ADDSTRING, 0, (LPARAM)T_ACT_BLOCK.get());
        for (const auto& p : g_proxies) {
            std::wstring lbl = L"Proxy " + p.type + L" (" + p.label + L")";
            SendMessageW(g_hDlgAction, CB_ADDSTRING, 0, (LPARAM)lbl.c_str());
        }

        // Set action selection
        int sel = 0;
        if (g_dlgRule.actionKey == L"Block") sel = 1;
        else if (g_dlgRule.actionKey.rfind(L"Proxy:", 0) == 0) {
            std::wstring pid = g_dlgRule.actionKey.substr(6);
            for (size_t i = 0; i < g_proxies.size(); ++i) {
                if (g_proxies[i].id == pid) {
                    sel = (int)(2 + i);
                    break;
                }
            }
        }
        SendMessageW(g_hDlgAction, CB_SETCURSEL, sel, 0);

        // 6. Checkbox
        g_hDlgEnabled = CreateWindowExW(0, L"BUTTON", T_DLG_CHK_ENABLED.get(), WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX | WS_TABSTOP, 20, 340, 470, 24, hWnd, (HMENU)IDC_DLG_ENABLED, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hDlgEnabled, L"DarkMode_Explorer", NULL);
        SendMessageW(g_hDlgEnabled, BM_SETCHECK, g_dlgRule.enabled ? BST_CHECKED : BST_UNCHECKED, 0);

        // 7. Action Buttons (Owner-draw calm style)
        g_hDlgBtnOk = CreateWindowExW(0, L"BUTTON", T_DLG_BTN_OK.get(), WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_TABSTOP, 275, 385, 105, 32, hWnd, (HMENU)IDC_DLG_OK, GetModuleHandle(NULL), NULL);
        g_hDlgBtnCancel = CreateWindowExW(0, L"BUTTON", T_DLG_BTN_CANCEL.get(), WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_TABSTOP, 390, 385, 100, 32, hWnd, (HMENU)IDC_DLG_CANCEL, GetModuleHandle(NULL), NULL);

        ApplyFontToAllChildren(hWnd, g_hFontNormal);
        return 0;
    }

    case WM_ERASEBKGND: {
        HDC hdc = (HDC)wParam;
        RECT rc;
        GetClientRect(hWnd, &rc);
        FillRect(hdc, &rc, g_hBrushBg);
        return 1;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        return (INT_PTR)g_hBrushBg;
    }

    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORLISTBOX: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, RGB(220, 220, 220));
        SetBkColor(hdc, g_colEditBg);
        return (INT_PTR)g_hBrushEditBg;
    }

    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT pdis = (LPDRAWITEMSTRUCT)lParam;
        if (pdis->CtlType == ODT_BUTTON) {
            DrawCustomDialogButton(pdis, g_hDlgHoveredBtn);
            return TRUE;
        }
        break;
    }

    case WM_SETCURSOR: {
        HWND hTarget = (HWND)wParam;
        if (hTarget == g_hDlgBtnOk || hTarget == g_hDlgBtnCancel) {
            if (g_hDlgHoveredBtn != hTarget) {
                HWND old = g_hDlgHoveredBtn;
                g_hDlgHoveredBtn = hTarget;
                if (old) InvalidateRect(old, NULL, FALSE);
                InvalidateRect(g_hDlgHoveredBtn, NULL, FALSE);

                TRACKMOUSEEVENT tme = { sizeof(TRACKMOUSEEVENT), TME_LEAVE, hWnd, 0 };
                TrackMouseEvent(&tme);
            }
        }
        break;
    }

    case WM_MOUSELEAVE: {
        if (g_hDlgHoveredBtn) {
            HWND old = g_hDlgHoveredBtn;
            g_hDlgHoveredBtn = NULL;
            InvalidateRect(old, NULL, FALSE);
        }
        break;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == IDC_DLG_OK) {
            wchar_t bufName[256] = {}, bufApps[512] = {}, bufPorts[256] = {};
            GetWindowTextW(g_hDlgName, bufName, 256);
            std::wstring name = TrimW(bufName);
            if (name.empty()) {
                MessageBoxW(hWnd, T_DLG_ERR_NAME.get(), T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONWARNING);
                return 0;
            }
            GetWindowTextW(g_hDlgApps, bufApps, 512);
            GetWindowTextW(g_hDlgPorts, bufPorts, 256);

            int tLen = GetWindowTextLengthW(g_hDlgTargets);
            std::vector<wchar_t> tBuf(tLen + 1);
            GetWindowTextW(g_hDlgTargets, tBuf.data(), tLen + 1);

            g_dlgRule.name = name;
            g_dlgRule.apps = TrimW(bufApps);
            if (g_dlgRule.apps.empty()) g_dlgRule.apps = L"Any";
            g_dlgRule.targets = TrimW(tBuf.data());
            if (g_dlgRule.targets.empty()) g_dlgRule.targets = L"Any";
            g_dlgRule.ports = TrimW(bufPorts);
            if (g_dlgRule.ports.empty()) g_dlgRule.ports = L"Any";

            int actIdx = (int)SendMessageW(g_hDlgAction, CB_GETCURSEL, 0, 0);
            if (actIdx == 0) g_dlgRule.actionKey = L"Direct";
            else if (actIdx == 1) g_dlgRule.actionKey = L"Block";
            else if (actIdx >= 2 && (size_t)(actIdx - 2) < g_proxies.size()) {
                g_dlgRule.actionKey = L"Proxy:" + g_proxies[actIdx - 2].id;
            }
            g_dlgRule.actionLabel = GetActionLabel(g_dlgRule.actionKey);
            g_dlgRule.enabled = (SendMessageW(g_hDlgEnabled, BM_GETCHECK, 0, 0) == BST_CHECKED);

            g_dlgRuleAccepted = true;
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        } else if (id == IDC_DLG_CANCEL) {
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        }
        return 0;
    }
    }
    return DefWindowProcW(hWnd, uMsg, wParam, lParam);
}

bool ShowSingleRuleDialog(HWND hParent, RuleItem& rule, bool isNew) {
    g_dlgRule = rule;
    g_dlgRuleAccepted = false;
    g_hDlgHoveredBtn = NULL;

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = SingleRuleDlgProc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetSingleRuleDlgClass";
    RegisterClassExW(&wc);

    int w = 525;
    int h = 475;
    RECT rcParent;
    GetWindowRect(hParent, &rcParent);
    int x = rcParent.left + (rcParent.right - rcParent.left - w) / 2;
    int y = rcParent.top + (rcParent.bottom - rcParent.top - h) / 2;

    HWND hDlg = CreateWindowExW(
        WS_EX_DLGMODALFRAME,
        L"ToInetSingleRuleDlgClass",
        isNew ? T_DLG_RULE_TITLE_NEW.get() : T_DLG_RULE_TITLE_EDIT.get(),
        WS_POPUP | WS_CAPTION | WS_SYSMENU,
        x, y, w, h,
        hParent, NULL, GetModuleHandle(NULL), NULL
    );

    BOOL darkMode = TRUE;
    DwmSetWindowAttribute(hDlg, 20, &darkMode, sizeof(darkMode));
    DwmSetWindowAttribute(hDlg, 19, &darkMode, sizeof(darkMode));
    COLORREF captionColor = RGB(24, 24, 24);
    DwmSetWindowAttribute(hDlg, 35, &captionColor, sizeof(captionColor));

    ShowWindow(hDlg, SW_SHOW);
    UpdateWindow(hDlg);
    EnableWindow(hParent, FALSE);

    MSG msg;
    while (IsWindow(hDlg) && GetMessageW(&msg, NULL, 0, 0)) {
        if (msg.message == WM_KEYDOWN && msg.wParam == VK_ESCAPE) {
            DestroyWindow(hDlg);
            break;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    EnableWindow(hParent, TRUE);
    SetForegroundWindow(hParent);
    UnregisterClassW(L"ToInetSingleRuleDlgClass", GetModuleHandle(NULL));

    if (g_dlgRuleAccepted) {
        rule = g_dlgRule;
        return true;
    }
    return false;
}

// Add Proxy Dialog Procedure
static ProxyItem g_dlgProxy;
static bool g_dlgProxyAccepted = false;
static HWND g_hPrxLabel = NULL, g_hPrxProto = NULL, g_hPrxHost = NULL, g_hPrxPort = NULL;
static HWND g_hPrxBtnAdd = NULL, g_hPrxBtnCancel = NULL;
static HWND g_hPrxHoveredBtn = NULL;

LRESULT CALLBACK AddProxyDlgProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        // Label
        CreateWindowExW(0, L"STATIC", T_PRX_LBL_NAME.get(), WS_CHILD | WS_VISIBLE, 20, 16, 380, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hPrxLabel = CreateWindowExW(0, L"EDIT", L"", WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL | WS_TABSTOP, 20, 36, 380, 26, hWnd, (HMENU)IDC_PRX_LABEL, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hPrxLabel, L"DarkMode_CFD", NULL);

        // Protocol
        CreateWindowExW(0, L"STATIC", T_PRX_LBL_PROTO.get(), WS_CHILD | WS_VISIBLE, 20, 68, 380, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hPrxProto = CreateWindowExW(0, L"COMBOBOX", L"", WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, 20, 88, 380, 140, hWnd, (HMENU)IDC_PRX_PROTO, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hPrxProto, L"DarkMode_CFD", NULL);
        SendMessageW(g_hPrxProto, CB_ADDSTRING, 0, (LPARAM)L"SOCKS5");
        SendMessageW(g_hPrxProto, CB_ADDSTRING, 0, (LPARAM)L"HTTPS");
        SendMessageW(g_hPrxProto, CB_ADDSTRING, 0, (LPARAM)L"HTTP");
        SendMessageW(g_hPrxProto, CB_ADDSTRING, 0, (LPARAM)L"SOCKS4");
        SendMessageW(g_hPrxProto, CB_SETCURSEL, 0, 0);

        // Host
        CreateWindowExW(0, L"STATIC", T_PRX_LBL_HOST.get(), WS_CHILD | WS_VISIBLE, 20, 120, 250, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hPrxHost = CreateWindowExW(0, L"EDIT", L"127.0.0.1", WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL | WS_TABSTOP, 20, 140, 250, 26, hWnd, (HMENU)IDC_PRX_HOST, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hPrxHost, L"DarkMode_CFD", NULL);

        // Port
        CreateWindowExW(0, L"STATIC", T_PRX_LBL_PORT.get(), WS_CHILD | WS_VISIBLE, 285, 120, 115, 18, hWnd, NULL, GetModuleHandle(NULL), NULL);
        g_hPrxPort = CreateWindowExW(0, L"EDIT", L"1080", WS_CHILD | WS_VISIBLE | WS_BORDER | ES_NUMBER | ES_AUTOHSCROLL | WS_TABSTOP, 285, 140, 115, 26, hWnd, (HMENU)IDC_PRX_PORT, GetModuleHandle(NULL), NULL);
        SetWindowTheme(g_hPrxPort, L"DarkMode_CFD", NULL);

        // Buttons
        g_hPrxBtnAdd = CreateWindowExW(0, L"BUTTON", T_PRX_BTN_ADD.get(), WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_TABSTOP, 195, 188, 100, 32, hWnd, (HMENU)IDC_PRX_ADD, GetModuleHandle(NULL), NULL);
        g_hPrxBtnCancel = CreateWindowExW(0, L"BUTTON", T_PRX_BTN_CANCEL.get(), WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_TABSTOP, 305, 188, 95, 32, hWnd, (HMENU)IDC_PRX_CANCEL, GetModuleHandle(NULL), NULL);

        ApplyFontToAllChildren(hWnd, g_hFontNormal);
        return 0;
    }

    case WM_ERASEBKGND: {
        HDC hdc = (HDC)wParam;
        RECT rc;
        GetClientRect(hWnd, &rc);
        FillRect(hdc, &rc, g_hBrushBg);
        return 1;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, g_colText);
        SetBkMode(hdc, TRANSPARENT);
        return (INT_PTR)g_hBrushBg;
    }

    case WM_CTLCOLOREDIT:
    case WM_CTLCOLORLISTBOX: {
        HDC hdc = (HDC)wParam;
        SetTextColor(hdc, RGB(220, 220, 220));
        SetBkColor(hdc, g_colEditBg);
        return (INT_PTR)g_hBrushEditBg;
    }

    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT pdis = (LPDRAWITEMSTRUCT)lParam;
        if (pdis->CtlType == ODT_BUTTON) {
            DrawCustomDialogButton(pdis, g_hPrxHoveredBtn);
            return TRUE;
        }
        break;
    }

    case WM_SETCURSOR: {
        HWND hTarget = (HWND)wParam;
        if (hTarget == g_hPrxBtnAdd || hTarget == g_hPrxBtnCancel) {
            if (g_hPrxHoveredBtn != hTarget) {
                HWND old = g_hPrxHoveredBtn;
                g_hPrxHoveredBtn = hTarget;
                if (old) InvalidateRect(old, NULL, FALSE);
                InvalidateRect(g_hPrxHoveredBtn, NULL, FALSE);

                TRACKMOUSEEVENT tme = { sizeof(TRACKMOUSEEVENT), TME_LEAVE, hWnd, 0 };
                TrackMouseEvent(&tme);
            }
        }
        break;
    }

    case WM_MOUSELEAVE: {
        if (g_hPrxHoveredBtn) {
            HWND old = g_hPrxHoveredBtn;
            g_hPrxHoveredBtn = NULL;
            InvalidateRect(old, NULL, FALSE);
        }
        break;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == IDC_PRX_ADD) {
            wchar_t bufL[128] = {}, bufH[128] = {}, bufP[32] = {};
            GetWindowTextW(g_hPrxLabel, bufL, 128);
            GetWindowTextW(g_hPrxHost, bufH, 128);
            GetWindowTextW(g_hPrxPort, bufP, 32);

            std::wstring lbl = TrimW(bufL);
            std::wstring host = TrimW(bufH);
            if (lbl.empty() || host.empty()) {
                MessageBoxW(hWnd, T_PRX_ERR_EMPTY.get(), T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
                return 0;
            }

            wchar_t proto[32] = {};
            GetWindowTextW(g_hPrxProto, proto, 32);

            g_dlgProxy.label = lbl;
            g_dlgProxy.type = proto;
            g_dlgProxy.address = host;
            g_dlgProxy.port = bufP;
            g_dlgProxy.options = L"48";

            g_dlgProxyAccepted = true;
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        } else if (id == IDC_PRX_CANCEL) {
            PostMessageW(hWnd, WM_CLOSE, 0, 0);
        }
        return 0;
    }
    }
    return DefWindowProcW(hWnd, uMsg, wParam, lParam);
}

bool ShowAddProxyDialog(HWND hParent, ProxyItem& outProxy) {
    g_dlgProxyAccepted = false;
    g_hPrxHoveredBtn = NULL;

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = AddProxyDlgProc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetAddProxyDlgClass";
    RegisterClassExW(&wc);

    int w = 435;
    int h = 275;
    RECT rcParent;
    GetWindowRect(hParent, &rcParent);
    int x = rcParent.left + (rcParent.right - rcParent.left - w) / 2;
    int y = rcParent.top + (rcParent.bottom - rcParent.top - h) / 2;

    HWND hDlg = CreateWindowExW(
        WS_EX_DLGMODALFRAME,
        L"ToInetAddProxyDlgClass",
        T_PRX_TITLE.get(),
        WS_POPUP | WS_CAPTION | WS_SYSMENU,
        x, y, w, h,
        hParent, NULL, GetModuleHandle(NULL), NULL
    );

    BOOL darkMode = TRUE;
    DwmSetWindowAttribute(hDlg, 20, &darkMode, sizeof(darkMode));
    DwmSetWindowAttribute(hDlg, 19, &darkMode, sizeof(darkMode));
    COLORREF captionColor = RGB(24, 24, 24);
    DwmSetWindowAttribute(hDlg, 35, &captionColor, sizeof(captionColor));

    ShowWindow(hDlg, SW_SHOW);
    UpdateWindow(hDlg);
    EnableWindow(hParent, FALSE);

    MSG msg;
    while (IsWindow(hDlg) && GetMessageW(&msg, NULL, 0, 0)) {
        if (msg.message == WM_KEYDOWN && msg.wParam == VK_ESCAPE) {
            DestroyWindow(hDlg);
            break;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    EnableWindow(hParent, TRUE);
    SetForegroundWindow(hParent);
    UnregisterClassW(L"ToInetAddProxyDlgClass", GetModuleHandle(NULL));

    if (g_dlgProxyAccepted) {
        outProxy = g_dlgProxy;
        return true;
    }
    return false;
}

void SyncRulesCheckState() {
    for (int i = 0; i < (int)g_rules.size(); ++i) {
        g_rules[i].enabled = ListView_GetCheckState(g_hListView, i);
    }
}

void OnAddRule() {
    SyncRulesCheckState();
    RuleItem r;
    r.enabled = true;
    r.apps = L"Any";
    r.targets = L"Any";
    r.ports = L"Any";
    r.actionKey = L"Direct";

    if (ShowSingleRuleDialog(g_hMainWnd, r, true)) {
        if (!g_rules.empty() && _wcsicmp(g_rules.back().name.c_str(), L"default") == 0) {
            g_rules.insert(g_rules.end() - 1, r);
        } else {
            g_rules.push_back(r);
        }
        PopulateListView();
    }
}

void OnAddProxy() {
    SyncRulesCheckState();
    ProxyItem p;
    if (ShowAddProxyDialog(g_hMainWnd, p)) {
        int maxId = 99;
        for (const auto& pr : g_proxies) {
            int pid = _wtoi(pr.id.c_str());
            if (pid > maxId) maxId = pid;
        }
        p.id = std::to_wstring(maxId + 1);
        g_proxies.push_back(p);

        // Update all rules labels
        for (auto& r : g_rules) {
            r.actionLabel = GetActionLabel(r.actionKey);
        }
        PopulateListView();

        std::wstring msg = (g_lang == LANG_RU) ?
            (L"Прокси '" + p.label + L"' (" + p.type + L" " + p.address + L":" + p.port + L") добавлен в список!\nТеперь вы можете выбрать его в правилах.") :
            (L"Proxy '" + p.label + L"' (" + p.type + L" " + p.address + L":" + p.port + L") added to the list!\nYou can now assign it to rules.");
        MessageBoxW(g_hMainWnd, msg.c_str(), T_PRX_SUCCESS_TITLE.get(), MB_OK | MB_ICONINFORMATION);
    }
}

void OnEditRule() {
    int sel = ListView_GetNextItem(g_hListView, -1, LVNI_SELECTED);
    if (sel < 0 || sel >= (int)g_rules.size()) return;

    SyncRulesCheckState();
    RuleItem r = g_rules[sel];
    if (ShowSingleRuleDialog(g_hMainWnd, r, false)) {
        g_rules[sel] = r;
        PopulateListView();
        ListView_SetItemState(g_hListView, sel, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
    }
}

void OnDeleteRule() {
    int sel = ListView_GetNextItem(g_hListView, -1, LVNI_SELECTED);
    if (sel < 0 || sel >= (int)g_rules.size()) return;

    if (_wcsicmp(g_rules[sel].name.c_str(), L"default") == 0) {
        MessageBoxW(g_hMainWnd, T_WARN_DEFAULT_DEL.get(), T_MSG_TITLE_WARN.get(), MB_OK | MB_ICONWARNING);
        return;
    }

    std::wstring prompt = (g_lang == LANG_RU) ?
        (L"Удалить правило '" + g_rules[sel].name + L"'?") :
        (L"Delete rule '" + g_rules[sel].name + L"'?");
    if (MessageBoxW(g_hMainWnd, prompt.c_str(), T_MSG_TITLE_CONF.get(), MB_YESNO | MB_ICONQUESTION) == IDYES) {
        SyncRulesCheckState();
        g_rules.erase(g_rules.begin() + sel);
        PopulateListView();
    }
}

void OnMoveUp() {
    int sel = ListView_GetNextItem(g_hListView, -1, LVNI_SELECTED);
    if (sel <= 0 || sel >= (int)g_rules.size()) return;

    SyncRulesCheckState();
    std::swap(g_rules[sel], g_rules[sel - 1]);
    PopulateListView();
    ListView_SetItemState(g_hListView, sel - 1, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
}

void OnMoveDown() {
    int sel = ListView_GetNextItem(g_hListView, -1, LVNI_SELECTED);
    if (sel < 0 || sel >= (int)g_rules.size() - 1) return;

    // Do not displace Default rule at the end
    if (_wcsicmp(g_rules[sel + 1].name.c_str(), L"default") == 0) return;

    SyncRulesCheckState();
    std::swap(g_rules[sel], g_rules[sel + 1]);
    PopulateListView();
    ListView_SetItemState(g_hListView, sel + 1, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
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

// Subclassed header proc for custom calm dark styling (eliminates jet black background)
LRESULT CALLBACK HeaderSubclassProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam, UINT_PTR uIdSubclass, DWORD_PTR dwRefData) {
    (void)dwRefData;
    switch (uMsg) {
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hWnd, &ps);

        RECT rcClient;
        GetClientRect(hWnd, &rcClient);

        // Calm dark slate/charcoal background (#262626)
        HBRUSH hBr = CreateSolidBrush(RGB(38, 38, 38));
        FillRect(hdc, &rcClient, hBr);
        DeleteObject(hBr);

        int count = Header_GetItemCount(hWnd);
        HPEN hPenDivider = CreatePen(PS_SOLID, 1, RGB(58, 58, 58));
        HGDIOBJ oldPen = SelectObject(hdc, hPenDivider);
        SelectObject(hdc, g_hFontBold);
        SetBkMode(hdc, TRANSPARENT);
        SetTextColor(hdc, RGB(220, 220, 220));

        const wchar_t* colFallbacks[] = {
            T_COL_NAME.get(), T_COL_APPS.get(), T_COL_TARGETS.get(), T_COL_PORTS.get(), T_COL_ACTION.get()
        };

        for (int i = 0; i < count; ++i) {
            RECT rcItem;
            Header_GetItemRect(hWnd, i, &rcItem);

            wchar_t textBuf[128] = { 0 };
            HDITEMW hdi = { 0 };
            hdi.mask = HDI_TEXT;
            hdi.pszText = textBuf;
            hdi.cchTextMax = 128;
            Header_GetItem(hWnd, i, &hdi);

            const wchar_t* pText = textBuf;
            if (wcslen(pText) == 0 && i < 5) {
                pText = colFallbacks[i];
            }

            RECT rcText = rcItem;
            rcText.left += 8;
            rcText.right -= 8;
            DrawTextW(hdc, pText, -1, &rcText, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS);

            // Divider on the right
            MoveToEx(hdc, rcItem.right - 1, rcItem.top + 3, NULL);
            LineTo(hdc, rcItem.right - 1, rcItem.bottom - 3);
        }

        // Bottom border
        HPEN hPenBottom = CreatePen(PS_SOLID, 1, RGB(50, 50, 50));
        SelectObject(hdc, hPenBottom);
        MoveToEx(hdc, rcClient.left, rcClient.bottom - 1, NULL);
        LineTo(hdc, rcClient.right, rcClient.bottom - 1);
        DeleteObject(hPenBottom);

        SelectObject(hdc, oldPen);
        DeleteObject(hPenDivider);

        EndPaint(hWnd, &ps);
        return 0;
    }
    case WM_ERASEBKGND:
        return 1;
    case WM_NCDESTROY:
        RemoveWindowSubclass(hWnd, HeaderSubclassProc, uIdSubclass);
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
        // Calm steel blue
        if (isSelected)      { colBg = RGB(24, 62, 96);  colBorder = RGB(36, 82, 126); }
        else if (isHovered)  { colBg = RGB(42, 92, 140); colBorder = RGB(52, 110, 165); }
        else                 { colBg = RGB(32, 78, 120); colBorder = RGB(36, 82, 126); }
    } else if (dis->CtlID == IDC_BTN_DEL_RULE) {
        // Calm muted crimson/wine
        if (isSelected)      { colBg = RGB(95, 32, 32);  colBorder = RGB(125, 45, 45); }
        else if (isHovered)  { colBg = RGB(135, 48, 48); colBorder = RGB(155, 55, 55); }
        else                 { colBg = RGB(115, 38, 38); colBorder = RGB(125, 45, 45); }
    } else {
        // Calm dark charcoal
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
    SelectObject(hdc, g_hFontNormal);
    DrawTextW(hdc, text, -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

// Window Procedure
LRESULT CALLBACK WndProc(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        g_hMainWnd = hWnd;

        g_hFontNormal = CreateFontW(16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontBold   = CreateFontW(16, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
        g_hFontSmall  = CreateFontW(14, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

        // Rules ListView (X=18, Y=40, W=868, H=500)
        g_hListView = CreateWindowExW(0, WC_LISTVIEWW, L"",
            WS_CHILD | WS_VISIBLE | WS_BORDER | LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
            18, 40, 868, 500, hWnd, (HMENU)IDC_LIST_RULES, GetModuleHandle(NULL), NULL);

        ListView_SetExtendedListViewStyle(g_hListView, LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES | LVS_EX_CHECKBOXES | LVS_EX_DOUBLEBUFFER);
        SetWindowTheme(g_hListView, L"DarkMode_Explorer", NULL);
        ListView_SetBkColor(g_hListView, RGB(24, 24, 24));
        ListView_SetTextBkColor(g_hListView, RGB(24, 24, 24));
        ListView_SetTextColor(g_hListView, RGB(220, 220, 220));

        HWND hHeader = ListView_GetHeader(g_hListView);
        if (hHeader) {
            SetWindowSubclass(hHeader, HeaderSubclassProc, (UINT_PTR)hHeader, 0);
            SendMessageW(hHeader, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);
        }

        SendMessageW(g_hListView, WM_SETFONT, (WPARAM)g_hFontNormal, TRUE);

        // Add Columns
        LVCOLUMNW lvc = {};
        lvc.mask = LVCF_TEXT | LVCF_WIDTH | LVCF_SUBITEM;

        lvc.iSubItem = 0; lvc.pszText = const_cast<wchar_t*>(T_COL_NAME.get()); lvc.cx = 150;
        ListView_InsertColumn(g_hListView, 0, &lvc);
        lvc.iSubItem = 1; lvc.pszText = const_cast<wchar_t*>(T_COL_APPS.get()); lvc.cx = 160;
        ListView_InsertColumn(g_hListView, 1, &lvc);
        lvc.iSubItem = 2; lvc.pszText = const_cast<wchar_t*>(T_COL_TARGETS.get()); lvc.cx = 240;
        ListView_InsertColumn(g_hListView, 2, &lvc);
        lvc.iSubItem = 3; lvc.pszText = const_cast<wchar_t*>(T_COL_PORTS.get()); lvc.cx = 110;
        ListView_InsertColumn(g_hListView, 3, &lvc);
        lvc.iSubItem = 4; lvc.pszText = const_cast<wchar_t*>(T_COL_ACTION.get()); lvc.cx = 185;
        ListView_InsertColumn(g_hListView, 4, &lvc);

        // Action Buttons Row (Y = 550, H = 34)
        int btnY = 550;
        int btnH = 34;

        g_hBtnAddRule  = CreateWindowExW(0, L"BUTTON", T_BTN_ADD_RULE.get(),  WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 18,  btnY, 140, btnH, hWnd, (HMENU)IDC_BTN_ADD_RULE,  GetModuleHandle(NULL), NULL);
        g_hBtnAddProxy = CreateWindowExW(0, L"BUTTON", T_BTN_ADD_PROXY.get(), WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 164, btnY, 140, btnH, hWnd, (HMENU)IDC_BTN_ADD_PROXY, GetModuleHandle(NULL), NULL);
        g_hBtnEdit     = CreateWindowExW(0, L"BUTTON", T_BTN_EDIT.get(),      WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 310, btnY, 130, btnH, hWnd, (HMENU)IDC_BTN_EDIT_RULE, GetModuleHandle(NULL), NULL);
        g_hBtnDelete   = CreateWindowExW(0, L"BUTTON", T_BTN_DELETE.get(),    WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 446, btnY, 90,  btnH, hWnd, (HMENU)IDC_BTN_DEL_RULE,  GetModuleHandle(NULL), NULL);
        g_hBtnUp       = CreateWindowExW(0, L"BUTTON", T_BTN_UP.get(),        WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 542, btnY, 78,  btnH, hWnd, (HMENU)IDC_BTN_UP,        GetModuleHandle(NULL), NULL);
        g_hBtnDown     = CreateWindowExW(0, L"BUTTON", T_BTN_DOWN.get(),      WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 626, btnY, 78,  btnH, hWnd, (HMENU)IDC_BTN_DOWN,      GetModuleHandle(NULL), NULL);
        g_hBtnCancel   = CreateWindowExW(0, L"BUTTON", T_BTN_CANCEL.get(),    WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 710, btnY, 82,  btnH, hWnd, (HMENU)IDC_BTN_CANCEL,    GetModuleHandle(NULL), NULL);
        g_hBtnSave     = CreateWindowExW(0, L"BUTTON", T_BTN_SAVE.get(),      WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 798, btnY, 88,  btnH, hWnd, (HMENU)IDC_BTN_SAVE,      GetModuleHandle(NULL), NULL);

        // Subclass all buttons for hover tracking
        HWND btns[] = { g_hBtnAddRule, g_hBtnAddProxy, g_hBtnEdit, g_hBtnDelete, g_hBtnUp, g_hBtnDown, g_hBtnCancel, g_hBtnSave };
        for (HWND b : btns) {
            SetWindowSubclass(b, ButtonSubclassProc, (UINT_PTR)b, 0);
        }

        ApplyFontToAllChildren(hWnd, g_hFontNormal);

        if (LoadPPX()) {
            PopulateListView();
        } else {
            MessageBoxW(hWnd, (g_lang == LANG_RU) ? L"Файл профиля Toinet.ppx не найден!" : L"Toinet.ppx profile file not found!", T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONERROR);
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

    case WM_NOTIFY: {
        LPNMHDR pnm = (LPNMHDR)lParam;
        if (pnm->idFrom == IDC_LIST_RULES) {
            if (pnm->code == NM_DBLCLK) {
                OnEditRule();
                return 0;
            }
            if (pnm->code == NM_CUSTOMDRAW) {
                LPNMLVCUSTOMDRAW pcd = (LPNMLVCUSTOMDRAW)lParam;
                switch (pcd->nmcd.dwDrawStage) {
                case CDDS_PREPAINT:
                    return CDRF_NOTIFYITEMDRAW;
                case CDDS_ITEMPREPAINT: {
                    int item = (int)pcd->nmcd.dwItemSpec;
                    bool isSel = (ListView_GetItemState(g_hListView, item, LVIS_SELECTED) & LVIS_SELECTED) != 0;
                    if (isSel) {
                        pcd->clrText = RGB(255, 255, 255);
                        pcd->clrTextBk = RGB(32, 78, 120); // Calm steel blue selection
                    } else {
                        pcd->clrText = RGB(220, 220, 220);
                        pcd->clrTextBk = (item % 2 == 0) ? RGB(24, 24, 24) : RGB(30, 30, 30);
                    }
                    return CDRF_NOTIFYSUBITEMDRAW;
                }
                case (CDDS_ITEMPREPAINT | CDDS_SUBITEM): {
                    int item = (int)pcd->nmcd.dwItemSpec;
                    bool isSel = (ListView_GetItemState(g_hListView, item, LVIS_SELECTED) & LVIS_SELECTED) != 0;
                    if (isSel) {
                        pcd->clrText = RGB(255, 255, 255);
                        pcd->clrTextBk = RGB(32, 78, 120);
                    } else {
                        pcd->clrText = RGB(220, 220, 220);
                        pcd->clrTextBk = (item % 2 == 0) ? RGB(24, 24, 24) : RGB(30, 30, 30);
                    }
                    return CDRF_NEWFONT;
                }
                }
                return CDRF_DODEFAULT;
            }
        }
        break;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == IDC_BTN_ADD_RULE) {
            OnAddRule();
        } else if (id == IDC_BTN_ADD_PROXY) {
            OnAddProxy();
        } else if (id == IDC_BTN_EDIT_RULE) {
            OnEditRule();
        } else if (id == IDC_BTN_DEL_RULE) {
            OnDeleteRule();
        } else if (id == IDC_BTN_UP) {
            OnMoveUp();
        } else if (id == IDC_BTN_DOWN) {
            OnMoveDown();
        } else if (id == IDC_BTN_SAVE) {
            SyncRulesCheckState();
            if (SavePPX()) {
                MessageBoxW(hWnd, T_MSG_SAVED.get(), T_MSG_TITLE_OK.get(), MB_OK | MB_ICONINFORMATION);
                DestroyWindow(hWnd);
            } else {
                MessageBoxW(hWnd, (g_lang == LANG_RU) ? L"Ошибка при сохранении Toinet.ppx" : L"Error saving Toinet.ppx", T_MSG_TITLE_ERR.get(), MB_OK | MB_ICONERROR);
            }
        } else if (id == IDC_BTN_CANCEL) {
            DestroyWindow(hWnd);
        }
        return 0;
    }

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hWnd, &ps);

        SelectObject(hdc, g_hFontSmall);
        SetTextColor(hdc, RGB(160, 160, 160));
        SetBkMode(hdc, TRANSPARENT);
        TextOutW(hdc, 20, 14, T_HEADER_NOTE.get(), (int)wcslen(T_HEADER_NOTE.get()));

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
    INITCOMMONCONTROLSEX icex = { sizeof(INITCOMMONCONTROLSEX), ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES | ICC_LISTVIEW_CLASSES };
    InitCommonControlsEx(&icex);

    InitPathsAndLang();

    g_hBrushBg = CreateSolidBrush(g_colBg);
    g_hBrushEditBg = CreateSolidBrush(g_colEditBg);

    WNDCLASSEXW wc = { sizeof(WNDCLASSEXW) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = g_hBrushBg;
    wc.lpszClassName = L"ToInetRulesEditorWnd";

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

    RECT rcWin = { 0, 0, 904, 598 };
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
