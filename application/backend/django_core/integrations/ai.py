from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
from django.conf import settings
import httpx


@dataclass(frozen=True)
class AICompletionResult:
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: int = 0
    raw_meta: Dict[str, Any] = field(default_factory=dict)


class AIProviderBase(ABC):
    provider_key: str
    display_name: str

    @abstractmethod
    def complete_chat(
        self,
        *,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 1200,
        api_key: str = "",
        base_url: str = "",
        timeout_seconds: int = 25,
    ) -> AICompletionResult:
        raise NotImplementedError

    @abstractmethod
    def list_supported_models(self) -> List[Dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def check_health(self, *, api_key: str = "", base_url: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class GapGPTAdapter(AIProviderBase):
    """
    GapGPT (https://gapgpt.app) OpenAI-Compatible Unified Gateway Adapter
    Verified Official Spec:
      - Base URL: https://api.gapgpt.app/v1
      - Auth:     Authorization: Bearer <GAPGPT_API_KEY>
      - Endpoint: POST /chat/completions
      - Rate Limit: ~300 RPM; HTTP 429 handled via exponential backoff.
    """

    provider_key = "gapgpt"
    display_name = "GapGPT Unified AI Gateway"

    SUPPORTED_MODELS = [
        {"id": "gpt-4o", "label": "GPT-4o (توصیه‌شده متعادل)"},
        {"id": "gpt-5.6", "label": "GPT-5.6 (تحلیل پیشرفته)"},
        {"id": "gpt-6.2-sol", "label": "GPT-6.2 Sol (استدلال عمیق)"},
        {"id": "claude-sonnet", "label": "Claude Sonnet (نگارش فارسی روان)"},
        {"id": "gemini-flash", "label": "Gemini Flash (پاسخ سریع)"},
        {"id": "deepseek-v4", "label": "DeepSeek V4 (اقتصادی و تحلیلی)"},
    ]

    def list_supported_models(self) -> List[Dict[str, str]]:
        return self.SUPPORTED_MODELS

    def check_health(self, *, api_key: str = "", base_url: str = "") -> Dict[str, Any]:
        resolved_key = (api_key or getattr(settings, "GAPGPT_API_KEY", "") or "").strip()
        resolved_base = (base_url or getattr(settings, "GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")).rstrip("/")
        if not resolved_key:
            return {
                "provider": self.provider_key,
                "configured": False,
                "base_url": resolved_base,
                "default_model": getattr(settings, "GAPGPT_DEFAULT_MODEL", "gpt-4o"),
                "message": "کلید GAPGPT_API_KEY تنظیم نشده است؛ تا زمان تنظیم کلید، پاسخ‌ها از موتور تحلیلی بومی آژانس تولید می‌شوند.",
            }
        return {
            "provider": self.provider_key,
            "configured": True,
            "base_url": resolved_base,
            "default_model": getattr(settings, "GAPGPT_DEFAULT_MODEL", "gpt-4o"),
            "message": "اتصال GapGPT آماده و کلید به‌صورت امن در سرور پیکربندی شده است.",
        }

    def complete_chat(
        self,
        *,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 1200,
        api_key: str = "",
        base_url: str = "",
        timeout_seconds: int = 25,
    ) -> AICompletionResult:
        resolved_key = (api_key or getattr(settings, "GAPGPT_API_KEY", "") or "").strip()
        resolved_base = (base_url or getattr(settings, "GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")).rstrip("/")
        resolved_model = (model or getattr(settings, "GAPGPT_DEFAULT_MODEL", "gpt-4o")).strip()
        timeout = float(timeout_seconds or getattr(settings, "GAPGPT_TIMEOUT_SECONDS", 25))

        if not resolved_key:
            raise ValueError("GAPGPT_NOT_CONFIGURED")

        url = f"{resolved_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {resolved_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        started = time.monotonic()
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", str(0.6 * (2 ** attempt))))
                    if attempt < 2:
                        time.sleep(min(retry_after, 3.0))
                        continue
                    raise ValueError("GAPGPT_RATE_LIMIT: محدودیت نرخ درخواست GapGPT (429)؛ لطفاً چند لحظه بعد تلاش کنید.")
                if resp.status_code in (401, 403):
                    raise ValueError("GAPGPT_AUTH_ERROR: کلید دسترسی GapGPT نامعتبر یا منقضی شده است.")
                resp.raise_for_status()
                body = resp.json()
                choices = body.get("choices") or []
                content = ""
                if choices and isinstance(choices[0], dict):
                    msg = choices[0].get("message") or {}
                    content = str(msg.get("content") or "").strip()
                usage = body.get("usage") or {}
                tokens = int(usage.get("total_tokens") or 0)
                latency = int((time.monotonic() - started) * 1000)
                return AICompletionResult(
                    content=content,
                    model=str(body.get("model") or resolved_model),
                    provider="GAPGPT",
                    tokens_used=tokens,
                    latency_ms=latency,
                    raw_meta={"usage": usage, "id": body.get("id", "")},
                )
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.4 * (2 ** attempt))
                    continue
                raise ValueError("GAPGPT_TIMEOUT: زمان پاسخ‌گویی سرویس GapGPT به پایان رسید.") from exc
            except ValueError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.4 * (2 ** attempt))
                    continue
                raise ValueError(f"GAPGPT_UPSTREAM_ERROR: {exc}") from exc

        raise ValueError(f"GAPGPT_UPSTREAM_ERROR: {last_error}")
