# قرارداد فنی آداپتورهای ارائه‌دهندگان و موتور بومی‌سازی

## ۱. آداپتورهای سرویس‌های جانبی (Strategy & Adapter Pattern)

تمام سرویس‌های بیرونی در `backend/integrations/` با الگوی Interface + Registry پیاده‌سازی می‌شوند و پیکربندی هر آژانس یا پلتفرم در مدل `ProviderConfiguration` نگهداری می‌شود.

### ۱.۱. درگاه پرداخت (`PaymentProviderBase`)
- **متدهای قرارداد:**
  - `create_payment_intent(amount: Decimal, currency: str, callback_url: str, metadata: dict) -> PaymentInitResult`
  - `verify_payment(authority_or_ref: str, expected_amount: Decimal, currency: str) -> PaymentVerifyResult`
  - `parse_webhook(headers: dict, payload: bytes) -> WebhookEvent`
  - `refund_payment(reference_id: str, amount: Decimal, reason: str) -> RefundResult`
- **آداپتورهای پیش‌فرض:** `SandboxPaymentAdapter` (توسعه و تست بدون اتصال واقعی)، ساختار آماده برای `ZarinpalAdapter`, `IdPayAdapter`, `StripeAdapter`.

### ۱.۲. سرویس پیامک (`SMSProviderBase`)
- **متدهای قرارداد:**
  - `send_sms(phone_number: str, message: str, sender_line: str | None = None) -> SMSDeliveryResult`
  - `send_otp(phone_number: str, template_key: str, tokens: dict[str, str]) -> SMSDeliveryResult`
  - `get_delivery_status(provider_message_id: str) -> DeliveryStatus`
- **آداپتورهای پیش‌فرض:** `ConsoleSMSAdapter` (ثبت خروجی امن در لاگ توسعه بدون افشای کلید در UI)، ساختار آماده برای `KavenegarAdapter`, `GhasedakAdapter`, `TwilioAdapter`.

### ۱.۳. سرویس نقشه (`MapProviderBase`)
- **متدهای قرارداد:**
  - `geocode(address: str, country_code: str = "IR") -> GeoCoordinate | None`
  - `reverse_geocode(latitude: Decimal, longitude: Decimal) -> ReverseGeoAddress`
  - `distance_meters(origin: GeoCoordinate, destination: GeoCoordinate) -> int`
  - `get_client_tile_config() -> MapClientConfig` (بازگرداندن نوع نقشه و کلید عمومی مجاز یا URL کاشی بدون افشای کلید سرور)
- **آداپتورهای پیش‌فرض:** `OpenStreetMapAdapter` (رایگان و بدون نیاز به کلید در محیط توسعه)، ساختار آماده برای `NeshanAdapter`, `BaladAdapter`, `MapboxAdapter`, `GoogleMapsAdapter`.

---

## ۲. موتور بومی‌سازی، ارز و تقویم (`common.localization`)

### ۲.۱. تقویم و زمان
- ذخیره در PostgreSQL: همیشه `TIMESTAMPTZ` در منطقه زمانی `UTC`.
- تبدیل در Backend: `CalendarAdapter` از طریق کتابخانه `jdatetime` محاسبه ابتدا/انتهای ماه و سال شمسی (برای گزارش‌های مالی و دوره‌های حقوق) و `datetime` استاندارد را برای تقویم میلادی فراهم می‌کند.
- تبدیل در Frontend: بر اساس `user.preferred_calendar` (یا `agency.default_calendar`) نمایش به‌صورت شمسی (`fa-IR-u-ca-persian`) یا میلادی انجام می‌شود.

### ۲.۲. ارز و تبدیل صریح ریال / تومان
- مبنای محاسبه دقیق در جدول `Currency`:
  - `IRR`: `decimal_places = 0`, `base_unit_factor = Decimal("1")`
  - `IRT`: `decimal_places = 0`, `base_unit_factor = Decimal("10")`
  - `USD`: `decimal_places = 2`, `base_unit_factor = Decimal(...)` (یا نرخ تبدیل جدول `ExchangeRate`)
- **قاعده تبدیل صریح:** هر رکورد مالی فیلد `currency_code` را صریح ذخیره می‌کند. در تبدیل بین `IRT` و `IRR`:
  - `1 IRT = 10 IRR`
  - هنگام تبدیل از `IRR` به `IRT` در نمایش یا تبدیل صریح، باقیمانده کسری ریالی هرگز در حسابداری گم نمی‌شود و ثبت‌های حسابداری همیشه بر پایه `agency.accounting_currency` تراز می‌شوند.

### ۲.۳. واحدهای اندازه‌گیری
- ذخیره متراژها در دیتابیس به‌صورت استاندارد `Decimal` بر مبنای `SQM` (مترمربع) و نمایش بر اساس `MeasurementUnit` (`SQM`، `SQFT`، `HECTARE`) با ضرایب تبدیل صریح.
