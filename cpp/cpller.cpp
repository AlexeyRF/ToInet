#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wininet.h>
#include <string>
#include <iostream>

#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "advapi32.lib")

void refresh_internet_settings() {
    InternetSetOptionW(NULL, INTERNET_OPTION_SETTINGS_CHANGED, NULL, 0);
    InternetSetOptionW(NULL, INTERNET_OPTION_REFRESH, NULL, 0);
}

bool set_proxy(const std::wstring& port, const std::wstring& /*mode*/) {
    HKEY hKey;
    LONG res = RegOpenKeyExW(
        HKEY_CURRENT_USER,
        L"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
        0,
        KEY_SET_VALUE,
        &hKey
    );
    if (res != ERROR_SUCCESS) {
        return false;
    }

    DWORD enable = 1;
    RegSetValueExW(hKey, L"ProxyEnable", 0, REG_DWORD, reinterpret_cast<const BYTE*>(&enable), sizeof(DWORD));

    std::wstring proxy_server;
    if (port == L"1785") {
        proxy_server = L"http=127.0.0.1:" + port + L";https=127.0.0.1:" + port;
    } else {
        proxy_server = L"socks=127.0.0.1:" + port;
    }

    RegSetValueExW(
        hKey,
        L"ProxyServer",
        0,
        REG_SZ,
        reinterpret_cast<const BYTE*>(proxy_server.c_str()),
        static_cast<DWORD>((proxy_server.length() + 1) * sizeof(wchar_t))
    );

    RegCloseKey(hKey);
    refresh_internet_settings();
    return true;
}

bool disable_proxy() {
    HKEY hKey;
    LONG res = RegOpenKeyExW(
        HKEY_CURRENT_USER,
        L"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
        0,
        KEY_SET_VALUE,
        &hKey
    );
    if (res != ERROR_SUCCESS) {
        return false;
    }

    DWORD enable = 0;
    RegSetValueExW(hKey, L"ProxyEnable", 0, REG_DWORD, reinterpret_cast<const BYTE*>(&enable), sizeof(DWORD));
    RegDeleteValueW(hKey, L"ProxyServer");

    RegCloseKey(hKey);
    refresh_internet_settings();
    return true;
}

int wmain(int argc, wchar_t* argv[]) {
    // Supports:
    // cpller.exe <port> <flag> [mode]
    // or cpller.exe cpller <port> <flag> [mode]
    if (argc < 2) {
        std::wcout << L"Usage: cpller.exe <port> <flag: 1|0> [mode]\n";
        return 1;
    }

    int offset = 1;
    if (_wcsicmp(argv[1], L"cpller") == 0) {
        offset = 2;
    }

    if (argc < offset + 2) {
        std::wcout << L"Usage: cpller.exe <port> <flag: 1|0> [mode]\n";
        return 1;
    }

    std::wstring port = argv[offset];
    std::wstring flag = argv[offset + 1];
    std::wstring mode = (argc > offset + 2) ? argv[offset + 2] : L"classic";

    if (flag == L"1") {
        set_proxy(port, mode);
    } else {
        disable_proxy();
    }

    return 0;
}
