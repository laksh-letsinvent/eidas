// Thin fetch wrappers against the Phase 3.5 FastAPI service (service/main.py).
// Local dev tool only — see CLAUDE.md's Phase 3.5 decisions. Base URL is
// overridable via NEXT_PUBLIC_VERIFIER_SERVICE_URL for flexibility, but the
// service itself is never deployed.

import type { AuthorizationRequest } from "./request";
import type { CredentialOffer } from "./vci";

const BASE_URL = process.env.NEXT_PUBLIC_VERIFIER_SERVICE_URL ?? "http://localhost:8420";

interface CredentialOfferResponse extends CredentialOffer {
  offer_id: string;
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${path} -> ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function fetchCredentialOffer(): Promise<CredentialOfferResponse> {
  return postJson<CredentialOfferResponse>("/credential-offer");
}

export function fetchCredential(offerId: string, proofJwt: string): Promise<{ credential: string }> {
  return postJson<{ credential: string }>("/issue", { offer_id: offerId, proof_jwt: proofJwt });
}

export function fetchAuthorizationRequest(): Promise<AuthorizationRequest> {
  return postJson<AuthorizationRequest>("/authorization-request");
}

export function postVerify(presentation: string, request: AuthorizationRequest): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>("/verify", { presentation, request });
}

export function submitPresentation(nonce: string, presentation: string): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>("/present", { nonce, presentation });
}

export async function pollPresentation(nonce: string): Promise<string | null> {
  const response = await fetch(`${BASE_URL}/present/${nonce}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`poll /present/${nonce} -> ${response.status}`);
  const body = (await response.json()) as { presentation: string };
  return body.presentation;
}

export interface TamperDemoResult {
  species: string;
  description: string;
  presentation: string;
  request: AuthorizationRequest;
  expected_decision: "accept" | "reject";
  expected_check: string | null;
}

export function postTamperDemo(species: string): Promise<TamperDemoResult> {
  return postJson<TamperDemoResult>("/tamper-demo", { species });
}
