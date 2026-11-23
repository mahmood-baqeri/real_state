from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
import httpx


@dataclass(frozen=True)
class PaymentInitResult:
    authority: str
    redirect_url: str
    provider_key: str
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentVerifyResult:
    is_paid: bool
    reference_id: str
    verified_amount: Decimal
    currency: str
    raw_response: Dict[str, Any]
    error_message: str = ""


@dataclass(frozen=True)
class GatewayHealthResult:
    ok: bool
    status: str
    message: str


class PaymentProviderBase(ABC):
    provider_key: str
    display_name: str
    supports_sandbox: bool = True
    required_credential_fields: List[str] = []

    @abstractmethod
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
    ) -> PaymentInitResult:
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
        order_id: str = "",
    ) -> PaymentVerifyResult:
        raise NotImplementedError

    def test_connection(
        self,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
    ) -> GatewayHealthResult:
        creds = credentials or {}
        missing = [f for f in self.required_credential_fields if not str(creds.get(f, "")).strip()]
        if missing and not is_sandbox:
            return GatewayHealthResult(
                ok=False,
                status="MISSING_CREDENTIALS",
                message=f"فیلدهای احراز هویت درگاه تکمیل نشده‌اند: {', '.join(missing)}",
            )
        return GatewayHealthResult(
            ok=True,
            status="READY",
            message=f"پیکربندی {self.display_name} ({'Sandbox' if is_sandbox else 'Production'}) معتبر است.",
        )


def _to_rials(amount: Decimal, currency: str) -> int:
    val = int(Decimal(amount))
    if (currency or "IRT").upper() == "IRT":
        return val * 10
    return val


class SandboxPaymentAdapter(PaymentProviderBase):
    provider_key = "sandbox"
    display_name = "درگاه آزمایشی داخلی (Sandbox)"
    supports_sandbox = True
    required_credential_fields = []

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
    ) -> PaymentInitResult:
        authority = f"SBX-{uuid.uuid4().hex[:12].upper()}"
        sep = "&" if "?" in callback_url else "?"
        return PaymentInitResult(
            authority=authority,
            redirect_url=f"{callback_url}{sep}authority={authority}&status=OK&provider=sandbox",
            provider_key=self.provider_key,
            raw_response={"mode": "sandbox", "authority": authority},
        )

    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
        order_id: str = "",
    ) -> PaymentVerifyResult:
        paid = authority.startswith("SBX-")
        return PaymentVerifyResult(
            is_paid=paid,
            reference_id=f"REF-{authority}" if paid else "",
            verified_amount=expected_amount,
            currency=currency,
            raw_response={"sandbox": True, "authority": authority, "paid": paid},
            error_message="" if paid else "شناسه پرداخت آزمایشی نامعتبر است.",
        )


class ZarinpalPaymentAdapter(PaymentProviderBase):
    """
    Zarinpal REST v4 Payment Gateway Adapter
    Official Endpoints:
      - Production Request: https://payment.zarinpal.com/pg/v4/payment/request.json
      - Production Verify:  https://payment.zarinpal.com/pg/v4/payment/verify.json
      - Sandbox Request:    https://sandbox.zarinpal.com/pg/v4/payment/request.json
      - Sandbox Verify:     https://sandbox.zarinpal.com/pg/v4/payment/verify.json
    """

    provider_key = "zarinpal"
    display_name = "زرین‌پال (Zarinpal v4)"
    supports_sandbox = True
    required_credential_fields = ["merchant_id"]

    def _base_host(self, is_sandbox: bool) -> str:
        return "https://sandbox.zarinpal.com" if is_sandbox else "https://payment.zarinpal.com"

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
    ) -> PaymentInitResult:
        creds = credentials or {}
        merchant_id = str(creds.get("merchant_id") or "").strip()
        if not merchant_id:
            if is_sandbox:
                merchant_id = "00000000-0000-0000-0000-000000000000"
            else:
                raise ValueError("کد پذیرنده زرین‌پال (merchant_id) پیکربندی نشده است.")

        host = self._base_host(is_sandbox)
        payload = {
            "merchant_id": merchant_id,
            "amount": max(1000, _to_rials(amount, currency)),
            "callback_url": callback_url,
            "description": (metadata or {}).get("description", "پرداخت اشتراک بنیان ملک"),
            "metadata": {
                k: str(v)
                for k, v in (metadata or {}).items()
                if k in ("mobile", "email", "order_id") and v
            },
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(
                    f"{host}/pg/v4/payment/request.json",
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                body = resp.json()
        except Exception as exc:
            if is_sandbox:
                authority = f"S000000000000000000000000000{uuid.uuid4().hex[:8].upper()}"
                return PaymentInitResult(
                    authority=authority,
                    redirect_url=f"{host}/pg/StartPay/{authority}",
                    provider_key=self.provider_key,
                    raw_response={"sandbox_offline_fallback": True, "detail": str(exc)},
                )
            raise ValueError(f"خطا در اتصال به درگاه زرین‌پال: {exc}") from exc

        data = body.get("data") or {}
        if data.get("code") == 100 and data.get("authority"):
            authority = str(data["authority"])
            return PaymentInitResult(
                authority=authority,
                redirect_url=f"{host}/pg/StartPay/{authority}",
                provider_key=self.provider_key,
                raw_response=body,
            )
        err = body.get("errors") or {}
        raise ValueError(f"خطای زرین‌پال در ایجاد تراکنش: {err}")

    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
        order_id: str = "",
    ) -> PaymentVerifyResult:
        creds = credentials or {}
        merchant_id = str(creds.get("merchant_id") or "").strip() or (
            "00000000-0000-0000-0000-000000000000" if is_sandbox else ""
        )
        if not merchant_id:
            return PaymentVerifyResult(
                is_paid=False,
                reference_id="",
                verified_amount=Decimal("0"),
                currency=currency,
                raw_response={},
                error_message="merchant_id زرین‌پال تنظیم نشده است.",
            )

        host = self._base_host(is_sandbox)
        payload = {
            "merchant_id": merchant_id,
            "authority": authority,
            "amount": max(1000, _to_rials(expected_amount, currency)),
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(
                    f"{host}/pg/v4/payment/verify.json",
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                body = resp.json()
        except Exception as exc:
            return PaymentVerifyResult(
                is_paid=False,
                reference_id="",
                verified_amount=Decimal("0"),
                currency=currency,
                raw_response={"error": str(exc)},
                error_message="خطا در ارتباط با سرور تایید زرین‌پال.",
            )

        data = body.get("data") or {}
        code = data.get("code")
        if code in (100, 101):
            return PaymentVerifyResult(
                is_paid=True,
                reference_id=str(data.get("ref_id") or authority),
                verified_amount=expected_amount,
                currency=currency,
                raw_response=body,
            )
        return PaymentVerifyResult(
            is_paid=False,
            reference_id="",
            verified_amount=Decimal("0"),
            currency=currency,
            raw_response=body,
            error_message=f"تایید پرداخت در زرین‌پال ناموفق بود (کد {code}).",
        )


class ZibalPaymentAdapter(PaymentProviderBase):
    """
    Zibal REST v1 Payment Gateway Adapter
    Official Endpoints:
      - Request:  POST https://gateway.zibal.ir/v1/request
      - StartPay: https://gateway.zibal.ir/start/{trackId}
      - Verify:   POST https://gateway.zibal.ir/v1/verify
    Sandbox: merchant = "zibal"
    """

    provider_key = "zibal"
    display_name = "زیبال (Zibal v1)"
    supports_sandbox = True
    required_credential_fields = ["merchant"]

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
    ) -> PaymentInitResult:
        creds = credentials or {}
        merchant = str(creds.get("merchant") or creds.get("merchant_id") or "").strip()
        if is_sandbox and not merchant:
            merchant = "zibal"
        if not merchant:
            raise ValueError("مرچنت کد درگاه زیبال (merchant) پیکربندی نشده است.")

        payload = {
            "merchant": merchant,
            "amount": max(1000, _to_rials(amount, currency)),
            "callbackUrl": callback_url,
            "orderId": str((metadata or {}).get("order_id") or uuid.uuid4().hex[:10]),
            "description": (metadata or {}).get("description", "پرداخت بنیان ملک"),
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post("https://gateway.zibal.ir/v1/request", json=payload)
                body = resp.json()
        except Exception as exc:
            if is_sandbox:
                track_id = f"ZBL-{uuid.uuid4().hex[:10].upper()}"
                return PaymentInitResult(
                    authority=track_id,
                    redirect_url=f"https://gateway.zibal.ir/start/{track_id}",
                    provider_key=self.provider_key,
                    raw_response={"sandbox_offline_fallback": True, "detail": str(exc)},
                )
            raise ValueError(f"خطا در ارتباط با زیبال: {exc}") from exc

        if body.get("result") == 100 and body.get("trackId"):
            track_id = str(body["trackId"])
            return PaymentInitResult(
                authority=track_id,
                redirect_url=f"https://gateway.zibal.ir/start/{track_id}",
                provider_key=self.provider_key,
                raw_response=body,
            )
        raise ValueError(f"خطای زیبال: {body.get('message', body.get('result'))}")

    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
        order_id: str = "",
    ) -> PaymentVerifyResult:
        creds = credentials or {}
        merchant = str(creds.get("merchant") or creds.get("merchant_id") or "").strip() or (
            "zibal" if is_sandbox else ""
        )
        if not merchant:
            return PaymentVerifyResult(
                is_paid=False,
                reference_id="",
                verified_amount=Decimal("0"),
                currency=currency,
                raw_response={},
                error_message="مرچنت کد زیبال تنظیم نشده است.",
            )
        try:
            track_val: Any = int(authority) if authority.isdigit() else authority
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(
                    "https://gateway.zibal.ir/v1/verify",
                    json={"merchant": merchant, "trackId": track_val},
                )
                body = resp.json()
        except Exception as exc:
            return PaymentVerifyResult(
                is_paid=False,
                reference_id="",
                verified_amount=Decimal("0"),
                currency=currency,
                raw_response={"error": str(exc)},
                error_message="خطا در ارتباط با سرویس تایید زیبال.",
            )

        if body.get("result") in (100, 201):
            return PaymentVerifyResult(
                is_paid=True,
                reference_id=str(body.get("refNumber") or authority),
                verified_amount=expected_amount,
                currency=currency,
                raw_response=body,
            )
        return PaymentVerifyResult(
            is_paid=False,
            reference_id="",
            verified_amount=Decimal("0"),
            currency=currency,
            raw_response=body,
            error_message=body.get("message") or f"کد خطای زیبال: {body.get('result')}",
        )


class IDPayPaymentAdapter(PaymentProviderBase):
    """
    IDPay v1.1 REST API Adapter
    Official Endpoints:
      - Request: POST https://api.idpay.ir/v1.1/payment
      - Verify:  POST https://api.idpay.ir/v1.1/payment/verify
    Headers: X-API-KEY, optional X-SANDBOX: 1
    """

    provider_key = "idpay"
    display_name = "آیدی‌پی (IDPay v1.1)"
    supports_sandbox = True
    required_credential_fields = ["api_key"]

    def _headers(self, api_key: str, is_sandbox: bool) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }
        if is_sandbox:
            h["X-SANDBOX"] = "1"
        return h

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
    ) -> PaymentInitResult:
        creds = credentials or {}
        api_key = str(creds.get("api_key") or "").strip()
        if not api_key and not is_sandbox:
            raise ValueError("کلید API آیدی‌پی (api_key) تنظیم نشده است.")
        api_key = api_key or "6a7f99eb-7c20-4412-a972-6dfb7cd253a4"
        order_id = str((metadata or {}).get("order_id") or uuid.uuid4().hex[:12])
        payload = {
            "order_id": order_id,
            "amount": max(1000, _to_rials(amount, currency)),
            "callback": callback_url,
            "desc": (metadata or {}).get("description", "پرداخت بنیان ملک"),
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(
                    "https://api.idpay.ir/v1.1/payment",
                    json=payload,
                    headers=self._headers(api_key, is_sandbox),
                )
                body = resp.json()
        except Exception as exc:
            if is_sandbox:
                auth_id = f"IDP-{uuid.uuid4().hex[:12].upper()}"
                return PaymentInitResult(
                    authority=auth_id,
                    redirect_url=f"https://idpay.ir/p/ws-sandbox/{auth_id}",
                    provider_key=self.provider_key,
                    raw_response={"sandbox_offline_fallback": True, "detail": str(exc)},
                )
            raise ValueError(f"خطا در ارتباط با آیدی‌پی: {exc}") from exc

        if body.get("id") and body.get("link"):
            return PaymentInitResult(
                authority=str(body["id"]),
                redirect_url=str(body["link"]),
                provider_key=self.provider_key,
                raw_response=body,
            )
        raise ValueError(f"خطای آیدی‌پی: {body.get('error_message', body)}")

    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
        *,
        credentials: Optional[Dict[str, Any]] = None,
        is_sandbox: bool = True,
        order_id: str = "",
    ) -> PaymentVerifyResult:
        creds = credentials or {}
        api_key = str(creds.get("api_key") or "").strip() or (
            "6a7f99eb-7c20-4412-a972-6dfb7cd253a4" if is_sandbox else ""
        )
        if not api_key:
            return PaymentVerifyResult(
                is_paid=False,
                reference_id="",
                verified_amount=Decimal("0"),
                currency=currency,
                raw_response={},
                error_message="کلید API آیدی‌پی تنظیم نشده است.",
            )
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(
                    "https://api.idpay.ir/v1.1/payment/verify",
                    json={"id": authority, "order_id": order_id or authority},
                    headers=self._headers(api_key, is_sandbox),
                )
                body = resp.json()
        except Exception as exc:
            return PaymentVerifyResult(
                is_paid=False,
                reference_id="",
                verified_amount=Decimal("0"),
                currency=currency,
                raw_response={"error": str(exc)},
                error_message="خطا در ارتباط با سرور تایید آیدی‌پی.",
            )

        if body.get("status") in (100, 101):
            return PaymentVerifyResult(
                is_paid=True,
                reference_id=str(body.get("track_id") or authority),
                verified_amount=expected_amount,
                currency=currency,
                raw_response=body,
            )
        return PaymentVerifyResult(
            is_paid=False,
            reference_id="",
            verified_amount=Decimal("0"),
            currency=currency,
            raw_response=body,
            error_message=body.get("error_message") or "تایید پرداخت در آیدی‌پی ناموفق بود.",
        )
