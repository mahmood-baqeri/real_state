export type CalendarMode = "jalali" | "gregorian" | (string & {});
export type CurrencyCode = "IRT" | "IRR" | "USD" | "EUR" | "AED" | (string & {});
export type AreaUnit = "SQM" | "SQFT";
export type PlatformRole = "SUPER_ADMIN" | "AGENCY_USER" | "CUSTOMER";
export type EffectiveRole =
  | "SUPER_ADMIN"
  | "AGENCY_MANAGER"
  | "SALES_MANAGER"
  | "BRANCH_MANAGER"
  | "AGENCY_ACCOUNTANT"
  | "SUPPORT_AGENT"
  | "AGENT"
  | "CUSTOMER";

export interface AgencyMembershipBrief {
  id: string;
  agency_id: string;
  agency_name: string;
  role_code: string;
  role_name: string;
  branch_id: string | null;
  branch_name: string | null;
}

export interface UserProfile {
  id: string;
  phone_number: string;
  email: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  platform_role: PlatformRole;
  status: string;
  preferred_language: string;
  preferred_calendar: CalendarMode;
  preferred_currency: CurrencyCode;
  timezone: string;
  is_mfa_enabled: boolean;
  effective_permissions: string[];
  memberships: AgencyMembershipBrief[];
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface ProvinceItem {
  id: string;
  country_id?: string;
  code?: string;
  name_fa: string;
  name_en: string;
  slug: string;
  center_lat: string | null;
  center_lng: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface CityItem {
  id: string;
  province_id: string;
  province_name?: string;
  name_fa: string;
  name_en: string;
  slug: string;
  center_lat: string | null;
  center_lng: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface DistrictItem {
  id: string;
  city_id: string;
  city_name?: string;
  name_fa: string;
  name_en: string;
  slug: string;
  center_lat: string | null;
  center_lng: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface NeighborhoodItem {
  id: string;
  district_id: string;
  district_name?: string;
  city_id?: string;
  city_name?: string;
  name_fa: string;
  name_en: string;
  slug: string;
  center_lat: string | null;
  center_lng: string | null;
  sort_order: number;
  is_active: boolean;
}

export type AmenityValueType = "BOOLEAN" | "INTEGER" | "DECIMAL" | "TEXT" | "CHOICE";

export interface AmenityCategoryItem {
  code: string;
  name_fa: string;
  name_en: string;
  icon_name?: string;
  sort_order: number;
  is_active: boolean;
}

export interface AmenityItem {
  code: string;
  category_code?: string | null;
  category_name_fa?: string;
  name_fa: string;
  name_en: string;
  icon_name?: string;
  value_type?: AmenityValueType;
  unit_label?: string;
  options_json?: string[];
  value_text?: string;
  value_number?: string | null;
  sort_order?: number;
  is_active?: boolean;
}

export interface AmenityValueInput {
  code: string;
  value_text?: string;
  value_number?: number | string | null;
}

export interface PropertyMediaItem {
  id: string;
  media_type: string;
  url: string;
  title: string;
  is_cover: boolean;
  is_public: boolean;
  sort_order?: number;
}

export interface PropertyLocation {
  country?: string;
  country_id?: string;
  province_id?: string | null;
  city_id?: string | null;
  district_id?: string | null;
  neighborhood_id?: string | null;
  province: string;
  city: string;
  district: string;
  neighborhood: string;
  street?: string;
  full_address?: string;
  postal_code?: string;
  latitude: string | null;
  longitude: string | null;
  hide_exact_address: boolean;
}

export interface PropertyPriceHistoryItem {
  id: string;
  previous_price: string;
  new_price: string;
  currency_code: CurrencyCode;
  changed_at: string;
}

export interface PropertyStatusHistoryItem {
  id: string;
  from_status: string;
  to_status: string;
  reason: string;
  changed_at: string;
}

export interface PropertyTimelineEvent {
  id: string;
  type: string;
  title: string;
  detail: string;
  occurred_at: string;
}

export interface PropertyItem {
  id: string;
  property_code: string;
  title: string;
  description: string;
  property_type: { code: string; name_fa: string; name_en: string; category: string };
  deal_type: { code: string; name_fa: string; name_en: string; is_rental: boolean };
  property_type_id?: string;
  deal_type_id?: string;
  usage_type: string;
  status: string;
  visibility?: string;
  is_featured: boolean;
  is_exclusive?: boolean;
  is_negotiable: boolean;
  land_area_sqm: string;
  built_area_sqm: string;
  bedrooms: number;
  bathrooms: number;
  floor_number: number | null;
  total_floors: number | null;
  building_age: number | null;
  deed_type: string;
  deed_status?: string;
  currency: CurrencyCode;
  total_price: string;
  price_per_sqm: string;
  deposit_amount: string;
  rent_amount: string;
  min_acceptable_price?: string | null;
  amenities: AmenityItem[];
  location: PropertyLocation | null;
  media_items: PropertyMediaItem[];
  agency_id: string;
  agency_name: string;
  branch_id?: string | null;
  view_count: number;
  inquiry_count?: number;
  owners?: { id: string; full_name: string; phone_number?: string; ownership_percent?: string; ownership_share_percent?: string; masked?: boolean; message?: string }[];
  assigned_agents?: { membership_id: string; full_name: string; role: string }[];
  price_history?: PropertyPriceHistoryItem[];
  status_history?: PropertyStatusHistoryItem[];
  latest_rejection_reason?: string | null;
  documents?: DocumentItem[];
  related_properties?: PublicSearchProperty[];
  virtual_tour_id?: string | null;
  virtual_tour_status?: string | null;
  has_virtual_tour?: boolean;
  created_at: string;
}

export interface PublicSearchProperty {
  id: string;
  property_code: string;
  title: string;
  property_type_id: string;
  property_type_name: string;
  deal_type_id: string;
  deal_type_name: string;
  built_area_sqm: string;
  bedrooms: number;
  total_price: string;
  price_per_sqm: string;
  deposit_amount: string;
  rent_amount: string;
  currency_id: CurrencyCode;
  is_featured: boolean;
  province_id?: string | null;
  city_id?: string | null;
  district_id?: string | null;
  neighborhood_id?: string | null;
  province?: string;
  city: string;
  district: string;
  neighborhood: string;
  latitude?: string | null;
  longitude?: string | null;
  amenities?: { code: string; name_fa: string }[];
  agency_name: string;
  cover_url: string | null;
}

export interface PropertyCatalog {
  property_types: { code: string; name_fa: string; name_en: string; category: string }[];
  deal_types: { code: string; name_fa: string; name_en: string; is_rental: boolean }[];
  amenity_categories?: AmenityCategoryItem[];
  amenities: AmenityItem[];
}

export interface AgencyItem {
  id: string;
  name: string;
  slug: string;
  registration_number: string;
  tax_id: string;
  phone: string;
  email: string;
  description: string;
  country: string;
  default_currency: CurrencyCode;
  default_calendar: CalendarMode;
  timezone: string;
  area_unit: AreaUnit;
  status: string;
  owner_name: string;
  created_at: string;
}

export interface AgencyAccessPolicy {
  id: string;
  agency_id: string;
  property_view_scope: string;
  property_edit_scope: string;
  customer_view_scope: string;
  customer_edit_scope: string;
  owner_pii_visibility: string;
  negotiation_visibility: string;
  contract_visibility: string;
  financial_visibility: string;
  commission_visibility: string;
  agent_performance_visibility: string;
}

export interface BranchItem {
  id: string;
  name: string;
  code: string;
  province: string;
  city: string;
  address: string;
  phone: string;
  is_main: boolean;
  is_active: boolean;
}

export interface CooperationItem {
  id: string;
  requester_agency_id: string;
  requester_agency_name: string;
  provider_agency_id: string;
  provider_agency_name: string;
  default_split_percent: string;
  status: string;
}

export interface TeamMemberItem {
  id: string;
  user_id: string;
  full_name: string;
  phone_number: string;
  email: string | null;
  role_code: string;
  role_name: string;
  branch_id: string | null;
  branch_name: string | null;
  status: string;
  joined_at: string;
  overrides: { permission_code: string; effect: string }[];
}

export interface RoleItem {
  id: string;
  code: string;
  name: string;
  scope: string;
  is_system_role: boolean;
  permissions: string[];
}

export interface PermissionItem {
  code: string;
  module: string;
  description: string;
}

export interface EmployeeItem {
  id: string;
  membership_id: string;
  full_name: string;
  phone_number: string;
  role_name: string;
  branch_name: string | null;
  employee_code: string;
  job_title: string;
  employment_type: string;
  hire_date: string;
  monthly_sales_target: string;
  is_active: boolean;
  compensation_plans: {
    id: string;
    model_type: string;
    base_salary: string;
    commission_multiplier: string;
    effective_from: string;
    is_active: boolean;
  }[];
}

export interface CustomerItem {
  id: string;
  agency: string;
  agency_name?: string | null;
  customer_type: string;
  full_name: string;
  primary_phone: string;
  secondary_phone: string;
  email: string;
  source: string;
  assigned_membership: string | null;
  assigned_agent_name: string | null;
  lead_score: number;
  readiness_level: string;
  tags: string[];
  is_active: boolean;
  shares: { id: string; membership_id: string; agent_name: string; access_level: string }[];
  requirements: {
    id: string;
    deal_type: string;
    property_type: string;
    target_city: string;
    target_districts: string[];
    min_area_sqm: string;
    max_area_sqm: string;
    min_budget: string;
    max_budget: string;
    min_bedrooms: number;
  }[];
  interactions?: {
    id: string;
    channel: string;
    summary: string;
    is_private: boolean;
    author_name: string;
    created_at: string;
  }[];
  tasks?: {
    id: string;
    title: string;
    status: string;
    due_at: string;
    assigned_name: string | null;
  }[];
  contracts?: {
    id: string;
    contract_number: string;
    status: string;
    amount: string;
    property_title: string | null;
    created_at: string;
  }[];
  negotiations?: {
    id: string;
    status: string;
    property_title: string | null;
    latest_proposed_price: string;
    created_at: string;
  }[];
  appointments?: {
    id: string;
    status: string;
    property_title: string | null;
    scheduled_start: string;
  }[];
  documents?: {
    id: string;
    title: string;
    category: string;
    created_at: string;
  }[];
  created_at: string;
}

export interface LeadActivityItem {
  id: string;
  activity_type: string;
  note: string;
  created_by_name: string;
  created_at: string;
}

export interface LeadItem {
  id: string;
  agency_id?: string;
  agency_name?: string | null;
  full_name: string;
  phone_number: string;
  request_type: string;
  property_id: string | null;
  property_title: string | null;
  source: string;
  assigned_membership_id?: string | null;
  assigned_agent_name: string | null;
  converted_customer_id: string | null;
  status: string;
  notes: string;
  activities?: LeadActivityItem[];
  created_at: string;
}

export interface PipelineStage {
  id: string;
  code: string;
  name: string;
  sort_order: number;
  is_terminal_won: boolean;
  is_terminal_lost: boolean;
}

export interface PipelineItem {
  id: string;
  customer: string;
  customer_name: string;
  stage: string;
  stage_code: string;
  stage_name: string;
  property: string | null;
  property_title: string | null;
  assigned_agent_name: string | null;
  notes: string;
  updated_at: string;
}

export interface FollowUpTask {
  id: string;
  customer: string;
  customer_name: string;
  agent_name: string;
  title: string;
  due_at: string;
  status: string;
  completed_at: string | null;
}

export interface InteractionItem {
  id: string;
  customer_id: string;
  customer_name: string;
  agent_name: string | null;
  channel: string;
  summary: string;
  is_private: boolean;
  created_at: string;
}

export interface AppointmentItem {
  id: string;
  agency: string;
  property: string;
  property_title: string;
  customer: string;
  customer_name: string;
  agent_membership: string;
  agent_name: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
  customer_feedback: string;
  agent_report: string;
  created_at: string;
}

export interface OfferVersionItem {
  id: string;
  version_number: number;
  offered_by: string;
  recipient_role?: string;
  currency: CurrencyCode;
  proposed_price: string;
  proposed_deposit: string;
  proposed_rent: string;
  discount_amount: string;
  payment_terms?: Record<string, unknown>;
  notes?: string;
  response_note?: string;
  status: string;
  valid_until?: string | null;
  created_at: string;
}

export interface NegotiationActivityItem {
  id: string;
  activity_type: string;
  title: string;
  description: string;
  outcome: string;
  next_action: string;
  next_action_due_at: string | null;
  is_completed: boolean;
  actor_name: string;
  created_at: string;
}

export interface NegotiationItem {
  id: string;
  agency_id?: string;
  property_id: string;
  property_code: string;
  property_title: string;
  property_location?: string;
  customer_id: string;
  customer_name: string;
  owner_customer_id?: string | null;
  owner_name?: string;
  agent_membership_id?: string | null;
  agent_name: string;
  deal_type: string;
  deal_type_name: string;
  status: string;
  asking_price?: string;
  initial_proposed_price?: string;
  latest_proposed_price?: string;
  agreed_price?: string | null;
  price_delta?: string;
  price_delta_percent?: number;
  next_followup_at?: string | null;
  next_action?: string;
  is_followup_overdue?: boolean;
  last_activity_at?: string | null;
  outcome_reason?: string;
  converted_contract_id?: string | null;
  converted_contract_number?: string | null;
  notes: string;
  offers: OfferVersionItem[];
  activities?: NegotiationActivityItem[];
  created_at: string;
}

export interface NegotiationAnalytics {
  total_count: number;
  active_count: number;
  won_count: number;
  lost_count: number;
  overdue_followups_count: number;
  win_rate_percent: number;
  avg_discount_percent: number;
  avg_duration_days: number;
  avg_offers_per_negotiation: number;
  stage_breakdown: { status: string; count: number }[];
  failure_reasons: { reason: string; count: number }[];
}

export interface ContractAmendmentItem {
  id: string;
  amendment_number: number;
  title: string;
  reason: string;
  changes_json: Record<string, unknown>;
  status: string;
  approved_by_name?: string | null;
  approved_at?: string | null;
  created_at: string;
}

export interface ContractItem {
  id: string;
  agency_id?: string;
  agency_name?: string | null;
  contract_number: string;
  internal_tracking_code: string;
  contract_type: string;
  property_id: string;
  property_code: string;
  property_title: string;
  deal_type: string;
  deal_type_name: string;
  currency: CurrencyCode;
  amount: string;
  deposit_amount: string;
  rent_amount: string;
  advance_payment: string;
  remaining_amount: string;
  payment_method: string;
  status: string;
  is_editable?: boolean;
  start_date: string | null;
  end_date: string | null;
  parties: { id: string; full_name: string; party_role: string; customer_id: string | null }[];
  amendments?: ContractAmendmentItem[];
  created_at: string;
}

export interface DealItem {
  id: string;
  deal_code: string;
  contract_id: string;
  contract_number: string;
  property_id: string;
  property_code: string;
  property_title: string;
  primary_agent_name: string;
  co_agent_name: string | null;
  currency: CurrencyCode;
  deal_value: string;
  status: string;
  closed_at: string | null;
  created_at: string;
}

export interface CommissionItem {
  id: string;
  deal_id: string;
  deal_code: string;
  property_title: string;
  currency: CurrencyCode;
  base_amount: string;
  gross_commission: string;
  discount_amount: string;
  tax_amount: string;
  net_distributable: string;
  status: string;
  shares: {
    id: string;
    beneficiary_type: string;
    beneficiary_name: string;
    share_percent_of_net: string;
    calculated_amount: string;
    is_included_in_payroll: boolean;
  }[];
  created_at: string;
}

export interface CoaAccount {
  id: string;
  code: string;
  name: string;
  account_type: string;
  level: string;
  parent_id: string | null;
}

export interface JournalEntryItem {
  id: string;
  entry_number: string;
  entry_date: string;
  description: string;
  currency: CurrencyCode;
  status: string;
  source_type: string;
  lines: {
    id: string;
    account_id: string;
    account_code: string;
    account_name: string;
    description: string;
    debit: string;
    credit: string;
  }[];
}

export interface PayrollCycleItem {
  id: string;
  title: string;
  period_start: string;
  period_end: string;
  status: string;
  payslips: {
    id: string;
    employee_code: string;
    employee_name: string;
    base_salary_amount: string;
    commission_amount: string;
    tax_amount: string;
    net_payable: string;
    status: string;
    items: { id: string; item_type: string; description: string; amount: string }[];
  }[];
}

export interface DocumentItem {
  id: string;
  agency_id?: string;
  agency_name?: string | null;
  title: string;
  category: string;
  access_level: string;
  property_id: string | null;
  property_title: string | null;
  customer_id?: string | null;
  customer_name: string | null;
  contract_id?: string | null;
  contract_number: string | null;
  versions: {
    id: string;
    version_number: number;
    file_key: string;
    mime_type: string;
    file_size_bytes: number;
  }[];
  created_at: string;
}

export interface NotificationItem {
  id: string;
  agency_id: string | null;
  agency_name: string | null;
  channel: string;
  title: string;
  body: string;
  delivery_status: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor_name: string;
  actor_phone: string | null;
  ip_address: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface GlobalSearchHit {
  id: string;
  title: string;
  subtitle: string;
  href: string;
}

export interface GlobalSearchResult {
  properties: GlobalSearchHit[];
  customers: GlobalSearchHit[];
  owners: GlobalSearchHit[];
  agents: GlobalSearchHit[];
  contracts: GlobalSearchHit[];
  tickets: GlobalSearchHit[];
  documents: GlobalSearchHit[];
  articles: GlobalSearchHit[];
  total_hits: number;
}

export interface SavedViewItem {
  id: string;
  module: string;
  title: string;
  filters_json: Record<string, string>;
  sort_by: string;
  columns_json: string[];
  layout_mode: string;
  is_default: boolean;
}

export interface UnifiedCalendarEvent {
  id: string;
  event_type: "VIEWING" | "TASK" | "CONTRACT" | "CHEQUE";
  title: string;
  subtitle: string;
  start_at: string;
  end_at: string | null;
  status: string;
  href: string;
}

export interface DashboardWidgetConfig {
  id: string;
  title: string;
  enabled: boolean;
}

export interface DashboardLayoutConfig {
  role_code: string;
  widgets: DashboardWidgetConfig[];
  default_period_days: number;
}

export interface OnboardingStepItem {
  key: string;
  title: string;
  href: string;
  completed: boolean;
}

export interface OnboardingProgressData {
  role_code: string;
  dismissed: boolean;
  completed_steps: string[];
  steps: OnboardingStepItem[];
}

export interface OperationsCenterData {
  summary: {
    overdue_tasks_count: number;
    pending_tasks_count: number;
    expiring_contracts_count: number;
    due_cheques_count: number;
    urgent_tickets_count: number;
    pending_properties_count: number;
  };
  overdue_tasks: {
    id: string;
    title: string;
    customer_name: string;
    agent_name: string;
    due_at: string;
    is_overdue: boolean;
    href: string;
  }[];
  expiring_contracts: {
    id: string;
    contract_number: string;
    property_title: string;
    end_date: string | null;
    status: string;
    href: string;
  }[];
  due_cheques: {
    id: string;
    cheque_number: string;
    direction: string;
    amount: string;
    due_date: string;
    status: string;
    href: string;
  }[];
  urgent_tickets: {
    id: string;
    ticket_number: string;
    subject: string;
    priority: string;
    status: string;
    created_at: string;
    href: string;
  }[];
  pending_properties: {
    id: string;
    property_code: string;
    title: string;
    total_price: string;
    created_at: string;
    href: string;
  }[];
}

export interface AnalyticsData {
  period_days: number;
  properties_by_status: { status: string; count: number }[];
  deals_by_status: { status: string; count: number; volume: string }[];
  leads_by_status: { status: string; count: number }[];
  sales_funnel?: { stage: string; count: number }[];
  district_breakdown?: { district: string; count: number; avg_price_per_sqm: string }[];
  timeline_series?: {
    label: string;
    deals_count: number;
    properties_added: number;
    deal_volume: string;
    revenue: string;
    expense: string;
  }[];
  branch_comparison?: {
    branch_id: string;
    branch_name: string;
    properties_count: number;
    members_count: number;
  }[];
  activity_heatmap?: {
    day: string;
    slots: { slot: string; count: number }[];
  }[];
  period_comparison?: {
    current_volume: string;
    previous_volume: string;
    current_deals_count: number;
    previous_deals_count: number;
  };
  negotiations_count: number;
  agent_leaderboard: {
    membership_id: string;
    agent_name: string;
    total_commission: string;
    deals_count: number;
  }[];
}

export interface RssTopicsResult {
  source: string;
  requires_human_approval: boolean;
  topics: {
    title: string;
    angle: string;
    reference_url?: string;
  }[];
}

export interface PaymentGatewayItem {
  id: string;
  provider_key: string;
  display_name: string;
  description: string;
  is_sandbox: boolean;
  priority: number;
  required_fields: string[];
  last_check_status: string;
}

export interface ManagedGatewayConfig {
  id: string;
  agency_id: string | null;
  provider_key: string;
  display_name: string;
  description: string;
  priority: number;
  is_active: boolean;
  is_sandbox: boolean;
  config_json: Record<string, unknown>;
  has_credentials: boolean;
  masked_credentials: Record<string, string>;
  last_checked_at: string | null;
  last_check_status: string;
  last_check_message: string;
}

export interface AiStatusResponse {
  provider: string;
  configured: boolean;
  status: string;
  base_url: string;
  default_model: string;
  supported_models: (string | { id: string; label: string })[];
  message: string;
}

export interface AiChatMessageResult {
  reply: string;
  provider: string;
  model: string;
  task_mode: string;
  tokens_used: number;
  latency_ms: number;
  fallback_note?: string;
}

export interface SystemSettingItem {
  id: string;
  key: string;
  agency_id: string | null;
  country_code: string;
  title_fa: string;
  title_en: string;
  description: string;
  category: string;
  subcategory: string;
  value_type: "STRING" | "INTEGER" | "DECIMAL" | "BOOLEAN" | "JSON" | "SECRET" | "COLOR" | "SELECT" | string;
  value: unknown;
  default_value: unknown;
  has_secret_value: boolean;
  validation_schema: {
    min?: number;
    max?: number;
    options?: string[];
    [key: string]: unknown;
  };
  is_active: boolean;
  sensitivity_level: "PUBLIC" | "ADMIN" | "SECRET" | string;
  is_editable: boolean;
  requires_restart: boolean;
  sort_order: number;
  updated_at: string;
}

export interface SystemSettingHistoryItem {
  id: string;
  setting_key: string;
  agency_id_snapshot: string | null;
  previous_value: unknown;
  new_value: unknown;
  is_secret: boolean;
  change_reason: string;
  changed_by_name: string;
  created_at: string;
}

export interface BrandMediaSlotItem {
  /** Backward-compatible alias of slot_key; BrandMediaSlot uses slot_key as its primary key. */
  id?: string;
  slot_key: string;
  category: string;
  title_fa: string;
  description?: string;
  image_url: string;
  dark_image_url: string;
  alt_text: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface SiteContentBlockItem {
  id?: string;
  slug_key: string;
  page_key: string;
  section_key: string;
  title_fa: string;
  subtitle_fa: string;
  body_html: string;
  cta_label: string;
  cta_href: string;
  items_json: Record<string, unknown>[];
  status?: string;
  sort_order?: number;
  is_active?: boolean;
}

export interface CalendarSystemItem {
  code: string;
  name_fa: string;
  name_en: string;
  date_format: string;
  datetime_format: string;
  is_default: boolean;
  is_active?: boolean;
  sort_order?: number;
}

export interface CountryItem {
  code: string;
  alpha3_code: string;
  name_fa: string;
  name_en: string;
  default_language: string;
  supported_languages: string[];
  default_calendar: string;
  supported_calendars: string[];
  default_currency: string;
  default_currency_code?: string;
  timezone: string;
  default_timezone?: string;
  phone_prefix: string;
  flag_url: string;
  sort_order?: number;
  is_active?: boolean;
  area_unit?: string;
}

export interface CurrencyConfigItem {
  code: string;
  name_fa: string;
  name_en: string;
  symbol: string;
  decimal_places: number;
  minor_unit: string;
  description: string;
  base_unit_factor?: string;
  exchange_rate_to_base: string;
  sort_order?: number;
  is_active?: boolean;
}

export interface ExchangeRateItem {
  id: string;
  base_currency_code: string;
  quote_currency_code: string;
  rate: string;
  source: string;
  effective_at: string;
  is_active?: boolean;
}

export interface ExchangeRateHistoryItem {
  id: string;
  base_currency_code: string;
  quote_currency_code: string;
  previous_rate: string | null;
  new_rate: string;
  source: string;
  change_reason: string;
  changed_by_name: string;
  created_at: string;
}

export interface PublicLegalSummaryItem {
  slug: string;
  doc_type: string;
  title_fa: string;
  version_number: number;
  requires_acceptance: boolean;
  effective_at: string | null;
}

export interface PublicBootstrapPayload {
  public_settings: Record<string, unknown>;
  branding: Record<string, BrandMediaSlotItem>;
  content_blocks: Record<string, SiteContentBlockItem>;
  legal_documents: PublicLegalSummaryItem[];
  countries: CountryItem[];
  calendars: CalendarSystemItem[];
  currencies: CurrencyConfigItem[];
  exchange_rates: ExchangeRateItem[];
  map_provider: {
    provider_key: string;
    display_name: string;
    tile_url: string;
    dark_tile_url: string;
    attribution: string;
    max_zoom: number;
    requires_api_key: boolean;
  };
}

export interface SmsTemplateItem {
  id: string;
  key: string;
  event_type: string;
  name_fa: string;
  body_template: string;
  sample_tokens: string[];
  provider_template_id: string;
  is_active: boolean;
  updated_at: string;
}

export interface SmsDeliveryLogItem {
  id: string;
  recipient_masked: string;
  event_type: string;
  template_key: string;
  provider_key: string;
  status: string;
  message_id: string;
  cost_amount: string;
  error_message: string;
  agency_name: string | null;
  actor_name: string | null;
  created_at: string;
}

export interface SmsSettingsStats {
  enabled: boolean;
  daily_cap: number;
  cost_per_segment: string;
  fallback_enabled: boolean;
  event_toggles: Record<string, boolean>;
  stats: {
    today_sent: number;
    month_sent: number;
    month_failed: number;
    month_estimated_cost: string;
  };
}

export interface AdminSessionItem {
  id: string;
  user_id: string;
  user_name: string;
  user_phone: string;
  device_name: string;
  device_type: string;
  auth_method: string;
  ip_address: string | null;
  user_agent: string;
  is_suspicious: boolean;
  suspicious_reason: string;
  last_active_at: string;
  expires_at: string | null;
  created_at: string;
  is_current: boolean;
}

export interface SecurityEventItem {
  id: string;
  identifier: string;
  user_name: string | null;
  ip_address: string | null;
  succeeded: boolean;
  failure_reason: string;
  created_at: string;
}

export interface LegalDocumentVersionItem {
  id: string;
  version_number: number;
  title_fa: string;
  summary: string;
  change_note: string;
  edited_by_name: string;
  created_at: string;
}

export interface LegalSectionItem {
  id?: string;
  title: string;
  body_html: string;
  sort_order: number;
}

export interface LegalDocumentItem {
  id: string;
  slug: string;
  doc_type: string;
  title_fa: string;
  title_en: string;
  summary: string;
  body_html: string;
  sections_json?: LegalSectionItem[];
  status: string;
  version_number: number;
  requires_acceptance: boolean;
  effective_at: string | null;
  published_at: string | null;
  meta_title: string;
  meta_description: string;
  sort_order: number;
  is_system_doc: boolean;
  updated_at: string;
  accepted_by_current_user?: boolean;
  versions?: LegalDocumentVersionItem[];
}

export interface LegalAcceptanceItem {
  id: string;
  document_slug: string;
  document_title: string;
  version_number: number;
  user_name: string;
  user_phone: string;
  ip_address: string | null;
  accepted_at: string;
}

export interface PropertyVerificationAnomaly {
  code: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | string;
  message: string;
}

export interface PropertyVerificationData {
  id?: string;
  property_id: string;
  physical_verified: boolean;
  physical_notes: string;
  deed_verified: boolean;
  deed_notes: string;
  owner_consent_verified: boolean;
  owner_consent_notes: string;
  verification_status: "UNVERIFIED" | "PENDING" | "VERIFIED" | "REJECTED" | "EXCEPTION_APPROVED" | string;
  verified_by_name: string | null;
  verified_at: string | null;
  evidence_document_id: string | null;
  evidence_document_title: string | null;
  exception_override: boolean;
  override_reason: string;
  override_by_name: string | null;
  history: {
    id: string;
    from_status: string;
    to_status: string;
    notes: string;
    changed_by_name: string;
    created_at: string;
  }[];
  anomaly_flags: PropertyVerificationAnomaly[];
}

export interface PropertyViolationReportItem {
  id: string;
  property_id: string;
  property_code: string;
  property_title: string;
  agency_id: string;
  agency_name: string;
  reason_type: string;
  details: string;
  status: string;
  reporter_name: string;
  inspector_name: string | null;
  resolution_note: string;
  resolved_at: string | null;
  created_at: string;
}

export interface SystemHealthPayload {
  database_ok: boolean;
  redis_ok: boolean;
  environment_mode: string;
  settings_count: number;
  active_sessions_count: number;
  suspicious_sessions_count: number;
  env_status: {
    key: string;
    label: string;
    configured: boolean;
  }[];
  providers_summary: {
    category: string;
    provider_key: string;
    display_name: string;
    is_active: boolean;
    is_sandbox: boolean;
    last_check_status: string;
  }[];
}

// ---------- Virtual Tour, 360° Experience, Floor Plan & 3D Model Module ----------

export interface VirtualTourRoomTypeOption {
  code: string;
  /** API currently returns `label`; `label_fa` is accepted for backward compatibility. */
  label?: string;
  label_fa?: string;
}

export interface VirtualTourCapturePolicy {
  horizontal_steps: number;
  require_ceiling_floor: boolean;
  target_overlap_percent: number;
  min_image_width_px: number;
  min_image_height_px: number;
  min_blur_score: number;
  min_brightness: number;
  max_brightness: number;
  min_contrast: number;
  min_usable_images_for_stitch: number;
  stitcher_engine: string;
  panorama_output_width: number;
  max_upload_file_mb: number;
}

export interface VirtualTourLimitsConfig {
  module_enabled: boolean;
  max_floors: number;
  max_scenes: number;
  max_hotspots_per_scene: number;
  require_manager_approval: boolean;
  require_property_verified_for_publish: boolean;
  dollhouse_wall_height_m: number;
  dollhouse_wall_thickness_m: number;
  dollhouse_default_opacity: number;
  analytics_enabled: boolean;
}

export interface VirtualTourConfigBundle {
  room_types: VirtualTourRoomTypeOption[];
  capture_policy: VirtualTourCapturePolicy;
  limits: VirtualTourLimitsConfig;
}

export interface TourFloorItem {
  id: string;
  tour_id: string;
  title: string;
  order: number;
  elevation_m: string;
  description: string;
  created_at: string;
}

export interface PanoramaVersionItem {
  id: string;
  scene_id: string;
  capture_session_id: string | null;
  version: number;
  state: string;
  projection: string;
  width_px: number;
  height_px: number;
  source_image_count: number;
  engine: string;
  quality_report: Record<string, unknown>;
  is_current: boolean;
  panorama_url: string | null;
  thumbnail_url: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  rejection_reason: string;
  created_at: string;
}

export interface HotspotItem {
  id: string;
  scene_id: string;
  kind: "info" | "scene_link" | "feature" | "media" | "measurement" | string;
  title: string;
  body: string;
  yaw: number;
  pitch: number;
  target_scene_id: string | null;
  target_scene_title: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface SceneLinkItem {
  id: string;
  tour_id: string;
  source_scene_id: string;
  source_scene_title: string;
  target_scene_id: string;
  target_scene_title: string;
  yaw: number;
  pitch: number;
  title: string;
  bidirectional: boolean;
  reverse_yaw: number | null;
  created_at: string;
}

export interface TourSceneItem {
  id: string;
  tour_id: string;
  floor_id: string;
  floor_title: string;
  title: string;
  room_type: string;
  description: string;
  order: number;
  is_start_scene: boolean;
  active: boolean;
  initial_yaw: number;
  initial_pitch: number;
  thumbnail_url: string | null;
  width_m: string | null;
  length_m: string | null;
  height_m: string | null;
  geometry_source: string;
  current_panorama: PanoramaVersionItem | null;
  panorama_count: number;
  capture_sessions_count: number;
  hotspots_count: number;
  panoramas?: PanoramaVersionItem[];
  hotspots?: HotspotItem[];
  outgoing_links?: SceneLinkItem[];
  created_at: string;
}

export interface CaptureGuideStepItem {
  id: string;
  sequence: number;
  yaw: number;
  pitch: number;
  label: string;
  required: boolean;
  expected_overlap_percent: number;
  state: "pending" | "captured" | "passed" | "needs_retake" | "skipped" | string;
  guidance: string;
  image_id: string | null;
  image_url: string | null;
}

export interface CaptureImageAnalysis {
  corrupt?: boolean;
  width?: number;
  height?: number;
  blur_score?: number;
  brightness?: number;
  contrast?: number;
  noise_level?: number;
  dhash?: string;
  min_hamming_distance?: number;
  is_duplicate?: boolean;
  issues?: string[];
  warnings?: string[];
  recommendations?: string[];
}

export interface CaptureImageItem {
  id: string;
  session_id: string;
  scene_id: string;
  sequence: number;
  filename: string;
  mime_type: string;
  size_bytes: number;
  width: number;
  height: number;
  status: string;
  analysis: CaptureImageAnalysis;
  yaw: number;
  pitch: number;
  image_url: string;
  captured_at: string;
}

export interface CaptureSessionSummary {
  session_id: string;
  total_steps: number;
  captured_steps: number;
  skipped_steps: number;
  retake_steps: number;
  usable_images_count: number;
  rejected_images_count: number;
  min_usable_required: number;
  ready_to_stitch: boolean;
  has_ceiling: boolean;
  has_floor: boolean;
  angular_gaps: string[];
  completion_percent: number;
}

export interface CaptureSessionItem {
  id: string;
  tour_id: string;
  scene_id: string;
  scene_title: string;
  status: string;
  device_info: Record<string, unknown>;
  capture_config: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  summary: CaptureSessionSummary;
  steps: CaptureGuideStepItem[];
  images: CaptureImageItem[];
}

export interface ProcessingJobItem {
  id: string;
  tour_id: string;
  scene_id: string | null;
  scene_title: string | null;
  job_type: string;
  state: "queued" | "running" | "succeeded" | "failed" | "cancelled" | string;
  progress: number;
  current_step: string;
  celery_task_id: string;
  error: string;
  result: Record<string, unknown>;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface QualityIssueItem {
  code: string;
  message: string;
  fix?: string;
}

export interface TourQualityReportItem {
  id: string;
  tour_id: string;
  is_ready_to_publish: boolean;
  blocking_issues_count: number;
  warning_issues_count: number;
  report_data: {
    blocking_issues?: QualityIssueItem[];
    warnings?: QualityIssueItem[];
    scenes_count?: number;
    captured_scenes_count?: number;
    approved_panoramas_count?: number;
    incomplete_scenes?: { scene_id: string; title: string; reason: string }[];
    links_count?: number;
    rejected_images_count?: number;
    failed_jobs_count?: number;
    plan_status?: Record<string, unknown>;
    dollhouse_status?: Record<string, unknown>;
    scan_status?: {
      total_count?: number;
      validated_count?: number;
      total_points?: number;
    };
  };
  created_at: string;
}

export interface TourPublicationItem {
  id: string;
  tour_id: string;
  version: number;
  is_active: boolean;
  public_slug: string;
  published_by_name: string | null;
  published_at: string;
  unpublished_at: string | null;
  scenes_count: number;
  floors_count: number;
}

export interface VirtualTourDetail {
  id: string;
  property_id: string;
  property_code: string;
  property_title: string;
  property_status: string;
  property_visibility: string;
  agency_id: string;
  branch_id: string | null;
  title: string;
  description: string;
  status: string;
  settings_override: Record<string, unknown>;
  published_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  floors: TourFloorItem[];
  scenes: TourSceneItem[];
  links: SceneLinkItem[];
  floorplans?: FloorPlanAssetItem[];
  rooms?: RoomGeometryItem[];
  walls?: WallSegmentItem[];
  generated_models?: GeneratedModelAssetItem[];
  current_model?: GeneratedModelAssetItem | null;
  scans?: ScanAssetItem[];
  active_publication: TourPublicationItem | null;
  latest_quality_report: TourQualityReportItem | null;
  recent_jobs: ProcessingJobItem[];
  config: VirtualTourConfigBundle;
}

export interface VirtualTourGetEnvelope {
  tour?: null;
  id?: string;
  config: VirtualTourConfigBundle;
}

export interface PublicVirtualTourScene {
  id: string;
  floor_id: string;
  floor_title: string;
  title: string;
  room_type: string;
  description: string;
  is_start_scene: boolean;
  initial_yaw: number;
  initial_pitch: number;
  panorama_version_id: string;
  panorama_url: string;
  thumbnail_url: string;
  width_px: number;
  height_px: number;
  links: {
    id: string;
    target_scene_id: string;
    target_scene_title: string;
    yaw: number;
    pitch: number;
    title: string;
  }[];
  hotspots: {
    id: string;
    kind: string;
    title: string;
    body: string;
    yaw: number;
    pitch: number;
    target_scene_id: string | null;
    metadata: Record<string, unknown>;
  }[];
}

export interface PublicVirtualTourData {
  tour_id: string;
  property_id: string;
  publication_version: number;
  public_slug: string;
  published_at: string;
  title: string;
  description: string;
  floors: {
    id: string;
    title: string;
    order: number;
    elevation_m: string;
  }[];
  scenes: PublicVirtualTourScene[];
  floorplans?: FloorPlanAssetItem[];
  dollhouse?: GeneratedModelAssetItem | null;
  rooms?: RoomGeometryItem[];
}

export interface TourAnalyticsSummary {
  tour_id: string;
  total_views: number;
  unique_visitors: number;
  total_sessions: number;
  completed_sessions: number;
  completion_rate_percent: number;
  avg_duration_seconds: number;
  hotspot_clicks: number;
  dollhouse_opens: number;
  floorplan_opens: number;
  popular_scenes: { scene_id: string; title: string; visits: number }[];
  device_breakdown: { device_type: string; count: number }[];
}

export interface FloorPlanAssetItem {
  id: string;
  tour_id: string;
  floor_id: string;
  floor_title?: string;
  file_type: string;
  filename: string;
  width_px: number;
  height_px: number;
  scale_m_per_px: number | null;
  calibration_data: Record<string, unknown>;
  file_url: string;
  created_at: string;
}

export interface RoomGeometryItem {
  id: string;
  tour_id: string;
  floor_id: string;
  scene_id: string | null;
  scene_title?: string | null;
  label: string;
  room_type: string;
  polygon_points: [number, number][];
  area_sqm: string;
  perimeter_m: string;
  height_m: string;
  source: string;
  color_hex: string;
}

export interface WallSegmentItem {
  id: string;
  floor_id: string;
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  thickness_m: number;
  height_m: number;
  is_exterior?: boolean;
  openings?: WallOpeningItem[];
}

export interface WallOpeningItem {
  id: string;
  wall_id: string;
  kind: "door" | "window" | "arch" | "balcony" | string;
  offset_ratio: number;
  width_m: number;
  height_m: number;
  sill_height_m: number;
}

export interface GeneratedModelAssetItem {
  id: string;
  tour_id: string;
  version: number;
  format: string;
  state: string;
  geometry_source: string;
  estimated_accuracy: string;
  total_area_sqm: string;
  file_url: string;
  size_bytes: number;
  metadata: Record<string, unknown>;
  is_current: boolean;
  created_at: string;
}

export interface ScanProcessingResultItem {
  raw_points_count: number;
  downsampled_points_count: number;
  outlier_points_count: number;
  estimated_footprint_sqm: string;
  point_density_per_sqm: number;
  height_stats: {
    floor_y?: number;
    ceiling_y?: number;
    height_m?: number;
  };
  engine: string;
  notes: string;
}

export interface ScanBoundingBox {
  min?: [number, number, number];
  max?: [number, number, number];
  dimensions_m?: {
    width?: number;
    length?: number;
    height?: number;
  };
}

export interface ScanAssetItem {
  id: string;
  tour_id: string;
  floor_id: string | null;
  floor_title?: string | null;
  scene_id: string | null;
  scene_title?: string | null;
  format: string;
  filename: string;
  size_bytes: number;
  status: string;
  source_device: string;
  points_count: number;
  bounding_box: ScanBoundingBox;
  raw_file_url?: string;
  preview_glb_url: string | null;
  density_map_url: string | null;
  processing_notes: string;
  processing_result?: ScanProcessingResultItem | null;
  created_at: string;
}


