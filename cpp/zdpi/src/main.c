#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <limits.h>
#include <ctype.h>

#include "params.h"
#include "proxy.h"
#include "packets.h"
#include "error.h"
#include "conev.h"
#include "protocol.h"
#include "fake_data.h"
#include "helpers.h"

#ifndef _WIN32
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <netdb.h>
    #include <fcntl.h>
    #include <netinet/in.h>
    #include <netinet/tcp.h>
    #include <sys/socket.h>
    #include <sys/resource.h>
    #include <ifaddrs.h>
    
    #define DAEMON
#else
    #include <ws2tcpip.h>
    #include "win_service.h"
    #define close(fd) closesocket(fd)
#endif

#define VERSION "2.0-zapret2"

struct packet fake_tls = { 
    sizeof(tls_data), tls_data, 0
};
struct packet fake_http = { 
    sizeof(http_data), http_data, 0
};
struct packet fake_udp = { 
    sizeof(udp_data), udp_data, 0
};


struct params params = {
    .await_int = 10,
    
    .ipv6 = 1,
    .resolve = 1,
    .udp = 1,
    .max_open = 512,
    .bfsize = 16384,
    .baddr = {
        .in6 = { .sin6_family = AF_INET6 }
    },
    .laddr = {
        .in = { .sin_family = AF_INET }
    },
    .debug = 0
};


static const char help_text[] = {
    "==================================================================\n"
    "         zDPI - Advanced ByeDPI with Zapret2 DPI Engine           \n"
    "==================================================================\n"
    "Usage: zdpi [OPTIONS]\n\n"
    "ZAPRET2 ADVANCED OPTIONS:\n"
    "    --dpi-desync <modes>      Desync modes: fake,split,disorder,fakedsplit,\n"
    "                              fakeddisorder,multisplit,tlsrec,oob\n"
    "    --dpi-desync-split-pos <p>Positions/markers: midsld,sld,endsld,sniext,\n"
    "                              sni,endsni,extlen,method, or numbers\n"
    "    --dpi-desync-ttl <num>    TTL for fake packets (default: 3)\n"
    "    --dpi-desync-fake-tls <t> TLS fake: google, kyber, rutracker, <file>, <hex>\n"
    "    --dpi-desync-fake-quic <t>QUIC fake: google, <file>, <hex>\n"
    "    --dpi-desync-fake-sni <s> Spoof SNI in fake packets\n"
    "    --quic-drop, --drop-quic  Drop QUIC Initial to force instant HTTP/2 fallback\n"
    "    --wsize <size_kb>         Clamp TCP window size\n\n"
    "BYEDPI OPTIONS:\n"
    "    -i, --ip <ip>             Listening IP, default 127.0.0.1 (or 0.0.0.0)\n"
    "    -p, --port <num>          Listening port, default 1080\n"
    "    -c, --max-conn <count>    Connection count limit, default 512\n"
    "    -b, --buf-size <size>     Buffer size, default 16384\n"
    "    -x, --debug <level>       Print logs, 0, 1 or 2\n"
    "    -g, --def-ttl <num>       TTL for all outgoing connections\n"
    "    -s, --split <pos_t>       Split at position\n"
    "    -d, --disorder <pos_t>    Split and send reverse order\n"
    "    -f, --fake <pos_t>        Split and send fake packet\n"
    "    -r, --tlsrec <pos_t>      Make TLS record at position (midsld, sniext, etc.)\n"
    "    -t, --ttl <num>           TTL of fake packets, default 8\n"
    "    -n, --fake-sni <str>      Change SNI in fake\n"
    "    -M, --mod-http <mods>     Modify HTTP: h,d,r,m (methodeol), u (unixeol), t (tab)\n"
    "    -A, --auto <t,r,s,n,c>    Auto-detect: torst,redirect,ssl_err\n"
    "    -H, --hosts <file|:str>   Hosts whitelist\n"
    "    -j, --ipset <file|:str>   IP whitelist\n"
    "    -U, --no-udp              Deny UDP association\n"
    "    -N, --no-domain           Deny domain resolving\n"
};


const struct option options[] = {
    #ifdef DAEMON
    {"daemon",        0, 0, 'D'},
    {"pidfile",       1, 0, 'w'},
    #endif
    {"no-domain",     0, 0, 'N'},
    {"no-ipv6",       0, 0, 'X'},
    {"no-udp",        0, 0, 'U'},
    {"help",          0, 0, 'h'},
    {"version",       0, 0, 'v'},
    {"ip",            1, 0, 'i'},
    {"port",          1, 0, 'p'},
    #ifdef __linux__
    {"transparent",   0, 0, 'E'},
    #endif
    {"conn-ip",       1, 0, 'I'},
    {"buf-size",      1, 0, 'b'},
    {"max-conn",      1, 0, 'c'},
    {"debug",         1, 0, 'x'},
    
    #ifdef TCP_FASTOPEN_CONNECT
    {"tfo",           0, 0, 'F'},
    #endif
    {"auto",          1, 0, 'A'},
    {"auto-mode",     1, 0, 'L'},
    {"cache-ttl",     1, 0, 'u'},
    #ifdef TIMEOUT_SUPPORT
    {"tcp-timeout",   1, 0, 'T'},
    #endif
    {"tls-timeout",   1, 0, 'W'},
    {"copy",          1, 0, 'B'},
    {"cache-file",    1, 0, 'y'},
    {"proto",         1, 0, 'K'},
    {"hosts",         1, 0, 'H'},
    {"pf",            1, 0, 'V'},
    {"round",         1, 0, 'R'},
    {"split",         1, 0, 's'},
    {"disorder",      1, 0, 'd'},
    {"oob",           1, 0, 'o'},
    {"disoob",        1, 0, 'q'},
    #ifdef FAKE_SUPPORT
    {"fake",          1, 0, 'f'},
    #ifdef __linux__
    {"md5sig",        0, 0, 'S'},
    #endif
    {"fake-sni",      1, 0, 'n'},
    #endif
    {"ttl",           1, 0, 't'},
    {"fake-data",     1, 0, 'l'},
    {"fake-offset",   1, 0, 'O'},
    {"fake-tls-mod",  1, 0, 'Q'},
    {"oob-data",      1, 0, 'e'},
    {"mod-http",      1, 0, 'M'},
    {"tlsrec",        1, 0, 'r'},
    {"tlsminor",      1, 0, 'm'},
    {"udp-fake",      1, 0, 'a'},
    {"def-ttl",       1, 0, 'g'},
    {"wait-send",     0, 0, 'Z'}, //
    {"await-int",     1, 0, 'z'}, //
    #ifdef __linux__
    {"drop-sack",     0, 0, 'Y'},
    {"protect-path",  1, 0, 'P'}, //
    #endif
    {"ipset",         1, 0, 'j'},
    {"connect-to",    1, 0, 'C'}, //
    {"rst",           0, 0, '0'}, //
    {"comment",       1, 0, '#'}, //
    {"cache-merge",   1, 0, '/'},
    {"dpi-desync",          1, 0, 1001},
    {"dpi-desync-split-pos",1, 0, 1002},
    {"dpi-desync-ttl",      1, 0, 1003},
    {"dpi-desync-autottl",  1, 0, 1004},
    {"dpi-desync-fake-tls", 1, 0, 1005},
    {"dpi-desync-fake-quic",1, 0, 1006},
    {"dpi-desync-fake-sni", 1, 0, 1007},
    {"dpi-desync-fooling",  1, 0, 1008},
    {"dpi-desync-any-protocol", 0, 0, 1009},
    {"dpi-desync-cutoff",   1, 0, 1010},
    {"wsize",               1, 0, 1011},
    {"quic-drop",           0, 0, 1012},
    {"drop-quic",           0, 0, 1012},
    {"hostlist",            1, 0, 'H'},
    {"fake-hex",            1, 0, 1015},
    {"fake-file",           1, 0, 'l'},
    {"split-pos",           1, 0, 1002},
    {0}
};
    

ssize_t parse_cform(char *buffer, size_t blen, 
        const char *str, size_t slen)
{
    static char esca[] = {
        'r','\r','n','\n','t','\t','\\','\\',
        'f','\f','b','\b','v','\v','a','\a', 0
    };
    size_t i = 0, p = 0;
    for (; p < slen && i < blen; ++p, ++i) {
        if (str[p] != '\\') {
            buffer[i] = str[p];
            continue;
        }
        p++;
        char *e = esca;
        for (; *e; e += 2) {
            if (*e == str[p]) {
                buffer[i] = *(e + 1);
                break;
            }
        }
        if (*e) {
            continue;
        }
        int n = 0;
        if (sscanf(&str[p], "x%2hhx%n", (uint8_t *)&buffer[i], &n) == 1
              || sscanf(&str[p], "%3hho%n", (uint8_t *)&buffer[i], &n) == 1) {
            p += (n - 1);
            continue;
        }
        i--; p--;
    }
    return i;
}


char *data_from_str(const char *str, ssize_t *size)
{
    ssize_t len = strlen(str);
    if (len == 0) {
        return 0;
    }
    char *d = malloc(len);
    if (!d) {
        return 0;
    }
    ssize_t i = parse_cform(d, len, str, len);
    
    char *m = len != i ? realloc(d, i) : 0;
    if (i == 0) {
        return 0;
    }
    *size = i;
    return m ? m : d;
}


char *ftob(const char *str, ssize_t *sl)
{
    if (*str == ':') {
        return data_from_str(str + 1, sl);
    }
    char *buffer = 0;
    long size;
    
    FILE *file = fopen(str, "rb");
    if (!file) {
        return 0;
    }
    do {
        if (fseek(file, 0, SEEK_END)) {
            break;
        }
        size = ftell(file);
        if (size <= 0) {
            break;
        }
        if (fseek(file, 0, SEEK_SET)) {
            break;
        }
        if (!(buffer = malloc(size))) {
            break;
        }
        size_t rs = fread(buffer, 1, size, file);
        if (rs != (size_t )size) {
            free(buffer);
            buffer = 0;
        }
    } while (0);
    if (buffer) {
        *sl = size;
    }
    fclose(file);
    return buffer;
}


static inline int lower_char(char *cl)
{
    char c = *cl;
    if (c < 'A') {
        if (c > '9' || c < '-')
            return -1;
    }
    else if (c < 'a') {
        if (c > 'Z') 
            return -1;
        *cl = c + 32;
    }
    else if (c > 'z') 
        return -1;
    return 0;
}


int parse_hosts(struct mphdr *hdr, char *buffer, size_t size)
{
    size_t num = 0;
    bool drop = 0;
    char *end = buffer + size;
    char *e = buffer, *s = buffer;
    
    for (; e <= end; e++) {
        if (e != end && *e != ' ' && *e != '\n' && *e != '\r') {
            if (lower_char(e)) {
                drop = 1;
            }
            continue;
        }
        if (s == e) {
            s++;
            continue;
        }
        if (!drop) {
            if (!mem_add(hdr, s, e - s, sizeof(struct elem))) {
                return -1;
            }
        } 
        else {
            LOG(LOG_E, "invalid host: num: %zd \"%.*s\"\n", num + 1, ((int )(e - s)), s);
            drop = 0;
        }
        num++;
        s = e + 1;
    }
    LOG(LOG_S, "hosts count: %zd\n", hdr->count);
    return 0;
}


static int parse_ip(char *out, char *str, size_t size)
{
    long bits = 0;
    char *sep = memchr(str, '/', size);
    if (sep) {
        bits = strtol(sep + 1, 0, 10);
        if (bits <= 0) {
            return 0;
        }
        *sep = 0;
    }
    int len = sizeof(struct in_addr);
    
    if (inet_pton(AF_INET, str, out) <= 0) {
        if (inet_pton(AF_INET6, str, out) <= 0) {
            return 0;
        }
        else len = sizeof(struct in6_addr);
    }
    if (!bits || bits > len * 8) bits = len * 8;
    return (int )bits;
}


int parse_ipset(struct mphdr *hdr, char *buffer, size_t size)
{
    size_t num = 0;
    char *end = buffer + size;
    char *e = buffer, *s = buffer;
    
    for (; e <= end; e++) {
        if (e != end && *e != ' ' && *e != '\n' && *e != '\r') {
            continue;
        }
        if (s == e) {
            s++;
            continue;
        }
        char ip[e - s + 1];
        ip[e - s] = 0;
        memcpy(ip, s, e - s);
        
        num++;
        s = e + 1;
        
        char ip_stack[sizeof(struct in6_addr)];
        int bits = parse_ip(ip_stack, ip, sizeof(ip));
        if (bits <= 0) {
            LOG(LOG_E, "invalid ip: num: %zd\n", num);
            continue;
        }
        int len = bits / 8 + (bits % 8 ? 1 : 0);
        char *ip_raw = malloc(len);
        memcpy(ip_raw, ip_stack, len);
        
        struct elem *elem = mem_add(hdr, ip_raw, bits, sizeof(struct elem));
        if (!elem) {
            free(ip_raw);
            return -1;
        }
    }
    LOG(LOG_S, "ip count: %zd\n", hdr->count);
    return 0;
}


static int get_addr_ifname(const char *name, union sockaddr_u *addr)
{
    int err = -1, prefer_family = addr->sa.sa_family;

    #ifndef _WIN32
    struct ifaddrs *ifap, *ifa;
    
    if (getifaddrs(&ifap) || !ifap) {
        uniperror("getifaddrs");
        return -1;
    }
    for (ifa = ifap; ifa; ifa = ifa->ifa_next) {
        if (strcmp(ifa->ifa_name, name)) {
            continue;
        }
        if (!err && prefer_family
                 && prefer_family != ifa->ifa_addr->sa_family) {
            continue;
        }
        memcpy(addr, ifa->ifa_addr, SA_SIZE(ifa->ifa_addr));
        err = 0;
    }
    freeifaddrs(ifap);
    
    if (err && prefer_family == AF_INET6) {
        char *e = 0;
        addr->in6.sin6_scope_id = strtol(name, &e, 10);
        if (!*e) {
            err = 0;
        }
    }
    #endif
    return err;
}


int get_addr(const char *str, union sockaddr_u *addr)
{
    uint16_t port = addr->in.sin_port;
    const char *s = str, *p = s, *e = strchr(str, 0);
    
    if (*str == '[') {
        if (!(e = strchr(str, ']'))) {
            return -1;
        }
        s++; p = e + 1;
    }
    p = strchr(p, ':');
    if (p && isdigit(p[1])) {
        const char *end = 0;
        long val = strtol(p + 1, (char **)&end, 0);
        if (val <= 0 || val > 0xffff || *end)
            return -1;
        else
            port = htons(val);
        if (e > p) e = p;
    }
    const char *scope = strchr(s, '%');
    if (scope) { 
        p = e; 
        if (e > scope) e = scope;
    }
    if (e != s) {
        char str_ip[(e - s) + 1];
        memcpy(str_ip, s, e - s);
        str_ip[e - s] = 0;
        
        struct addrinfo hints = {0}, *res = 0;
        
        hints.ai_socktype = SOCK_STREAM;
        hints.ai_family = AF_UNSPEC;
        hints.ai_flags = AI_NUMERICHOST;
        
        if (getaddrinfo(str_ip, 0, &hints, &res) || !res) {
            return -1;
        }
        memcpy(addr, res->ai_addr, SA_SIZE(res->ai_addr));
        freeaddrinfo(res);
    }
    if (scope) {
        char str_scope[p - scope];
        memcpy(str_scope, scope + 1, p - scope - 1);
        str_scope[p - scope - 1] = 0;
        
        if (get_addr_ifname(str_scope, addr)) {
            return -1;
        }
    }
    addr->in.sin_port = port;
    return 0;
}


int get_addr_scheme(const char *str, union sockaddr_u *addr)
{
    const char *schemes[] = {
        "socks4://", "socks5://", "socks://", "ss://", 
        "http://", "sni://", "tcp://", 
    #ifdef __linux__
        "red://", 
    #endif
    0 };
    const int scheme_int[] = {
        MODE_SOCKS4, MODE_SOCKS5, MODE_SOCKS, MODE_SHADOWSOCKS, 
        MODE_HTTP, MODE_RAWTLS, MODE_TCP, MODE_TRANSPARENT
    };
    int mode = 0;
    for (size_t i = 0; schemes[i]; i++) {
        int s_len = strlen(schemes[i]);
        if (!strncmp(str, schemes[i], s_len)) {
            mode = scheme_int[i];
            str += s_len;
            break;
        }
    }
    if (get_addr(str, addr)) {
        return -1;
    }
    return mode;
}


int get_default_ttl(void)
{
    int orig_ttl = -1, fd;
    socklen_t tsize = sizeof(orig_ttl);
    
    if ((fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        uniperror("socket");
        return -1;
    }
    if (getsockopt(fd, IPPROTO_IP, IP_TTL,
             (char *)&orig_ttl, &tsize) < 0) {
        uniperror("getsockopt IP_TTL");
    }
    close(fd);
    return orig_ttl;
}


bool ipv6_support(void)
{
    int fd = socket(AF_INET6, SOCK_STREAM, 0);
    if (fd < 0) {
        return 0;
    }
    close(fd);
    return 1;
}


int parse_offset(struct part *part, const char *str)
{
    if (posmarker_parse(str, &part->ppos) && part->ppos.marker != PM_ABS) {
        return 0;
    }
    char *end = 0;
    long val = strtol(str, &end, 0);
    
    while (*end == ':') {
        long rs = strtol(end + 1, &end, 0);
        if (rs < 0 || rs > INT_MAX) {
            return -1;
        }
        if (!part->r) {
            if (!rs) 
                return -1;
            part->r = rs;
        }
        else {
            part->s = rs;
            break;
        }
    }
    if (*end == '+') {
        switch (*(end + 1)) {
            case 's':
                part->flag = OFFSET_SNI;
                break;
            case 'h': 
                part->flag = OFFSET_HOST;
                break;
            case 'n':
                break;
            default:
                return -1;
        }
        switch (*(end + 2)) {
            case 'e':
                part->flag |= OFFSET_END;
                break;
            case 'm':
                part->flag |= OFFSET_MID;
                break;
            case 'r': //
                part->flag |= OFFSET_RAND;
                break;
            case 's': //
                part->flag |= OFFSET_START;
        }
    }
    else if (*end) {
        return -1;
    }
    part->pos = val;
    return 0;
}


void *add(void **root, int *n, size_t ss)
{
    char *p = realloc(*root, ss * (*n + 1));
    if (!p) {
        uniperror("realloc");
        return 0;
    }
    *root = p;
    p = (p + ((*n) * ss));
    memset(p, 0, ss);
    *n = *n + 1;
    return p;
}

static void apply_preset(struct desync_params *dp, const char *name)
{
    if (!strcmp(name, "youtube")) {
        dp->preset = PRESET_YOUTUBE;
        dp->fake_template = FAKE_TMPL_GOOGLE;
        dp->ttl = 3;
        dp->drop_quic = true;
        dp->mod_http = MH_HMIX | MH_METHODEOL;
        params.wait_send = true;
        params.await_int = 10;
        
        struct part *tr = add((void *)&dp->tlsrec, &dp->tlsrec_n, sizeof(struct part));
        if (tr) {
            memset(tr, 0, sizeof(*tr));
            posmarker_parse("midsld", &tr->ppos);
        }
        struct part *p1 = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p1) {
            memset(p1, 0, sizeof(*p1));
            p1->m = DESYNC_FAKE;
            posmarker_parse("midsld", &p1->ppos);
        }
        struct part *p2 = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p2) {
            memset(p2, 0, sizeof(*p2));
            p2->m = DESYNC_SPLIT;
            posmarker_parse("midsld", &p2->ppos);
        }
    } else if (!strcmp(name, "discord")) {
        dp->preset = PRESET_DISCORD;
        dp->fake_template = FAKE_TMPL_GOOGLE;
        dp->ttl = 3;
        params.udp = true;
        params.wait_send = true;
        params.await_int = 10;
        
        struct part *tr = add((void *)&dp->tlsrec, &dp->tlsrec_n, sizeof(struct part));
        if (tr) {
            memset(tr, 0, sizeof(*tr));
            tr->flag = OFFSET_SNI;
            tr->pos = 1;
        }
        struct part *p1 = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p1) {
            memset(p1, 0, sizeof(*p1));
            p1->m = DESYNC_FAKE;
            p1->pos = 1;
        }
        struct part *p2 = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p2) {
            memset(p2, 0, sizeof(*p2));
            p2->m = DESYNC_SPLIT;
            posmarker_parse("midsld", &p2->ppos);
        }
    } else {
        dp->preset = PRESET_GENERAL;
        dp->fake_template = FAKE_TMPL_GOOGLE;
        dp->ttl = 3;
        dp->drop_quic = true;
        dp->mod_http = MH_HMIX | MH_METHODEOL;
        params.wait_send = true;
        params.await_int = 10;
        
        struct part *tr = add((void *)&dp->tlsrec, &dp->tlsrec_n, sizeof(struct part));
        if (tr) {
            memset(tr, 0, sizeof(*tr));
            posmarker_parse("midsld", &tr->ppos);
        }
        struct part *p1 = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p1) {
            memset(p1, 0, sizeof(*p1));
            p1->m = DESYNC_FAKE;
            posmarker_parse("midsld", &p1->ppos);
        }
        struct part *p2 = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p2) {
            memset(p2, 0, sizeof(*p2));
            p2->m = DESYNC_SPLIT;
            posmarker_parse("midsld", &p2->ppos);
        }
        dp->detect = DETECT_TORST | DETECT_HTTP_LOCAT | DETECT_TLS_ERR;
        params.auto_reconnect = true;
    }
}

static void apply_zapret_desync(struct desync_params *dp, const char *modes)
{
    char buf[256];
    strncpy(buf, modes, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = 0;
    
    char *tok = strtok(buf, ",+ ");
    while (tok) {
        int m = DESYNC_SPLIT;
        if (!strcmp(tok, "fake")) m = DESYNC_FAKE;
        else if (!strcmp(tok, "split") || !strcmp(tok, "multisplit")) m = DESYNC_SPLIT;
        else if (!strcmp(tok, "disorder") || !strcmp(tok, "multidisorder")) m = DESYNC_DISORDER;
        else if (!strcmp(tok, "oob")) m = DESYNC_OOB;
        else if (!strcmp(tok, "disoob")) m = DESYNC_DISOOB;
        else if (!strcmp(tok, "fakedsplit")) m = DESYNC_FAKEDSPLIT;
        else if (!strcmp(tok, "fakeddisorder")) m = DESYNC_FAKEDDISORDER;
        else if (!strcmp(tok, "tlsrec")) {
            struct part *tr = add((void *)&dp->tlsrec, &dp->tlsrec_n, sizeof(struct part));
            if (tr) {
                memset(tr, 0, sizeof(*tr));
                posmarker_parse("midsld", &tr->ppos);
            }
            tok = strtok(NULL, ",+ ");
            continue;
        }
        
        struct part *p = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
        if (p) {
            memset(p, 0, sizeof(*p));
            p->m = m;
            posmarker_parse("midsld", &p->ppos);
        }
        tok = strtok(NULL, ",+ ");
    }
}

static void apply_zapret_split_pos(struct desync_params *dp, const char *positions)
{
    char buf[512];
    strncpy(buf, positions, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = 0;
    
    char *tok = strtok(buf, ",+ ");
    int idx = 0;
    while (tok) {
        if (idx < dp->parts_n) {
            parse_offset(&dp->parts[idx], tok);
        } else {
            struct part *p = add((void *)&dp->parts, &dp->parts_n, sizeof(struct part));
            if (p) {
                memset(p, 0, sizeof(*p));
                p->m = DESYNC_SPLIT;
                parse_offset(p, tok);
            }
        }
        if (idx < dp->tlsrec_n) {
            parse_offset(&dp->tlsrec[idx], tok);
        }
        idx++;
        tok = strtok(NULL, ",+ ");
    }
}


static struct desync_params *add_group(struct desync_params *prev)
{
    struct desync_params *dp = calloc(1, sizeof(*prev));
    if (!dp) {
        return 0;
    }
    if (prev) {
        dp->prev = prev;
        prev->next = dp;
    }
    dp->id = params.dp_n;
    dp->bit = 1 << dp->id;
    dp->str = "";
    
    params.dp_n++;
    params.dp_full_mask |= dp->bit;
    return dp;
}


#ifdef DAEMON
int init_pid_file(const char *fname)
{
    int pid_fd = open(fname, O_RDWR | O_CREAT, 0640);
    if (pid_fd < 0) {
        return -1;
    }
    struct flock fl = { 
        .l_whence = SEEK_CUR,
        .l_type = F_WRLCK
    };
    if (fcntl(pid_fd, F_SETLK, &fl) < 0) {
        close(pid_fd);
        return -1;
    }
    char pid_str[21];
    snprintf(pid_str, sizeof(pid_str), "%d", getpid());
    
    if (write(pid_fd, pid_str, strlen(pid_str)) < 0) {
        close(pid_fd);
        return -1;
    }
    return pid_fd;
}
#endif


void clear_params(char *line, char **argv)
{

    #ifdef _WIN32
    WSACleanup();
    #endif
    #ifdef DAEMON
    if (params.pid_fd > 0) {
        close(params.pid_fd);
    }
    if (params.pid_file) {
        unlink(params.pid_file);
    }
    #endif
    if (line) {
        free(line);
        free(argv);
    }
    if (params.mempool) {
        mem_destroy(params.mempool);
        params.mempool = 0;
    }
    for (int i = 0; i < params.need_free_n; i++) {
        free(params.need_free[i]);
    }
    params.need_free_n = 0;
    
    struct desync_params *dp = params.dp;
    while (dp) {
        free(dp->parts);
        free(dp->tlsrec);
        free(dp->fake_data.data);
        free(dp->fake_sni_list);
        mem_destroy(dp->hosts);
        mem_destroy(dp->ipset);
        
        struct desync_params *t = dp;
        dp = dp->next;
        memset(t, 0, sizeof(*t));
        free(t);
    }
    params.dp = 0;
}


int parse_args(int argc, char **argv) 
{
    char opt[512];
    int o = 0;
    for (int i = 0; options[i].name; i++) {
        if (options[i].val >= ' ' && options[i].val <= '~') {
            opt[o++] = (char)options[i].val;
            for (int c = options[i].has_arg; c > 0 && c <= 2; c--) {
                opt[o++] = ':';
            }
        }
    }
    opt[o] = '\0';
    //
    if (!params.laddr.in.sin_port) {
        params.laddr.in.sin_port = htons(1080);
    }
    if (!ipv6_support()) {
        params.baddr.sa.sa_family = AF_INET;
    }
    int rez;
    int invalid = 0;
    
    long val = 0;
    char *end = 0;
    bool all_limited = 1;
    
    int curr_optind = 1;
    
    params.mempool = mem_pool(MF_EXTRA, CMP_BITS);
    if (!params.mempool) {
        uniperror("mem_pool");
        return -1;
    }
    
    struct desync_params *dp = add_group(0);
    if (!dp) {
        return -1;
    }
    params.dp = dp;
    
    while (!invalid && (rez = getopt_long(
             argc, argv, opt, options, 0)) != -1) {
        switch (rez) {
        
        case 'N':
            params.resolve = 0;
            break;
        case 'X':
            params.ipv6 = 0;
            break;
        case 'U':
            params.udp = 0;
            break;
        #ifdef __linux__
        case 'E':
            params.mode = MODE_TRANSPARENT;
            break;
        #endif
        
        #ifdef DAEMON
        case 'D':
            params.daemonize = 1;
            break;
            
        case 'w':
            params.pid_file = optarg;
            break;
        #endif
        case 'h':
            printf(help_text);
            return 1;
        case 'v':
            printf("%s\n", VERSION);
            return 1;
        
        case 'i':;
            int mode = get_addr_scheme(optarg, &params.laddr);
            if (mode < 0)
                invalid = 1;
            else
                params.mode |= mode;
            break;
            
        case 'p':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > 0xffff || *end)
                invalid = 1;
            else
                params.laddr.in.sin_port = htons(val);
            break;
            
        case 'I':
            if (get_addr(optarg, &params.baddr) < 0)
                invalid = 1;
            break;
            
        case 'b':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > INT_MAX/4 || *end)
                invalid = 1;
            else
                params.bfsize = val;
            break;
            
        case 'c':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val >= (0xffff/2) || *end) 
                invalid = 1;
            else
                params.max_open = val;
            break;
           
        case 'x': //
            params.debug = strtol(optarg, 0, 0);
            if (params.debug < 0)
                invalid = 1;
            break;
            
        case 'y':
            dp->cache_file = optarg;
            if (!strcmp(dp->cache_file, "-")) {
                break;
            }
            FILE *file = fopen(dp->cache_file, "r");
            if (!file)
                perror("fopen");
            else {
                load_cache(params.mempool, file, dp);
                fclose(file);
                LOG(LOG_S, "cache ip count: %zd\n", params.mempool->count);
            }
            break;
            
        // desync options
        
        case 'F':
            params.tfo = 1;
            break;
            
        case 'L':
            end = optarg;
            while (end && !invalid) {
                switch (*end) {
                    case 'o':
                        dp->auto_level |= AUTO_ONRECONN;
                        break;
                    case 's': 
                        dp->auto_level |= AUTO_SORT;
                        break;
                    case 'n': 
                        dp->auto_level |= AUTO_NORECONN;
                        break;
                    default:
                        invalid = 1;
                        continue;
                }
                end = strchr(end, ',');
                if (end) end++;
            }
            break;
            
        case 'A':
            if (optind < curr_optind) {
                optind = curr_optind;
                continue;
            }
            if (!(dp->hosts || dp->proto || dp->pf[0] || dp->detect || dp->ipset)) {
                all_limited = 0;
            }
            dp = add_group(dp);
            if (!dp) {
                return -1;
            }
            end = optarg;
            while (end && !invalid) {
                switch (*end) {
                    case 't': 
                        dp->detect |= DETECT_TORST;
                        break;
                    case 'r': 
                        dp->detect |= DETECT_HTTP_LOCAT;
                        break;
                    case 's': 
                        dp->detect |= DETECT_TLS_ERR;
                        break;
                    case 'c':
                        dp->detect |= DETECT_CONNECT;
                        break;
                    case 'n': 
                        break;
                    case 'p':
                        if ((end = strchr(end, '='))) {
                            float f = strtof(end + 1, &end);
                            if (*end) invalid = 1;
                            else dp->prev->pri = (int )f;
                        }
                        break;
                    default:
                        invalid = 1;
                        continue;
                }
                end = strchr(end, ',');
                if (end) end++;
            }
            if (dp->detect) {
                params.auto_reconnect = 1;
            }
            dp->_optind = optind;
            break;
            
        case 'B':
            if (optind < curr_optind) {
                continue;
            }
            if (*optarg == 'i') {
                dp->pf[0] = htons(1);
                continue;
            }
            val = strtol(optarg, &end, 0);
            struct desync_params *itdp = params.dp;
            
            while (itdp && itdp->id != val - 1) {
                itdp = itdp->next;
            }
            if (!itdp) 
                invalid = 1;
            else {
                curr_optind = optind;
                optind = itdp->_optind;
            }
            break;
        
        case '#':
            dp->str = optarg;
            break;
            
        case 'u':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || *end) 
                invalid = 1;
            else {
                dp->cache_ttl = val;
            }
            break;
        
        case '/':
            val = strtol(optarg, &end, 0);
            if (val < 0 || val > 32 || *end) 
                invalid = 1;
            else 
                params.cache_pre = 32 - val;
            break;
            
        case 'T':;
            float f = strtof(optarg, &end);
            params.timeout = (f * 1000);
            if (*end == ':')
                params.tcp_to_bytes_lim = strtof(end + 1, &end);
            if (*end)
                invalid = 1;
            break;
            
        case 'W':
            f = strtof(optarg, &end);
            params.tls_timeout = (f * 1000);
            if (*end == ':') 
                params.tls_to_count_lim = strtof(end + 1, &end);
            if (*end == ':')
                params.tls_to_bytes_lim = strtof(end + 1, &end);
            if (*end)
                invalid = 1;
            break;
            
        case 'K':
            end = optarg;
            while (end && !invalid) {
                switch (*end) {
                    case 't': 
                        dp->proto |= IS_TCP | IS_HTTPS;
                        break;
                    case 'h': 
                        dp->proto |= IS_TCP | IS_HTTP;
                        break;
                    case 'u': 
                        dp->proto |= IS_UDP;
                        break;
                    case 'i': 
                        dp->proto |= IS_IPV4;
                        break;
                    default:
                        invalid = 1;
                        continue;
                }
                end = strchr(end, ',');
                if (end) end++;
            }
            break;
            
        case 'H':
            if (!dp->hosts && 
                    !(dp->hosts = mem_pool(MF_STATIC, CMP_HOST))) {
                return -1;
            }
            ssize_t size = 0;
            char *data = ftob(optarg, &size);
            if (!data) {
                uniperror("read/parse");
                invalid = 1;
                continue;
            }
            char **d = add((void *)&params.need_free, &params.need_free_n, sizeof(data));
            if (!d) {
                return -1;
            }
            *d = data;
            if (parse_hosts(dp->hosts, data, size)) {
                uniperror("parse_hosts");
                return -1;
            }
            break;
            
        case 'j':
            data = ftob(optarg, &size);
            if (!data) {
                uniperror("read/parse");
                invalid = 1;
                continue;
            }
            if (!dp->ipset 
                    && !(dp->ipset = mem_pool(0, CMP_BITS))) {
                return -1;
            }
            if (parse_ipset(dp->ipset, data, size)) {
                uniperror("parse_ipset");
                invalid = 1;
            }
            free(data);
            break;
            
        case 's':
        case 'd':
        case 'o':
        case 'q':
        case 'f':
            ;
            struct part *part = add((void *)&dp->parts,
                &dp->parts_n, sizeof(struct part));
            if (!part) {
                return -1;
            }
            if (parse_offset(part, optarg)) {
                invalid = 1;
                break;
            }
            switch (rez) {
                case 's': part->m = DESYNC_SPLIT;
                    break;
                case 'd': part->m = DESYNC_DISORDER;
                    break;
                case 'o': part->m = DESYNC_OOB;
                    break;
                case 'q': part->m = DESYNC_DISOOB;
                    break;
                case 'f': part->m = DESYNC_FAKE;
            }
            break;
            
        case 't':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > 255 || *end) 
                invalid = 1;
            else
                dp->ttl = val;
            break;
            
        case 'S':
            dp->md5sig = 1;
            break;
            
        case 'O':
            if (parse_offset(&dp->fake_offset, optarg)) {
                invalid = 1;
                break;
            } else dp->fake_offset.m = 1;
            break;
            
        case 'Q':
            end = optarg;
            while (end && !invalid) {
                switch (*end) {
                    case 'r': 
                        dp->fake_mod |= FM_RAND;
                        break;
                    case 'o': 
                        dp->fake_mod |= FM_ORIG;
                        break;
                    case 'm': 
                        if ((end = strchr(end, '='))) {
                            val = strtol(end + 1, &end, 0);
                            if (!(val > INT_MAX || (*end && *end != ','))) {
                                dp->fake_tls_size = val;
                                break;
                            }
                        }
                        __attribute__((fallthrough));
                    default:
                        invalid = 1;
                        continue;
                }
                end = strchr(end, ',');
                if (end) end++;
            }
            break;
            
        case 'n':;
            const char **p = add((void *)&dp->fake_sni_list,
                    &dp->fake_sni_count, sizeof(optarg));
            if (!p) {
                invalid = 1;
                continue;
            }
            *p = optarg;
            break;
            
        case 'l':
            if (dp->fake_data.data) {
                continue;
            }
            dp->fake_data.data = ftob(optarg, &dp->fake_data.size);
            if (!dp->fake_data.data) {
                uniperror("read/parse");
                invalid = 1;
            }
            break;
            
        case 'e':
            val = parse_cform(dp->oob_char, 1, optarg, strlen(optarg));
            if (val != 1) {
                invalid = 1;
            }
            else dp->oob_char[1] = 1;
            break;
            
        case 'M':
            end = optarg;
            while (end && !invalid) {
                switch (*end) {
                    case 'r': 
                        dp->mod_http |= MH_SPACE;
                        break;
                    case 'h': 
                        dp->mod_http |= MH_HMIX;
                        break;
                    case 'd': 
                        dp->mod_http |= MH_DMIX;
                        break;
                    default:
                        invalid = 1;
                        continue;
                }
                end = strchr(end, ',');
                if (end) end++;
            }
            break;
            
        case 'r':
            part = add((void *)&dp->tlsrec,
                &dp->tlsrec_n, sizeof(struct part));
            if (!part) {
                return -1;
            }
            if (parse_offset(part, optarg)
                   || part->pos > 0xffff) {
                invalid = 1;
                break;
            }
            break;
            
        case 'm':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > 255 || *end) 
                invalid = 1;
            else {
                dp->tlsminor = val;
                dp->tlsminor_set = 1;
            }
            break;
            
        case 'a':
            val = strtol(optarg, &end, 0);
            if (val < 0 || val > INT_MAX || *end)
                invalid = 1;
            else
                dp->udp_fake_count = val;
            break;
            
        case 'V':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > USHRT_MAX)
                invalid = 1;
            else {
                dp->pf[0] = htons(val);
                if (*end == '-') {
                    val = strtol(end + 1, &end, 0);
                    if (val <= 0 || val > USHRT_MAX)
                        invalid = 1;
                }
                if (*end)
                    invalid = 1;
                else
                    dp->pf[1] = htons(val);
            }
            break;
            
        case 'R':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > INT_MAX)
                invalid = 1;
            else {
                dp->rounds[0] = val;
                if (*end == '-') {
                    val = strtol(end + 1, &end, 0);
                    if (val <= 0 || val > INT_MAX)
                        invalid = 1;
                }
                if (*end)
                    invalid = 1;
                else
                    dp->rounds[1] = val;
            }
            break;
            
        case 'g':
            val = strtol(optarg, &end, 0);
            if (val <= 0 || val > 255 || *end)
                invalid = 1;
            else {
                params.def_ttl = val;
                params.custom_ttl = 1;
            }
            break;
            
        case 'Y':
            dp->drop_sack = 1;
            break;
        
        case 'Z':
            params.wait_send = 1;
            break;
        
        case 'z':
            params.await_int = atoi(optarg);
            break;
            
        case '0':
            dp->rst = 1;
            break;
            
        case 'C':
            dp->out_type = get_addr_scheme(optarg, &dp->out_addr);
            if ((dp->out_type & OUT_SUPPORT) != dp->out_type) {
                invalid = 1;
            }
            if (!dp->out_type) dp->out_type = MODE_SOCKS5;
            params.delay_conn = 1;
            break;
        
        #ifdef __linux__
        case 'P':
            params.protect_path = optarg;
            break;
        #endif
        case 1001: // --dpi-desync
            apply_zapret_desync(dp, optarg);
            break;
            
        case 1002: // --dpi-desync-split-pos
            apply_zapret_split_pos(dp, optarg);
            break;
            
        case 1003: // --dpi-desync-ttl
        case 1004: // --dpi-desync-autottl
            val = strtol(optarg, &end, 0);
            if (val > 0 && val <= 255) dp->ttl = val;
            break;
            
        case 1005: // --dpi-desync-fake-tls
            if (!strcmp(optarg, "google")) dp->fake_template = FAKE_TMPL_GOOGLE;
            else if (!strcmp(optarg, "kyber")) dp->fake_template = FAKE_TMPL_KYBER;
            else if (!strcmp(optarg, "rutracker")) dp->fake_template = FAKE_TMPL_RUTRACKER;
            else if (!strncmp(optarg, "0x", 2) || !strncmp(optarg, "0X", 2)) {
                size_t hlen = strlen(optarg + 2) / 2;
                dp->fake_data.data = malloc(hlen);
                dp->fake_data.size = hlen;
                parse_hex_str(optarg + 2, (uint8_t *)dp->fake_data.data, &hlen);
            } else {
                dp->fake_data.data = ftob(optarg, &dp->fake_data.size);
            }
            break;
            
        case 1006: // --dpi-desync-fake-quic
            dp->fake_quic = true;
            break;
            
        case 1007: // --dpi-desync-fake-sni
            {
                const char **p = add((void *)&dp->fake_sni_list, &dp->fake_sni_count, sizeof(optarg));
                if (p) *p = optarg;
            }
            break;
            
        case 1008: // --dpi-desync-fooling
            break;
            
        case 1009: // --dpi-desync-any-protocol
            dp->proto = 0;
            break;
            
        case 1010: // --dpi-desync-cutoff
            break;
            
        case 1011: // --wsize
            dp->wsize = atoi(optarg);
            break;
            
        case 1012: // --quic-drop / --drop-quic
            dp->drop_quic = true;
            break;
            
        case 1015: // --fake-hex
            {
                const char *hx = optarg;
                if (!strncmp(hx, "0x", 2) || !strncmp(hx, "0X", 2)) hx += 2;
                size_t hlen = strlen(hx) / 2;
                dp->fake_data.data = malloc(hlen);
                dp->fake_data.size = hlen;
                parse_hex_str(hx, (uint8_t *)dp->fake_data.data, &hlen);
            }
            break;

        case 0:
            break;
            
        case '?':
            return -1;
            
        default: 
            printf("?: %c\n", rez);
            return -1;
        }
    }
    if (invalid) {
        fprintf(stderr, "invalid value: -%c %s\n", rez, optarg);
        return -1;
    }
    if (all_limited) {
        dp = add_group(dp);
        if (!dp) {
            return -1;
        }
    }
    if ((size_t )params.dp_n > sizeof(dp->bit) * 8) {
        LOG(LOG_E, "too many groups!\n");
    }
    if (params.baddr.sa.sa_family != AF_INET6) {
        params.ipv6 = 0;
    }
    if (!params.mode) params.mode |= (MODE_SOCKS4 | MODE_SOCKS5);
    return 0;
}


void dump_all_cache(void)
{
    for (struct desync_params *dp = params.dp; dp; dp = dp->next) {
        LOG(LOG_S, "group: %d (%s), triggered: %d, pri: %d, calls: %d\n", dp->id, dp->str, dp->fail_count, dp->pri, dp->calls);
        if (dp->cache_file) {
            if (!strcmp(dp->cache_file, "-")) {
                dump_cache(params.mempool, stdout, dp);
            }
            else {
                FILE *f = fopen(dp->cache_file, "w");
                if (!f) {
                    perror("fopen");
                    return;
                }
                dump_cache(params.mempool, f, dp);
                fclose(f);
            }
        }
    }
}


int init(void)
{
    if (!params.def_ttl) {
        if ((params.def_ttl = get_default_ttl()) < 1) {
            return -1;
        }
    }
    srand((unsigned int)time(0));
    
    #ifdef DAEMON
    if (params.daemonize && daemon(0, 0) < 0) {
        return -1;
    }
    if (params.pid_file 
            && (params.pid_fd = init_pid_file(params.pid_file)) < 0) {
        return -1;
    }
    #endif
    
    #ifndef _WIN32
    struct rlimit r = { 0 };
    rlim_t mc = params.max_open * 3 + 10;
    
    if (getrlimit(RLIMIT_NOFILE, &r) < 0) {
        uniperror("getrlimit");
    }
    else if (r.rlim_cur < mc) {
        r.rlim_cur = r.rlim_max < mc ? r.rlim_max : mc;
        
        if (setrlimit(RLIMIT_NOFILE, &r) < 0) {
            uniperror("setrlimit");
        }
    }
    #endif
    return 0;
}


int main(int argc, char **argv) 
{
    #ifdef _WIN32
    WSADATA wsa;
    
    if (WSAStartup(MAKEWORD(2, 2), &wsa)) {
        uniperror("WSAStartup");
        return -1;
    }
    if (register_winsvc(argc, argv)) {
        return 0;
    }
    #endif
    
    const char *local_port = getenv("SS_LOCAL_PORT");
    if (local_port) {
        params.laddr.in.sin_port = htons(atoi(local_port));
        #ifdef __linux__
        if (!access("protect_path", F_OK)) {
            params.protect_path = "protect_path";
        }
        #endif
        params.mode |= MODE_SHADOWSOCKS;
    }
    char *cmd_line = 0;
    const char *env_options = getenv("SS_PLUGIN_OPTIONS");
    
    if (env_options) {
        cmd_line = calloc(strlen(env_options) + 1, 1);
        strcpy(cmd_line, env_options);
        
        argc = 1;
        argv = calloc(64, sizeof(char *));
        argv[0] = cmd_line;
        
        for (char *c = cmd_line; *c && argc < 64; c++) {
            if (*c == ' ') {
                *c = 0;
                continue;
            }
            if (c == cmd_line || !c[-1]) {
                argv[argc++] = c;
            }
        }
    }
    
    int status = parse_args(argc, argv);
    if (status) {
        clear_params(cmd_line, argv);
        return status - 1;
    }
    LOG(LOG_S, "listen address: %s:%d\n", 
        straddr(params.laddr).s, ntohs(params.laddr.in.sin_port));
    
    printf("\n");
    printf("==================================================================\n");
    printf("           zDPI - Advanced ByeDPI with Zapret2 Engine             \n");
    printf("==================================================================\n");
    printf(" [i] Local SOCKS Proxy: %s:%d\n", 
        straddr(params.laddr).s, ntohs(params.laddr.in.sin_port));
    struct desync_params *cur_dp = params.dp;
    printf(" [i] Strategy: %s\n",
        (cur_dp && (cur_dp->parts_n > 0 || cur_dp->tlsrec_n > 0)) ? "Active Desync Pipeline" : "Direct Proxy");
    if (cur_dp && (cur_dp->parts_n > 0 || cur_dp->tlsrec_n > 0 || cur_dp->drop_quic)) {
        printf(" [i] TLS Desync: %d parts, %d tlsrec | Fake TTL: %d\n",
            cur_dp->parts_n, cur_dp->tlsrec_n, cur_dp->ttl ? cur_dp->ttl : 8);
        printf(" [i] QUIC (HTTP/3): %s\n", cur_dp->drop_quic ? "Dropped (instant TCP HTTP/2 fallback)" : "Active");
    }
    printf(" [i] Windows Driver: Pure User-Space (No WinDivert, No Admin Needed)\n");
    printf("==================================================================\n");
    printf(" Configure your browser / apps to use: socks5://%s:%d\n",
        straddr(params.laddr).s, ntohs(params.laddr.in.sin_port));
    printf(" Press Ctrl+C to terminate.\n");
    printf("==================================================================\n\n");
    fflush(stdout);
    
    if (init() < 0 || run(&params.laddr) < 0) {
        clear_params(cmd_line, argv);
        return -1;
    }
    dump_all_cache();
    clear_params(cmd_line, argv);
    return 0;
}
