import type { ApiKeyEnforcedModelTiers, ReasoningEffortType } from "@/features/api-keys/schemas";

export type TieredModelEnforcementDraft = {
  miniModel: string;
  miniReasoning: ReasoningEffortType;
  standardModel: string;
  standardReasoning: ReasoningEffortType;
};

export const EMPTY_TIERED_MODEL_ENFORCEMENT: TieredModelEnforcementDraft = {
  miniModel: "",
  miniReasoning: "none",
  standardModel: "",
  standardReasoning: "none",
};

export function tieredModelEnforcementFromValue(
  tiers: ApiKeyEnforcedModelTiers | null | undefined,
): TieredModelEnforcementDraft {
  return {
    miniModel: tiers?.mini?.model ?? "",
    miniReasoning: tiers?.mini?.reasoningEffort ?? "none",
    standardModel: tiers?.standard?.model ?? "",
    standardReasoning: tiers?.standard?.reasoningEffort ?? "none",
  };
}

export function tieredModelEnforcementToPayload(
  draft: TieredModelEnforcementDraft,
): ApiKeyEnforcedModelTiers | null {
  const miniModel = draft.miniModel.trim();
  const standardModel = draft.standardModel.trim();
  const mini =
    miniModel || draft.miniReasoning !== "none"
      ? {
          model: miniModel || null,
          reasoningEffort: draft.miniReasoning === "none" ? null : draft.miniReasoning,
        }
      : null;
  const standard =
    standardModel || draft.standardReasoning !== "none"
      ? {
          model: standardModel || null,
          reasoningEffort: draft.standardReasoning === "none" ? null : draft.standardReasoning,
        }
      : null;
  return mini || standard ? { mini, standard } : null;
}
