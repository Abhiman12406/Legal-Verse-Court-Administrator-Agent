"use client";

import React from "react";
import { Header } from "../components/layout/Header";
import { QueueSidebar } from "../components/layout/QueueSidebar";
import { SideBySideReview } from "../components/console/SideBySideReview";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Header />
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        <QueueSidebar />
        <SideBySideReview />
      </main>
    </div>
  );
}
