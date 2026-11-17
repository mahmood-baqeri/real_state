export type CalendarMode = "jalali" | "gregorian";
export type CurrencyCode = "IRT" | "IRR" | "USD" | "EUR" | "AED";
export type AreaUnit = "SQM" | "SQFT";
export type PlatformRole = "SUPER_ADMIN" | "AGENCY_USER" | "CUSTOMER";
export type EffectiveRole =
  | "SUPER_ADMIN"
  | "AGENCY_MANAGER"
  | "AGENCY_ACCOUNTANT"
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

export interface PropertyMediaItem {
  id: string;
  media_type: string;
  url: string;
  title: string;
  is_cover: boolean;
  is_public: boolean;
}

export interface PropertyLocation {
  country?: string;
  country_id?: string;
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
  amenities: { code: string; name_fa: string; name_en: string }[];
  location: PropertyLocation | null;
  media_items: PropertyMediaItem[];
  agency_id: string;
  agency_name: string;
  branch_id?: string | null;
  view_count: number;
  inquiry_count?: number;
  owners?: { id: string; full_name: string; phone_number?: string; ownership_percent: string }[];
  assigned_agents?: { membership_id: string; full_name: string; role: string }[];
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
  city: string;
  district: string;
  neighborhood: string;
  agency_name: string;
  cover_url: string | null;
}

export interface PropertyCatalog {
  property_types: { code: string; name_fa: string; name_en: string; category: string }[];
  deal_types: { code: string; name_fa: string; name_en: string; is_rental: boolean }[];
  amenities: { code: string; name_fa: string; name_en: string }[];
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
  created_at: string;
}

export interface LeadItem {
  id: string;
  full_name: string;
  phone_number: string;
  request_type: string;
  property_id: string | null;
  property_title: string | null;
  source: string;
  assigned_agent_name: string | null;
  converted_customer_id: string | null;
  status: string;
  notes: string;
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

export interface NegotiationItem {
  id: string;
  property_id: string;
  property_code: string;
  property_title: string;
  customer_id: string;
  customer_name: string;
  agent_name: string;
  deal_type: string;
  deal_type_name: string;
  status: string;
  notes: string;
  offers: {
    id: string;
    version_number: number;
    offered_by: string;
    currency: CurrencyCode;
    proposed_price: string;
    proposed_deposit: string;
    proposed_rent: string;
    discount_amount: string;
    status: string;
    created_at: string;
  }[];
  created_at: string;
}

export interface ContractItem {
  id: string;
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
  start_date: string | null;
  end_date: string | null;
  parties: { id: string; full_name: string; party_role: string; customer_id: string | null }[];
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
  title: string;
  category: string;
  access_level: string;
  property_id: string | null;
  property_title: string | null;
  customer_name: string | null;
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
