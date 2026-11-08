#pragma once

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <windows.h>
    typedef int socklen_t;
    #ifndef random
        #define random rand
    #endif
#else
    #include <arpa/inet.h>
    #include <netinet/in.h>
    #include <sys/socket.h>
#endif

#include <sys/stat.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>

#ifndef MIN
    #define MIN(a, b) (((a) < (b)) ? (a) : (b))
#endif
#ifndef MAX
    #define MAX(a, b) (((a) > (b)) ? (a) : (b))
#endif

typedef union
{
    struct sockaddr_in sa4;
    struct sockaddr_in6 sa6;
    char _align[32];
} sockaddr_in46;

int unique_size_t(size_t *pu, int ct);
int unique_ssize_t(ssize_t *pu, int ct);
void qsort_size_t(size_t *array, int ct);
void qsort_ssize_t(ssize_t *array, int ct);

int str_index(const char **strs, int count, const char *str);
void rtrim(char *s);
void replace_char(char *s, char from, char to);
const char *strncasestr(const char *s, const char *find, size_t slen);
bool is_identifier(const char *p);

bool parse_hex_str(const char *s, uint8_t *pbuf, size_t *size);
char hex_digit(uint8_t v);

bool strip_host_to_ip(char *host);

void print_sockaddr(const struct sockaddr *sa);
void ntopa46(const struct in_addr *ip, const struct in6_addr *ip6, char *str, size_t len);
void ntop46(const struct sockaddr *sa, char *str, size_t len);
void ntop46_port(const struct sockaddr *sa, char *str, size_t len);

uint16_t saport(const struct sockaddr *sa);
bool sa_has_addr(const struct sockaddr *sa);

bool seq_within(uint32_t s, uint32_t s1, uint32_t s2);
bool ipv6_addr_is_zero(const struct in6_addr *a);

uint16_t pntoh16(const uint8_t *p);
void phton16(uint8_t *p, uint16_t v);
uint32_t pntoh24(const uint8_t *p);
void phton24(uint8_t *p, uint32_t v);
uint32_t pntoh32(const uint8_t *p);
void phton32(uint8_t *p, uint32_t v);
uint64_t pntoh48(const uint8_t *p);
void phton48(uint8_t *p, uint64_t v);
uint64_t pntoh64(const uint8_t *p);
void phton64(uint8_t *p, uint64_t v);

uint16_t bswap16(uint16_t u);
uint32_t bswap24(uint32_t u);
uint64_t bswap48(uint64_t u);

void fill_random_bytes(uint8_t *p, size_t sz);
void fill_random_az(uint8_t *p, size_t sz);
void fill_random_az09(uint8_t *p, size_t sz);
bool fill_crypto_random_bytes(uint8_t *p, size_t sz);

void bxor(const uint8_t *x1, const uint8_t *x2, uint8_t *result, size_t sz);
void band(const uint8_t *x1, const uint8_t *x2, uint8_t *result, size_t sz);
void bor(const uint8_t *x1, const uint8_t *x2, uint8_t *result, size_t sz);

bool parse_int16(const char *p, int16_t *v);
bool parse_int32(const char *p, int32_t *v);
bool parse_uint16(const char *p, uint16_t *v);
bool parse_uint32(const char *p, uint32_t *v);

bool load_file(const char *filename, off_t offset, void *buffer, size_t *buffer_size);
