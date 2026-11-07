import os
import sys
import ctypes
from typing import List, Tuple, Optional

_dll = None
_ws_mask_inplace = None
_ws_mask_copy = None
_mtproto_find_packets = None

try:
    current_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(current_dir, "bin", "tgws_accel.dll"),
        os.path.join(current_dir, "tgws_accel.dll"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "tgws_accel.dll")
    ]
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, "bin", "tgws_accel.dll"))
        candidates.append(os.path.join(sys._MEIPASS, "tgws_accel.dll"))
    for cand in candidates:
        if os.path.exists(cand):
            _dll = ctypes.CDLL(cand)
            break
except Exception as e:
    _dll = None

if _dll is not None:
    try:
        # void ws_mask_inplace(uint8_t* data, size_t len, uint32_t mask)
        _ws_mask_inplace = _dll.ws_mask_inplace
        _ws_mask_inplace.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint32]
        _ws_mask_inplace.restype = None

        # void ws_mask_copy(const uint8_t* src, uint8_t* dst, size_t len, uint32_t mask)
        _ws_mask_copy = _dll.ws_mask_copy
        _ws_mask_copy.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint32]
        _ws_mask_copy.restype = None

        # int mtproto_find_packets(...)
        _mtproto_find_packets = _dll.mtproto_find_packets
        _mtproto_find_packets.argtypes = [
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.c_int
        ]
        _mtproto_find_packets.restype = ctypes.c_int
        
        ACCEL_AVAILABLE = True
    except Exception:
        ACCEL_AVAILABLE = False
else:
    ACCEL_AVAILABLE = False


def fast_mask(mask: bytes, data: bytes) -> bytes:
    """Mask or unmask bytes using SIMD (AVX2/64-bit) C++ acceleration."""
    if not data:
        return data
    if not ACCEL_AVAILABLE:
        n = len(data)
        mask_rep = (mask * (n // 4 + 1))[:n]
        return (int.from_bytes(data, 'big') ^ int.from_bytes(mask_rep, 'big')).to_bytes(n, 'big')

    n = len(data)
    mask_u32 = int.from_bytes(mask, 'little')
    out = ctypes.create_string_buffer(n)
    _ws_mask_copy(data, out, n, mask_u32)
    return out.raw


def fast_mask_inplace(buf: bytearray, mask: bytes) -> None:
    """Mask or unmask bytearray in-place without memory allocation."""
    if not buf or not ACCEL_AVAILABLE:
        return
    n = len(buf)
    mask_u32 = int.from_bytes(mask, 'little')
    ptr = (ctypes.c_char * n).from_buffer(buf)
    _ws_mask_inplace(ptr, n, mask_u32)


_MAX_BATCH_PACKETS = 64
_out_offsets = (ctypes.c_size_t * _MAX_BATCH_PACKETS)()
_out_lengths = (ctypes.c_size_t * _MAX_BATCH_PACKETS)()

def fast_find_packets(proto_type: int, plain_buf: bytearray, start_offset: int) -> Tuple[int, List[Tuple[int, int]]]:
    """Scan bytearray for MTProto packet boundaries.
    Returns (count, list of (offset, length)). Count is -1 on protocol error."""
    if not ACCEL_AVAILABLE:
        return 0, []

    buf_len = len(plain_buf)
    if buf_len <= start_offset:
        return 0, []

    ptr = (ctypes.c_char * buf_len).from_buffer(plain_buf)
    count = _mtproto_find_packets(
        ctypes.c_uint32(proto_type).value,
        ptr,
        buf_len,
        start_offset,
        _out_offsets,
        _out_lengths,
        _MAX_BATCH_PACKETS
    )
    if count <= 0:
        return count, []

    res = [(_out_offsets[i], _out_lengths[i]) for i in range(count)]
    return count, res
