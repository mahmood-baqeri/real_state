from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PaymentInitResult:
    authority: str
    redirect_url: str
    provider_key: str


@dataclass(frozen=True)
class PaymentVerifyResult:
    is_paid: bool
    reference_id: str
    verified_amount: Decimal
    currency: str
    raw_response: Dict[str, Any]


class PaymentProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitResult:
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
    ) -> PaymentVerifyResult:
        raise NotImplementedError


class SandboxPaymentAdapter(PaymentProviderBase):
    provider_key = "sandbox"

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitResult:
        authority = f"SBX-{abs(hash((str(amount), currency, callback_url))) % 10000000:07d}"
        return PaymentInitResult(
            authority=authority,
            redirect_url=f"{callback_url}?authority={authority}&status=OK",
            provider_key=self.provider_key,
        )

    def verify_payment(
        self,
        authority: str,
        expected_amount: Decimal,
        currency: str,
    ) -> PaymentVerifyResult:
        return PaymentVerifyResult(
            is_paid=authority.startswith("SBX-"),
            reference_id=f"REF-{authority}",
            verified_amount=expected_amount,
            currency=currency,
            raw_response={"sandbox": True, "authority": authority},
        )
