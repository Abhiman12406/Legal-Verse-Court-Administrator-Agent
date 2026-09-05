"use client";

import React, { useState } from "react";
import {
  Search,
  AlertCircle,
  Clock,
  CheckCircle2,
  Lock,
  Flame,
  FileText,
  ShieldAlert,
  Inbox,
  Database,
  RefreshCw,
} from "lucide-react";
import { useDocket } from "../../store/DocketContext";
import { SeverityLevel } from "../../types/lexis";

export function QueueSidebar() {
  const { filings, selectedFilingId, selectFiling, isLoading, seedDatabase } = useDocket();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");

  const filteredFilings = filings.filter((item) => {
    const matchesSearch =
      item.case_number.toLowerCase().includes(search.toLowerCase()) ||
      item.document_title.toLowerCase().includes(search.toLowerCase());
    if (severityFilter === "ALL") return matchesSearch;
    return matchesSearch && item.severity_level === severityFilter;
  });

  const getSeverityBadge = (level: SeverityLevel, isEmergency: boolean) => {
    if (isEmergency || level === "SEV-1") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-red-950/90 text-red-300 border border-red-500/40 shrink-0">
          <Flame className="w-3 h-3 text-red-400" /> SEV-1
        </span>
      );
    }
    if (level === "SEV-3: UNSTRUCTURED_PRO_SE") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-purple-950/90 text-purple-300 border border-purple-500/40 shrink-0">
          <ShieldAlert className="w-3 h-3 text-purple-400" /> SEV-3 PRO SE
        </span>
      );
    }
    if (level === "SEV-2") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-950/90 text-amber-300 border border-amber-500/40 shrink-0">
          <AlertCircle className="w-3 h-3 text-amber-400" /> SEV-2 DEFECT
        </span>
      );
    }
    if (level === "SEV-3") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-950/90 text-amber-300 border border-amber-500/40 shrink-0">
          <AlertCircle className="w-3 h-3 text-amber-400" /> SEV-3
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950/90 text-emerald-300 border border-emerald-500/40 shrink-0">
        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> CLEAN
      </span>
    );
  };

  return (
    <aside className="w-full lg:w-80 xl:w-92 bg-slate-950 border-r border-slate-800 flex flex-col h-[calc(100vh-3.5rem)] shrink-0">
      {/* Sidebar Top Search & Filter Bar */}
      <div className="p-3.5 border-b border-slate-800 space-y-2.5 bg-slate-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-200">
            <Inbox className="w-4 h-4 text-emerald-400" />
            <span>Intake Queue</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => seedDatabase(true)}
              disabled={isLoading}
              title="Re-seed PostgreSQL ACID Benchmark Records"
              className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-indigo-400" : ""}`} />
            </button>
            <span className="text-[11px] font-mono text-slate-400">
              {filteredFilings.length} / {filings.length}
            </span>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search case # or filing title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>

        {/* Severity Filter Pills */}
        <div className="grid grid-cols-5 gap-1 text-[10px] font-semibold">
          {[
            { id: "ALL", label: "All" },
            { id: "SEV-1", label: "SEV-1" },
            { id: "SEV-2", label: "SEV-2" },
            { id: "SEV-3: UNSTRUCTURED_PRO_SE", label: "Pro Se" },
            { id: "CLEAN", label: "Clean" },
          ].map((btn) => (
            <button
              key={btn.id}
              type="button"
              onClick={() => setSeverityFilter(btn.id)}
              className={`py-1 rounded text-center transition-all cursor-pointer ${
                severityFilter === btn.id
                  ? "bg-slate-700 text-white font-bold"
                  : "bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Queue Item List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2 custom-scrollbar">
        {isLoading && filings.length === 0 && (
          <div className="p-8 text-center space-y-3">
            <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto opacity-70" />
            <p className="text-xs text-slate-400 font-mono">Connecting to ACID PostgreSQL...</p>
          </div>
        )}

        {!isLoading && filings.length === 0 && (
          <div className="p-6 text-center space-y-3 bg-slate-900/40 rounded-xl border border-slate-800/80 my-4 mx-2">
            <Database className="w-8 h-8 text-slate-500 mx-auto" />
            <div className="text-xs font-bold text-slate-300">Database Empty</div>
            <p className="text-[11px] text-slate-400">
              No active pleadings in ACID storage. Populate benchmark dockets:
            </p>
            <button
              onClick={() => seedDatabase(true)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer w-full"
            >
              Seed Benchmark Dockets
            </button>
          </div>
        )}

        {filteredFilings.map((filing) => {
          const isSelected = filing.id === selectedFilingId;
          return (
            <div
              key={filing.id}
              onClick={() => selectFiling(filing.id)}
              className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                isSelected
                  ? "bg-slate-800/90 border-emerald-500/80 shadow-md shadow-emerald-500/5"
                  : "bg-slate-900/50 border-slate-800/80 hover:bg-slate-900 hover:border-slate-700"
              }`}
            >
              {/* Top Row: Case Number & Severity */}
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="font-mono text-[11px] font-bold text-slate-300 truncate">
                  {filing.case_number}
                </span>
                {getSeverityBadge(filing.severity_level, filing.is_emergency)}
              </div>

              {/* Pleading Title */}
              <h3 className="text-xs font-semibold text-slate-100 line-clamp-2 leading-relaxed mb-2">
                {filing.document_title}
              </h3>

              {/* Bottom Metadata */}
              <div className="flex items-center gap-2 text-[10px] text-slate-400">
                <span className="flex items-center gap-1 font-mono">
                  <FileText className="w-3 h-3 text-slate-500" />
                  {filing.party_type}
                </span>

                {filing.is_ifp_pending && (
                  <span className="flex items-center gap-1 text-blue-400 font-bold px-1.5 py-0.2 rounded bg-blue-950/80 border border-blue-500/40 text-[9px] font-mono">
                    IFP TOLL
                  </span>
                )}

                {filing.is_ex_parte_tro && filing.rule_65b_notice_certified === false && (
                  <span className="flex items-center gap-1 text-rose-400 font-bold px-1.5 py-0.2 rounded bg-rose-950/80 border border-rose-500/40 text-[9px] font-mono">
                    RULE 65(b)
                  </span>
                )}

                {filing.is_castro_response && (
                  <span className="flex items-center gap-1 text-emerald-400 font-bold px-1.5 py-0.2 rounded bg-emerald-950/80 border border-emerald-500/40 text-[9px] font-mono">
                    CASTRO RET
                  </span>
                )}

                {filing.castro_election_status === "PENDING_ELECTION" && (
                  <span className="flex items-center gap-1 text-indigo-400 font-bold px-1.5 py-0.2 rounded bg-indigo-950/90 border border-indigo-500/40 text-[9px] font-mono">
                    CASTRO 14D
                  </span>
                )}

                {filing.is_sealed && (
                  <span className="flex items-center gap-1 text-amber-400 font-bold">
                    <Lock className="w-3 h-3" /> SEALED
                  </span>
                )}

                <span className="ml-auto font-mono text-[10px] text-slate-400 flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {filing.workflow_status}
                </span>
              </div>
            </div>
          );
        })}

        {!isLoading && filteredFilings.length === 0 && filings.length > 0 && (
          <div className="text-center py-10 text-xs text-slate-500">
            No filings match the current filter.
          </div>
        )}
      </div>
    </aside>
  );
}
