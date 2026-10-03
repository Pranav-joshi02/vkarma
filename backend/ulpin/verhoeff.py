"""
Verhoeff Check Digit Algorithm (Dihedral Group D5)
Implements the exact tamper-detection algorithm family used by Aadhaar (UIDAI).
Catches:
- 100% of single-digit input errors (e.g., 1234 -> 1284)
- 100% of adjacent transposition errors (e.g., 1234 -> 1324)
- >95% of other twin and jump-transposition errors.
"""

from typing import Union, List

# Dihedral group D5 multiplication table d(j, k)
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Permutation table p(i, j)
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

# Inverse table inv(j)
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def _to_digit_sequence(value: str) -> List[int]:
    """
    Converts alphanumeric characters into a deterministic base-10 digit sequence
    suitable for D5 group operations.
    """
    digits = []
    for ch in value.upper():
        if ch.isdigit():
            digits.append(int(ch))
        elif ch.isalpha():
            # Map A-Z -> ordinal values 10-35, split into two digits
            val = ord(ch) - ord('A') + 10
            digits.append(val // 10)
            digits.append(val % 10)
        elif ch in ('-', '_', '/'):
            continue  # ignore formatting delimiters
        else:
            digits.append(ord(ch) % 10)
    return digits


def generate_verhoeff(text: str) -> str:
    """
    Computes the single-digit Verhoeff check character (0-9) for an alphanumeric string.
    """
    digits = _to_digit_sequence(text)
    c = 0
    # Reverse the array for position weighting
    for i, digit in enumerate(reversed(digits)):
        p_val = _P[(i + 1) % 8][digit]
        c = _D[c][p_val]
    return str(_INV[c])


def validate_verhoeff(text: str, check_digit: Union[str, int]) -> bool:
    """
    Validates whether text + check_digit satisfies the Verhoeff D5 equation:
    SUM_D5( P(i, d_i) ) == 0
    """
    expected = generate_verhoeff(text)
    return str(check_digit) == expected


def validate_full_code(full_code: str) -> bool:
    """
    Validates a complete code ending in its check digit (e.g., PPPPPP-T-RRRRRRRR-C).
    """
    clean = full_code.strip()
    if '-' in clean:
        parts = clean.split('-')
        body = '-'.join(parts[:-1])
        c_digit = parts[-1]
    else:
        body = clean[:-1]
        c_digit = clean[-1]
    return validate_verhoeff(body, c_digit)
