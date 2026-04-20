import { z } from "zod";

export const SystemHealthMetricsSchema = z.object({
  totalAccounts: z.number().int().nonnegative().nullable().optional(),
  activeAccounts: z.number().int().nonnegative().nullable().optional(),
  unavailableAccounts: z.number().int().nonnegative().nullable().optional(),
  unavailableRatio: z.number().nonnegative().nullable().optional(),
  requestCount: z.number().int().nonnegative().nullable().optional(),
  rateLimitRatio: z.number().nonnegative().nullable().optional(),
  projectedExhaustionAt: z.string().datetime({ offset: true }).nullable().optional(),
  riskLevel: z.enum(["warning", "danger", "critical"]).nullable().optional(),
});

export const SystemHealthAlertSchema = z.object({
  code: z.string(),
  severity: z.enum(["warning", "critical"]),
  title: z.string(),
  message: z.string(),
  href: z.string(),
  metrics: SystemHealthMetricsSchema.nullable().optional(),
});

export const SystemHealthResponseSchema = z.object({
  status: z.enum(["healthy", "warning", "critical"]),
  updatedAt: z.string().datetime({ offset: true }),
  alert: SystemHealthAlertSchema.nullable(),
});

export type SystemHealthMetrics = z.infer<typeof SystemHealthMetricsSchema>;
export type SystemHealthAlert = z.infer<typeof SystemHealthAlertSchema>;
export type SystemHealthResponse = z.infer<typeof SystemHealthResponseSchema>;
