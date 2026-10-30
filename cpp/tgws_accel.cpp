#include <cstdint>
#include <cstddef>
#include <cstring>
#include <immintrin.h>

#if defined(_MSC_VER)
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

EXPORT const char* tgws_accel_version() {
    return "1.1.0";
}

// In-place WebSocket masking using AVX2 with 64-bit and 8-bit fallbacks
EXPORT void ws_mask_inplace(uint8_t* data, size_t len, uint32_t mask) {
    if (!data || len == 0) return;

    size_t i = 0;

#if defined(__AVX2__) || defined(_M_X64) || defined(_M_IX86)
    // 32-byte chunks with AVX2 if supported
    if (len >= 32) {
        __m256i vmask = _mm256_set1_epi32(static_cast<int>(mask));
        for (; i + 32 <= len; i += 32) {
            __m256i chunk = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(data + i));
            chunk = _mm256_xor_si256(chunk, vmask);
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(data + i), chunk);
        }
    }
#endif

    // 8-byte chunks fallback
    uint64_t mask64 = (static_cast<uint64_t>(mask) << 32) | mask;
    for (; i + 8 <= len; i += 8) {
        *reinterpret_cast<uint64_t*>(data + i) ^= mask64;
    }

    // 1-byte tail
    const uint8_t* m8 = reinterpret_cast<const uint8_t*>(&mask);
    for (; i < len; ++i) {
        data[i] ^= m8[i & 3];
    }
}

// Copy and mask from src to dst in a single pass
EXPORT void ws_mask_copy(const uint8_t* src, uint8_t* dst, size_t len, uint32_t mask) {
    if (!src || !dst || len == 0) return;

    size_t i = 0;

#if defined(__AVX2__) || defined(_M_X64) || defined(_M_IX86)
    if (len >= 32) {
        __m256i vmask = _mm256_set1_epi32(static_cast<int>(mask));
        for (; i + 32 <= len; i += 32) {
            __m256i chunk = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(src + i));
            chunk = _mm256_xor_si256(chunk, vmask);
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(dst + i), chunk);
        }
    }
#endif

    uint64_t mask64 = (static_cast<uint64_t>(mask) << 32) | mask;
    for (; i + 8 <= len; i += 8) {
        uint64_t chunk = *reinterpret_cast<const uint64_t*>(src + i);
        *reinterpret_cast<uint64_t*>(dst + i) = chunk ^ mask64;
    }

    const uint8_t* m8 = reinterpret_cast<const uint8_t*>(&mask);
    for (; i < len; ++i) {
        dst[i] = src[i] ^ m8[i & 3];
    }
}

// Protocol constants matching tgws utils.py
constexpr uint32_t PROTO_ABRIDGED_TAG = 0xefefefef;
constexpr uint32_t PROTO_INTERMEDIATE_TAG = 0xeeeeeeee;
constexpr uint32_t PROTO_PADDED_INTERMEDIATE_TAG = 0xdddddddd;

// Fast scan for MTProto packet boundaries in buffer
// Returns number of complete packets found, or -1 on protocol error
EXPORT int mtproto_find_packets(
    uint32_t proto_type,
    const uint8_t* plain_buf,
    size_t buf_len,
    size_t start_offset,
    size_t* out_offsets,
    size_t* out_lengths,
    int max_packets
) {
    if (!plain_buf || !out_offsets || !out_lengths || max_packets <= 0) {
        return 0;
    }

    int count = 0;
    size_t offset = start_offset;

    bool is_abridged = (proto_type == PROTO_ABRIDGED_TAG || proto_type == 1);
    bool is_intermediate = (proto_type == PROTO_INTERMEDIATE_TAG || proto_type == PROTO_PADDED_INTERMEDIATE_TAG || proto_type == 2 || proto_type == 3);

    if (!is_abridged && !is_intermediate) {
        return 0; // Not a framed transport protocol
    }

    while (offset < buf_len && count < max_packets) {
        size_t avail = buf_len - offset;
        size_t packet_len = 0;

        if (is_abridged) {
            if (avail < 1) break;
            uint8_t first = plain_buf[offset];
            if (first == 0x7F || first == 0xFF) {
                if (avail < 4) break;
                uint32_t payload_len = static_cast<uint32_t>(plain_buf[offset + 1])
                    | (static_cast<uint32_t>(plain_buf[offset + 2]) << 8)
                    | (static_cast<uint32_t>(plain_buf[offset + 3]) << 16);
                payload_len *= 4;
                if (payload_len == 0) return -1; // Protocol error
                packet_len = 4 + payload_len;
            } else {
                uint32_t payload_len = static_cast<uint32_t>(first & 0x7F) * 4;
                if (payload_len == 0) return -1; // Protocol error
                packet_len = 1 + payload_len;
            }
        } else { // intermediate
            if (avail < 4) break;
            uint32_t payload_len = *reinterpret_cast<const uint32_t*>(plain_buf + offset) & 0x7FFFFFFF;
            if (payload_len == 0) return -1; // Protocol error
            packet_len = 4 + payload_len;
        }

        if (avail < packet_len) {
            break; // Incomplete packet, wait for more data
        }

        out_offsets[count] = offset;
        out_lengths[count] = packet_len;
        offset += packet_len;
        count++;
    }

    return count;
}

} // extern "C"
