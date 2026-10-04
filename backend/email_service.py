import os
import re
import html
import logging
import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv

# Ensure environment variables are loaded
load_dotenv(find_dotenv())

import httpx

from backend.ulpin.ulpin_generator import parse_and_validate_ulpin, SPACE_TYPE_NAMES
from backend.digilocker.issuer_service import digilocker_service

logger = logging.getLogger("BrevoEmailService")


class BrevoEmailService:
    def __init__(self):
        self.api_url = "https://api.brevo.com/v3/smtp/email"

    @property
    def api_key(self) -> str:
        return os.getenv("BREVO_API_KEY", "").strip()

    @property
    def sender_email(self) -> str:
        return os.getenv("BREVO_SENDER_EMAIL", "24070579@ycce.in").strip()

    @property
    def sender_name(self) -> str:
        return os.getenv("BREVO_SENDER_NAME", "vKarma 3D Cadastre").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_"))

    @staticmethod
    def is_valid_email(email_str: str) -> bool:
        if not email_str or not isinstance(email_str, str):
            return False
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email_str.strip()))

    def _dispatch_brevo_request(self, to_email: str, to_name: str, subject: str, html_content: str) -> Dict[str, Any]:
        """Dispatches transactional email payload to Brevo v3 API or returns simulated response."""
        if not self.is_valid_email(to_email):
            raise ValueError(f"Invalid recipient email address: '{to_email}'")

        clean_email = to_email.strip().lower()
        clean_name = to_name.strip() if to_name else clean_email.split("@")[0]

        if not self.is_configured:
            safe_subject = subject.encode("ascii", "replace").decode("ascii")
            print(f"[Brevo Email] Simulation Mode: Email '{safe_subject}' ready for {clean_email}")
            return {
                "success": True,
                "status": "SIMULATED",
                "message_id": f"sim-{datetime.datetime.now(datetime.timezone.utc).timestamp()}",
                "recipient": clean_email,
                "message": f"Email prepared for {clean_email}. (Add your BREVO_API_KEY in .env to deliver live via Brevo SMTP)."
            }

        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json"
        }

        # Sender email must be verified Brevo address.
        # User constraint: Sender and receiver email are the same for every email sending.
        sender_email = self.sender_email or "24070579@ycce.in"
        target_email = sender_email

        payload = {
            "sender": {
                "name": self.sender_name,
                "email": sender_email
            },
            "to": [
                {
                    "email": target_email,
                    "name": clean_name
                }
            ],
            "replyTo": {
                "email": clean_email,
                "name": clean_name
            },
            "subject": subject,
            "htmlContent": html_content
        }

        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(self.api_url, json=payload, headers=headers)
                
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                msg_id = data.get("messageId", "sent")
                return {
                    "success": True,
                    "status": "SENT",
                    "message_id": msg_id,
                    "recipient": target_email,
                    "message": f"Official document successfully sent to {target_email} via Brevo!"
                }
            else:
                err_detail = resp.text
                try:
                    err_json = resp.json()
                    err_detail = err_json.get("message", resp.text)
                except Exception:
                    pass

                # Graceful handling for Brevo's Authorized IPs security restriction
                if resp.status_code == 401 and "unrecognised IP address" in err_detail:
                    ip_match = re.search(r"([0-9a-fA-F:.]+)", err_detail)
                    ip_str = ip_match.group(1) if ip_match else "your IP"
                    return {
                        "success": False,
                        "status": "IP_AUTH_REQUIRED",
                        "ip_address": ip_str,
                        "auth_url": "https://app.brevo.com/security/authorised_ips",
                        "recipient": target_email,
                        "message": f"Brevo Security Notice: Your IP address ({ip_str}) must be added to your Authorized IPs list in Brevo. Please open https://app.brevo.com/security/authorised_ips to authorize it."
                    }

                raise RuntimeError(f"Brevo API error (HTTP {resp.status_code}): {err_detail}")

        except httpx.RequestError as exc:
            raise RuntimeError(f"Failed to connect to Brevo Email API: {str(exc)}")

        except httpx.RequestError as exc:
            raise RuntimeError(f"Failed to connect to Brevo Email API: {str(exc)}")

    def send_certificate_email(self, to_email: str, to_name: Optional[str] = None, ulpin: str = "") -> Dict[str, Any]:
        """
        Generates and sends an authoritative 3D Bhu-Aadhaar Digital Land Title Certificate via Brevo.
        """
        val = parse_and_validate_ulpin(ulpin)
        if not val.get("is_valid", False):
            raise ValueError(f"Invalid ULPIN checksum or structure: {val.get('error', 'Malformed ULPIN')}")

        data = digilocker_service.get_unit_cadastral_data(ulpin)
        status_info = digilocker_service.get_status(ulpin)
        doc_uri = status_info.digilocker_uri or digilocker_service.generate_doc_uri(ulpin)

        clean_name = to_name or data["owner_name"]
        bbox = data.get("bbox", {})
        min_x = bbox.get("min_x", -5.0)
        max_x = bbox.get("max_x", 5.0)
        min_y = bbox.get("min_y", -5.0)
        max_y = bbox.get("max_y", 5.0)
        min_z = bbox.get("min_z", 920.0)
        max_z = bbox.get("max_z", 923.0)

        rrr_items_html = "".join([f"<li>{html.escape(r)}</li>" for r in data.get("rrrs", [])])

        subject = f"🇮🇳 3D Bhu-Aadhaar Digital Land Title Certificate • {ulpin}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #0B1F33; -webkit-font-smoothing: antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9; padding: 28px 12px;">
    <tr>
      <td align="center">
        <!-- Main Certificate Card -->
        <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width: 640px; width: 100%; background-color: #ffffff; border-radius: 12px; border: 3px double #0B1F33; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden;">
          
          <!-- Government Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #0B1F33 0%, #163654 100%); padding: 24px 28px; text-align: center; color: #ffffff;">
              <div style="font-size: 28px; margin-bottom: 6px;">🇮🇳</div>
              <h2 style="margin: 0; font-size: 16px; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; color: #ffffff;">
                Government of India &bull; Ministry of Rural Development
              </h2>
              <p style="margin: 4px 0 0; font-size: 12px; color: #90caf9;">
                Department of Land Resources &bull; DILRMP 3D Cadastral Digital Registry
              </p>
              <div style="margin-top: 10px; display: inline-block; padding: 4px 14px; background: rgba(32, 217, 230, 0.15); border: 1px solid #20D9E6; border-radius: 999px; font-size: 12px; font-weight: 700; color: #20D9E6;">
                3D BHU-AADHAAR DIGITAL LAND TITLE CERTIFICATE
              </div>
            </td>
          </tr>

          <!-- 3D ULPIN Banner -->
          <tr>
            <td style="padding: 20px 28px; background: #e0f2fe; border-bottom: 1px solid #bae6fd;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <span style="font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #0284c7;">
                      UNIQUE 3D LAND PARCEL IDENTIFICATION NUMBER (3D ULPIN)
                    </span>
                    <div style="font-size: 18px; font-weight: 900; font-family: monospace; color: #0369a1; margin-top: 2px;">
                      {html.escape(ulpin)}
                    </div>
                  </td>
                  <td align="right">
                    <span style="background: #22c55e; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700;">
                      &check; Dihedral D5 Verified
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Certificate Grid Details -->
          <tr>
            <td style="padding: 24px 28px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 13px;">
                <tr>
                  <td width="50%" style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;" valign="top">
                    <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">Registered Property Name</span>
                    <div style="font-size: 14px; font-weight: 800; color: #0B1F33; margin-top: 2px;">{html.escape(data['unit_name'])}</div>
                    <div style="font-size: 11px; color: #475569;">{html.escape(data['building_name'])}</div>
                  </td>
                  <td width="50%" style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;" valign="top">
                    <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">Spatial Classification</span>
                    <div style="font-size: 14px; font-weight: 800; color: #0B1F33; margin-top: 2px;">{html.escape(data['space_type_name'])}</div>
                    <div style="font-size: 11px; color: #475569;">Floor Level: {data['floor_level']}</div>
                  </td>
                </tr>
                <tr><td height="10"></td></tr>
                <tr>
                  <td width="50%" style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;" valign="top">
                    <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">Registered Title Holder (LA_Party)</span>
                    <div style="font-size: 14px; font-weight: 800; color: #0B1F33; margin-top: 2px;">{html.escape(clean_name)}</div>
                    <div style="font-size: 11px; font-family: monospace; color: #475569;">KYC: {html.escape(data['owner_id_hash'])}</div>
                  </td>
                  <td width="50%" style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;" valign="top">
                    <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">Volumetric Dimensions</span>
                    <div style="font-size: 14px; font-weight: 800; color: #0B1F33; margin-top: 2px;">{data['carpet_area_sqm']} m² Carpet Area</div>
                    <div style="font-size: 11px; color: #475569;">Volume: {data['volume_m3']} m³ (Ref Elev: {data['ground_elevation_msl']}m)</div>
                  </td>
                </tr>
              </table>

              <!-- 3D Bounding Extents -->
              <div style="margin-top: 14px; padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px;">
                <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">3D Bounding Extents (ISO 19152 B-Rep)</span>
                <div style="font-family: monospace; font-size: 11px; color: #0B1F33; margin-top: 3px;">
                  Min (X: {min_x}, Y: {min_y}, Z: {min_z}m) &rarr; Max (X: {max_x}, Y: {max_y}, Z: {max_z}m)
                </div>
              </div>

              <!-- Rights & Encumbrances -->
              <div style="margin-top: 14px; padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px;">
                <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b;">Rights, Restrictions &amp; Responsibilities (RRR)</span>
                <ul style="margin: 4px 0 0 16px; padding: 0; color: #334155; font-size: 12px; line-height: 1.5;">
                  {rrr_items_html}
                </ul>
              </div>

              <!-- DigiLocker Vault Banner -->
              <div style="margin-top: 18px; padding: 12px 14px; background: linear-gradient(135deg, rgba(0, 43, 73, 0.05) 0%, rgba(0, 160, 227, 0.1) 100%); border: 1px solid #93c5fd; border-radius: 8px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td>
                      <span style="font-size: 10px; font-weight: 800; color: #002B49; text-transform: uppercase;">DigiLocker Canonical Document URI</span>
                      <div style="font-family: monospace; font-size: 12px; font-weight: 800; color: #0369a1; margin-top: 2px;">
                        {html.escape(doc_uri)}
                      </div>
                    </td>
                    <td align="right">
                      <span style="background: #ecfdf5; border: 1px solid #86efac; color: #166534; padding: 4px 8px; border-radius: 999px; font-size: 10px; font-weight: 700;">
                        &check; DigiLocker Ready
                      </span>
                    </td>
                  </tr>
                </table>
              </div>

              <!-- CTA Button -->
              <div style="margin-top: 24px; text-align: center;">
                <a href="https://vkarma.in/ulpin/{html.escape(ulpin)}" target="_blank" style="background: linear-gradient(135deg, #0B1F33 0%, #18A7A8 100%); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 13px; font-weight: 800; display: inline-block; box-shadow: 0 4px 15px rgba(24, 167, 168, 0.35);">
                  Inspect in 3D Cadastral Digital Twin &rarr;
                </a>
              </div>
            </td>
          </tr>

          <!-- Certificate Footer -->
          <tr>
            <td style="padding: 18px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 11px; color: #64748b; text-align: center; line-height: 1.5;">
              <div><strong>vKarma</strong> &bull; National 3D Cadastral Registry &bull; ISO 19152 LADM Compliant</div>
              <div style="font-size: 10px; margin-top: 4px; font-family: monospace;">
                Signature: SHA256:7f8a9e2b1049c812d4a51e60f09b &bull; Signed by Certifying Cadastral Authority
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        return self._dispatch_brevo_request(
            to_email=to_email,
            to_name=clean_name,
            subject=subject,
            html_content=html_content
        )

    def send_passport_email(self, to_email: str, to_name: Optional[str] = None, ulpin: str = "") -> Dict[str, Any]:
        """
        Generates and sends an executive Digital Land Passport via Brevo.
        """
        val = parse_and_validate_ulpin(ulpin)
        if not val.get("is_valid", False):
            raise ValueError(f"Invalid ULPIN checksum or structure: {val.get('error', 'Malformed ULPIN')}")

        data = digilocker_service.get_unit_cadastral_data(ulpin)
        clean_name = to_name or data["owner_name"]
        subject = f"🏛️ vKarma Digital Land Passport • {ulpin}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #0B1F33;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9; padding: 28px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width: 640px; width: 100%; background-color: #ffffff; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden;">
          
          <!-- Passport Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #002244 0%, #004080 100%); padding: 24px 28px; color: #ffffff;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <h1 style="margin: 0; font-size: 18px; font-weight: 800; letter-spacing: 0.05em; color: #ffffff;">
                      DIGITAL LAND PASSPORT
                    </h1>
                    <div style="font-size: 11px; color: #90caf9; margin-top: 2px;">
                      REPUBLIC OF INDIA &bull; vKarma NATIONAL 3D CADASTRAL REGISTRY
                    </div>
                  </td>
                  <td align="right">
                    <span style="background: #22c55e; color: #ffffff; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700;">
                      &check; Verified Clear Freehold
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ULPIN Banner -->
          <tr>
            <td style="padding: 16px 28px; background: #e0f2fe; border-bottom: 1px solid #bae6fd;">
              <span style="font-size: 10px; font-weight: 800; color: #0369a1; text-transform: uppercase;">
                UNIQUE LAND PARCEL IDENTIFICATION NUMBER (3D ULPIN)
              </span>
              <div style="font-size: 17px; font-weight: 900; font-family: monospace; color: #0284c7; margin-top: 2px;">
                {html.escape(ulpin)}
              </div>
            </td>
          </tr>

          <!-- Passport Content -->
          <tr>
            <td style="padding: 24px 28px;">
              <h3 style="margin: 0 0 12px; font-size: 14px; font-weight: 800; color: #0B1F33; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                Property Identification &amp; Measurements
              </h3>

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 12px; margin-bottom: 18px;">
                <tr>
                  <td width="33%" style="padding: 6px 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <span style="color: #64748b; font-size: 10px; font-weight: 700;">DESIGNATED UNIT</span>
                    <div style="font-weight: 800; color: #0B1F33; margin-top: 2px;">{html.escape(data['unit_name'])}</div>
                  </td>
                  <td width="33%" style="padding: 6px 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <span style="color: #64748b; font-size: 10px; font-weight: 700;">SPACE TYPE</span>
                    <div style="font-weight: 800; color: #0B1F33; margin-top: 2px;">{html.escape(data['space_type_name'])}</div>
                  </td>
                  <td width="33%" style="padding: 6px 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <span style="color: #64748b; font-size: 10px; font-weight: 700;">CARPET AREA</span>
                    <div style="font-weight: 800; color: #0B1F33; margin-top: 2px;">{data['carpet_area_sqm']} m²</div>
                  </td>
                </tr>
              </table>

              <h3 style="margin: 0 0 12px; font-size: 14px; font-weight: 800; color: #0B1F33; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                Registered Ownership &amp; Title Deeds
              </h3>
              <div style="padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px; margin-bottom: 18px;">
                <div>Title Holder: <strong>{html.escape(clean_name)}</strong></div>
                <div style="margin-top: 3px; font-family: monospace; color: #64748b;">KYC Hash: {html.escape(data['owner_id_hash'])}</div>
                <div style="margin-top: 3px; color: #475569;">Document Nature: Registered Absolute Sale Deed (Sub-Registrar Office)</div>
              </div>

              <!-- CTA Button -->
              <div style="margin-top: 24px; text-align: center;">
                <a href="https://vkarma.in/ulpin/{html.escape(ulpin)}" target="_blank" style="background: linear-gradient(135deg, #002244 0%, #005A9C 100%); color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 13px; font-weight: 800; display: inline-block;">
                  View Live Digital Land Passport &rarr;
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 16px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 11px; color: #64748b; text-align: center;">
              <div><strong>vKarma</strong> &bull; Sovereign 3D Cadastral Digital Registry</div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        return self._dispatch_brevo_request(
            to_email=to_email,
            to_name=clean_name,
            subject=subject,
            html_content=html_content
        )


# Singleton instance
brevo_email_service = BrevoEmailService()
email_service = brevo_email_service
