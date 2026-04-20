import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { createElement, type PropsWithChildren } from "react";
import { describe, expect, it } from "vitest";

import { useSystemHealth } from "@/features/system-health/hooks/use-system-health";
import { server } from "@/test/mocks/server";

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe("useSystemHealth", () => {
  it("loads the system health payload and configures 30s refetch", async () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useSystemHealth(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("healthy");

    const query = queryClient.getQueryCache().find({ queryKey: ["system-health"] });
    const refetchInterval = (query?.options as { refetchInterval?: unknown } | undefined)?.refetchInterval;
    expect(refetchInterval).toBe(30_000);
  });

  it("exposes critical alerts from the endpoint", async () => {
    server.use(
      http.get("/api/system-health", () =>
        HttpResponse.json({
          status: "critical",
          updatedAt: "2026-01-01T00:00:00Z",
          alert: {
            code: "capacity_exhaustion_risk",
            severity: "critical",
            title: "Capacity exhaustion is imminent",
            message: "Remaining system capacity is projected to exhaust soon.",
            href: "/dashboard",
            metrics: {
              riskLevel: "critical",
            },
          },
        }),
      ),
    );

    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useSystemHealth(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.alert?.code).toBe("capacity_exhaustion_risk");
  });
});
