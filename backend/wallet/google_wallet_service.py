"""
vKarma Google Wallet Integration Service
Issues official Google Wallet Generic Passes for 3D Bhu-Aadhaar Land Passports.
Citizens can save their 3D land title credentials directly into Google Wallet on Android / Wear OS / Web.
"""

import os
import json
import time
import logging
import urllib.request
import urllib.parse
import urllib.error
import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv

# Ensure environment variables are loaded
load_dotenv(find_dotenv())

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.ulpin.ulpin_generator import parse_and_validate_ulpin, SPACE_TYPE_NAMES
from backend.digilocker.issuer_service import digilocker_service

logger = logging.getLogger("GoogleWalletService")


class GoogleWalletService:
    def __init__(self):
        self.class_suffix = "vkarma_3d_land_passport_class"

    @property
    def issuer_id(self) -> str:
        return os.getenv("GOOGLE_WALLET_ISSUER_ID", "3388000000022345678").strip()

    def _get_service_account_dict(self) -> Dict[str, Any]:
        """Resolves Google Service Account credentials from env var JSON, key file, or project root."""
        # 1. Direct JSON string from environment variable (ideal for cloud platforms like Render/Railway)
        sa_json_env = os.getenv("GOOGLE_WALLET_SERVICE_ACCOUNT_JSON", "").strip()
        if sa_json_env and sa_json_env.startswith("{"):
            try:
                return json.loads(sa_json_env)
            except Exception:
                pass

        # 2. File path from GOOGLE_WALLET_KEY_FILE or fallback to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        key_file = os.getenv("GOOGLE_WALLET_KEY_FILE", "").strip()
        candidates = []
        if key_file:
            candidates.append(key_file)
            if not os.path.isabs(key_file):
                candidates.append(os.path.join(project_root, key_file))
                candidates.append(os.path.join(os.getcwd(), key_file))
        candidates.append(os.path.join(project_root, "vkarma-wallet-d0c9502a0925.json"))
        candidates.append(os.path.join(os.getcwd(), "vkarma-wallet-d0c9502a0925.json"))

        for path in candidates:
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content.startswith("{"):
                            return json.loads(content)
                except Exception:
                    pass
        return {}

    @property
    def service_account_email(self) -> str:
        override = os.getenv("GOOGLE_WALLET_SA_EMAIL", "").strip()
        if override:
            return override
        sa_dict = self._get_service_account_dict()
        if sa_dict.get("client_email"):
            return sa_dict["client_email"]
        return "vkarma-wallet@vkarma-cadastre.iam.gserviceaccount.com"

    @property
    def private_key_raw(self) -> str:
        """Returns PEM formatted private key if provided in environment or file."""
        key_env = os.getenv("GOOGLE_WALLET_PRIVATE_KEY", "").strip()
        if key_env:
            return key_env.replace("\\n", "\n")

        sa_dict = self._get_service_account_dict()
        if sa_dict.get("private_key"):
            return sa_dict["private_key"]

        key_file = os.getenv("GOOGLE_WALLET_KEY_FILE", "").strip()
        if key_file and os.path.exists(key_file):
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip().startswith("{"):
                        data = json.loads(content)
                        return data.get("private_key", "")
                    return content
            except Exception:
                pass
        return ""

    @property
    def is_live_configured(self) -> bool:
        """Checks if real Google Cloud Service Account credentials are provided."""
        return bool(self.private_key_raw and "PRIVATE KEY" in self.private_key_raw)

    def get_class_id(self) -> str:
        return f"{self.issuer_id}.{self.class_suffix}"

    def get_oauth_token(self) -> Optional[str]:
        """Generates an OAuth2 access token for the Google Wallet REST API."""
        if not self.is_live_configured:
            return None
        try:
            now = int(time.time())
            claim = {
                "iss": self.service_account_email,
                "scope": "https://www.googleapis.com/auth/wallet_object.issuer",
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now,
                "exp": now + 3600
            }
            grant_jwt = jwt.encode(claim, self.private_key_raw, algorithm="RS256")
            req = urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=urllib.parse.urlencode({
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": grant_jwt
                }).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
            return resp.get("access_token")
        except Exception as e:
            logger.warning(f"Could not obtain Google Wallet OAuth2 token: {e}")
            return None

    def ensure_class_exists(self, token: str) -> bool:
        """Ensures the genericClass exists on Google Wallet."""
        class_id = self.get_class_id()
        try:
            req = urllib.request.Request(
                f"https://walletobjects.googleapis.com/walletobjects/v1/genericClass/{class_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                try:
                    gclass = self.build_generic_class()
                    insert_req = urllib.request.Request(
                        "https://walletobjects.googleapis.com/walletobjects/v1/genericClass",
                        data=json.dumps(gclass).encode("utf-8"),
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                    )
                    urllib.request.urlopen(insert_req, timeout=10)
                    return True
                except Exception as insert_err:
                    logger.error(f"Error creating genericClass: {insert_err}")
                    return False
            logger.warning(f"Error checking genericClass: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error checking genericClass: {e}")
            return False

    def upsert_generic_object(self, generic_object: Dict[str, Any], token: str) -> bool:
        """Inserts or updates the genericObject via Google Wallet REST API."""
        obj_id = generic_object["id"]
        try:
            insert_req = urllib.request.Request(
                "https://walletobjects.googleapis.com/walletobjects/v1/genericObject",
                data=json.dumps(generic_object).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            urllib.request.urlopen(insert_req, timeout=10)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 409:  # Already exists, update it via PUT
                try:
                    update_req = urllib.request.Request(
                        f"https://walletobjects.googleapis.com/walletobjects/v1/genericObject/{obj_id}",
                        data=json.dumps(generic_object).encode("utf-8"),
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        },
                        method="PUT"
                    )
                    urllib.request.urlopen(update_req, timeout=10)
                    return True
                except Exception:
                    return True
            logger.warning(f"Notice during genericObject upsert: {e}")
            return False
        except Exception as e:
            logger.warning(f"Notice during genericObject upsert: {e}")
            return False

    def get_object_id(self, ulpin: str) -> str:
        clean = ulpin.replace("-", "_").replace(" ", "_")
        return f"{self.issuer_id}.bhu_{clean}"

    def build_generic_class(self) -> Dict[str, Any]:
        """Constructs the standard Google Wallet GenericClass for 3D Land Passports."""
        return {
            "id": self.get_class_id(),
            "issuerName": "vKarma 3D Cadastral Digital Registry",
            "reviewStatus": "UNDER_REVIEW",
            "classTemplateInfo": {}
        }

    def build_generic_object(self, ulpin: str, recipient_name: Optional[str] = None) -> Dict[str, Any]:
        """Constructs the Google Wallet GenericObject for a specific 3D parcel."""
        val = parse_and_validate_ulpin(ulpin)
        if not val.get("is_valid", False):
            raise ValueError(f"Invalid ULPIN checksum or structure: {val.get('error', 'Malformed ULPIN')}")

        data = digilocker_service.get_unit_cadastral_data(ulpin)
        owner_name = recipient_name or data.get("owner_name", "Citizen Owner")
        space_type = val.get("space_type", "A")
        space_type_name = val.get("space_type_name", SPACE_TYPE_NAMES.get(space_type, "3D Volumetric Space"))

        bbox = data.get("bbox", {})
        min_x = bbox.get("min_x", -5.0)
        max_x = bbox.get("max_x", 5.0)
        min_y = bbox.get("min_y", -5.0)
        max_y = bbox.get("max_y", 5.0)
        min_z = bbox.get("min_z", 920.0)
        max_z = bbox.get("max_z", 923.0)

        carpet_area = round((max_x - min_x) * (max_y - min_y), 2) if (max_x > min_x and max_y > min_y) else 85.0
        volume = round(carpet_area * (max_z - min_z), 2) if max_z > min_z else round(carpet_area * 3.0, 2)
        floor = data.get("floor_number", 1)

        object_id = self.get_object_id(ulpin)
        portal_url = f"https://vkarma.in/ulpin/{ulpin}"

        return {
            "id": object_id,
            "classId": self.get_class_id(),
            "state": "ACTIVE",
            "cardTitle": {
                "defaultValue": {
                    "language": "en-US",
                    "value": "vKarma • 3D Bhu-Aadhaar"
                }
            },
            "header": {
                "defaultValue": {
                    "language": "en-US",
                    "value": ulpin
                }
            },
            "subheader": {
                "defaultValue": {
                    "language": "en-US",
                    "value": owner_name
                }
            },
            "hexBackgroundColor": "#002244",
            "logo": {
                "sourceUri": {
                    "uri": "https://raw.githubusercontent.com/google/material-design-icons/master/png/action/account_balance/materialicons/48dp/2x/baseline_account_balance_black_48dp.png"
                },
                "contentDescription": {
                    "defaultValue": {
                        "language": "en-US",
                        "value": "vKarma 3D Cadastral Authority"
                    }
                }
            },
            "barcode": {
                "type": "QR_CODE",
                "value": portal_url,
                "alternateText": ulpin
            },
            "textModulesData": [
                {
                    "id": "owner_name",
                    "header": "TITLE HOLDER",
                    "body": owner_name
                },
                {
                    "id": "space_type",
                    "header": "SPACE TYPE",
                    "body": f"{space_type_name} ({space_type})"
                },
                {
                    "id": "floor_level",
                    "header": "FLOOR LEVEL",
                    "body": f"Level {floor}"
                },
                {
                    "id": "carpet_area",
                    "header": "CARPET AREA",
                    "body": f"{carpet_area} m²"
                },
                {
                    "id": "volume",
                    "header": "VOLUMETRIC EXTENT",
                    "body": f"{volume} m³"
                },
                {
                    "id": "z_bounds",
                    "header": "3D ELEVATION (Z)",
                    "body": f"{min_z:.1f}m - {max_z:.1f}m MSL"
                },
                {
                    "id": "iso_standard",
                    "header": "CADASTRAL STANDARD",
                    "body": "ISO 19152 LADM / Verhoeff D5"
                },
                {
                    "id": "legal_jurisdiction",
                    "header": "JURISDICTION",
                    "body": "Republic of India • DoLR DILRMP"
                }
            ],
            "linksModuleData": {
                "uris": [
                    {
                        "uri": portal_url,
                        "description": "View Live 3D Cadastral Digital Twin",
                        "id": "view_3d_twin"
                    },
                    {
                        "uri": f"https://vkarma.in/certificate/{ulpin}",
                        "description": "Download Official DigiLocker XML Title",
                        "id": "verify_certificate"
                    }
                ]
            }
        }

    def generate_signed_jwt(
        self,
        generic_class: Dict[str, Any],
        generic_object: Dict[str, Any],
        origin: Optional[str] = None
    ) -> str:
        """
        Creates and signs the Google Wallet JWT.
        Uses live RS256 private key when configured, or generates an RSA key pair for testing/sandbox.
        """
        now = int(time.time())

        # If live credentials exist, ensure class exists and pre-insert object via REST API
        if self.is_live_configured:
            token = self.get_oauth_token()
            if token:
                self.ensure_class_exists(token)
                self.upsert_generic_object(generic_object, token)

        # Build list of authorized origins to satisfy Google Wallet security validation
        origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost",
            "http://127.0.0.1",
            "https://vkarma.in",
            "http://vkarma.in",
            "https://pay.google.com",
            "https://wallet.google.com"
        ]
        for env_key in ("PUBLIC_URL", "APP_URL", "RENDER_EXTERNAL_URL"):
            val = os.getenv(env_key, "").strip()
            if val and val not in origins:
                origins.append(val)
        if origin and origin.strip() and origin.strip() not in origins:
            origins.append(origin.strip())

        # Compact representation with core presentation fields required by Google Wallet Web renderer
        compact_obj = {
            "id": generic_object["id"],
            "classId": generic_object["classId"],
            "cardTitle": generic_object.get("cardTitle"),
            "header": generic_object.get("header"),
            "subheader": generic_object.get("subheader"),
            "logo": generic_object.get("logo"),
            "barcode": generic_object.get("barcode"),
            "hexBackgroundColor": generic_object.get("hexBackgroundColor", "#002244")
        }

        claims = {
            "iss": self.service_account_email,
            "aud": "google",
            "origins": origins,
            "typ": "savetowallet",
            "iat": now,
            "payload": {
                "genericClasses": [generic_class],
                "genericObjects": [generic_object]
            }
        }

        if self.is_live_configured:
            signed_jwt = jwt.encode(claims, self.private_key_raw, algorithm="RS256")
            return signed_jwt
        else:
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pem_key = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode("utf-8")
            signed_jwt = jwt.encode(claims, pem_key, algorithm="RS256")
            return signed_jwt

    def create_google_wallet_pass(
        self,
        ulpin: str,
        recipient_name: Optional[str] = None,
        origin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full workflow: builds Class & Object, signs JWT, and returns official Google Wallet Save URL.
        """
        generic_class = self.build_generic_class()
        generic_object = self.build_generic_object(ulpin=ulpin, recipient_name=recipient_name)
        signed_token = self.generate_signed_jwt(generic_class, generic_object, origin=origin)

        save_url = f"https://pay.google.com/gp/v/save/{signed_token}"

        return {
            "success": True,
            "status": "LIVE" if self.is_live_configured else "SANDBOX",
            "ulpin": ulpin,
            "owner_name": generic_object["subheader"]["defaultValue"]["value"],
            "save_url": save_url,
            "jwt": signed_token,
            "pass_object": generic_object,
            "pass_class": generic_class,
            "message": "Google Wallet 3D Land Passport generated successfully."
        }


# Singleton instance
google_wallet_service = GoogleWalletService()
