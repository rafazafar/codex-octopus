import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { GlobalIncidentBar } from "@/components/layout/global-incident-bar";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

describe("GlobalIncidentBar", () => {
  it("renders nothing when the system is healthy", async () => {
    const { queryByText } = renderWithProviders(<GlobalIncidentBar />);
    expect(queryByText("View")).toBeNull();
  });

  it("renders the alert title, message, and link when a warning is active", async () => {
    server.use(
      http.get("/api/system-health", () =>
        HttpResponse.json({
          status: "warning",
          updatedAt: "2026-01-01T00:00:00Z",
          alert: {
            code: "rate_limit_wave",
            severity: "warning",
            title: "Rate limit wave detected",
            message: "Rate limiting is affecting a large share of recent traffic.",
            href: "/dashboard",
            metrics: {
              requestCount: 60,
              rateLimitRatio: 0.4,
            },
          },
        }),
      ),
    );

    const { findByText } = renderWithProviders(<GlobalIncidentBar />);

    expect(await findByText("Rate limit wave detected")).toBeInTheDocument();
    expect(await findByText("Rate limiting is affecting a large share of recent traffic.")).toBeInTheDocument();
    expect(await findByText("View")).toHaveAttribute("href", "/dashboard");
  });
});
