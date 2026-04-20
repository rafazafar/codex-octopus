import { get } from "@/lib/api-client";
import { getRuntimeConnectAddress } from "@/features/accounts/api";
import { getSettings } from "@/features/settings/api";
import {
  OnboardingHealthSchema,
  type OnboardingCheck,
  type OnboardingClient,
} from "@/features/onboarding/schemas";
import type { DashboardSettings } from "@/features/settings/schemas";

export async function getOnboardingBootstrap() {
  const [settings, runtime] = await Promise.all([
    getSettings(),
    getRuntimeConnectAddress().catch(() => ({ connectAddress: "" })),
  ]);

  return {
    settings,
    runtimeConnectAddress: runtime.connectAddress || "",
  };
}

function getModelListPath(client: OnboardingClient): string {
  return client === "codex_cli" ? "/backend-api/codex/models" : "/v1/models";
}

function authMismatchCheck(
  path: string,
  settings: DashboardSettings,
): OnboardingCheck | null {
  if (!settings.apiKeyAuthEnabled) {
    return null;
  }

  return {
    id: "model-auth",
    label: "Model endpoint auth",
    status: "warning",
    detail: `${path} requires a dashboard-generated API key before the client can connect.`,
    remediation: "Create or select an API key in the APIs page, then populate the generated env var in the client config.",
  };
}

export async function runOnboardingChecks(
  client: OnboardingClient,
  settings: DashboardSettings,
): Promise<OnboardingCheck[]> {
  const checks: OnboardingCheck[] = [];

  try {
    await get("/health/ready", OnboardingHealthSchema);
    checks.push({
      id: "readiness",
      label: "Server readiness",
      status: "success",
      detail: "Server responded successfully to /health/ready.",
      remediation: null,
    });
  } catch (error) {
    checks.push({
      id: "readiness",
      label: "Server readiness",
      status: "error",
      detail:
        error instanceof Error ? error.message : "Failed to reach /health/ready.",
      remediation:
        "Confirm the dashboard origin is reachable and the codex-lb instance is healthy before testing client setup.",
    });
  }

  const modelPath = getModelListPath(client);
  try {
    const response = await fetch(modelPath, {
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });

    if (response.status === 401) {
      const mismatch = authMismatchCheck(modelPath, settings);
      if (mismatch) {
        checks.push(mismatch);
        return checks;
      }
    }

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as { models?: unknown[] };
    checks.push({
      id: "models",
      label: "Model list",
      status: "success",
      detail: `${modelPath} returned ${(payload.models ?? []).length} model entries.`,
      remediation: null,
    });
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.includes("401") &&
      !settings.apiKeyAuthEnabled
    ) {
      checks.push({
        id: "models",
        label: "Model list",
        status: "error",
        detail: `${modelPath} rejected the request with 401.`,
        remediation:
          "The selected client endpoint is returning unauthorized even though API-key auth is disabled. Re-check auth middleware and reverse proxy headers.",
      });
    } else {
      checks.push({
        id: "models",
        label: "Model list",
        status: "error",
        detail:
          error instanceof Error
            ? error.message
            : `Failed to query ${modelPath}.`,
        remediation:
          "Confirm the selected client endpoint is exposed on this deployment and that any reverse proxy forwards the request correctly.",
      });
    }
  }

  if (client === "codex_cli") {
    const needsWebsocketProxyNote =
      settings.upstreamStreamTransport === "auto" ||
      settings.upstreamStreamTransport === "websocket";
    checks.push({
      id: "websocket-guidance",
      label: "Codex websocket guidance",
      status: needsWebsocketProxyNote ? "info" : "success",
      detail: needsWebsocketProxyNote
        ? "Codex setups benefit from websocket upgrade support on the dashboard origin."
        : "Current transport settings do not require special websocket handling for V1 onboarding guidance.",
      remediation: needsWebsocketProxyNote
        ? "If codex-lb sits behind a reverse proxy, forward websocket upgrades for /backend-api/codex/responses."
        : null,
    });
  }

  return checks;
}
