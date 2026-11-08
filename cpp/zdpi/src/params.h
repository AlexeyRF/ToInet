#ifndef PARAMS_H
#define PARAMS_H

#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>
#include <assert.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
#else
    #include <arpa/inet.h>
    #include <netinet/in.h>
    #include <unistd.h>
    #include <sys/socket.h>
#endif

#include "mpool.h"
#include "protocol.h"

#if defined(__linux__) || defined(_WIN32)
#define FAKE_SUPPORT 1
#define TIMEOUT_SUPPORT 1
#endif

#define OFFSET_END      1
#define OFFSET_MID      2
#define OFFSET_RAND     4
#define OFFSET_SNI      8
#define OFFSET_HOST     16
#define OFFSET_START    32
#define OFFSET_SLD      64
#define OFFSET_MIDSLD   128
#define OFFSET_ENDSLD   256
#define OFFSET_SNI_EXT  512
#define OFFSET_EXT_LEN  1024
#define OFFSET_METHOD   2048

#define DETECT_HTTP_LOCAT 1
#define DETECT_TLS_ERR 2
#define DETECT_TORST 8
#define DETECT_CONNECT 16

#define AUTO_ONRECONN 1
#define AUTO_NORECONN 2
#define AUTO_SORT 4

#define MODE_SOCKS5 1
#define MODE_SOCKS4 2
#define MODE_HTTP 4
#define MODE_TRANSPARENT 8
#define MODE_SHADOWSOCKS 16
#define MODE_RAWTLS 32
#define MODE_TCP 64
#define MODE_SOCKS (MODE_SOCKS4 | MODE_SOCKS5)

#define OUT_SUPPORT (MODE_SOCKS5 | MODE_TCP)

#define FM_RAND 1
#define FM_ORIG 2
#define FM_PADENCAP 4
#define FM_DUPSID 8

#define MH_HMIX 1
#define MH_DMIX 2
#define MH_SPACE 4
#define MH_METHODEOL 8
#define MH_UNIXEOL 16
#define MH_TAB 32

enum demode {
    DESYNC_NONE,
    DESYNC_SPLIT,
    DESYNC_DISORDER,
    DESYNC_OOB,
    DESYNC_DISOOB,
    DESYNC_FAKE,
    DESYNC_FAKEDSPLIT,
    DESYNC_FAKEDDISORDER,
    DESYNC_MULTISPLIT,
    DESYNC_TLSREC
};

enum preset_type {
    PRESET_NONE = 0,
    PRESET_GENERAL,
    PRESET_YOUTUBE,
    PRESET_DISCORD
};

enum fake_tmpl_type {
    FAKE_TMPL_DEFAULT = 0,
    FAKE_TMPL_GOOGLE,
    FAKE_TMPL_KYBER,
    FAKE_TMPL_RUTRACKER,
    FAKE_TMPL_CUSTOM
};

#ifdef STR_MODE
static const char *demode_str[] = {
    "DESYNC_NONE",
    "DESYNC_SPLIT",
    "DESYNC_DISORDER",
    "DESYNC_OOB",
    "DESYNC_DISOOB",
    "DESYNC_FAKE",
    "DESYNC_FAKEDSPLIT",
    "DESYNC_FAKEDDISORDER",
    "DESYNC_MULTISPLIT",
    "DESYNC_TLSREC"
};
#endif

union sockaddr_u {
    struct sockaddr sa;
    struct sockaddr_in in;
    struct sockaddr_in6 in6;
};

struct part {
    int m;
    int flag;
    long pos;
    int r, s;
    struct proto_pos ppos;
};

struct packet {
     ssize_t size;
     char  *data;
     ssize_t off;
};

struct desync_params {
    int ttl;
    bool md5sig;
    struct packet fake_data;
    int udp_fake_count;
    struct part fake_offset;
    int fake_sni_count;
    const char **fake_sni_list;
    int fake_mod;
    int fake_tls_size;
    bool drop_sack;
    char oob_char[2];
    
    int parts_n;
    struct part *parts;
    
    int mod_http;
    int tlsrec_n;
    struct part *tlsrec;
    uint8_t tlsminor;
    bool tlsminor_set;
    
    bool drop_quic;
    bool fake_quic;
    struct packet fake_quic_data;
    int wsize;
    int fake_template;
    int preset;
    
    int proto;
    short detect;
    short auto_level;
    struct mphdr *hosts;
    struct mphdr *ipset;
    uint16_t pf[2];
    int rounds[2];
    
    bool rst;
    
    uint16_t out_type;
    union sockaddr_u out_addr;
    
    int _optind;
    int id;
    uint64_t bit;
    int fail_count;
    int pri;
    int calls;
    const char *str;
    long cache_ttl;
    const char *cache_file;
    
    struct desync_params *prev;
    struct desync_params *next;
};

struct params {
    int dp_n;
    struct desync_params *dp;
    uint64_t dp_full_mask;
    int await_int;
    bool wait_send;
    int def_ttl;
    bool custom_ttl;
    
    bool tfo;
    unsigned int timeout, tls_timeout;
    int tls_to_count_lim;
    int tls_to_bytes_lim;
    int tcp_to_bytes_lim;
    char cache_pre;
    int mode;
    bool ipv6;
    bool resolve;
    bool udp;
    bool delay_conn;
    bool auto_reconnect;
    int max_open;
    int debug;
    size_t bfsize;
    union sockaddr_u baddr;
    union sockaddr_u laddr;
    struct mphdr *mempool;
    
    char **need_free;
    int need_free_n;
    
    const char *protect_path;
    bool daemonize;
    const char *pid_file;
    int pid_fd;
};

extern struct params params;

extern struct packet fake_tls;
extern struct packet fake_http;
extern struct packet fake_udp;

#endif
