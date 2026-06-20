// Types mirroring the Drawback Engine FastAPI contract (base path /api).
// Money values are plain numbers in USD. Dates are ISO "YYYY-MM-DD" strings.

export type Confidence = "high" | "medium" | "low";

/** Provision codes as emitted by the engine. */
export type ProvisionCode = "58" | "59" | "51" | "52" | "53" | string;

// ── Config ──────────────────────────────────────────────────────────────────
export interface ConfigRow {
  charge: string;
  eligible: boolean;
  authority: string;
  note: string;
}

export interface ConfigSummary {
  version: string;
  as_of: string;
  eligible: string[];
  ineligible: string[];
  rows: ConfigRow[];
}

export interface HealthResponse {
  ok: boolean;
  as_of: string;
  config: string;
}

// ── Assumptions registry (GET /api/assumptions) ──────────────────────────────
export type AssumptionTag = "VERIFIED" | "INFERRED" | "GUESS";

/** The correctable affordance attached to a claimant-resolvable assumption. */
export interface AssumptionCorrection {
  prompt: string;
  confirm_label: string;
  confirm_effect: string;
  override_label: string;
  override_effect: string;
}

export interface Assumption {
  id: string;
  tag: AssumptionTag;
  title: string;
  summary: string;
  correctable: boolean;
  correction?: AssumptionCorrection;
  // Additive fields (GET /api/assumptions now also returns these). Optional so
  // existing consumers are unaffected.
  legal?: boolean;
  upside_only?: boolean;
  citations?: string[];
}

export interface AssumptionsResponse {
  count: number;
  assumptions: Assumption[];
}

// ── Estimate ────────────────────────────────────────────────────────────────
export interface Breakdown {
  key: string;
  label: string;
  recovery: number;
  quantity: number;
  pair_count: number;
}

export interface BlockedItem {
  reason: string;
  hts8: string;
  amount: number;
  quantity: number;
  detail: string;
  related_reference?: string;
}

export interface Trace {
  match_basis: string;
  provision: ProvisionCode;
  rule_citations: string[];
  assumption_ids: string[];
  computation_steps: string[];
  eligible_charges: Record<string, number>;
  excluded_charges: Record<string, string>;
  import_date: string;
  export_date: string;
  claim_date: string;
  within_window: boolean;
  flags: string[];
}

export interface MatchedPair {
  import_entry: string;
  import_line_no: number;
  export_reference: string;
  hts8: string;
  quantity: number;
  provision: ProvisionCode;
  per_unit_designated_duty: number;
  per_unit_comparator_duty: number | null;
  per_unit_recovery: number;
  recovery: number;
  recovery_low: number;
  confidence: Confidence;
  in_headline: boolean;
  import_year: number;
  trace: Trace;
}

export interface DataQualityIssue {
  severity: "error" | "warning" | string;
  row: number;
  field: string;
  message: string;
}

export interface DataQualityReport {
  imports_parsed: number;
  exports_parsed: number;
  imports_dropped: number;
  exports_dropped: number;
  issues: DataQualityIssue[];
}

export interface EstimateSummary {
  headline_point: number;
  headline_low: number;
  potential_total: number;
  eligible_duty_pool: number;
  headline_pair_count: number;
  total_pair_count: number;
  imports: number;
  exports: number;
}

export interface Estimate {
  token: string;
  config: ConfigSummary;
  as_of: string;
  tariff_config_version: string;

  headline_point: number;
  headline_low: number;
  potential_total: number;
  eligible_duty_pool: number;

  summary: EstimateSummary;

  by_year: Breakdown[];
  by_hts: Breakdown[];
  by_program: Breakdown[];

  blocked: BlockedItem[];
  blocked_by_reason: Record<string, number>;

  matched_pairs: MatchedPair[];
  matched_pairs_truncated?: number;
  data_quality: DataQualityReport;

  filing_checklist: string[];
  notes: string[];
}

// ── Filing (Layer 3) ────────────────────────────────────────────────────────
export interface ClaimImportLine {
  itin: number;
  entry_filer_code: string;
  entry_number: string;
  cbp_line: number;
  hts10: string;
  quantity: number;
  entered_value_per_unit: number;
  accounting_method_code: string;
  revenue_claimed: Record<string, number>;
}

export interface ClaimExportLine {
  action: string;
  hts10: string;
  quantity: number;
  export_date: string;
  destination_country: string;
  bol_indicator: boolean;
  bol_carrier_scac: string;
  unique_identifier: string;
  linked_itins: number[];
}

export interface ClaimTotals {
  by_accounting_class: Record<string, number>;
  grand_total_claimed: number;
}

export interface Claim {
  filing_action: string;
  application_identifier: string;
  entry_filer_code: string;
  claim_number: string;
  filing_port: string;
  drawback_provision_code: ProvisionCode;
  drawback_provision_label: string;
  claimant_id: string;
  accelerated_payment: boolean;
  electronic_signature: string;
  imports: ClaimImportLine[];
  exports: ClaimExportLine[];
  totals: ClaimTotals;
  simulated: boolean;
  banner: string;
  issues: string[];
  transmission_text: string;
}

export interface ClaimsResponse {
  simulated: boolean;
  banner: string;
  claims: Claim[];
}

export interface SubmitClaimResult {
  claim_number: string;
  provision: ProvisionCode;
  grand_total_claimed: number;
  valid: boolean;
  issues: string[];
  files: string[];
}

export interface SubmitResponse {
  simulated: boolean;
  banner: string;
  claims: SubmitClaimResult[];
  /** present once a sign-off has been recorded — the attestation travels with
   *  the (simulated) transmission manifest (COMPLIANCE §4 P3). */
  signoff?: SignoffRecord;
}

// ── Defensibility report (GET /api/defensibility/{token}) ────────────────────
// The per-claim "validate from the trace alone" artifact (COMPLIANCE §4 P6).
// `tier` mirrors the assumption tags; `contributes_to` says whether a fired rule
// underpins the audit-defensible headline or only the needs-review upside.
export type DefensibilityTier = AssumptionTag; // "VERIFIED" | "INFERRED" | "GUESS"
export type ContributesTo = "defensible" | "review";

export interface DefensibilityReconciliation {
  ok: boolean;
  invariant: string;
  total_claimed: number;
  duty_paid_on_claimed: number;
  per_pair_caps_checked: string[];
  violations: string[];
}

export interface DefensibilityRule {
  id: string;
  title: string;
  tier: DefensibilityTier;
  legal: boolean;
  upside_only: boolean;
  citations: string[];
  contributes_to: ContributesTo;
}

export interface DefensibilityClaimLine {
  import_entry: string;
  import_line_no: number;
  export_reference: string;
  provision: ProvisionCode;
  in_headline: boolean;
  claimed: number;
  defensible: number;
  needs_review: number;
  basis_rules: string[];
  basis_all_verified: boolean;
  blocking_rules: string[];
}

export interface DefensibilityReport {
  as_of: string;
  defensible_headline: number;
  best_estimate: number;
  needs_review_total: number;
  headline_basis: string;
  reconciliation: DefensibilityReconciliation;
  tier_summary: Record<DefensibilityTier, number>;
  rules_fired: DefensibilityRule[];
  claim_lines: DefensibilityClaimLine[];
  disclaimer: string;
}

// ── Licensed-filer sign-off (POST /api/claims/{token}/signoff) ───────────────
// COMPLIANCE §4 P3 — the logged human attestation that gates finalizing a claim.
export type FilerRole =
  | "licensed_customs_broker"
  | "customs_attorney"
  | "self_filer_own_account";

export interface SignoffRequest {
  filer_name: string;
  role: FilerRole;
  license_number?: string;
  accepted_defensible: boolean;
  accepted_review_understood?: boolean;
}

/** The recorded attestation returned by a successful sign-off (also attached to
 *  the submit manifest's `signoff` field). */
export interface SignoffRecord {
  signed: boolean;
  filer_name: string;
  role: FilerRole;
  license_number: string;
  attested_on: string;
  accepted_defensible: boolean;
  accepted_review_understood: boolean;
  statement: string;
}

// ── Lifecycle (Layer 3) ──────────────────────────────────────────────────────
export interface LifecycleStep {
  state: string;
  status: "complete" | "projected" | string;
  on: string;
  note: string;
}

export interface LifecycleResponse {
  simulated: boolean;
  banner: string;
  filing_date: string;
  accelerated_payment: boolean;
  current_state: string;
  estimated_amount: number;
  projected_first_payment: string;
  retention_deadline: string;
  steps: LifecycleStep[];
}
