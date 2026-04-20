import { z } from "zod";

export const OnboardingClientSchema = z.enum([
  "codex_cli",
  "opencode",
  "openai_compatible",
]);

export const OnboardingDeploymentSchema = z.enum([
  "local",
  "remote",
  "reverse_proxy",
]);

export const OnboardingHealthSchema = z.object({
  status: z.string(),
});

export const OnboardingModelListSchema = z.object({
  models: z.array(z.unknown()),
});

export const OnboardingCheckSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(["success", "warning", "error", "info"]),
  detail: z.string(),
  remediation: z.string().nullable(),
});

export const PublicOnboardingBootstrapSchema = z.object({
  connectAddress: z.string(),
  apiKeyAuthEnabled: z.boolean(),
});

export type OnboardingClient = z.infer<typeof OnboardingClientSchema>;
export type OnboardingDeployment = z.infer<typeof OnboardingDeploymentSchema>;
export type OnboardingCheck = z.infer<typeof OnboardingCheckSchema>;
export type PublicOnboardingBootstrap = z.infer<typeof PublicOnboardingBootstrapSchema>;
