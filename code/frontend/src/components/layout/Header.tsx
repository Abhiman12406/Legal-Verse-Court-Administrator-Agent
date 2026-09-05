"use client";

import React, { useState } from "react";
import {
  Scale,
  ShieldCheck,
  Clock,
  UserCheck,
  AlertTriangle,
  UploadCloud,
  FileCheck2,
  Bell,
  Zap,
  CheckCircle2,
  Trash2,
} from "lucide-react";
import { useDocket } from "../../store/DocketContext";
import { PdfValidationModal } from "../modals/PdfValidationModal";

export function Header() {
  const { filings, notifications, queueMetrics, clearNotifications } = useDocket();
  const [isValidationModalOpen, setIsValidationModalOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const emergencyCount = filings.filter((f) => f.is_emergency).length;
  const pendingCount = filings.filter(
    (f) => f.workflow_status === "AWAITING_CLERK"
  ).length;
  const validatedCount = filings.filter(
    (f) => f.workflow_status === "COMPLETED" || f.workflow_status === "VALIDATED"
  ).length;

  const hasCritical = notifications.some((n) => n.priority === "CRITICAL");

  return (
    <header className="bg-slate-950 border-b border-slate-800 text-slate-100 sticky top-0 z-40">
      <div className="max-w-[1920px] mx-auto px-4 lg:px-6 h-14 flex items-center justify-between">
        {/* Brand & Court Enclave Title */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold shadow-[0_0_15px_rgba(16,185,129,0.12)]">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-wider text-base text-white">
                LEXISOPS
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                COURT ADMIN OS
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Metropolis Trial Court • Procedural Intake & Exception Console
            </p>
          </div>
        </div>

        {/* Live Operational Health & Queue Telemetry */}
        <div className="flex items-center gap-3 text-xs">
          {emergencyCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-red-950/80 border border-red-500/50 text-red-300 font-bold animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              <span>{emergencyCount} SEV-1 Emergency</span>
            </div>
          )}

          {/* Redis In-Memory Broker & Priority Queue Status */}
          <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs">
            <Zap className="w-3.5 h-3.5 text-rose-400" />
            <span className="font-mono text-[11px] text-slate-300">
              Redis Queue:{" "}
              <span className="text-rose-400 font-semibold">
                {queueMetrics.total_depth}
              </span>
              {queueMetrics.emergency > 0 && (
                <span className="text-red-400 ml-1">({queueMetrics.emergency} TRO)</span>
              )}
            </span>
          </div>

          <div className="hidden lg:flex items-center gap-3 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-[11px] font-mono">
            <span className="flex items-center gap-1 text-amber-400 font-semibold">
              <Clock className="w-3 h-3" /> {pendingCount} Pending Triage
            </span>
            <span className="text-slate-600">|</span>
            <span className="flex items-center gap-1 text-emerald-400 font-semibold">
              <FileCheck2 className="w-3 h-3" /> {validatedCount} Validated
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-[11px]">CJIS 5.9 Enclave</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs">
            <UserCheck className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-slate-300">Clerk #42</span>
          </div>

          {/* Redis Real-Time Notification Bell & Tray */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 transition-colors"
              title="Real-Time Clerk Notifications (Redis Pub/Sub)"
            >
              <Bell className="w-4 h-4" />
              {notifications.length > 0 && (
                <span
                  className={`absolute -top-1 -right-1 px-1.5 py-0.2 rounded-full text-[9px] font-bold text-white ${
                    hasCritical ? "bg-red-600 animate-pulse" : "bg-rose-500"
                  }`}
                >
                  {notifications.length}
                </span>
              )}
            </button>

            {/* Notification Dropdown Panel */}
            {isNotificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl z-50 overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-rose-400" />
                    <span className="text-xs font-bold text-white">
                      Live Redis Event Stream
                    </span>
                  </div>
                  {notifications.length > 0 && (
                    <button
                      type="button"
                      onClick={clearNotifications}
                      className="text-[10px] text-slate-400 hover:text-red-400 flex items-center gap-1 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" /> Clear
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60 text-xs">
                  {notifications.length === 0 ? (
                    <div className="px-4 py-8 text-center text-slate-500 text-xs">
                      No active Redis notifications. Listening to Pub/Sub channel...
                    </div>
                  ) : (
                    notifications.map((n) => (
                      <div
                        key={n.event_id}
                        className="px-4 py-3 hover:bg-slate-800/40 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                              n.priority === "CRITICAL"
                                ? "bg-red-950 border border-red-500/60 text-red-300"
                                : n.priority === "HIGH"
                                ? "bg-amber-950 border border-amber-500/60 text-amber-300"
                                : "bg-blue-950 border border-blue-500/60 text-blue-300"
                            }`}
                          >
                            {n.event_type}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {n.iso_time ? n.iso_time.slice(11, 19) : "Just now"}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-300 font-mono">
                          {n.payload?.case_number && (
                            <span className="text-emerald-400 font-semibold mr-1.5">
                              {n.payload.case_number}
                            </span>
                          )}
                          {n.payload?.filing_id && (
                            <span className="text-slate-400 mr-1.5">
                              [{n.payload.filing_id}]
                            </span>
                          )}
                          {n.payload?.action ||
                            n.payload?.status ||
                            n.payload?.alert ||
                            n.payload?.election ||
                            "Docket Event Recorded"}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Primary PDF Ingress Action */}
          <button
            type="button"
            onClick={() => setIsValidationModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-black rounded-lg bg-emerald-500 hover:bg-emerald-400 text-emerald-950 shadow-md shadow-emerald-500/20 transition-all cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span className="hidden sm:inline">Upload & Validate PDF</span>
            <span className="sm:hidden">Upload</span>
          </button>
        </div>
      </div>

      {/* Real-Time PDF Ingress Modal */}
      <PdfValidationModal
        isOpen={isValidationModalOpen}
        onClose={() => setIsValidationModalOpen(false)}
      />
    </header>
  );
}

