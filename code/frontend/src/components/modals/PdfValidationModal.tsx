"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  Flame,
  X,
  ArrowRight,
  Sparkles,
  RefreshCw,
  Cpu,
} from "lucide-react";
import { useDocket } from "../../store/DocketContext";
import { DocketFilingItem, ProceduralDefect, SeverityLevel } from "../../types/lexis";

interface ValidationResult {
  filename: string;
  case_number: string | null;
  document_title: string;
  filing_party_type: string;
  page_count: number;
  filing_date: string;
  ingestion_mode: string;
  extraction_confidence: number;
  ocr_latency_ms: number;
  has_embedded_text_layer: boolean;
  has_signature: boolean;
  has_certificate_of_service: boolean;
  has_formal_caption: boolean;
  is_emergency: boolean;
  is_sealed: boolean;
  security_cleared: boolean;
  is_valid: boolean;
  severity_level: SeverityLevel;
  requires_clerk_review: boolean;
  workflow_status: string;
  pro_se_quarantined: boolean;
  procedural_defects: ProceduralDefect[];
  security_violations: string[];
  audit_hash_sha256: string;
  raw_text_snippet: string;
}

interface PdfValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PdfValidationModal({ isOpen, onClose }: PdfValidationModalProps) {
  const { addFiling } = useDocket();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ValidationResult | null>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (file: File) => {
    setIsUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/filings/validate-pdf", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }

      const data: ValidationResult = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to validate PDF document."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const loadSample = (type: "clean" | "defective" | "pro_se") => {
    let sampleText = "";
    let sampleFilename = "";

    if (type === "clean") {
      sampleFilename = "motion_summary_judgment.pdf";
      sampleText = `IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT
CASE NO: 2026-CV-044192
DIVISION: CIVIL COMMERCIAL

OMEGA INDUSTRIES INC., Plaintiff
v.
TITAN ENERGY CORP., Defendant

PLAINTIFF'S MOTION FOR SUMMARY JUDGMENT
Plaintiff Omega Industries Inc. respectfully moves this Court pursuant to Local Rule 56 for entry of Summary Judgment.

Respectfully submitted,
/s/ Gregory Hayes, Esq.
Counsel for Plaintiff

CERTIFICATE OF SERVICE
I hereby certify that a true copy was served electronically via ECF upon all registered counsel on September 4, 2026.
/s/ Gregory Hayes, Esq.`;
    } else if (type === "defective") {
      sampleFilename = "defective_pleading_no_signature.pdf";
      sampleText = `IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT
CASE NO: 2026-CV-077312

ACME CORP v. BETA LLC
MOTION TO EXTEND DISCOVERY SCHEDULE

The parties move to extend discovery deadline.
[DEFECT: Missing signature block]
[DEFECT: Missing certificate of service]`;
    } else {
      sampleFilename = "informal_pro_se_letter.pdf";
      sampleText = `TO THE CLERK OF METROPOLIS COURT:
I am writing pro se because I cannot pay the filing fees and need an extension to respond.
/s/ John Tenant`;
    }

    const blob = new Blob([sampleText], { type: "application/pdf" });
    const file = new File([blob], sampleFilename, { type: "application/pdf" });
    processFile(file);
  };

  const handleAddToQueue = () => {
    if (!result) return;

    const newFiling: DocketFilingItem = {
      id: `filing-${Date.now()}`,
      case_id: result.case_number
        ? `c-${result.case_number.toLowerCase()}`
        : `c-${Date.now()}`,
      case_number: result.case_number || "PENDING-CASE-NO",
      court_division: "GENERAL CIVIL",
      assigned_judge_id: "HON. ELENA CARTER",
      document_title: result.document_title,
      party_type: result.filing_party_type as any,
      filing_date: result.filing_date,
      is_emergency: result.is_emergency,
      is_sealed: result.is_sealed,
      severity_level: result.severity_level,
      workflow_status: result.workflow_status as any,
      extraction_confidence: result.extraction_confidence,
      signature_detected: result.has_signature,
      certificate_of_service_valid: result.has_certificate_of_service,
      pro_se_quarantined: result.pro_se_quarantined,
      defects: result.procedural_defects,
      raw_text: result.raw_text_snippet,
    };

    addFiling(newFiling);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-3xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                PDF Filing Ingress & Rule Validator
                <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
                  STATUTORY GATING
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Upload court pleadings to evaluate Local Civil Rules, captions, and PII gates.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 custom-scrollbar">
          {/* Upload Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragActive
                ? "border-emerald-400 bg-emerald-500/5 shadow-inner"
                : "border-slate-700 hover:border-slate-500 hover:bg-slate-800/50 bg-slate-950/40"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileInput}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center gap-3">
              <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-300 border border-slate-700">
                {isUploading ? (
                  <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
                ) : (
                  <FileText className="w-6 h-6 text-slate-400" />
                )}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-200">
                  {isUploading
                    ? "Executing Digital Ingress & Rule Verification..."
                    : "Drag & drop a legal PDF pleading, or click to browse"}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Supports electronic court filings, scanned motions, and statutory docket records.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Sample Presets */}
          <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/60 pt-4">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Test With Presets:
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => loadSample("clean")}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                Clean Motion (Pass)
              </button>
              <button
                type="button"
                onClick={() => loadSample("defective")}
                className="px-2.5 py-1 rounded bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 border border-amber-500/40 transition-colors"
              >
                Defective (Rule 11.1 / 5.2b)
              </button>
              <button
                type="button"
                onClick={() => loadSample("pro_se")}
                className="px-2.5 py-1 rounded bg-purple-950/50 hover:bg-purple-900/60 text-purple-300 border border-purple-500/40 transition-colors"
              >
                Pro Se Quarantine
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-xl bg-red-950/50 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Validation Result Display */}
          {result && (
            <div className="border border-slate-800 rounded-xl bg-slate-950/80 p-5 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-200">
              {/* Result Header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-300">
                      {result.case_number || "NO CASE # DETECTED"}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        result.severity_level === "CLEAN"
                          ? "bg-emerald-950 text-emerald-300 border-emerald-500/50"
                          : result.severity_level.includes("UNSTRUCTURED_PRO_SE")
                          ? "bg-purple-950 text-purple-300 border-purple-500/50"
                          : result.severity_level === "SEV-1"
                          ? "bg-red-950 text-red-300 border-red-500/50"
                          : "bg-amber-950 text-amber-300 border-amber-500/50"
                      }`}
                    >
                      {result.severity_level}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-100 mt-1">
                    {result.document_title}
                  </h3>
                </div>

                <div className="text-right">
                  <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                    <Cpu className="w-3.5 h-3.5 text-slate-500" />
                    {result.ingestion_mode} ({result.ocr_latency_ms}ms)
                  </span>
                  <span className="text-[11px] font-mono text-emerald-400 font-semibold">
                    Confidence: {(result.extraction_confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Statutory Rules Checklist Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80">
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-300">Rule 11.1 Signature</span>
                  {result.has_signature ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                  )}
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-300">Rule 5.2(b) Service</span>
                  {result.has_certificate_of_service ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                  )}
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-300">Rule 3.1 Caption</span>
                  {result.has_formal_caption ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                  )}
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-300">CJIS PII Gate</span>
                  {result.security_cleared ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <ShieldAlert className="w-4 h-4 text-red-400" />
                  )}
                </div>
              </div>

              {/* Defects List */}
              {result.procedural_defects.length > 0 && (
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                  <p className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                    Cited Procedural Defects ({result.procedural_defects.length})
                  </p>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {result.procedural_defects.map((defect, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-amber-400 font-mono text-[11px] shrink-0">
                          [{defect.rule_citation}]
                        </span>
                        <span className="text-slate-300 leading-relaxed">
                          {defect.defect_description}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action Button: Add to Docket Queue */}
              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={handleAddToQueue}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-500/20 transition-all"
                >
                  <span>Add to Live Intake Queue</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
