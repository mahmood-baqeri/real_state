from unittest.mock import patch
import socket
import pytest
from django.test import SimpleTestCase

from common.sanitizer import sanitize_html
from common.tenant.context import is_tenant_bypassed, tenant_bypass
from common.exceptions import ValidationDomainError
from apps.ai_assistant.services import _assert_ssrf_safe_https_url


class TenantBypassNestingTests(SimpleTestCase):
    def test_nested_allowlisted_bypass_restores_outer_state(self):
        self.assertFalse(is_tenant_bypassed())
        with tenant_bypass(reason="platform_seed"):
            self.assertTrue(is_tenant_bypassed())
            with tenant_bypass(reason="public_catalog"):
                self.assertTrue(is_tenant_bypassed())
            self.assertTrue(is_tenant_bypassed())
        self.assertFalse(is_tenant_bypassed())


def test_html_sanitizer_removes_script_event_handlers_and_javascript_urls():
    result = sanitize_html('<script>alert(1)</script><p onclick="alert(2)">Safe <a href="javascript:alert(3)">link</a></p>')
    assert "script" not in result.lower()
    assert "onclick" not in result.lower()
    assert "javascript:" not in result.lower()
    assert "Safe" in result and "link" in result


def test_rss_url_requires_https_without_userinfo_or_custom_ports():
    with pytest.raises(ValidationDomainError):
        _assert_ssrf_safe_https_url("http://example.com/feed")
    with pytest.raises(ValidationDomainError):
        _assert_ssrf_safe_https_url("https://user:pass@example.com/feed")
    with pytest.raises(ValidationDomainError):
        _assert_ssrf_safe_https_url("https://example.com:8443/feed")


def test_rss_dns_rejects_private_ip_addresses():
    private_record = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    with patch("apps.ai_assistant.services.socket.getaddrinfo", return_value=private_record):
        with pytest.raises(ValidationDomainError):
            _assert_ssrf_safe_https_url("https://example.com/feed")


def test_rss_dns_accepts_public_ip_addresses():
    public_record = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    with patch("apps.ai_assistant.services.socket.getaddrinfo", return_value=public_record):
        assert _assert_ssrf_safe_https_url("https://example.com/feed") == "https://example.com/feed"
