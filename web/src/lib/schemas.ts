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
});
export type SessionState = z.infer<typeof sessionStateSchema>;

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
