"""
Unit Tests for Verhoeff Dihedral D5 Tamper Detection
"""

import pytest
from backend.ulpin.verhoeff import generate_verhoeff, validate_verhoeff, validate_full_code


def test_verhoeff_generation():
    check = generate_verhoeff("560103-A-5ZS90BBJ")
    assert isinstance(check, str)
    assert len(check) == 1
    assert check.isdigit()


def test_verhoeff_validation():
    base = "560103-A-5ZS90BBJ"
    check = generate_verhoeff(base)
    assert validate_verhoeff(base, check) is True
    assert validate_full_code(f"{base}-{check}") is True


def test_verhoeff_catches_single_digit_substitution():
    base = "560103-A-5ZS90BBJ"
    check = generate_verhoeff(base)
    # Tamper one character in base
    corrupt_base = "560104-A-5ZS90BBJ"
    assert validate_verhoeff(corrupt_base, check) is False


def test_verhoeff_catches_transposition():
    base = "123456"
    check = generate_verhoeff(base)
    # Transpose 23 -> 32
    transposed = "132456"
    assert validate_verhoeff(transposed, check) is False
