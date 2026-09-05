"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldAlert,
  Send,
  UserCheck,
  CalendarCheck,
  ChevronRight,
  Info,
  Check,
  Building,
  Layers,
  ShieldCheck,
  Hash,
  Sparkles,
  Copy,
  Cpu,
  Gavel,
  Scale,
} from "lucide-react";
import { useDocket } from "../../store/DocketContext";
import { ClerkActionType } from "../../types/lexis";

const PRO_SE_RELIEF_OPTIONS = [
  {
    id: "FEE_WAIVER",
    title: "Petition for In Forma Pauperis (Fee Waiver)",
    description: "Indigent filing fee waiver request under Administrative Directive 2026-04",
    code: "IFP-WAIVER",
  },
  {
    id: "STAY_EVICTION",
    title: "Emergency Motion for Stay of Eviction / Writ",
    description: "Ex parte stay of restitution writ & enforcement pause",
    code: "STAY-EVICT",
  },
  {
    id: "EXTEND_TIME",
    title: "Motion for Extension of Time (14-30 Days)",
    description: "Enlargement of time to answer or retain legal aid counsel",
    code: "TIME-EXT",
  },
  {
    id: "APPOINT_COUNSEL",
    title: "Application for Pro Bono / Legal Aid Assignment",
    description: "Referral to civil legal services volunteer lawyers project",
    code: "COUNSEL-REQ",
  },
  {
    id: "ADA_ACCOMMODATION",
    title: "Request for Court Interpreter & ADA Accommodation",
    description: "Language access / Spanish interpreter & disability accommodation",
    code: "ADA-INTERP",
  },
  {
    id: "VACATE_DEFAULT",
    title: "Motion to Vacate Entry of Default",
    description: "Application to set aside default judgment on good cause",
    code: "VAC-DFLT",
  },
];

type DetailTab = "compliance" | "scheduling" | "audit";

export function SideBySideReview() {
  const {
    selectedFiling,
    auditTrail,
    tamperedEntryId,
    toggleTamperSimulation,
    approveOverride,
    issueDeficiency,
    strikePleading,
    adjudicateIFP,
    adjudicateExParte,
    issueCastroWarning,
    processCastroElection,
    reassignJudge,
    isOfflineFallbackActive,
    offlineWarningMessage,
    currentRole,
    currentClearance,
    setCourtRole,
    seedDatabase,
    isLoading,
  } = useDocket();

  const [activeDetailTab, setActiveDetailTab] = useState<DetailTab>("compliance");
  const [overrideNotes, setOverrideNotes] = useState("");
  const [deficiencyNotes, setDeficiencyNotes] = useState("");
  const [selectedJudge, setSelectedJudge] = useState(selectedFiling?.assigned_judge_id || "HON. ELENA CARTER");
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedRelief, setSelectedRelief] = useState<string | null>(
    selectedFiling?.relief_designation || null
  );

  useEffect(() => {
    if (selectedFiling) {
      setSelectedRelief(selectedFiling.relief_designation || null);
      setSelectedJudge(selectedFiling.assigned_judge_id);
    }
  }, [selectedFiling?.id, selectedFiling?.relief_designation, selectedFiling?.assigned_judge_id]);

  if (!selectedFiling) {
    return (
      <section className="flex-1 flex flex-col items-center justify-center h-[calc(100vh-3.5rem)] bg-slate-950 p-8 text-center">
        <Scale className="w-16 h-16 text-indigo-400 mb-4 opacity-70 animate-pulse" />
        <h2 className="text-xl font-bold text-slate-100">ACID PostgreSQL Docket Empty</h2>
        <p className="text-sm text-slate-400 max-w-md mt-2 mb-6">
          The court database currently contains no active dockets or filings.
          Initialize the benchmark cases and statutory pleading records directly into PostgreSQL.
        </p>
        <button
          onClick={() => seedDatabase(true)}
          disabled={isLoading}
          className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-50 cursor-pointer"
        >
          {isLoading ? "Seeding Database..." : "Seed PostgreSQL Docket Records"}
        </button>
      </section>
    );
  }

  const isQuarantined =
    selectedFiling.severity_level === "SEV-3: UNSTRUCTURED_PRO_SE" ||
    Boolean(selectedFiling.pro_se_quarantined) ||
    (selectedFiling.party_type === "PRO_SE" && selectedFiling.extraction_confidence < 0.75);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await approveOverride(
        overrideNotes || "Clerk override authorized upon verified relief designation.",
        selectedRelief || undefined
      );
      setOverrideNotes("");
      setActionSuccessMessage("Clerk Override Approved: Verified relief calendarized, HMAC token signed, and notice dispatched.");
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeficiency = async () => {
    setIsSubmitting(true);
    try {
      await issueDeficiency(
        deficiencyNotes || "Mandatory procedural defects cited. 14-day statutory cure notice dispatched.",
        selectedRelief || undefined
      );
      setDeficiencyNotes("");
      setActionSuccessMessage("Deficiency Notice Dispatched: Litigant granted 14 days under FRCP 5(d)(4) conditional docketing.");
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStrike = async () => {
    setIsSubmitting(true);
    try {
      await strikePleading();
      setActionSuccessMessage("Judicial Order Entered: Pleading officially stricken from docket under Fed. R. Civ. P. 5(d)(4).");
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGrantIFP = async () => {
    setIsSubmitting(true);
    try {
      await adjudicateIFP("GRANT");
      setActionSuccessMessage("In Forma Pauperis GRANTED: Court filing fees permanently waived under 28 U.S.C. § 1915.");
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDenyIFP = async () => {
    setIsSubmitting(true);
    try {
      await adjudicateIFP("DENY");
      setActionSuccessMessage("In Forma Pauperis DENIED: Mandatory 21-day fee tender grace period initiated under Williams-Guice.");
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExpeditedNotice = async () => {
    setIsSubmitting(true);
    try {
      await adjudicateExParte("ISSUE_EXPEDITED_NOTICE_ORDER");
      setActionSuccessMessage("Expedited Notice Order Issued: 4-hour telephonic service required; 24-hour hearing window established under Rule 65(b).");
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOverrideEmergencyTRO = async () => {
    setIsSubmitting(true);
    try {
      await adjudicateExParte("JUDICIAL_OVERRIDE_EMERGENCY_TRO");
      setActionSuccessMessage("Judicial Emergency Override Granted: Ex parte TRO issued for 14 calendar days upon explicit statutory finding of imminent irreparable harm under Rule 65(b)(2).");
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeclassifyStandardMotion = async () => {
    setIsSubmitting(true);
    try {
      await adjudicateExParte("DECLASSIFY_TO_STANDARD_MOTION");
      setActionSuccessMessage("Application Declassified: Ex parte status denied under Rule 65(b); reverted to standard noticed motion with statutory 21-day notice buffer.");
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleIssueCastroWarning = async () => {
    if (!selectedRelief) return;
    setIsSubmitting(true);
    try {
      await issueCastroWarning(selectedRelief);
      setActionSuccessMessage(`Castro Warning Dispatched: Litigant warned under Castro v. United States, 540 U.S. 375 with 14-day statutory election form.`);
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCastroElection = async (election: "AFFIRM" | "AMEND" | "WITHDRAW") => {
    setIsSubmitting(true);
    try {
      await processCastroElection(election);
      if (election === "AFFIRM") {
        setActionSuccessMessage("Castro Election AFFIRMED: Pleading formally docketed under new relief designation without preclusion.");
      } else if (election === "AMEND") {
        setActionSuccessMessage("Castro Election AMEND: 14-day statutory leave to file amended formal pleading granted.");
      } else {
        setActionSuccessMessage("Castro Election WITHDRAW: Pleading withdrawn without prejudice; no successive motion bar attached.");
      }
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJudgeReassign = (newJudge: string) => {
    setSelectedJudge(newJudge);
    reassignJudge(newJudge);
    setActionSuccessMessage(`Docket reassigned to ${newJudge}.`);
    setTimeout(() => setActionSuccessMessage(null), 4000);
  };

  const handleCopyText = () => {
    navigator.clipboard.writeText(selectedFiling.raw_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden bg-slate-950">
      {/* Top Filing Operational Strip */}
      <div className="px-6 py-3.5 border-b border-slate-800 bg-slate-900/70 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
              {selectedFiling.case_number}
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs text-slate-400 font-medium">
              {selectedFiling.court_division}
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs text-slate-400 font-mono">
              Filing Date: {selectedFiling.filing_date}
            </span>
          </div>
          <h2 className="text-sm font-extrabold text-slate-100 mt-0.5 line-clamp-1">
            {selectedFiling.document_title}
          </h2>
        </div>

        {/* RBAC Persona Selector & Status Badges */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <span className="text-[10px] uppercase font-mono px-2 text-slate-400 font-bold">RBAC:</span>
            <button
              type="button"
              onClick={() => setCourtRole("CLERK")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all cursor-pointer ${
                currentRole === "CLERK"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Clerk
            </button>
            <button
              type="button"
              onClick={() => setCourtRole("CHIEF_JUDGE")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all cursor-pointer ${
                currentRole === "CHIEF_JUDGE"
                  ? "bg-amber-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Chief Judge (In Camera)
            </button>
            <button
              type="button"
              onClick={() => setCourtRole("PUBLIC")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all cursor-pointer ${
                currentRole === "PUBLIC"
                  ? "bg-slate-700 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Public
            </button>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700 text-slate-300 text-xs font-mono">
            <span className="text-slate-400">Confidence:</span>
            <span className="font-bold text-emerald-400">
              {(selectedFiling.extraction_confidence * 100).toFixed(1)}%
            </span>
          </div>

          {selectedFiling.is_ifp_pending && (
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-950/90 border border-blue-500/60 text-blue-300 text-xs font-mono font-bold animate-pulse"
              title="28 U.S.C. § 1915 In Forma Pauperis petition pending. Procedural deficiency and dismissal clocks frozen."
            >
              <Scale className="w-3.5 h-3.5 text-blue-400" />
              <span>28 U.S.C. § 1915 IFP TOLLING ACTIVE</span>
            </div>
          )}

          {selectedFiling.ifp_ruling?.decision === "GRANT" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/90 border border-emerald-500/60 text-emerald-300 text-xs font-mono font-bold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>IFP GRANTED (FEES WAIVED)</span>
            </div>
          )}

          {selectedFiling.ifp_ruling?.decision === "DENY" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-orange-950/90 border border-orange-500/60 text-orange-300 text-xs font-mono font-bold">
              <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
              <span>IFP DENIED (21-DAY TENDER GRACE)</span>
            </div>
          )}

          {selectedFiling.is_ex_parte_tro && selectedFiling.rule_65b_notice_certified === false && !selectedFiling.ex_parte_action && (
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-950/90 border border-rose-500/80 text-rose-300 text-xs font-mono font-bold animate-pulse"
              title="Fed. R. Civ. P. 65(b)(1)(B): Emergency ex parte TRO lacks required attorney written notice certification."
            >
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>SEV-1: UNNOTICED EX PARTE APPLICATION (RULE 65(b)(1)(B) DEFECT)</span>
            </div>
          )}

          {selectedFiling.ex_parte_action === "ISSUE_EXPEDITED_NOTICE_ORDER" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/90 border border-amber-500/60 text-amber-300 text-xs font-mono font-bold">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>EXPEDITED 4H NOTICE ORDERED (24H HEARING)</span>
            </div>
          )}

          {selectedFiling.ex_parte_action === "JUDICIAL_OVERRIDE_EMERGENCY_TRO" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/90 border border-emerald-500/60 text-emerald-300 text-xs font-mono font-bold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>EX PARTE TRO ISSUED (RULE 65(b)(2) FINDING)</span>
            </div>
          )}

          {selectedFiling.ex_parte_action === "DECLASSIFY_TO_STANDARD_MOTION" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-950/90 border border-blue-500/60 text-blue-300 text-xs font-mono font-bold">
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>DECLASSIFIED TO STANDARD NOTICED MOTION (21-DAY BUFFER)</span>
            </div>
          )}

          {selectedFiling.is_castro_response && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/90 border border-emerald-500/60 text-emerald-300 text-xs font-mono font-bold">
              <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>CASTRO ELECTION RETURNED: {selectedFiling.castro_election}</span>
              {selectedFiling.castro_tracking_token && (
                <span className="text-emerald-400/80 font-normal ml-1 text-[11px]">
                  ({selectedFiling.castro_tracking_token})
                </span>
              )}
            </div>
          )}

          {selectedFiling.castro_election_status === "PENDING_ELECTION" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-950/90 border border-indigo-500/60 text-indigo-300 text-xs font-mono font-bold animate-pulse">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>CASTRO 14-DAY ELECTION PENDING</span>
            </div>
          )}

          {selectedFiling.castro_election_status === "AFFIRMED" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/90 border border-emerald-500/60 text-emerald-300 text-xs font-mono font-bold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>RECHARACTERIZATION AFFIRMED (CASTRO V. U.S.)</span>
            </div>
          )}

          {selectedFiling.castro_election_status === "WITHDRAWN" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300 text-xs font-mono font-bold">
              <XCircle className="w-3.5 h-3.5 text-slate-400" />
              <span>WITHDRAWN WITHOUT PREJUDICE (CASTRO ELECTION)</span>
            </div>
          )}

          {selectedFiling.docket_status === "CONDITIONALLY_LODGED" && !selectedFiling.is_ifp_pending && (
            <div
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-amber-950/90 border border-amber-500/60 text-amber-300 text-xs font-mono font-bold"
              title="Under Fed. R. Civ. P. 5(d)(4), paper is conditionally lodged pending 14-day cure."
            >
              <span>FRCP 5(d)(4) LODGED</span>
              {selectedFiling.cure_deadline && (
                <span className="text-amber-400/90 font-normal ml-1 text-[11px]">
                  (Cure by {selectedFiling.cure_deadline})
                </span>
              )}
            </div>
          )}

          {selectedFiling.docket_status === "STRICKEN_BY_COURT" && (
            <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-rose-950/90 border border-rose-500/60 text-rose-300 text-xs font-mono font-bold">
              <span>STRICKEN BY JUDICIAL ORDER</span>
            </div>
          )}

          <span
            className={`text-xs font-bold px-3 py-1 rounded-lg border ${
              selectedFiling.severity_level === "CLEAN"
                ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/50"
                : selectedFiling.severity_level === "SEV-1"
                ? "bg-red-950/80 text-red-300 border-red-500/50"
                : selectedFiling.severity_level.includes("PRO_SE")
                ? "bg-purple-950/80 text-purple-300 border-purple-500/50"
                : "bg-amber-950/80 text-amber-300 border-amber-500/50"
            }`}
          >
            {selectedFiling.severity_level}
          </span>
        </div>
      </div>

      {/* Sealed Document Isolation / In Camera Access Banners */}
      {(selectedFiling.is_redacted || (selectedFiling.is_sealed && currentRole !== "CHIEF_JUDGE")) && (
        <div className="px-6 py-2.5 bg-rose-950/70 border-b border-rose-500/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-rose-200 animate-in fade-in">
          <div className="flex items-center gap-2 font-mono">
            <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 animate-pulse" />
            <span className="font-bold">SEALED COURT DOCKET (CJIS / FEDRAMP RULE 5.9):</span>
            <span className="text-slate-300">
              Juvenile records & PII are isolated. Content redacted for role:{" "}
              <span className="font-bold text-rose-300 uppercase underline">{currentRole}</span>.
            </span>
          </div>
          <button
            type="button"
            onClick={() => setCourtRole("CHIEF_JUDGE")}
            className="text-[11px] font-semibold text-rose-300 hover:text-white underline cursor-pointer shrink-0"
          >
            Switch to Chief Judge (In Camera Clearance) &rarr;
          </button>
        </div>
      )}

      {selectedFiling.is_sealed && currentRole === "CHIEF_JUDGE" && (
        <div className="px-6 py-2 bg-amber-950/70 border-b border-amber-500/40 flex items-center gap-2 text-xs text-amber-200 font-mono animate-in fade-in">
          <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="font-bold">IN CAMERA UNREDACTED JUDICIAL INSPECTION ACTIVE:</span>
          <span className="text-amber-300/90">
            Access authorized under Article III judicial privilege. Inspection event cryptographically chained into audit ledger.
          </span>
        </div>
      )}

      {/* Offline Mode Warning Banner */}
      {isOfflineFallbackActive && (
        <div className="px-6 py-2 bg-amber-950/60 border-b border-amber-500/40 text-amber-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>{offlineWarningMessage || "Offline Mode Active: Local simulated tokens in use."}</span>
        </div>
      )}

      {/* Action Success Toast */}
      {actionSuccessMessage && (
        <div className="px-6 py-2 bg-emerald-950/80 border-b border-emerald-500/50 text-emerald-300 text-xs flex items-center justify-between animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="font-medium">{actionSuccessMessage}</span>
          </div>
          <button
            onClick={() => setActionSuccessMessage(null)}
            className="text-emerald-400 hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      {/* Main Dual-Pane Body */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* LEFT PANE: Raw Legal Pleading & Text Inspection */}
        <div className="flex-1 flex flex-col border-b lg:border-b-0 lg:border-r border-slate-800 bg-slate-950 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-800 bg-slate-900/40 flex items-center justify-between text-xs text-slate-400 shrink-0">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" />
              <span className="font-semibold text-slate-200">Scanned Document Ingress Stream</span>
            </div>
            <button
              onClick={handleCopyText}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer text-[11px]"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>{copied ? "Copied" : "Copy Raw Text"}</span>
            </button>
          </div>

          <div className="flex-1 p-5 overflow-y-auto font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap bg-slate-950/90 custom-scrollbar">
            {selectedFiling.raw_text}
          </div>
        </div>

        {/* RIGHT PANE: Sovereign Judicial Compliance & Action Console */}
        <div className="flex-1 flex flex-col bg-slate-900/40 overflow-hidden">
          {/* Detail Sub-Navigation Tabs */}
          <div className="px-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between shrink-0">
            <nav className="flex space-x-1">
              {[
                { id: "compliance", label: "Procedural Rules", count: selectedFiling.defects.length },
                { id: "scheduling", label: "Courtroom Scheduling", count: selectedFiling.scheduled_slot ? 1 : 0 },
                { id: "audit", label: "Cryptographic Chain", count: auditTrail.length },
              ].map((tab) => {
                const isActive = activeDetailTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveDetailTab(tab.id as DetailTab)}
                    className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                      isActive
                        ? "border-emerald-400 text-emerald-400"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span>{tab.label}</span>
                    {tab.count > 0 && (
                      <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                        {tab.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Sub-Panel Content Container */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
            {/* 1. COMPLIANCE & RULES TAB */}
            {activeDetailTab === "compliance" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                {/* Rule Checklist Tiles */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-200">Rule 11.1 Signature</div>
                      <div className="text-[11px] text-slate-400">Wet-ink, cryptographic or /s/ notation</div>
                    </div>
                    {selectedFiling.signature_detected ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-amber-400 shrink-0" />
                    )}
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-200">Rule 5.2(b) Service</div>
                      <div className="text-[11px] text-slate-400">Certificate of transmission to parties</div>
                    </div>
                    {selectedFiling.certificate_of_service_valid ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-amber-400 shrink-0" />
                    )}
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-200">Rule 3.1 Case Format</div>
                      <div className="text-[11px] text-slate-400">Standard YYYY-XX-XXXXXX notation</div>
                    </div>
                    {/^\d{4}-[A-Z]{2}-\d{5,6}$/.test(selectedFiling.case_number) ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
                    )}
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-200">CJIS 5.9 Security</div>
                      <div className="text-[11px] text-slate-400">SSN, juvenile PII & sealed case gate</div>
                    </div>
                    {!selectedFiling.is_sealed ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : (
                      <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />
                    )}
                  </div>
                </div>

                {/* 28 U.S.C. § 1915 IFP Tolling Callout */}
                {selectedFiling.is_ifp_pending && (
                  <div className="p-4 rounded-xl bg-blue-950/50 border border-blue-500/50 text-blue-200 text-xs space-y-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-bold text-blue-300">
                        <Scale className="w-4 h-4 text-blue-400" />
                        <span>28 U.S.C. § 1915 Indigency Tolling Subsystem Active</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-blue-900/80 border border-blue-400/40 text-[10px] font-mono font-bold text-blue-300">
                        TIMERS SUSPENDED
                      </span>
                    </div>
                    <p className="text-[11px] text-blue-200/90 leading-relaxed">
                      Indigent litigant submitted an Application to Proceed In Forma Pauperis (Form AO 240 / Fee Waiver). Under <em>Williams-Guice v. Board of Education</em>, 45 F.3d 161 (7th Cir. 1995), automated deficiency strike clocks and fee collection deadlines are legally frozen pending judicial review.
                    </p>
                    <div className="flex items-center gap-2 pt-1">
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={handleGrantIFP}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-colors cursor-pointer disabled:opacity-50"
                      >
                        Grant IFP (Waive Fees)
                      </button>
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={handleDenyIFP}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-orange-600 hover:bg-orange-500 text-white shadow-sm transition-colors cursor-pointer disabled:opacity-50"
                      >
                        Deny IFP (21-Day Tender Grace)
                      </button>
                    </div>
                  </div>
                )}

                {selectedFiling.ifp_ruling && (
                  <div
                    className={`p-4 rounded-xl text-xs space-y-1.5 border ${
                      selectedFiling.ifp_ruling.decision === "GRANT"
                        ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-200"
                        : "bg-orange-950/40 border-orange-500/50 text-orange-200"
                    }`}
                  >
                    <div className="font-bold flex items-center gap-2">
                      <Scale className="w-4 h-4" />
                      <span>
                        {selectedFiling.ifp_ruling.decision === "GRANT"
                          ? "28 U.S.C. § 1915 In Forma Pauperis GRANTED"
                          : "28 U.S.C. § 1915 In Forma Pauperis DENIED"}
                      </span>
                    </div>
                    <p className="text-[11px] opacity-90 leading-relaxed">
                      {selectedFiling.ifp_ruling.decision === "GRANT"
                        ? "Judicial order entered: Filing fees permanently waived. Pleading proceeds directly to docket validation."
                        : `Judicial order entered: Under Williams-Guice, litigant is granted a statutory 21-calendar-day fee tender grace period expiring on ${selectedFiling.ifp_ruling.fee_grace_deadline || selectedFiling.cure_deadline}.`}
                    </p>
                  </div>
                )}

                {/* FRCP 65(b)(1)(B) Emergency Ex Parte Gate Callout */}
                {selectedFiling.is_ex_parte_tro && (
                  <div className={`p-4 rounded-xl border text-xs space-y-3 ${
                    selectedFiling.rule_65b_notice_certified === false
                      ? "bg-rose-950/40 border-rose-500/60 text-rose-200"
                      : "bg-emerald-950/30 border-emerald-500/40 text-emerald-200"
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-bold">
                        <AlertTriangle className={`w-4 h-4 ${selectedFiling.rule_65b_notice_certified === false ? "text-rose-400" : "text-emerald-400"}`} />
                        <span>Fed. R. Civ. P. 65(b)(1)(B) Ex Parte Notice Verification Gate</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        selectedFiling.rule_65b_notice_certified === false
                          ? "bg-rose-900/80 border border-rose-400/50 text-rose-300"
                          : "bg-emerald-900/80 border border-emerald-400/50 text-emerald-300"
                      }`}>
                        {selectedFiling.rule_65b_notice_certified === false ? "NOTICE UNCERTIFIED (SEV-1)" : "RULE 65(b) CERTIFIED"}
                      </span>
                    </div>

                    <p className="text-[11px] leading-relaxed opacity-90">
                      {selectedFiling.rule_65b_notice_certified === false
                        ? "Under Fed. R. Civ. P. 65(b)(1)(B) and Granny Goose Foods v. Teamsters, 415 U.S. 423 (1974), an ex parte temporary restraining order cannot legally issue without attorney written certification detailing notice efforts or reasons notice should not be required. Pleading retains SEV-1 Critical Halt status pending judicial disposition."
                        : "Sworn Rule 65(b)(1)(B) certification verified: Attorney certified notice efforts and established immediate irreparable injury prior to hearing."}
                    </p>

                    {selectedFiling.rule_65b_notice_certified === false && !selectedFiling.ex_parte_action && (
                      <div className="pt-2 border-t border-rose-500/30 space-y-2">
                        <div className="text-[11px] font-bold text-rose-300 uppercase tracking-wider">
                          Tri-Partite Judicial Action Palette:
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          <button
                            type="button"
                            disabled={isSubmitting}
                            onClick={handleExpeditedNotice}
                            className="p-2.5 rounded-lg bg-amber-950/80 hover:bg-amber-900 border border-amber-500/50 text-amber-200 text-left transition-colors cursor-pointer disabled:opacity-50"
                          >
                            <div className="font-bold text-xs flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5 text-amber-400" />
                              <span>Expedited Notice</span>
                            </div>
                            <div className="text-[10px] text-amber-300/80 mt-1">
                              4-hour telephonic service + 24h hearing
                            </div>
                          </button>

                          <button
                            type="button"
                            disabled={isSubmitting}
                            onClick={handleOverrideEmergencyTRO}
                            className="p-2.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-500/50 text-rose-200 text-left transition-colors cursor-pointer disabled:opacity-50"
                          >
                            <div className="font-bold text-xs flex items-center gap-1.5">
                              <Gavel className="w-3.5 h-3.5 text-rose-400" />
                              <span>Judicial Override</span>
                            </div>
                            <div className="text-[10px] text-rose-300/80 mt-1">
                              Rule 65(b)(2) irreparable harm TRO (14d)
                            </div>
                          </button>

                          <button
                            type="button"
                            disabled={isSubmitting}
                            onClick={handleDeclassifyStandardMotion}
                            className="p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 text-left transition-colors cursor-pointer disabled:opacity-50"
                          >
                            <div className="font-bold text-xs flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-slate-300" />
                              <span>Declassify Motion</span>
                            </div>
                            <div className="text-[10px] text-slate-400 mt-1">
                              Revert to standard 21-day noticed motion
                            </div>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Procedural Defects List */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Cited Procedural Defects ({selectedFiling.defects.length})
                    </h3>
                  </div>


                  {selectedFiling.defects.length === 0 ? (
                    <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2.5">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                      <div>
                        <div className="font-bold">Zero Procedural Defects Cited</div>
                        <div className="text-[11px] text-emerald-400/80">
                          Document fully satisfies Local Rules and Court Administration statutory standards.
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedFiling.defects.map((defect, i) => (
                        <div
                          key={i}
                          className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-amber-400 font-mono">
                              {defect.rule_citation}
                            </span>
                            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                              {defect.severity}
                            </span>
                          </div>
                          <p className="text-xs text-slate-200 leading-relaxed">
                            {defect.defect_description}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Pro Se Quarantine Assistance Box */}
                {isQuarantined && (
                  <div className="p-4 rounded-xl bg-purple-950/40 border border-purple-500/40 space-y-3">
                    <div className="flex items-start gap-2.5">
                      <ShieldAlert className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-xs font-bold text-purple-200">
                          SEV-3 Unstructured Pro Se Pleading Quarantined
                        </div>
                        <div className="text-[11px] text-purple-300/80 leading-relaxed">
                          Administrative Directive 2026-04(b) suspends automated notice generation. Please designate verified relief before authorizing clerk override.
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-bold text-slate-300 block">
                        Assisted Relief Designation:
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {PRO_SE_RELIEF_OPTIONS.map((opt) => {
                          const isPicked = selectedRelief === opt.title;
                          return (
                            <button
                              key={opt.id}
                              type="button"
                              onClick={() => setSelectedRelief(opt.title)}
                              className={`p-2 rounded-lg border text-left transition-all cursor-pointer text-xs ${
                                isPicked
                                  ? "bg-purple-900/60 border-purple-400 text-white font-semibold"
                                  : "bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-850"
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-[11px] truncate">{opt.title}</span>
                                {isPicked && <Check className="w-3.5 h-3.5 text-purple-400 shrink-0" />}
                              </div>
                              <span className="text-[10px] text-slate-400 block mt-0.5 truncate">
                                Code: {opt.code}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {selectedRelief && (
                      <div className="mt-3 p-3 bg-slate-950/80 rounded-lg border border-purple-500/40 space-y-2.5">
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-bold text-purple-200 flex items-center gap-1.5">
                            <Scale className="w-3.5 h-3.5 text-purple-400" />
                            <span>Castro v. United States Recharacterization Warning</span>
                          </div>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 border border-purple-500/30 text-purple-300">
                            CASTRO-RECLASS-{selectedFiling.case_number}-{selectedFiling.id}
                          </span>
                        </div>

                        <div className="text-[11px] text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded border border-slate-800 font-sans">
                          <p className="font-semibold text-purple-300 mb-1">Mandatory Preclusion Warning (540 U.S. 375):</p>
                          Pro Se pleading will be recharacterized as <strong className="text-white">"{selectedRelief}"</strong>. Litigant must be cautioned that subsequent motions may be barred as second/successive or under res judicata, and given 14 calendar days to <span className="text-emerald-300">[AFFIRM]</span>, <span className="text-blue-300">[AMEND]</span>, or <span className="text-rose-300">[WITHDRAW]</span> without prejudice.
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <div className="text-[10px] text-slate-400 font-mono">
                            Statutory Clock: 14 Days from issuance
                          </div>
                          <button
                            type="button"
                            disabled={isSubmitting}
                            onClick={handleIssueCastroWarning}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white transition-all cursor-pointer disabled:opacity-50"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Dispatch Castro Warning & 14-Day Form</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {selectedFiling.is_castro_response && (
                  <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/50 space-y-3">
                    <div className="flex items-start gap-2.5">
                      <UserCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-xs font-bold text-emerald-200">
                          Castro v. United States Statutory Election Return Ingress
                        </div>
                        <div className="text-[11px] text-emerald-300/80 leading-relaxed">
                          This submission was automatically recognized via machine-readable tracking token{" "}
                          <span className="font-mono text-emerald-300 font-bold">{selectedFiling.castro_tracking_token}</span>{" "}
                          and linked to the pending pro se docket record.
                        </div>
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950/70 rounded-lg border border-emerald-500/30 text-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400 text-[11px]">Elected Option:</span>
                        <span className="font-mono font-bold text-emerald-300 px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40">
                          {selectedFiling.castro_election || "AFFIRM"}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300">
                        {selectedFiling.castro_election === "WITHDRAW"
                          ? "Litigant elects to withdraw submission without prejudice. No preclusive/successive bar attaches under Castro v. United States, 540 U.S. 375."
                          : selectedFiling.castro_election === "AMEND"
                          ? "Litigant requests 14-day statutory leave to file amended pleading asserting all claims."
                          : "Litigant consents to the Court's recharacterization and requests formal adjudication without preclusion penalty."}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={() => handleCastroElection(selectedFiling.castro_election || "AFFIRM")}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-slate-950 transition-all cursor-pointer disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Confirm & Apply Election ({selectedFiling.castro_election || "AFFIRM"})</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 2. COURTROOM SCHEDULING TAB (OR-Tools CP-SAT) */}
            {activeDetailTab === "scheduling" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                {selectedFiling.scheduled_slot ? (
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div className="flex items-center gap-2">
                        <CalendarCheck className="w-5 h-5 text-emerald-400" />
                        <div>
                          <div className="text-xs font-bold text-white">
                            Confirmed Hearing Calendar Slot
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono">
                            Slot ID: {selectedFiling.scheduled_slot.hearing_id}
                          </div>
                        </div>
                      </div>
                      <span className="text-xs font-bold px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                        {selectedFiling.scheduled_slot.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[11px]">Assigned Courtroom:</span>
                        <span className="font-bold text-slate-100 font-mono text-sm">
                          {selectedFiling.scheduled_slot.courtroom_id}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Assigned Judge:</span>
                        <span className="font-bold text-slate-100">
                          {selectedFiling.scheduled_slot.assigned_judge_id}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Scheduled Hearing Date:</span>
                        <span className="font-bold text-emerald-400 font-mono text-sm">
                          {selectedFiling.scheduled_slot.scheduled_date}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[11px]">Hearing Start Time:</span>
                        <span className="font-bold text-slate-100 font-mono text-sm">
                          {selectedFiling.scheduled_slot.start_time} (60 Min)
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Statutory Advance Notice Buffer Satisfied (&gt; 21 Business Days)</span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Google OR-Tools integer solver verified zero judge/courtroom conflict and locked specialized certified interpreter hardware.
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                        <ShieldCheck className="w-4 h-4" />
                        <span>28 U.S.C. § 455 Conflict Screen Passed</span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Party Rule 7.1 corporate disclosures cross-referenced against judicial financial roster. Zero statutory disqualifications found.
                        {selectedFiling.conflicted_judges_excluded && selectedFiling.conflicted_judges_excluded.length > 0 && (
                          <span className="block text-amber-400/90 font-mono mt-0.5">
                            Conflicted judicial officers excluded: {selectedFiling.conflicted_judges_excluded.join(", ")}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-2">
                    <Building className="w-8 h-8 text-slate-500 mx-auto" />
                    <h4 className="text-xs font-bold text-slate-200">Hearing Not Yet Scheduled</h4>
                    <p className="text-xs text-slate-400 max-w-sm mx-auto">
                      Procedural review must be cleared or clerk override authorized before OR-Tools CP-SAT solver allocates courtroom and calendar resources.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 3. CRYPTOGRAPHIC CHAIN OF CUSTODY TAB */}
            {activeDetailTab === "audit" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <div>
                        <div className="text-xs font-bold text-white">SHA-256 Chained Audit Ledger</div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {auditTrail.length} Append-Only Blocks Verified
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleTamperSimulation(1)}
                      className="px-2.5 py-1 text-[11px] font-bold rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors cursor-pointer"
                    >
                      {tamperedEntryId !== null ? "Restore Ledger" : "Simulate Tampering"}
                    </button>
                  </div>

                  {tamperedEntryId !== null && (
                    <div className="p-3 rounded-lg bg-red-950/60 border border-red-500/80 text-red-300 text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                      <span>Tamper Alert: Block #{tamperedEntryId} hash invalidated. Pipeline suspended.</span>
                    </div>
                  )}

                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    {auditTrail.slice(-6).map((entry) => (
                      <div
                        key={entry.entry_id}
                        className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs space-y-1.5 font-mono"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-emerald-400">Block #{entry.entry_id} • {entry.event_type}</span>
                          <span className="text-slate-500">{entry.timestamp.slice(11, 19)}Z</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 text-[10px] my-1">
                          <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-indigo-300">
                            Model: {entry.model_version || entry.agent_version || "gemini-2.5-flash"}
                          </span>
                          {entry.prompt_hash && (
                            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-purple-300 truncate max-w-[170px]" title={entry.prompt_hash}>
                              Prompt: {entry.prompt_hash.slice(0, 16)}...
                            </span>
                          )}
                          {entry.decision && (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
                              Decision: {entry.decision}
                            </span>
                          )}
                          {Boolean(entry.clerk_override) && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-950/80 border border-amber-500/40 text-amber-300 font-semibold">
                              Clerk Override Logged
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500 truncate">
                          Hash: <span className="text-slate-400">{entry.current_hash}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* BOTTOM ACTION BAR: CLERK DECISION CONSOLE */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/80 space-y-3 shrink-0">
            <div className="flex flex-wrap items-center justify-between gap-3">
              {/* Judicial Reassignment */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400 text-[11px] font-semibold">Assigned Judge:</span>
                <select
                  value={selectedJudge}
                  onChange={(e) => handleJudgeReassign(e.target.value)}
                  className="px-2.5 py-1 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="HON. ELENA CARTER">Hon. Elena Carter</option>
                  <option value="HON. MARCUS VANCE">Hon. Marcus Vance</option>
                  <option value="HON. SARAH LIN">Hon. Sarah Lin</option>
                </select>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                {selectedFiling.is_ifp_pending && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={handleGrantIFP}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-950/90 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/50 transition-all cursor-pointer disabled:opacity-50"
                      title="Grant In Forma Pauperis & Waive Fees under 28 U.S.C. § 1915"
                    >
                      <Scale className="w-3.5 h-3.5" />
                      <span>Grant IFP</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={handleDenyIFP}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-orange-950/90 hover:bg-orange-900 text-orange-300 border border-orange-500/50 transition-all cursor-pointer disabled:opacity-50"
                      title="Deny IFP & Enforce 21-Day Tender Grace Period under Williams-Guice"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Deny IFP (21-Day Grace)</span>
                    </button>
                  </>
                )}

                {selectedFiling.is_ex_parte_tro && selectedFiling.rule_65b_notice_certified === false && !selectedFiling.ex_parte_action && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={handleExpeditedNotice}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-950/90 hover:bg-amber-900 text-amber-300 border border-amber-500/50 transition-all cursor-pointer disabled:opacity-50"
                      title="Issue Expedited Notice Order: 4-hour telephonic service + 24-hour hearing setting"
                    >
                      <Clock className="w-3.5 h-3.5" />
                      <span>Expedited Notice (24h)</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={handleOverrideEmergencyTRO}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-purple-950/90 hover:bg-purple-900 text-purple-300 border border-purple-500/50 transition-all cursor-pointer disabled:opacity-50"
                      title="Judicial Override: Grant 14-Day Emergency TRO under Rule 65(b)(2)"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>Override Emergency TRO</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={handleDeclassifyStandardMotion}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 transition-all cursor-pointer disabled:opacity-50"
                      title="Declassify to Standard Noticed Motion (Statutory 21-Day Notice Buffer)"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>Declassify (21d Notice)</span>
                    </button>
                  </>
                )}

                {(selectedFiling.castro_election_status === "PENDING_ELECTION" || selectedFiling.is_castro_response) && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => handleCastroElection("AFFIRM")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-950/90 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/50 transition-all cursor-pointer disabled:opacity-50"
                      title="Affirm recharacterization under Castro v. United States and formally docket"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Affirm Recharacterization</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => handleCastroElection("AMEND")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-blue-950/90 hover:bg-blue-900 text-blue-300 border border-blue-500/50 transition-all cursor-pointer disabled:opacity-50"
                      title="Grant 14-day statutory leave to amend pleading under Castro"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>Leave to Amend (14d)</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => handleCastroElection("WITHDRAW")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-600 transition-all cursor-pointer disabled:opacity-50"
                      title="Withdraw submission without prejudice (no successive bar)"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Withdraw (No Bar)</span>
                    </button>
                  </>
                )}

                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={handleStrike}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-500/40 transition-all cursor-pointer disabled:opacity-50"
                  title="Article III Judicial Order to Strike non-conforming pleading under FRCP 5(d)(4)"
                >
                  <Gavel className="w-3.5 h-3.5" />
                  <span>Order to Strike</span>
                </button>

                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={handleDeficiency}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-500/40 transition-all cursor-pointer disabled:opacity-50"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Issue Deficiency Notice</span>
                </button>

                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={handleApprove}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-black bg-emerald-500 hover:bg-emerald-400 text-emerald-950 shadow-md shadow-emerald-500/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{isSubmitting ? "Signing & Transmitting..." : "Approve Clerk Override"}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
