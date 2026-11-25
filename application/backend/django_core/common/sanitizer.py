"""پاک‌سازی HTML قابل نمایش با فهرست محدود تگ‌ها و ویژگی‌ها."""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "strong", "b", "em", "i", "u",
    "ul", "ol", "li", "blockquote", "code", "pre",
    "a", "span", "div", "table", "thead", "tbody", "tr", "th", "td",
}

VOID_TAGS = {"br", "hr"}

SKIP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "form", "svg", "math"}

ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}


def _is_safe_url(raw_url: str) -> bool:
    """فقط مسیر محلی، پیوند درون‌صفحه و پروتکل‌های مجاز را می‌پذیرد."""
    val = (raw_url or "").strip()
    if not val or any(ord(char) < 32 or char == "\\" for char in val):
        return False
    if val.startswith("//"):
        return False
    if val.startswith(("/", "#")):
        return True
    try:
        parsed = urlparse(val)
    except ValueError:
        return False
    return parsed.scheme.lower() in ("http", "https", "mailto", "tel")


class _SafeHTMLSanitizer(HTMLParser):
    """تگ‌ها و ویژگی‌های مجاز را با خروجی HTML متوازن بازسازی می‌کند."""
    def __init__(self) -> None:
        """بافر خروجی و وضعیت تگ‌های باز را برای یک سند آماده می‌کند."""
        super().__init__(convert_charrefs=False)
        self.chunks: list[str] = []
        self._skip_depth = 0
        self._open_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """تگ آغازین و ویژگی‌های مجازش را به خروجی اضافه می‌کند."""
        t = tag.lower()
        if t in SKIP_CONTENT_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0 or t not in ALLOWED_TAGS:
            return

        allowed = ALLOWED_ATTRS.get(t, set())
        cleaned_attrs: list[str] = []
        has_target_blank = False
        for k, v in attrs:
            attr_name = (k or "").lower().strip()
            if attr_name not in allowed or attr_name == "rel":
                continue
            attr_val = (v or "").strip()
            if attr_name == "href" and not _is_safe_url(attr_val):
                continue
            if attr_name == "target":
                if attr_val == "_blank":
                    has_target_blank = True
                else:
                    continue
            cleaned_attrs.append(f'{attr_name}="{escape(attr_val, quote=True)}"')

        if t == "a" and has_target_blank:
            cleaned_attrs.append('rel="noopener noreferrer"')

        attr_str = (" " + " ".join(cleaned_attrs)) if cleaned_attrs else ""
        self.chunks.append(f"<{t}{attr_str}>")
        if t not in VOID_TAGS:
            self._open_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        """تگ پایان و تگ‌های باز داخل آن را به ترتیب می‌بندد."""
        t = tag.lower()
        if t in SKIP_CONTENT_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth > 0 or t not in ALLOWED_TAGS or t in VOID_TAGS:
            return
        if t in self._open_stack:
            while self._open_stack:
                top = self._open_stack.pop()
                self.chunks.append(f"</{top}>")
                if top == t:
                    break

    def handle_data(self, data: str) -> None:
        """متن قابل نمایش خارج از محتوای حذف‌شده را escape می‌کند."""
        if self._skip_depth == 0:
            self.chunks.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        """موجودیت HTML نام‌دار خارج از بخش حذف‌شده را حفظ می‌کند."""
        if self._skip_depth == 0:
            self.chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """ارجاع عددی کاراکتر را در متن قابل نمایش حفظ می‌کند."""
        if self._skip_depth == 0:
            self.chunks.append(f"&#{name};")

    def get_sanitized(self) -> str:
        """تگ‌های باز باقی‌مانده را می‌بندد و متن نهایی را برمی‌گرداند."""
        while self._open_stack:
            top = self._open_stack.pop()
            self.chunks.append(f"</{top}>")
        return "".join(self.chunks).strip()


def sanitize_html(raw_html: str) -> str:
    """HTML ورودی را برای نمایش در محتوای عمومی پاک‌سازی می‌کند."""
    if not raw_html:
        return ""
    parser = _SafeHTMLSanitizer()
    parser.feed(raw_html)
    parser.close()
    return parser.get_sanitized()
