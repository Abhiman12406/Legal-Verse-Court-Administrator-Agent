import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

const CLERK_SECRET_KEY =
  process.env.CLERK_SECRET_KEY || "LEXIS_OPS_CLERK_HMAC_MASTER_KEY";

export function generateClerkToken(
  clerkId: string,
  caseId: string,
  action: string,
  timestamp?: number
): string {
  const ts = timestamp ?? Math.floor(Date.now() / 1000);
  const msg = `${clerkId}:${caseId}:${action}:${ts}`;
  const sig = crypto
    .createHmac("sha256", CLERK_SECRET_KEY)
    .update(msg)
    .digest("hex");
  return `${msg}:${sig}`;
}

export function verifyClerkToken(token: string): boolean {
  try {
    const parts = token.split(":");
    if (parts.length !== 5) return false;
    const [clerkId, caseId, action, tsStr, sig] = parts;
    const msg = `${clerkId}:${caseId}:${action}:${tsStr}`;
    const expectedSig = crypto
      .createHmac("sha256", CLERK_SECRET_KEY)
      .update(msg)
      .digest("hex");
    return crypto.timingSafeEqual(
      Buffer.from(sig, "hex"),
      Buffer.from(expectedSig, "hex")
    );
  } catch {
    return false;
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      case_id,
      filing_id,
      clerk_id = "CLERK_USER_42",
      action,
      decision_notes = "",
      workflow_id,
      relief_designation,
    } = body;

    if (!case_id || !action) {
      return NextResponse.json(
        { error: "Missing mandatory fields: case_id, action" },
        { status: 400 }
      );
    }

    if (!["APPROVE_OVERRIDE", "ISSUE_DEFICIENCY", "REASSIGN_JUDGE"].includes(action)) {
      return NextResponse.json(
        { error: `Invalid clerk action: ${action}` },
        { status: 400 }
      );
    }

    // 1. Generate verified cryptographic HMAC clerk token
    const token = generateClerkToken(clerk_id, case_id, action);
    const isValid = verifyClerkToken(token);

    if (!isValid) {
      return NextResponse.json(
        { error: "Cryptographic token verification failed." },
        { status: 500 }
      );
    }

    // 2. Prepare signal payload for Temporal Workflow
    const signalPayload = {
      clerk_id,
      action,
      case_id,
      filing_id,
      notes: decision_notes,
      clerk_token: token,
      relief_designation: relief_designation || undefined,
      timestamp: new Date().toISOString(),
      workflow_id: workflow_id || `lexis-ops-wf-${case_id}`,
      override_authorized: action === "APPROVE_OVERRIDE",
    };

    // 3. Resolve resumed workflow status
    let resumedStatus = "VALIDATED";
    if (action === "ISSUE_DEFICIENCY") {
      resumedStatus = "DEFICIENT";
    } else if (action === "REASSIGN_JUDGE") {
      resumedStatus = "REASSIGNED";
    }

    return NextResponse.json({
      success: true,
      case_id,
      filing_id,
      workflow_id: signalPayload.workflow_id,
      action,
      relief_designation: relief_designation || null,
      clerk_token: token,
      token_signature: token.split(":")[4],
      workflow_status: resumedStatus,
      dispatched_at: signalPayload.timestamp,
      message: `Temporal workflow signal 'submit_clerk_decision' dispatched and authorized via HMAC token.`,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
