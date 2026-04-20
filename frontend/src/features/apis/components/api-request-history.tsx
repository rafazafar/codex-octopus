import { useMemo } from "react";

import { AlertMessage } from "@/components/alert-message";
import { useAccounts } from "@/features/accounts/hooks/use-accounts";
import { RequestFilters } from "@/features/dashboard/components/filters/request-filters";
import { RecentRequestsTable } from "@/features/dashboard/components/recent-requests-table";
import { useRequestLogsWithOptions } from "@/features/dashboard/hooks/use-request-logs";
import { REQUEST_STATUS_LABELS } from "@/utils/constants";
import { formatModelLabel, formatSlug } from "@/utils/formatters";

type ApiRequestHistoryProps = {
  apiKeyId: string;
  apiKeyName: string;
};

const MODEL_OPTION_DELIMITER = ":::";

export function ApiRequestHistory({
  apiKeyId,
  apiKeyName: _apiKeyName,
}: ApiRequestHistoryProps) {
  const { accountsQuery } = useAccounts();
  const { filters, logsQuery, optionsQuery, updateFilters } =
    useRequestLogsWithOptions({
      apiKeyId,
      includeAccountFilters: false,
    });

  const modelOptions = useMemo(
    () =>
      (optionsQuery.data?.modelOptions ?? []).map((option) => ({
        value: `${option.model}${MODEL_OPTION_DELIMITER}${option.reasoningEffort ?? ""}`,
        label: formatModelLabel(option.model, option.reasoningEffort),
      })),
    [optionsQuery.data?.modelOptions],
  );

  const statusOptions = useMemo(
    () =>
      (optionsQuery.data?.statuses ?? []).map((status) => ({
        value: status,
        label: REQUEST_STATUS_LABELS[status] ?? formatSlug(status),
      })),
    [optionsQuery.data?.statuses],
  );

  const errorMessage =
    (logsQuery.error instanceof Error && logsQuery.error.message) ||
    (optionsQuery.error instanceof Error && optionsQuery.error.message) ||
    null;

  if (logsQuery.isPending && !logsQuery.data) {
    return (
      <div className="rounded-lg border bg-muted/20 p-6 text-sm text-muted-foreground">
        Loading request history...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {errorMessage ? (
        <AlertMessage variant="error">{errorMessage}</AlertMessage>
      ) : null}

      <RequestFilters
        filters={filters}
        modelOptions={modelOptions}
        statusOptions={statusOptions}
        showAccountFilter={false}
        searchPlaceholder="Search request id, model, error..."
        onSearchChange={(search) => updateFilters({ search, offset: 0 })}
        onTimeframeChange={(timeframe) => updateFilters({ timeframe, offset: 0 })}
        onAccountChange={() => undefined}
        onModelChange={(modelOptionsSelected) =>
          updateFilters({ modelOptions: modelOptionsSelected, offset: 0 })
        }
        onStatusChange={(statuses) => updateFilters({ statuses, offset: 0 })}
        onReset={() =>
          updateFilters({
            search: "",
            timeframe: "all",
            accountIds: [],
            modelOptions: [],
            statuses: [],
            offset: 0,
          })
        }
      />

      <RecentRequestsTable
        requests={logsQuery.data?.requests ?? []}
        accounts={accountsQuery.data ?? []}
        total={logsQuery.data?.total ?? 0}
        limit={filters.limit}
        offset={filters.offset}
        hasMore={logsQuery.data?.hasMore ?? false}
        emptyTitle="No request history"
        emptyDescription="No requests for this API key match the current filters."
        onLimitChange={(limit) => updateFilters({ limit, offset: 0 })}
        onOffsetChange={(offset) => updateFilters({ offset })}
      />
    </div>
  );
}
