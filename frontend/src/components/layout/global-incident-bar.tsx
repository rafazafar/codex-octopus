import { AlertTriangle, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { useSystemHealth } from "@/features/system-health/hooks/use-system-health";
import { cn } from "@/lib/utils";

const severityStyles = {
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-800 dark:text-amber-300",
  critical: "border-destructive/20 bg-destructive/10 text-destructive",
} as const;

export function GlobalIncidentBar() {
  const systemHealthQuery = useSystemHealth();
  const alert = systemHealthQuery.data?.alert;

  if (systemHealthQuery.isLoading || systemHealthQuery.isError || !alert) {
    return null;
  }

  return (
    <div className="sticky top-[53px] z-10 border-b bg-background/90 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/70 sm:px-6">
      <div
        className={cn(
          "mx-auto flex w-full max-w-[1500px] items-center justify-between gap-3 py-2 text-sm",
          severityStyles[alert.severity],
        )}
      >
        <div className="flex min-w-0 items-start gap-2.5">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div className="min-w-0">
            <p className="font-medium">{alert.title}</p>
            <p className="truncate text-xs opacity-90 sm:text-sm">{alert.message}</p>
          </div>
        </div>
        <Link
          to={alert.href}
          className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium hover:bg-black/5 dark:hover:bg-white/10"
        >
          View
          <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}
