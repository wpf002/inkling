import { z } from "zod";

export const consentSchema = z.object({
  gameplay: z.boolean(),
  interaction_patterns: z.boolean(),
  self_report: z.boolean(),
  retain_profile_7d: z.boolean(),
  research_aggregate: z.boolean(),
});
export type Consent = z.infer<typeof consentSchema>;

export const sessionCreateResponseSchema = z.object({
  session_id: z.string().uuid(),
  anonymous_token: z.string(),
  created_at: z.string(),
});

export const sessionStateSchema = z.object({
  session_id: z.string().uuid(),
  anonymous_token: z.string(),
  consent: consentSchema,
  age_attested: z.boolean(),
  has_self_report: z.boolean(),
  completed_at: z.string().nullable(),
  created_at: z.string(),
  completed_rounds: z.array(z.string()).default([]),
  next_round: z.string().nullable().default(null),
});
export type SessionState = z.infer<typeof sessionStateSchema>;

export const roundManifestEntrySchema = z.object({
  id: z.string(),
  title: z.string(),
  duration_s: z.number(),
  content_file: z.string().optional(),
  constructs: z.array(z.string()),
});
export type RoundManifestEntry = z.infer<typeof roundManifestEntrySchema>;

export const selfReportItemDefSchema = z.object({
  id: z.string(),
  construct: z.string(),
  prompt: z.string(),
  scale: z.string(),
});
export type SelfReportItemDef = z.infer<typeof selfReportItemDefSchema>;

export const selfReportItemsResponseSchema = z.object({
  items: z.array(selfReportItemDefSchema),
});

export const selfReportItemSchema = z.object({
  item_id: z.string().min(1).max(32),
  response: z.number().int().min(1).max(5),
});

export const selfReportSubmissionSchema = z.object({
  responses: z.array(selfReportItemSchema).min(1),
});
export type SelfReportSubmission = z.infer<typeof selfReportSubmissionSchema>;

export const roundEventSchema = z.object({
  event_type: z.string().min(1).max(64),
  payload: z.record(z.string(), z.unknown()),
  t_ms: z.number().int().min(0),
});
export type RoundEventBody = z.infer<typeof roundEventSchema>;

export const roundEventBatchResponseSchema = z.object({
  accepted: z.number().int(),
});

export const inferenceSchema = z.object({
  construct: z.string(),
  tier: z.enum(["high", "medium", "overreach"]),
  value: z.record(z.string(), z.unknown()),
  confidence: z.number(),
  evidence: z.record(z.string(), z.unknown()),
});
export type InferenceData = z.infer<typeof inferenceSchema>;

export const roundCompleteResponseSchema = z.object({
  inferences: z.array(inferenceSchema),
});

export const roundGambleSchema = z.object({
  id: z.string(),
  win: z.number(),
  lose: z.number(),
});
export type RoundGamble = z.infer<typeof roundGambleSchema>;

export const roundGamblesResponseSchema = z.object({
  round_id: z.string(),
  gambles: z.array(roundGambleSchema),
  conditions: z.array(z.string()),
  hurry_ms: z.number(),
  alpha: z.number(),
});
export type RoundGamblesResponse = z.infer<typeof roundGamblesResponseSchema>;
