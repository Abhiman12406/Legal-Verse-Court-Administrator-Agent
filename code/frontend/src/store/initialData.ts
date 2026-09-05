import { AuditRecord, DocketFilingItem } from "../types/lexis";

/**
 * Initial static data arrays are now empty.
 * All case records, active dockets, and append-only audit trail logs
 * are dynamically loaded from the ACID PostgreSQL database backend.
 */
export const INITIAL_FILINGS: DocketFilingItem[] = [];

export const INITIAL_AUDIT_TRAIL: AuditRecord[] = [];
