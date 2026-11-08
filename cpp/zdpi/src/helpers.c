#define _GNU_SOURCE
#include "helpers.h"
#include <ctype.h>
#include <errno.h>

#ifdef _WIN32
    #include <wincrypt.h>
#endif

int unique_size_t(size_t *pu, int ct)
{
    if (ct <= 1) return ct;
    int j = 0;
    for (int i = 1; i < ct; i++) {
        if (pu[j] != pu[i]) {
            j++;
            pu[j] = pu[i];
        }
    }
    return j + 1;
}

int unique_ssize_t(ssize_t *pu, int ct)
{
    if (ct <= 1) return ct;
    int j = 0;
    for (int i = 1; i < ct; i++) {
        if (pu[j] != pu[i]) {
            j++;
            pu[j] = pu[i];
        }
    }
    return j + 1;
}

static int cmp_size_t(const void *a, const void *b)
{
    size_t va = *(const size_t*)a;
    size_t vb = *(const size_t*)b;
    return (va > vb) - (va < vb);
}

static int cmp_ssize_t(const void *a, const void *b)
{
    ssize_t va = *(const ssize_t*)a;
    ssize_t vb = *(const ssize_t*)b;
    return (va > vb) - (va < vb);
}

void qsort_size_t(size_t *array, int ct)
{
    qsort(array, ct, sizeof(size_t), cmp_size_t);
}

void qsort_ssize_t(ssize_t *array, int ct)
{
    qsort(array, ct, sizeof(ssize_t), cmp_ssize_t);
}

int str_index(const char **strs, int count, const char *str)
{
    for (int i = 0; i < count; i++) {
        if (!strcmp(strs[i], str)) return i;
    }
    return -1;
}

void rtrim(char *s)
{
    char *p = s + strlen(s) - 1;
    while (p >= s && isspace((unsigned char)*p)) {
        *p-- = 0;
    }
}

void replace_char(char *s, char from, char to)
{
    for (; *s; s++) {
        if (*s == from) *s = to;
    }
}

const char *strncasestr(const char *s, const char *find, size_t slen)
{
    char c = *find++;
    if (!c) return s;
    size_t len = strlen(find);
    c = tolower((unsigned char)c);
    for (; slen >= len + 1; s++, slen--) {
        if (tolower((unsigned char)*s) == c && !strncasecmp(s + 1, find, len))
            return s;
    }
    return NULL;
}

bool is_identifier(const char *p)
{
    if (!*p || (!isalpha((unsigned char)*p) && *p != '_')) return false;
    for (p++; *p; p++) {
        if (!isalnum((unsigned char)*p) && *p != '_') return false;
    }
    return true;
}

#define INVALID_HEX_DIGIT ((uint8_t)-1)
static inline uint8_t parse_hex_digit(char c)
{
    return (c >= '0' && c <= '9') ? c - '0' : (c >= 'a' && c <= 'f') ? c - 'a' + 0xA : (c >= 'A' && c <= 'F') ? c - 'A' + 0xA : INVALID_HEX_DIGIT;
}

static inline bool parse_hex_byte(const char *s, uint8_t *pbyte)
{
    uint8_t u = parse_hex_digit(s[0]);
    uint8_t l = parse_hex_digit(s[1]);
    if (u == INVALID_HEX_DIGIT || l == INVALID_HEX_DIGIT) {
        *pbyte = 0;
        return false;
    }
    *pbyte = (u << 4) | l;
    return true;
}

bool parse_hex_str(const char *s, uint8_t *pbuf, size_t *size)
{
    uint8_t *pe = pbuf + *size;
    *size = 0;
    while (pbuf < pe && *s) {
        if (!parse_hex_byte(s, pbuf)) return false;
        pbuf++; s += 2; (*size)++;
    }
    return true;
}

char hex_digit(uint8_t v)
{
    return v <= 9 ? '0' + v : (v <= 0xF) ? v + 'A' - 0xA : '?';
}

bool strip_host_to_ip(char *host)
{
    size_t l;
    char *h, *p;
    uint8_t addr[16];

    for (h = host; *h == ' ' || *h == '\t'; h++);
    l = strlen(h);
    if (l >= 2) {
        if (*h == '[') {
            for (p = ++h; *p && *p != ']'; p++);
            if (*p == ']') {
                l = p - h;
                memmove(host, h, l);
                host[l] = 0;
                return inet_pton(AF_INET6, host, addr) > 0;
            }
        } else {
            if (inet_pton(AF_INET6, h, addr) > 0) {
                if (host != h) {
                    l = strlen(h);
                    memmove(host, h, l);
                    host[l] = 0;
                }
                return true;
            } else {
                for (p = h; *p && *p != ':'; p++);
                l = p - h;
                if (host != h) memmove(host, h, l);
                host[l] = 0;
                return inet_pton(AF_INET, host, addr) > 0;
            }
        }
    }
    return false;
}

void ntopa46(const struct in_addr *ip, const struct in6_addr *ip6, char *str, size_t len)
{
    if (!len) return;
    *str = 0;
    if (ip) inet_ntop(AF_INET, (void*)ip, str, len);
    else if (ip6) inet_ntop(AF_INET6, (void*)ip6, str, len);
    else snprintf(str, len, "UNKNOWN_FAMILY");
}

void ntop46(const struct sockaddr *sa, char *str, size_t len)
{
    ntopa46(sa->sa_family == AF_INET ? &((struct sockaddr_in*)sa)->sin_addr : NULL,
        sa->sa_family == AF_INET6 ? &((struct sockaddr_in6*)sa)->sin6_addr : NULL,
        str, len);
}

void ntop46_port(const struct sockaddr *sa, char *str, size_t len)
{
    char ip[INET6_ADDRSTRLEN];
    ntop46(sa, ip, sizeof(ip));
    switch (sa->sa_family) {
    case AF_INET:
        snprintf(str, len, "%s:%u", ip, ntohs(((struct sockaddr_in*)sa)->sin_port));
        break;
    case AF_INET6:
        snprintf(str, len, "[%s]:%u", ip, ntohs(((struct sockaddr_in6*)sa)->sin6_port));
        break;
    default:
        snprintf(str, len, "%s", ip);
    }
}

void print_sockaddr(const struct sockaddr *sa)
{
    char ip_port[64];
    ntop46_port(sa, ip_port, sizeof(ip_port));
    printf("%s", ip_port);
}

uint16_t saport(const struct sockaddr *sa)
{
    return ntohs(sa->sa_family == AF_INET ? ((struct sockaddr_in*)sa)->sin_port :
        sa->sa_family == AF_INET6 ? ((struct sockaddr_in6*)sa)->sin6_port : 0);
}

bool sa_has_addr(const struct sockaddr *sa)
{
    switch (sa->sa_family) {
    case AF_INET:
        return ((struct sockaddr_in*)sa)->sin_addr.s_addr != INADDR_ANY;
    case AF_INET6:
        return memcmp(((struct sockaddr_in6*)sa)->sin6_addr.s6_addr, "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 16) != 0;
    default:
        return false;
    }
}

bool seq_within(uint32_t s, uint32_t s1, uint32_t s2)
{
    return (s2 >= s1 && s >= s1 && s <= s2) || (s2 < s1 && (s <= s2 || s >= s1));
}

bool ipv6_addr_is_zero(const struct in6_addr *a)
{
    static const uint8_t zero[16] = {0};
    return !memcmp(a, zero, 16);
}

uint16_t pntoh16(const uint8_t *p) { return ((uint16_t)p[0] << 8) | (uint16_t)p[1]; }
void phton16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)(v >> 8); p[1] = (uint8_t)v; }
uint32_t pntoh24(const uint8_t *p) { return ((uint32_t)p[0] << 16) | ((uint32_t)p[1] << 8) | (uint32_t)p[2]; }
void phton24(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 16); p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)v; }
uint32_t pntoh32(const uint8_t *p) { return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | (uint32_t)p[3]; }
void phton32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v; }
uint64_t pntoh48(const uint8_t *p) { return ((uint64_t)p[0] << 40) | ((uint64_t)p[1] << 32) | ((uint64_t)p[2] << 24) | ((uint64_t)p[3] << 16) | ((uint64_t)p[4] << 8) | p[5]; }
void phton48(uint8_t *p, uint64_t v) { p[0] = (uint8_t)(v >> 40); p[1] = (uint8_t)(v >> 32); p[2] = (uint8_t)(v >> 24); p[3] = (uint8_t)(v >> 16); p[4] = (uint8_t)(v >> 8); p[5] = (uint8_t)v; }
uint64_t pntoh64(const uint8_t *p) { return ((uint64_t)p[0] << 56) | ((uint64_t)p[1] << 48) | ((uint64_t)p[2] << 40) | ((uint64_t)p[3] << 32) | ((uint64_t)p[4] << 24) | ((uint64_t)p[5] << 16) | ((uint64_t)p[6] << 8) | p[7]; }
void phton64(uint8_t *p, uint64_t v) { p[0] = (uint8_t)(v >> 56); p[1] = (uint8_t)(v >> 48); p[2] = (uint8_t)(v >> 40); p[3] = (uint8_t)(v >> 32); p[4] = (uint8_t)(v >> 24); p[5] = (uint8_t)(v >> 16); p[6] = (uint8_t)(v >> 8); p[7] = (uint8_t)v; }

uint16_t bswap16(uint16_t u) { return (u >> 8) | ((u & 0xFF) << 8); }
uint32_t bswap24(uint32_t u) { return ((u >> 16) & 0xFF) | (u & 0xFF00) | ((u << 16) & 0xFF0000); }
uint64_t bswap48(uint64_t u) { return ((u & 0xFF0000000000ULL) >> 40) | ((u & 0xFF00000000ULL) >> 24) | ((u & 0xFF000000ULL) >> 8) | ((u & 0xFF0000ULL) << 8) | ((u & 0xFF00ULL) << 24) | ((u & 0xFFULL) << 40); }

void fill_random_bytes(uint8_t *p, size_t sz)
{
    for (size_t k = 0; k < sz; k++) p[k] = (uint8_t)rand();
}

void fill_random_az(uint8_t *p, size_t sz)
{
    for (size_t k = 0; k < sz; k++) p[k] = 'a' + (rand() % 26);
}

void fill_random_az09(uint8_t *p, size_t sz)
{
    static const char set[] = "0123456789abcdefghijklmnopqrstuvwxyz";
    for (size_t k = 0; k < sz; k++) p[k] = set[rand() % (sizeof(set) - 1)];
}

bool fill_crypto_random_bytes(uint8_t *p, size_t sz)
{
#ifdef _WIN32
    HCRYPTPROV hProv;
    if (CryptAcquireContext(&hProv, NULL, NULL, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT | CRYPT_SILENT)) {
        BOOL ok = CryptGenRandom(hProv, (DWORD)sz, p);
        CryptReleaseContext(hProv, 0);
        if (ok) return true;
    }
#endif
    fill_random_bytes(p, sz);
    return true;
}

void bxor(const uint8_t *x1, const uint8_t *x2, uint8_t *result, size_t sz)
{
    for (; sz >= 8; x1 += 8, x2 += 8, result += 8, sz -= 8)
        *(uint64_t*)result = *(uint64_t*)x1 ^ *(uint64_t*)x2;
    for (; sz; x1++, x2++, result++, sz--)
        *result = *x1 ^ *x2;
}

void bor(const uint8_t *x1, const uint8_t *x2, uint8_t *result, size_t sz)
{
    for (; sz >= 8; x1 += 8, x2 += 8, result += 8, sz -= 8)
        *(uint64_t*)result = *(uint64_t*)x1 | *(uint64_t*)x2;
    for (; sz; x1++, x2++, result++, sz--)
        *result = *x1 | *x2;
}

void band(const uint8_t *x1, const uint8_t *x2, uint8_t *result, size_t sz)
{
    for (; sz >= 8; x1 += 8, x2 += 8, result += 8, sz -= 8)
        *(uint64_t*)result = *(uint64_t*)x1 & *(uint64_t*)x2;
    for (; sz; x1++, x2++, result++, sz--)
        *result = *x1 & *x2;
}

bool parse_int16(const char *p, int16_t *v)
{
    if (*p == '+' || *p == '-' || (*p >= '0' && *p <= '9')) {
        int i = atoi(p);
        *v = (int16_t)i;
        return *v == i;
    }
    return false;
}

bool parse_int32(const char *p, int32_t *v)
{
    if (*p == '+' || *p == '-' || (*p >= '0' && *p <= '9')) {
        long l = atol(p);
        *v = (int32_t)l;
        return *v == l;
    }
    return false;
}

bool parse_uint16(const char *p, uint16_t *v)
{
    if (*p >= '0' && *p <= '9') {
        int i = atoi(p);
        if (i >= 0 && i <= 65535) {
            *v = (uint16_t)i;
            return true;
        }
    }
    return false;
}

bool parse_uint32(const char *p, uint32_t *v)
{
    if (*p >= '0' && *p <= '9') {
        unsigned long l = strtoul(p, NULL, 10);
        *v = (uint32_t)l;
        return true;
    }
    return false;
}

bool load_file(const char *filename, off_t offset, void *buffer, size_t *buffer_size)
{
    FILE *F = fopen(filename, "rb");
    if (!F) return false;
    if (offset && fseek(F, offset, SEEK_SET) != 0) {
        fclose(F);
        return false;
    }
    size_t rd = fread(buffer, 1, *buffer_size, F);
    fclose(F);
    *buffer_size = rd;
    return true;
}
