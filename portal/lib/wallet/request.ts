// Mirrors wallet/request.py's DcqlLiteQuery/AuthorizationRequest shapes —
// same field names, so the TS and Python sides read as one protocol.

export interface DcqlLiteQuery {
  vct: string;
  required_claims: string[];
  required_tier: string | null;
  required_loa: string | null;
}

export interface AuthorizationRequest {
  verifier_id: string;
  nonce: string;
  query: DcqlLiteQuery;
}
