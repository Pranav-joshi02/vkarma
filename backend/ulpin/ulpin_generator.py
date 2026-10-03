"""
3D ULPIN (Unique Land Parcel Identification Number) Engine
Specification Format: PPPPPP-T-RRRRRRRR-C (~17 characters with hyphens)
- PPPPPP: 6-digit Indian postal pincode (the geographic 'bagging' partition key)
- T: 1-character space type code (A, C, S, M, P, U, B, R)
- RRRRRRRR: 8-character format-preserving Feistel token (non-sequential, pseudorandom)
- C: 1-digit Verhoeff Dihedral D5 check digit (catches all single errors and transpositions)
"""

from typing import Dict, Any, Optional
from .verhoeff import generate_verhoeff, validate_verhoeff
from .feistel_fpe import encrypt_serial_to_token, decrypt_token_to_serial

SPACE_TYPE_NAMES = {
    'A': 'Apartment / Residential Unit',
    'C': 'Common Corridor / Right of Way',
    'S': 'Staircase & Fire Evacuation Shaft',
    'M': 'Common Amenities / Clubhouse / Terrace',
    'P': 'Parking Bay (Basement / Surface / Stilt)',
    'U': 'Utility Line / Subsurface Infrastructure',
    'B': 'Standalone Building Envelope',
    'R': 'Air-Rights / Vertical Sky Envelope'
}


class ULPINResult:
    def __init__(self, ulpin: str, pincode: str, space_type: str, token: str, check_digit: str, internal_serial: int):
        self.ulpin = ulpin
        self.pincode = pincode
        self.space_type = space_type
        self.space_type_name = SPACE_TYPE_NAMES.get(space_type, "Unknown")
        self.token = token
        self.check_digit = check_digit
        self.internal_serial = internal_serial

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ulpin": self.ulpin,
            "pincode": self.pincode,
            "space_type": self.space_type,
            "space_type_name": self.space_type_name,
            "token": self.token,
            "check_digit": self.check_digit,
            "internal_serial": self.internal_serial,
            "is_valid": True
        }


def generate_3d_ulpin(pincode: str, space_type: str, serial: int) -> ULPINResult:
    """
    Generates a cryptographically secure, tamper-checked 3D ULPIN.
    """
    pincode = str(pincode).strip().zfill(6)
    if len(pincode) != 6 or not pincode.isdigit():
        raise ValueError(f"Invalid pincode '{pincode}'. Must be 6 digits.")

    space_type = space_type.upper().strip()
    if space_type not in SPACE_TYPE_NAMES:
        raise ValueError(f"Invalid space type '{space_type}'. Valid: {list(SPACE_TYPE_NAMES.keys())}")

    token = encrypt_serial_to_token(serial)
    raw_body = f"{pincode}-{space_type}-{token}"
    check_digit = generate_verhoeff(raw_body)
    full_ulpin = f"{raw_body}-{check_digit}"

    return ULPINResult(
        ulpin=full_ulpin,
        pincode=pincode,
        space_type=space_type,
        token=token,
        check_digit=check_digit,
        internal_serial=serial
    )


def parse_and_validate_ulpin(ulpin_str: str) -> Dict[str, Any]:
    """
    Parses and verifies a 3D ULPIN. Checks syntax, Verhoeff tamper check,
    and reverses the Feistel token to recover the internal serial.
    """
    clean = ulpin_str.strip().upper()
    parts = clean.split('-')
    if len(parts) != 4:
        return {
            "is_valid": False,
            "error": f"Invalid format: Expected 4 hyphen-separated parts (PPPPPP-T-RRRRRRRR-C), got {len(parts)} parts."
        }

    pincode, space_type, token, check_digit = parts

    if len(pincode) != 6 or not pincode.isdigit():
        return {"is_valid": False, "error": f"Invalid pincode '{pincode}'"}

    if space_type not in SPACE_TYPE_NAMES:
        return {"is_valid": False, "error": f"Unknown space type code '{space_type}'"}

    if len(token) != 8:
        return {"is_valid": False, "error": f"Invalid token length '{token}' (expected 8 characters)"}

    raw_body = f"{pincode}-{space_type}-{token}"
    if not validate_verhoeff(raw_body, check_digit):
        return {
            "is_valid": False,
            "error": "Tamper detected: Verhoeff check digit does not match body.",
            "expected_check_digit": generate_verhoeff(raw_body),
            "provided_check_digit": check_digit
        }

    try:
        serial = decrypt_token_to_serial(token)
    except Exception as e:
        return {"is_valid": False, "error": f"Token decryption error: {str(e)}"}

    return {
        "is_valid": True,
        "ulpin": clean,
        "pincode": pincode,
        "space_type": space_type,
        "space_type_name": SPACE_TYPE_NAMES.get(space_type, "Unknown"),
        "token": token,
        "check_digit": check_digit,
        "internal_serial": serial
    }
