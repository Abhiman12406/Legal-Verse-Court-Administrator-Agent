export type FilingPartyType = "PLAINTIFF" | "DEFENDANT" | "INTERVENOR" | "PRO_SE";

export type SeverityLevel =
  | "CLEAN"
  | "SEV-1"
  | "SEV-2"
  | "SEV-3"
  | "SEV-4"
  | "SEV-3: UNSTRUCTURED_PRO_SE";

export type DefectSeverity = "CURABLE_MINOR" | "MANDATORY_REJECT" | "EMERGENCY_HALT" | "SEV-3: UNSTRUCTURED_PRO_SE";

export interface ProceduralDefect {
  rule_citation: string;
  defect_description: string;
  severity: DefectSeverity;
  page_reference?: number;
}

export interface FilingValidationPayload {
  case_number: string;
  document_title: string;
  party_type: FilingPartyType;
  filing_date: string;
  signature_detected: boolean;
  certificate_of_service_valid: boolean;
  is_emergency: boolean;
  extraction_confidence: number;
  defects: ProceduralDefect[];
}

export type ClerkActionType =
  | "APPROVE_OVERRIDE"
  | "ISSUE_DEFICIENCY"
  | "REASSIGN_JUDGE"
  | "STRIKE_PLEADINGS";

export interface ClerkDecision {
  action: ClerkActionType;
  clerk_id: string;
  decision_notes: string;
  timestamp: string;
  clerk_token?: string;
  relief_designation?: string;
}


export interface ScheduledSlot {
  hearing_id: string;
  case_number: string;
  courtroom_id: string;
  assigned_judge_id: string;
  scheduled_date: string;
  start_time: string;
  duration_minutes: number;
  interpreter_locked: boolean;
  status: "CONFIRMED" | "TENTATIVE" | "CONFLICT";
}

export type CourtRole = "CLERK" | "CHIEF_JUDGE" | "PUBLIC";
export type CourtClearance = "STANDARD" | "SEALED_CONFIDENTIAL" | "JUDICIAL_RESTRICTED";

export interface AuditRecord {
  entry_id: number;
  timestamp: string;
  case_id: string;
  filing_id: string;
  agent_version: string;
  model_version?: string;
  prompt_hash?: string;
  decision?: string;
  clerk_override?: unknown;
  event_type: string;
  operator_id: string;
  decision_payload: Record<string, unknown>;
  previous_hash: string;
  current_hash: string;
}

export interface DocketFilingItem {
  id: string;
  case_id: string;
  case_number: string;
  court_division: string;
  assigned_judge_id: string;
  document_title: string;
  party_type: FilingPartyType;
  filing_date: string;
  is_emergency: boolean;
  is_sealed: boolean;
  severity_level: SeverityLevel;
  workflow_status:
    | "INGESTED"
    | "HALTED_SECURITY"
    | "AWAITING_CLERK"
    | "VALIDATED"
    | "DEFICIENT"
    | "SCHEDULED"
    | "COMPLETED";
  extraction_confidence: number;
  signature_detected: boolean;
  certificate_of_service_valid: boolean;
  raw_text: string;
  defects: ProceduralDefect[];
  clerk_decision?: ClerkDecision;
  scheduled_slot?: ScheduledSlot;
  generated_notice?: {
    notice_type: string;
    title: string;
    body_text: string;
    statutory_cure_days?: number;
  };
  relief_designation?: string;
  pro_se_quarantined?: boolean;
  docket_status?: "CONDITIONALLY_LODGED" | "VALIDATED" | "AWAITING_CLERK" | "PENDING_JUDICIAL_STRIKE" | "STRICKEN_BY_COURT" | "HALTED_SECURITY";
  cure_deadline?: string;
  lodged_receipt_timestamp?: string;
  conflict_screen_passed?: boolean;
  conflicted_judges_excluded?: string[];
  is_ifp_pending?: boolean;
  ifp_detected?: boolean;
  ifp_ruling?: {
    decision: "GRANT" | "DENY";
    fee_waived: boolean;
    fee_grace_deadline?: string;
    notice_title?: string;
    notice_text?: string;
  };
  is_ex_parte_tro?: boolean;
  rule_65b_notice_certified?: boolean;
  ex_parte_action?: "ISSUE_EXPEDITED_NOTICE_ORDER" | "JUDICIAL_OVERRIDE_EMERGENCY_TRO" | "DECLASSIFY_TO_STANDARD_MOTION";
  castro_notice?: CastroNotice;
  castro_tracking_token?: string;
  castro_election_status?: "PENDING_ELECTION" | "AFFIRMED" | "AMENDMENT_PENDING" | "WITHDRAWN";
  is_castro_response?: boolean;
  castro_election?: "AFFIRM" | "AMEND" | "WITHDRAW";
  is_redacted?: boolean;
  redaction_notice?: string;
  _access_level?: string;
}

export interface CastroNotice {
  case_number: string;
  filing_id: string;
  original_filing_title: string;
  received_date: string;
  proposed_recharacterization: string;
  castro_tracking_token: string;
  election_deadline: string;
  notice_text: string;
  election_options: string[];
  status: string;
}

export interface ClerkNotification {
  event_id: string;
  event_type: string;
  priority: "CRITICAL" | "HIGH" | "NORMAL";
  timestamp: number;
  iso_time: string;
  payload: Record<string, any>;
}

export interface QueueMetrics {
  emergency: number;
  standard: number;
  quarantine: number;
  total_depth: number;
  timestamp?: number;
}
