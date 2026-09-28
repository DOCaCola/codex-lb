import { z } from "zod";
import { get, post } from "@/lib/api-client";

const Answer = z.object({
  result: z.string(),
  resets_left: z.number().nullable(),
  cleared: z.array(z.string()),
});
const Operation = z.object({
  operationId: z.string(),
  grantId: z.string(),
  createdAt: z.string(),
  retryUntil: z.string(),
  leaseUntil: z.string(),
  result: Answer.nullable(),
});
const Grant = z.object({
  id: z.string(),
  label: z.string(),
  resets_total: z.number(),
  resets_left: z.number(),
  starts_at: z.string().nullable(),
  ends_at: z.string().nullable(),
  clears: z.array(z.string()),
  paused: z.boolean(),
  usable_now: z.boolean(),
  use_requires_limit: z.boolean(),
});
const Grants = z.object({
  status: z
    .object({
      eligible: z.boolean(),
      at_limit: z.boolean(),
      ineligible_reason: z.string().nullable(),
      cooldown_until: z.string().nullable(),
      grants: z.array(Grant),
    })
    .nullable(),
  error: z.string().nullable(),
  operations: z.array(Operation),
});
export type ResetGrant = z.infer<typeof Grant>;
export type ResetOperation = z.infer<typeof Operation>;
export type ResetRequest = {
  grantId: string;
  operationId: string;
  confirmed: true;
  acknowledgeUncertain: boolean;
};
const path = (id: string) =>
  `/api/claude-accounts/${encodeURIComponent(id)}/reset-grants`;
export const readGrants = (id: string) => get(path(id), Grants);
export const consumeGrant = (id: string, body: ResetRequest) =>
  post(
    `${path(id)}/consume`,
    z.object({ operation: Operation, refreshComplete: z.boolean() }),
    { body },
  );
