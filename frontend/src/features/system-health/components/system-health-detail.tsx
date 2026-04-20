import { AlertTriangle } from "lucide-react";

import type { SystemHealthAlert } from "@/features/system-health/schemas";
import { cn } from "@/lib/utils";
import { formatDateTimeInline, formatPercent, formatRate } from "@/utils/formatters";

const severityStyles = {
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-800 dark:text-amber-300",
  critical: "border-destructive/20 bg-destructive/10 text-destructive",
} as const;

function buildReasonLines(alert: SystemHealthAlert): string[] {
  const metrics = alert.metrics;
  if (!metrics) {
    return [];
  }

  switch (alert.code) {
    case "no_active_accounts":
    case "account_pool_collapse":
    case "account_pool_degraded":
      return [
        `Active accounts: ${metrics.activeAccounts ?? "--"} / ${metrics.totalAccounts ?? "--"}`,
        `Unavailable accounts: ${metrics.unavailableAccounts ?? "--"} (${formatPercent(metrics.unavailableRatio ? metrics.unavailableRatio * 100 : null)})`,
      ];
    case "capacity_exhaustion_risk":
    case "capacity_risk":
      return [
        `Risk level: ${metrics.riskLevel ?? "--"}`,
        `Projected exhaustion: ${formatDateTimeInline(metrics.projectedExhaustionAt)}`,
      ];
    case "rate_limit_wave":
      return [
        `Recent request volume: ${metrics.requestCount ?? "--"}`,
        `Rate-limited share: ${formatRate(metrics.rateLimitRatio)}`,
      ];
    default:
      return [];
  }
}

export function SystemHealthDetail({ alert }: { alert: SystemHealthAlert }) {
  const reasonLines = buildReasonLines(alert);

  return (
    <div className={cn("rounded-lg border px-4 py-3", severityStyles[alert.severity])}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <div className="min-w-0 space-y-1">
          <p className="font-medium">{alert.title}</p>
          <p className="text-sm opacity-90">{alert.message}</p>
          {reasonLines.length > 0 ? (
            <ul className="space-y-1 pt-1 text-xs opacity-90 sm:text-sm">
              {reasonLines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </div>
  );
}
