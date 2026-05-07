import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ReasoningEffortType } from "@/features/api-keys/schemas";
import type { TieredModelEnforcementDraft } from "@/features/api-keys/components/tiered-model-enforcement-utils";

export function TieredModelEnforcementFields({
  value,
  onChange,
}: {
  value: TieredModelEnforcementDraft;
  onChange: (value: TieredModelEnforcementDraft) => void;
}) {
  const update = (patch: Partial<TieredModelEnforcementDraft>) => onChange({ ...value, ...patch });

  return (
    <div className="space-y-2 rounded-md border p-2">
      <div className="text-sm font-medium">Tiered enforcement</div>
      <TierFields
        label="Mini"
        model={value.miniModel}
        reasoning={value.miniReasoning}
        modelPlaceholder="e.g. gpt-5.4-mini"
        onModelChange={(miniModel) => update({ miniModel })}
        onReasoningChange={(miniReasoning) => update({ miniReasoning })}
      />
      <TierFields
        label="Standard"
        model={value.standardModel}
        reasoning={value.standardReasoning}
        modelPlaceholder="e.g. gpt-5.4"
        onModelChange={(standardModel) => update({ standardModel })}
        onReasoningChange={(standardReasoning) => update({ standardReasoning })}
      />
    </div>
  );
}

function TierFields({
  label,
  model,
  reasoning,
  modelPlaceholder,
  onModelChange,
  onReasoningChange,
}: {
  label: string;
  model: string;
  reasoning: ReasoningEffortType;
  modelPlaceholder: string;
  onModelChange: (value: string) => void;
  onReasoningChange: (value: ReasoningEffortType) => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[80px_1fr_120px] sm:items-center">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <Input
        value={model}
        onChange={(event) => onModelChange(event.target.value)}
        placeholder={modelPlaceholder}
        autoComplete="off"
      />
      <Select value={reasoning} onValueChange={(next) => onReasoningChange(next as ReasoningEffortType)}>
        <SelectTrigger>
          <SelectValue placeholder="None" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">None</SelectItem>
          <SelectItem value="minimal">Minimal</SelectItem>
          <SelectItem value="low">Low</SelectItem>
          <SelectItem value="medium">Medium</SelectItem>
          <SelectItem value="high">High</SelectItem>
          <SelectItem value="xhigh">XHigh</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
