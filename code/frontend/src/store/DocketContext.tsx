"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  AuditRecord,
  ClerkActionType,
  ClerkNotification,
  CourtClearance,
  CourtRole,
  DocketFilingItem,
  QueueMetrics,
} from "../types/lexis";
import { INITIAL_AUDIT_TRAIL, INITIAL_FILINGS } from "./initialData";

interface DocketContextType {
  filings: DocketFilingItem[];
  selectedFiling: DocketFilingItem | undefined;
  selectedFilingId: string;
  auditTrail: AuditRecord[];
  tamperedEntryId: number | null;
  isOfflineFallbackActive: boolean;
  offlineWarningMessage: string | null;
  currentRole: CourtRole;
  currentClearance: CourtClearance;
  isLoading: boolean;
  notifications: ClerkNotification[];
  queueMetrics: QueueMetrics;
  clearNotifications: () => void;
  fetchQueueMetrics: () => Promise<void>;
  setCourtRole: (role: CourtRole) => void;
  seedDatabase: (force?: boolean) => Promise<void>;
  selectFiling: (id: string) => void;
  approveOverride: (notes: string, reliefDesignation?: string) => Promise<void>;
  issueDeficiency: (notes: string, reliefDesignation?: string) => Promise<void>;
  strikePleading: (notes?: string) => Promise<void>;
  adjudicateIFP: (decision: "GRANT" | "DENY", notes?: string) => Promise<void>;
  adjudicateExParte: (
    action: "ISSUE_EXPEDITED_NOTICE_ORDER" | "JUDICIAL_OVERRIDE_EMERGENCY_TRO" | "DECLASSIFY_TO_STANDARD_MOTION",
    notes?: string
  ) => Promise<void>;
  issueCastroWarning: (proposedRecharacterization: string) => Promise<void>;
  processCastroElection: (election: "AFFIRM" | "AMEND" | "WITHDRAW") => Promise<void>;
  reassignJudge: (newJudge: string) => void;
  toggleTamperSimulation: (entryId: number) => void;
  addFiling: (filing: DocketFilingItem) => void;
}


const DocketContext = createContext<DocketContextType | undefined>(undefined);

// Deterministic SHA-256 simulation helper for client-side fallback audit chaining
function computeAuditHash(raw: string): string {
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    const char = raw.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  const hex = Math.abs(hash).toString(16).padStart(8, "0");
  return `${hex}${hex}${hex}${hex}${hex}${hex}${hex}${hex}`.slice(0, 64);
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export function DocketProvider({ children }: { children: React.ReactNode }) {
  const [filings, setFilings] = useState<DocketFilingItem[]>(INITIAL_FILINGS);
  const [selectedFilingId, setSelectedFilingId] = useState<string>("filing-001");
  const [auditTrail, setAuditTrail] = useState<AuditRecord[]>(INITIAL_AUDIT_TRAIL);
  const [tamperedEntryId, setTamperedEntryId] = useState<number | null>(null);
  const [isOfflineFallbackActive, setIsOfflineFallbackActive] = useState<boolean>(false);
  const [offlineWarningMessage, setOfflineWarningMessage] = useState<string | null>(null);

  // Redis Pub/Sub Real-Time Notifications & Queue Telemetry
  const [notifications, setNotifications] = useState<ClerkNotification[]>([]);
  const [queueMetrics, setQueueMetrics] = useState<QueueMetrics>({
    emergency: 0,
    standard: 0,
    quarantine: 0,
    total_depth: 0,
  });

  const clearNotifications = () => {
    setNotifications([]);
  };

  const fetchQueueMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/queue/status`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.metrics) {
          setQueueMetrics(data.metrics);
        }
      }
    } catch {
      // offline / backend not running yet
    }
  }, []);

  // RBAC / ABAC Persona State
  const [currentRole, setCurrentRole] = useState<CourtRole>("CLERK");
  const [currentClearance, setCurrentClearance] = useState<CourtClearance>("STANDARD");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const selectedFiling =
    filings.find((f) => f.id === selectedFilingId) || filings[0];

  const selectFiling = (id: string) => {
    setSelectedFilingId(id);
  };

  const setCourtRole = (role: CourtRole) => {
    setCurrentRole(role);
    if (role === "CHIEF_JUDGE") {
      setCurrentClearance("SEALED_CONFIDENTIAL");
    } else {
      setCurrentClearance("STANDARD");
    }
  };

  const fetchDocketData = useCallback(
    async (role: CourtRole = currentRole, clearance: CourtClearance = currentClearance) => {
      setIsLoading(true);
      try {
        const userHeader = role === "CHIEF_JUDGE" ? "CHIEF_JUDGE_CARTER" : "CLERK_USER_42";
        const filingsRes = await fetch(`${API_BASE_URL}/filings`, {
          headers: {
            "X-Court-Role": role,
            "X-Court-Clearance": clearance,
            "X-Court-User": userHeader,
          },
        });

        if (filingsRes.ok) {
          const filingsData: DocketFilingItem[] = await filingsRes.json();
          setFilings(filingsData);
          if (filingsData.length > 0 && !filingsData.some((f) => f.id === selectedFilingId)) {
            setSelectedFilingId(filingsData[0].id);
          }
        }

        const auditRes = await fetch(`${API_BASE_URL}/audit/trail`);
        if (auditRes.ok) {
          const auditData: AuditRecord[] = await auditRes.json();
          setAuditTrail(auditData);
        }

        setIsOfflineFallbackActive(false);
        setOfflineWarningMessage(null);
      } catch {
        setIsOfflineFallbackActive(true);
        setOfflineWarningMessage("ACID Docket Backend offline. Check connection to port 8000.");
      } finally {
        setIsLoading(false);
      }
    },
    [currentRole, currentClearance, selectedFilingId]
  );

  useEffect(() => {
    fetchDocketData(currentRole, currentClearance);
  }, [currentRole, currentClearance, fetchDocketData]);

  // Connect to Redis SSE Notification Stream & Queue status on mount
  useEffect(() => {
    const loadRecentNotifications = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/notifications/recent?limit=20`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setNotifications(data);
          }
        }
      } catch {
        // Backend offline
      }
    };
    loadRecentNotifications();
    fetchQueueMetrics();

    let eventSource: EventSource | null = null;
    try {
      if (typeof window !== "undefined" && "EventSource" in window) {
        eventSource = new EventSource(`${API_BASE_URL}/notifications/stream`);
        eventSource.addEventListener("notification", (e: MessageEvent) => {
          try {
            const notif: ClerkNotification = JSON.parse(e.data);
            setNotifications((prev) => [notif, ...prev.slice(0, 49)]);
            fetchDocketData();
            fetchQueueMetrics();
          } catch (err) {
            console.error("Failed to parse Redis SSE event", err);
          }
        });
      }
    } catch {
      // EventSource failed
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [fetchDocketData, fetchQueueMetrics]);


  const seedDatabase = async (force: boolean = true) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/db/seed?force=${force}`, {
        method: "POST",
      });
      if (res.ok) {
        await fetchDocketData();
      }
    } catch {
      setOfflineWarningMessage("Failed to seed database: backend unreachable.");
    } finally {
      setIsLoading(false);
    }
  };

  const appendAudit = (eventType: string, payload: Record<string, unknown>) => {
    setAuditTrail((prev) => {
      const last = prev[prev.length - 1];
      const prevHash = last ? last.current_hash : "0".repeat(64);
      const timestamp = new Date().toISOString();
      const rawString = `${prevHash}|${timestamp}|${selectedFiling?.case_id || "SYS"}|${selectedFiling?.id || "FILING"}|${eventType}|CLERK_USER_42|${JSON.stringify(payload)}`;
      const currentHash = computeAuditHash(rawString);

      const newRecord: AuditRecord = {
        entry_id: prev.length + 1,
        timestamp,
        case_id: selectedFiling?.case_id || "c100",
        filing_id: selectedFiling?.id || "filing-001",
        agent_version: "lexis-ops-v2.0-acid",
        model_version: "gemini-2.5-flash",
        prompt_hash: "hash-" + Date.now().toString(16),
        decision: eventType,
        event_type: eventType,
        operator_id: "CLERK_USER_42",
        decision_payload: payload,
        previous_hash: prevHash,
        current_hash: currentHash,
      };
      return [...prev, newRecord];
    });
  };

  const approveOverride = async (notes: string, reliefDesignation?: string) => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const effectiveNotes = notes || "Clerk oral override authorized on papers.";
    const clerkToken = `CLERK_USER_42:${selectedFiling.case_id}:APPROVE_OVERRIDE:${Math.floor(Date.now() / 1000)}:CLERK_HMAC_SIG_VERIFIED`;

    try {
      await fetch(`${API_BASE_URL}/filings/clerk-adjudicate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          clerk_id: "CLERK_USER_42",
          action: "APPROVE_OVERRIDE",
          decision_notes: effectiveNotes,
          relief_designation: reliefDesignation || undefined,
          model_version: "gemini-2.5-flash",
          prompt_hash: "prompt-hash-override-" + Date.now().toString(16),
        }),
      });
    } catch {
      // offline fallback
    }

    setFilings((prev) =>
      prev.map((item) => {
        if (item.id !== selectedFilingId) return item;
        const effectiveTitle = reliefDesignation || item.document_title;
        return {
          ...item,
          document_title: effectiveTitle,
          relief_designation: reliefDesignation || item.relief_designation,
          pro_se_quarantined: false,
          workflow_status: "COMPLETED",
          severity_level: "CLEAN",
          docket_status: "VALIDATED",
          clerk_decision: {
            action: "APPROVE_OVERRIDE" as ClerkActionType,
            clerk_id: "CLERK_USER_42",
            decision_notes: effectiveNotes,
            timestamp,
            clerk_token: clerkToken,
            relief_designation: reliefDesignation || undefined,
          },
          scheduled_slot: {
            hearing_id: `slot-${Date.now()}`,
            case_number: item.case_number,
            courtroom_id: "CR-101",
            assigned_judge_id: item.assigned_judge_id,
            scheduled_date: "2026-09-29",
            start_time: "10:00:00",
            duration_minutes: 60,
            interpreter_locked: true,
            status: "CONFIRMED",
          },
          generated_notice: {
            notice_type: "NOTICE_OF_HEARING",
            title: `Formal Notice of Hearing - ${item.case_number}`,
            body_text: `PLEASE TAKE NOTICE that following Clerk Override (Token: ${clerkToken.slice(0, 24)}...) on verified relief '${effectiveTitle}', this motion has been set for hearing before ${item.assigned_judge_id} in Courtroom CR-101 on September 29, 2026 at 10:00 AM Local Time.`,
          },
        };
      })
    );

    appendAudit("CLERK_OVERRIDE_APPROVED", {
      notes: effectiveNotes,
      relief_designation: reliefDesignation,
      status: "VALIDATED",
      clerk_token: clerkToken,
    });
  };

  const issueDeficiency = async (notes: string, reliefDesignation?: string) => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const effectiveNotes = notes || "Mandatory procedural defects cited. Notice dispatched.";
    const clerkToken = `CLERK_USER_42:${selectedFiling.case_id}:ISSUE_DEFICIENCY:${Math.floor(Date.now() / 1000)}:CLERK_HMAC_SIG_VERIFIED`;

    try {
      await fetch(`${API_BASE_URL}/filings/clerk-adjudicate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          clerk_id: "CLERK_USER_42",
          action: "ISSUE_DEFICIENCY",
          decision_notes: effectiveNotes,
          relief_designation: reliefDesignation || undefined,
          model_version: "gemini-2.5-flash",
          prompt_hash: "prompt-hash-deficiency-" + Date.now().toString(16),
        }),
      });
    } catch {
      // offline fallback
    }

    setFilings((prev) =>
      prev.map((item) => {
        if (item.id !== selectedFilingId) return item;
        const effectiveTitle = reliefDesignation || item.document_title;
        return {
          ...item,
          document_title: effectiveTitle,
          relief_designation: reliefDesignation || item.relief_designation,
          pro_se_quarantined: false,
          workflow_status: "DEFICIENT",
          docket_status: "CONDITIONALLY_LODGED",
          clerk_decision: {
            action: "ISSUE_DEFICIENCY" as ClerkActionType,
            clerk_id: "CLERK_USER_42",
            decision_notes: effectiveNotes,
            timestamp,
            clerk_token: clerkToken,
            relief_designation: reliefDesignation || undefined,
          },
          generated_notice: {
            notice_type: "NOTICE_OF_DEFICIENCY",
            title: `Notice of Procedural Deficiency - ${item.case_number}`,
            statutory_cure_days: 14,
            body_text: `Pursuant to Local Rules, filing '${effectiveTitle}' is deemed DEFICIENT. The filing party is granted 14 CALENDAR DAYS to submit an amended filing curing all cited defects. Clerk Authorization Token: ${clerkToken.slice(0, 24)}... Note: Court staff cannot provide legal advice. Litigants may contact the Court Self-Help Center.`,
          },
        };
      })
    );

    appendAudit("DEFICIENCY_NOTICE_DISPATCHED", {
      notes: effectiveNotes,
      relief_designation: reliefDesignation,
      statutory_cure_days: 14,
      defects: selectedFiling.defects.length,
      clerk_token: clerkToken,
    });
  };

  const strikePleading = async (notes?: string) => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const effectiveNotes =
      notes ||
      "Pleading stricken by Judicial Order under Fed. R. Civ. P. 5(d)(4) following expiration of statutory cure window.";
    const tsEpoch = Math.floor(Date.now() / 1000);
    const judicialToken = `HON_JUDGE:${selectedFiling.case_number}:STRIKE_PLEADINGS:${tsEpoch}:MOCK_SIG`;

    try {
      await fetch(`${API_BASE_URL}/filings/strike`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          judge_id: selectedFiling.assigned_judge_id || "HON. ELENA CARTER",
          judicial_token: judicialToken,
          defects_cited: selectedFiling.defects.map((d) => d.rule_citation),
        }),
      });
    } catch {
      // offline fallback
    }

    setFilings((prev) =>
      prev.map((item) => {
        if (item.id !== selectedFilingId) return item;
        return {
          ...item,
          docket_status: "STRICKEN_BY_COURT",
          workflow_status: "COMPLETED",
          severity_level: "SEV-2",
          clerk_decision: {
            action: "STRIKE_PLEADINGS" as ClerkActionType,
            clerk_id: "HON. PRESIDING JUDGE",
            decision_notes: effectiveNotes,
            timestamp,
            clerk_token: judicialToken,
          },
          generated_notice: {
            notice_type: "ORDER_TO_STRIKE",
            title: `Order to Strike Non-Conforming Pleading - ${item.case_number}`,
            body_text: `PURSUANT TO LOCAL CIVIL RULE 5.4 AND FED. R. CIV. P. 5(d)(4), the 14-day cure period for '${item.document_title}' expired on ${item.cure_deadline || "statutory deadline"} without cure. IT IS HEREBY ORDERED that the pleading is STRICKEN from the active case docket. Judicial Token: ${judicialToken}`,
          },
        };
      })
    );

    appendAudit("PLEADINGS_STRICKEN_BY_ORDER", {
      notes: effectiveNotes,
      status: "STRICKEN_BY_COURT",
      judicial_token: judicialToken,
    });
  };

  const adjudicateIFP = async (decision: "GRANT" | "DENY", notes?: string) => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const effectiveNotes =
      notes ||
      (decision === "GRANT"
        ? "IFP Application Granted. Fees Waived under 28 U.S.C. § 1915."
        : "IFP Application Denied. 21-Day Tender Grace Period Enforced under Williams-Guice.");

    try {
      await fetch(`${API_BASE_URL}/filings/ifp-ruling`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          judge_id: selectedFiling.assigned_judge_id || "HON. SARAH LIN",
          decision,
          ruling_notes: effectiveNotes,
          effective_date: new Date().toISOString().split("T")[0],
        }),
      });
    } catch {
      // offline fallback
    }

    if (decision === "GRANT") {
      setFilings((prev) =>
        prev.map((item) => {
          if (item.id !== selectedFilingId) return item;
          return {
            ...item,
            is_ifp_pending: false,
            docket_status: "VALIDATED",
            workflow_status: "VALIDATED",
            cure_deadline: undefined,
            ifp_ruling: {
              decision: "GRANT",
              fee_waived: true,
            },
            generated_notice: {
              notice_type: "ORDER_GRANTING_IFP",
              title: `Order Granting In Forma Pauperis - ${item.case_number}`,
              body_text: `PURSUANT TO 28 U.S.C. § 1915, Plaintiff's Application to Proceed In Forma Pauperis is GRANTED. Court filing fees and administrative costs are permanently waived.`,
            },
          };
        })
      );
      appendAudit("IFP_APPLICATION_GRANTED", {
        decision: "GRANT",
        notes: effectiveNotes,
        fee_waived: true,
        timestamp,
      });
    } else {
      const graceDeadline = new Date(Date.now() + 21 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
      setFilings((prev) =>
        prev.map((item) => {
          if (item.id !== selectedFilingId) return item;
          return {
            ...item,
            is_ifp_pending: false,
            cure_deadline: graceDeadline,
            docket_status: "CONDITIONALLY_LODGED",
            workflow_status: "AWAITING_CLERK",
            ifp_ruling: {
              decision: "DENY",
              fee_waived: false,
              fee_grace_deadline: graceDeadline,
            },
            generated_notice: {
              notice_type: "NOTICE_OF_IFP_DENIAL",
              title: `Notice of IFP Denial & Order to Tender Filing Fee - ${item.case_number}`,
              body_text: `PURSUANT TO 28 U.S.C. § 1915 and Williams-Guice v. Board of Education, 45 F.3d 161 (7th Cir. 1995), the Application to Proceed In Forma Pauperis is DENIED. Litigant is granted 21 CALENDAR DAYS to tender filing fee (deadline: ${graceDeadline}) before dismissal proceedings commence.`,
              statutory_cure_days: 21,
            },
          };
        })
      );
      appendAudit("IFP_APPLICATION_DENIED_TENDER_GRACE", {
        decision: "DENY",
        notes: effectiveNotes,
        fee_grace_deadline: graceDeadline,
        fee_waived: false,
        timestamp,
      });
    }
  };

  const adjudicateExParte = async (
    action: "ISSUE_EXPEDITED_NOTICE_ORDER" | "JUDICIAL_OVERRIDE_EMERGENCY_TRO" | "DECLASSIFY_TO_STANDARD_MOTION",
    notes?: string
  ) => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const effectiveFindings =
      notes ||
      (action === "ISSUE_EXPEDITED_NOTICE_ORDER"
        ? "Expedited 4-hour telephonic notice ordered; 24h emergency hearing calendared."
        : action === "JUDICIAL_OVERRIDE_EMERGENCY_TRO"
        ? "Immediate irreparable harm found dispensing with notice under Rule 65(b)(2)."
        : "Extraordinary ex parte standard not satisfied; declassified to standard 21-day noticed motion.");

    try {
      await fetch(`${API_BASE_URL}/filings/frcp65b-adjudicate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          judge_id: selectedFiling.assigned_judge_id || "HON. MARCUS VANCE",
          action,
          judicial_findings: effectiveFindings,
          effective_date: new Date().toISOString().split("T")[0],
        }),
      });
    } catch {
      // offline fallback
    }

    if (action === "ISSUE_EXPEDITED_NOTICE_ORDER") {
      setFilings((prev) =>
        prev.map((item) => {
          if (item.id !== selectedFilingId) return item;
          return {
            ...item,
            ex_parte_action: action,
            workflow_status: "AWAITING_CLERK",
            generated_notice: {
              notice_type: "EXPEDITED_NOTICE_ORDER",
              title: `Expedited Notice Order & Setting of Emergency Hearing - ${item.case_number}`,
              body_text: `PURSUANT TO FED. R. CIV. P. 65(b)(1)(B), movant is ORDERED to effectuate telephonic/electronic notice within four (4) hours. Emergency hearing calendarized in 24 hours.`,
            },
          };
        })
      );
      appendAudit("EXPEDITED_NOTICE_ORDERED", {
        action,
        findings: effectiveFindings,
        hearing_window_hours: 24,
        timestamp,
      });
    } else if (action === "JUDICIAL_OVERRIDE_EMERGENCY_TRO") {
      setFilings((prev) =>
        prev.map((item) => {
          if (item.id !== selectedFilingId) return item;
          return {
            ...item,
            ex_parte_action: action,
            docket_status: "VALIDATED",
            workflow_status: "COMPLETED",
            generated_notice: {
              notice_type: "EMERGENCY_EX_PARTE_TRO",
              title: `Emergency Ex Parte Temporary Restraining Order - ${item.case_number}`,
              body_text: `PURSUANT TO FED. R. CIV. P. 65(b)(2), the Court finds imminent irreparable injury dispensing with notice. Temporary Restraining Order entered for 14 calendar days.`,
            },
          };
        })
      );
      appendAudit("EX_PARTE_TRO_GRANTED_JUDICIAL_OVERRIDE", {
        action,
        findings: effectiveFindings,
        tro_effective_days: 14,
        timestamp,
      });
    } else {
      setFilings((prev) =>
        prev.map((item) => {
          if (item.id !== selectedFilingId) return item;
          return {
            ...item,
            ex_parte_action: action,
            is_emergency: false,
            is_ex_parte_tro: false,
            severity_level: "SEV-2",
            docket_status: "VALIDATED",
            workflow_status: "VALIDATED",
            generated_notice: {
              notice_type: "ORDER_DECLASSIFYING_MOTION",
              title: `Order Declassifying Application to Standard Noticed Motion - ${item.case_number}`,
              body_text: `Ex parte relief denied for failure to satisfy Rule 65(b). Pleading declassified to standard noticed motion with 21-day statutory notice buffer.`,
            },
          };
        })
      );
      appendAudit("EX_PARTE_APPLICATION_DECLASSIFIED", {
        action,
        findings: effectiveFindings,
        notice_buffer_days: 21,
        timestamp,
      });
    }
  };

  const issueCastroWarning = async (proposedRecharacterization: string) => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const token = `CASTRO-RECLASS-${selectedFiling.case_number}-${selectedFiling.id}`;
    const baseDate = new Date();
    baseDate.setDate(baseDate.getDate() + 14);
    const deadline = baseDate.toISOString().split("T")[0];

    try {
      const res = await fetch(`${API_BASE_URL}/filings/recharacterize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          original_filing_title: selectedFiling.document_title,
          received_date: selectedFiling.filing_date,
          proposed_recharacterization: proposedRecharacterization,
          operator_id: "CLERK_ADMIN_01",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setFilings((prev) =>
          prev.map((item) => {
            if (item.id !== selectedFilingId) return item;
            return {
              ...item,
              relief_designation: proposedRecharacterization,
              castro_notice: data.notice,
              castro_tracking_token: data.tracking_token,
              castro_election_status: "PENDING_ELECTION",
              generated_notice: {
                notice_type: "CASTRO_WARNING_NOTICE",
                title: `Mandatory Castro Warning & 14-Day Election Advisory - ${item.case_number}`,
                body_text: data.notice.notice_text,
                statutory_cure_days: 14,
              },
            };
          })
        );
        appendAudit("CASTRO_WARNING_DISPATCHED", {
          tracking_token: data.tracking_token,
          proposed_recharacterization: proposedRecharacterization,
          election_deadline: data.election_deadline,
          timestamp,
        });
        return;
      }
    } catch {
      // Fallback
    }

    setFilings((prev) =>
      prev.map((item) => {
        if (item.id !== selectedFilingId) return item;
        return {
          ...item,
          relief_designation: proposedRecharacterization,
          castro_tracking_token: token,
          castro_election_status: "PENDING_ELECTION",
          castro_notice: {
            case_number: item.case_number,
            filing_id: item.id,
            original_filing_title: item.document_title,
            received_date: item.filing_date,
            proposed_recharacterization: proposedRecharacterization,
            castro_tracking_token: token,
            election_deadline: deadline,
            notice_text: `FORMAL NOTICE OF INTENT TO RECHARACTERIZE PRO SE PLEADING AND MANDATORY CASTRO WARNING ADVISORY (Castro v. United States, 540 U.S. 375 (2003)). Tracking Token: ${token}`,
            election_options: ["AFFIRM", "AMEND", "WITHDRAW"],
            status: "PENDING_ELECTION",
          },
          generated_notice: {
            notice_type: "CASTRO_WARNING_NOTICE",
            title: `Mandatory Castro Warning & 14-Day Election Advisory - ${item.case_number}`,
            body_text: `Under Castro v. United States, 540 U.S. 375, court proposes to recharacterize submission as ${proposedRecharacterization}. Litigant granted 14 days to affirm, amend, or withdraw. Token: ${token}`,
            statutory_cure_days: 14,
          },
        };
      })
    );
    appendAudit("CASTRO_WARNING_DISPATCHED", {
      tracking_token: token,
      proposed_recharacterization: proposedRecharacterization,
      election_deadline: deadline,
      timestamp,
    });
  };

  const processCastroElection = async (election: "AFFIRM" | "AMEND" | "WITHDRAW") => {
    if (!selectedFiling) return;
    const timestamp = new Date().toISOString();
    const token = selectedFiling.castro_tracking_token || `CASTRO-RECLASS-${selectedFiling.case_number}-${selectedFiling.id}`;

    try {
      await fetch(`${API_BASE_URL}/filings/castro-election`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_number: selectedFiling.case_number,
          filing_id: selectedFiling.id,
          tracking_token: token,
          election,
          operator_id: "SYSTEM_INGRESS",
        }),
      });
    } catch {
      // Fallback
    }

    setFilings((prev) =>
      prev.map((item) => {
        if (item.id !== selectedFilingId) return item;
        if (election === "AFFIRM") {
          return {
            ...item,
            castro_election_status: "AFFIRMED",
            docket_status: "VALIDATED",
            workflow_status: "VALIDATED",
            document_title: item.relief_designation || item.document_title,
            generated_notice: {
              notice_type: "RECHARACTERIZATION_AFFIRMED",
              title: `Recharacterization Formally Affirmed - ${item.case_number}`,
              body_text: `Pro Se litigant affirmed recharacterization as ${item.relief_designation}. Formally docketed without preclusive bar under Castro.`,
            },
          };
        } else if (election === "AMEND") {
          return {
            ...item,
            castro_election_status: "AMENDMENT_PENDING",
            docket_status: "AWAITING_CLERK",
            generated_notice: {
              notice_type: "LEAVE_TO_AMEND_GRANTED",
              title: `14-Day Leave to Amend Granted - ${item.case_number}`,
              body_text: `Litigant elected to amend pleading under Castro v. United States. 14-day statutory leave to file amended pleading granted.`,
            },
          };
        } else {
          return {
            ...item,
            castro_election_status: "WITHDRAWN",
            docket_status: "STRICKEN_BY_COURT",
            workflow_status: "COMPLETED",
            generated_notice: {
              notice_type: "SUBMISSION_WITHDRAWN_WITHOUT_PREJUDICE",
              title: `Pleading Withdrawn Without Prejudice - ${item.case_number}`,
              body_text: `Submission withdrawn pursuant to Castro election. No preclusive, successive, or res judicata bar attaches.`,
            },
          };
        }
      })
    );
    appendAudit(`CASTRO_ELECTION_${election}`, {
      tracking_token: token,
      election,
      timestamp,
    });
  };

  const reassignJudge = (newJudge: string) => {
    if (!selectedFiling) return;
    setFilings((prev) =>
      prev.map((item) => {
        if (item.id !== selectedFilingId) return item;
        return {
          ...item,
          assigned_judge_id: newJudge,
          workflow_status: "AWAITING_CLERK",
          clerk_decision: {
            action: "REASSIGN_JUDGE" as ClerkActionType,
            clerk_id: "CLERK_USER_42",
            decision_notes: `Docket reassigned to ${newJudge}.`,
            timestamp: new Date().toISOString(),
          },
        };
      })
    );
    appendAudit("JUDICIAL_REASSIGNMENT", { new_judge: newJudge });
  };

  const toggleTamperSimulation = (entryId: number) => {
    setTamperedEntryId((current) => (current === entryId ? null : entryId));
  };

  const addFiling = (filing: DocketFilingItem) => {
    setFilings((prev) => [filing, ...prev]);
    setSelectedFilingId(filing.id);
    appendAudit("PDF_FILING_MANUALLY_INGESTED", {
      case_number: filing.case_number,
      document_title: filing.document_title,
      severity_level: filing.severity_level,
      filing_id: filing.id,
    });
  };

  return (
    <DocketContext.Provider
      value={{
        filings,
        selectedFiling,
        selectedFilingId,
        auditTrail,
        tamperedEntryId,
        isOfflineFallbackActive,
        offlineWarningMessage,
        currentRole,
        currentClearance,
        isLoading,
        notifications,
        queueMetrics,
        clearNotifications,
        fetchQueueMetrics,
        setCourtRole,
        seedDatabase,
        selectFiling,
        approveOverride,
        issueDeficiency,
        strikePleading,
        adjudicateIFP,
        adjudicateExParte,
        issueCastroWarning,
        processCastroElection,
        reassignJudge,
        toggleTamperSimulation,
        addFiling,
      }}

    >
      {children}
    </DocketContext.Provider>
  );
}

export function useDocket() {
  const context = useContext(DocketContext);
  if (!context) {
    throw new Error("useDocket must be used within a DocketProvider");
  }
  return context;
}
