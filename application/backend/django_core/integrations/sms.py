from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Dict, Optional
import uuid
import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SMSDeliveryResult:
    accepted: bool
    provider_message_id: str
    provider_key: str
    error_message: str = ""


class SMSProviderBase(ABC):
    provider_key: str
    display_name: str
    supports_sandbox: bool = False
    required_credential_fields: list[str] = []

    @abstractmethod
    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_line: Optional[str] = None,
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        raise NotImplementedError

    @abstractmethod
    def send_otp(
        self,
        phone_number: str,
        template_key: str,
        tokens: Dict[str, str],
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        raise NotImplementedError

    def test_connection(
        self, *, credentials: Optional[dict] = None, is_sandbox: bool = False
    ) -> dict:
        creds = credentials or {}
        missing = [f for f in self.required_credential_fields if not str(creds.get(f) or "").strip()]
        if missing and not is_sandbox:
            return {
                "ok": False,
                "status": "MISSING_CREDENTIALS",
                "message": f"فیلدهای الزامی درگاه پیامک تکمیل نشده‌اند: {', '.join(missing)}",
            }
        return {
            "ok": True,
            "status": "READY",
            "message": f"پیکربندی سرویس پیامک {self.display_name} معتبر است.",
        }


class ConsoleSMSAdapter(SMSProviderBase):
    provider_key = "console"
    display_name = "ارسال شبیه‌ساز داخلی (Sandbox Console)"
    supports_sandbox = True
    required_credential_fields = []

    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_line: Optional[str] = None,
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        logger.info("[ConsoleSMS] to=%s line=%s msg=%s", phone_number, sender_line or "-", message)
        return SMSDeliveryResult(
            accepted=True,
            provider_message_id=f"console-sms-{uuid.uuid4().hex[:10]}",
            provider_key=self.provider_key,
        )

    def send_otp(
        self,
        phone_number: str,
        template_key: str,
        tokens: Dict[str, str],
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        logger.info("[ConsoleOTP] to=%s template=%s tokens=%s", phone_number, template_key, tokens)
        return SMSDeliveryResult(
            accepted=True,
            provider_message_id=f"console-otp-{uuid.uuid4().hex[:10]}",
            provider_key=self.provider_key,
        )


class KavenegarSMSAdapter(SMSProviderBase):
    provider_key = "kavenegar"
    display_name = "کاوه‌نگار (Kavenegar REST API)"
    supports_sandbox = False
    required_credential_fields = ["api_key", "sender_line"]

    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_line: Optional[str] = None,
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        creds = credentials or {}
        api_key = str(creds.get("api_key") or "").strip()
        line = str(sender_line or creds.get("sender_line") or "").strip()
        if not api_key:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message="کلید API کاوه‌نگار تنظیم نشده است.",
            )
        url = f"https://api.kavenegar.com/v1/{api_key}/sms/send.json"
        payload = {"receptor": phone_number, "message": message}
        if line:
            payload["sender"] = line
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, data=payload)
                data = resp.json() if resp.content else {}
                entries = data.get("entries") or []
                msg_id = str(entries[0].get("messageid")) if entries else f"kav-{uuid.uuid4().hex[:8]}"
                ok_flag = resp.status_code == 200 and (data.get("return", {}).get("status") == 200)
                return SMSDeliveryResult(
                    accepted=ok_flag,
                    provider_message_id=msg_id,
                    provider_key=self.provider_key,
                    error_message="" if ok_flag else str(data.get("return", {}).get("message") or resp.text[:160]),
                )
        except Exception as exc:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message=str(exc)[:200],
            )

    def send_otp(
        self,
        phone_number: str,
        template_key: str,
        tokens: Dict[str, str],
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        creds = credentials or {}
        api_key = str(creds.get("api_key") or "").strip()
        if not api_key:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message="کلید API کاوه‌نگار تنظیم نشده است.",
            )
        url = f"https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"
        payload = {"receptor": phone_number, "template": template_key, "token": str(tokens.get("code") or next(iter(tokens.values()), ""))}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, data=payload)
                data = resp.json() if resp.content else {}
                ok_flag = resp.status_code == 200 and (data.get("return", {}).get("status") == 200)
                entries = data.get("entries") or []
                msg_id = str(entries[0].get("messageid")) if entries else f"kav-otp-{uuid.uuid4().hex[:8]}"
                return SMSDeliveryResult(
                    accepted=ok_flag,
                    provider_message_id=msg_id,
                    provider_key=self.provider_key,
                    error_message="" if ok_flag else str(data.get("return", {}).get("message") or resp.text[:160]),
                )
        except Exception as exc:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message=str(exc)[:200],
            )


class MelipayamakSMSAdapter(SMSProviderBase):
    provider_key = "melipayamak"
    display_name = "ملی‌پیامک (Melipayamak)"
    supports_sandbox = False
    required_credential_fields = ["username", "password", "sender_line"]

    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_line: Optional[str] = None,
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        creds = credentials or {}
        username = str(creds.get("username") or "").strip()
        password = str(creds.get("password") or "").strip()
        line = str(sender_line or creds.get("sender_line") or "").strip()
        if not username or not password:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message="نام کاربری یا رمز وب‌سرویس ملی‌پیامک تنظیم نشده است.",
            )
        url = "https://rest.payamak-panel.com/api/SendSMS/SendSMS"
        payload = {
            "username": username,
            "password": password,
            "to": phone_number,
            "from": line,
            "text": message,
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload)
                data = resp.json() if resp.content else {}
                ok_flag = resp.status_code == 200 and int(data.get("RetStatus", 0)) == 1
                return SMSDeliveryResult(
                    accepted=ok_flag,
                    provider_message_id=str(data.get("Value") or ""),
                    provider_key=self.provider_key,
                    error_message="" if ok_flag else str(data.get("StrRetStatus") or resp.text[:160]),
                )
        except Exception as exc:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message=str(exc)[:200],
            )

    def send_otp(
        self,
        phone_number: str,
        template_key: str,
        tokens: Dict[str, str],
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        msg = f"{template_key}: {' '.join(str(v) for v in tokens.values())}"
        return self.send_sms(phone_number, msg, credentials=credentials)


class SMSIrSMSAdapter(SMSProviderBase):
    provider_key = "smsir"
    display_name = "پیامک‌ایرانیان (SMS.ir v1)"
    supports_sandbox = True
    required_credential_fields = ["api_key", "sender_line"]

    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_line: Optional[str] = None,
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        creds = credentials or {}
        api_key = str(creds.get("api_key") or "").strip()
        line = str(sender_line or creds.get("sender_line") or "").strip()
        if not api_key:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message="کلید API سرویس SMS.ir تنظیم نشده است.",
            )
        url = "https://api.sms.ir/v1/send/bulk"
        headers = {"X-API-KEY": api_key, "Accept": "application/json"}
        payload = {"lineNumber": line, "messageText": message, "mobiles": [phone_number]}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                data = resp.json() if resp.content else {}
                ok_flag = resp.status_code == 200 and int(data.get("status", 0)) == 1
                msg_ids = (data.get("data") or {}).get("messageIds") or []
                return SMSDeliveryResult(
                    accepted=ok_flag,
                    provider_message_id=str(msg_ids[0]) if msg_ids else f"smsir-{uuid.uuid4().hex[:8]}",
                    provider_key=self.provider_key,
                    error_message="" if ok_flag else str(data.get("message") or resp.text[:160]),
                )
        except Exception as exc:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message=str(exc)[:200],
            )

    def send_otp(
        self,
        phone_number: str,
        template_key: str,
        tokens: Dict[str, str],
        credentials: Optional[dict] = None,
    ) -> SMSDeliveryResult:
        creds = credentials or {}
        api_key = str(creds.get("api_key") or "").strip()
        if not api_key:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message="کلید API سرویس SMS.ir تنظیم نشده است.",
            )
        url = "https://api.sms.ir/v1/send/verify"
        headers = {"X-API-KEY": api_key, "Accept": "application/json"}
        params = [{"name": k, "value": str(v)} for k, v in tokens.items()]
        try:
            tpl_id = int(template_key) if str(template_key).isdigit() else 100000
        except Exception:
            tpl_id = 100000
        payload = {"mobile": phone_number, "templateId": tpl_id, "parameters": params}
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                data = resp.json() if resp.content else {}
                ok_flag = resp.status_code == 200 and int(data.get("status", 0)) == 1
                msg_id = str((data.get("data") or {}).get("messageId") or "")
                return SMSDeliveryResult(
                    accepted=ok_flag,
                    provider_message_id=msg_id,
                    provider_key=self.provider_key,
                    error_message="" if ok_flag else str(data.get("message") or resp.text[:160]),
                )
        except Exception as exc:
            return SMSDeliveryResult(
                accepted=False,
                provider_message_id="",
                provider_key=self.provider_key,
                error_message=str(exc)[:200],
            )
