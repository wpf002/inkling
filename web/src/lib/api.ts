import { z } from "zod";
import {
  Consent,
  RoundEventBody,
  roundCompleteResponseSchema,
  roundEventBatchResponseSchema,
  roundGamblesResponseSchema,
  selfReportItemsResponseSchema,
  SelfReportItemDef,
  SelfReportSubmission,
  sessionCreateResponseSchema,
  sessionStateSchema,
  SessionState,
} from "./schemas";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(`API ${status}: ${JSON.stringify(detail)}`);
  }
}

async function request<T extends z.ZodTypeAny>(
  path: string,
  schema: T,
  init: RequestInit & { token?: string } = {},
): Promise<z.infer<T>> {
  const { token, headers, ...rest } = init;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string> | undefined),
  };
  if (token) finalHeaders["X-Inkling-Session"] = token;

  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body);
  return schema.parse(body);
}

export const api = {
  createSession: (params: {
    consent: Consent;
    age_attested: boolean;
    anonymous_token: string;
  }) =>
    request("/sessions", sessionCreateResponseSchema, {
      method: "POST",
      body: JSON.stringify(params),
    }),

  getSession: (token: string): Promise<SessionState> =>
    request(`/sessions/${token}`, sessionStateSchema, {
      method: "GET",
      token,
    }),

  deleteSession: (token: string) =>
    request(
      `/sessions/${token}`,
      z.object({ status: z.string(), session_id: z.string() }),
      { method: "DELETE", token },
    ),

  submitSelfReport: (token: string, payload: SelfReportSubmission) =>
    request(
      `/sessions/${token}/self-report`,
      z.object({ saved: z.number() }),
      {
        method: "POST",
        body: JSON.stringify(payload),
        token,
      },
    ),

  getSelfReportItems: (): Promise<{ items: SelfReportItemDef[] }> =>
    request("/content/self-report-items", selfReportItemsResponseSchema, {
      method: "GET",
    }),

  postRoundEvents: (token: string, round: string, events: RoundEventBody[]) =>
    request(
      `/sessions/${token}/round-events`,
      roundEventBatchResponseSchema,
      {
        method: "POST",
        body: JSON.stringify({ round, events }),
        token,
      },
    ),

  postRoundComplete: (token: string, round: string) =>
    request(
      `/sessions/${token}/round-complete`,
      roundCompleteResponseSchema,
      {
        method: "POST",
        body: JSON.stringify({ round }),
        token,
      },
    ),

  getInferences: (token: string, round: string) =>
    request(
      `/sessions/${token}/inferences?round=${encodeURIComponent(round)}`,
      roundCompleteResponseSchema,
      { method: "GET", token },
    ),

  getRoundGambles: (round: string) =>
    request(
      `/content/round-gambles?round=${encodeURIComponent(round)}`,
      roundGamblesResponseSchema,
      { method: "GET" },
    ),

  getRoundContent: <T>(round: string): Promise<T> =>
    request(
      `/content/round-content?round=${encodeURIComponent(round)}`,
      z.unknown() as z.ZodType<T>,
      { method: "GET" },
    ),
};

export { ApiError };
