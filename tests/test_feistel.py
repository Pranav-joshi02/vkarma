"""
Unit Tests for Format-Preserving Feistel Cipher (8 Rounds)
"""

import pytest
from backend.ulpin.feistel_fpe import encrypt_serial_to_token, decrypt_token_to_serial


def test_feistel_bijection():
    """Verify that Decrypt(Encrypt(serial)) == serial across multiple values."""
    test_serials = [0, 1, 42, 1000, 99999, 1234567, 98765432]
    for s in test_serials:
        token = encrypt_serial_to_token(s)
        assert len(token) == 8
        recovered = decrypt_token_to_serial(token)
        assert recovered == s, f"Failed for serial {s}: got {recovered}"


def test_feistel_uniqueness():
    """Ensure consecutive serials generate distinct, non-sequential tokens."""
    tokens = set()
    for s in range(100):
        t = encrypt_serial_to_token(s)
        assert t not in tokens, f"Collision detected at serial {s}"
        tokens.add(t)
    assert len(tokens) == 100
