"""
Format-Preserving Encryption (FPE) using an 8-Round Balanced Feistel Network.
Encrypts an integer serial ID into an 8-character base-34 token (RRRRRRRR)
and decrypts it back bijectively without collisions or sequential enumeration.
"""

import hmac
import hashlib
from typing import Tuple

ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # 34 chars (omits confusing I & O)
RADIX = len(ALPHABET)
HALF_LEN = 4
DOMAIN_SIZE = RADIX ** HALF_LEN  # 34^4 = 1,336,336
TOTAL_DOMAIN = DOMAIN_SIZE * DOMAIN_SIZE  # ~1.78 * 10^12

DEFAULT_KEY = b"BHU_AADHAAR_3D_CADASTRAL_FPE_SALT_V1"


def _round_function(half_val: int, round_idx: int, key: bytes) -> int:
    """
    Cryptographic pseudo-random round function F using HMAC-SHA256.
    """
    msg = f"{round_idx}:{half_val}".encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    num = int.from_bytes(digest[:8], byteorder="big")
    return num % DOMAIN_SIZE


def _feistel_encrypt(l: int, r: int, rounds: int = 8, key: bytes = DEFAULT_KEY) -> Tuple[int, int]:
    """
    Standard balanced Feistel encryption:
    L_{i+1} = R_i
    R_{i+1} = (L_i + F(R_i, i)) mod DOMAIN_SIZE
    """
    for i in range(rounds):
        f_val = _round_function(r, i, key)
        new_r = (l + f_val) % DOMAIN_SIZE
        new_l = r
        l, r = new_l, new_r
    return l, r


def _feistel_decrypt(l: int, r: int, rounds: int = 8, key: bytes = DEFAULT_KEY) -> Tuple[int, int]:
    """
    Standard balanced Feistel decryption:
    Inverse of the encryption round:
    R_i = L_{i+1}
    L_i = (R_{i+1} - F(L_{i+1}, i)) mod DOMAIN_SIZE
    """
    for i in reversed(range(rounds)):
        prev_r = l
        prev_l = (r - _round_function(l, i, key) + DOMAIN_SIZE) % DOMAIN_SIZE
        l, r = prev_l, prev_r
    return l, r


def _int_to_base34(val: int, length: int) -> str:
    res = []
    for _ in range(length):
        res.append(ALPHABET[val % RADIX])
        val //= RADIX
    return "".join(reversed(res))


def _base34_to_int(text: str) -> int:
    val = 0
    for ch in text.upper():
        idx = ALPHABET.index(ch)
        val = val * RADIX + idx
    return val


def encrypt_serial_to_token(serial: int, key: bytes = DEFAULT_KEY) -> str:
    """
    Maps an integer serial (e.g., 1042) to an 8-character pseudorandom token.
    """
    serial = serial % TOTAL_DOMAIN
    l_init = serial // DOMAIN_SIZE
    r_init = serial % DOMAIN_SIZE
    l_enc, r_enc = _feistel_encrypt(l_init, r_init, rounds=8, key=key)
    return _int_to_base34(l_enc, HALF_LEN) + _int_to_base34(r_enc, HALF_LEN)


def decrypt_token_to_serial(token: str, key: bytes = DEFAULT_KEY) -> int:
    """
    Inverses the 8-character token back to the internal integer serial.
    """
    token = token.upper().replace("-", "").replace(" ", "")
    if len(token) != 8:
        raise ValueError(f"Expected 8-character token, got '{token}' ({len(token)})")
    l_enc = _base34_to_int(token[:4])
    r_enc = _base34_to_int(token[4:])
    l_orig, r_orig = _feistel_decrypt(l_enc, r_enc, rounds=8, key=key)
    return l_orig * DOMAIN_SIZE + r_orig
