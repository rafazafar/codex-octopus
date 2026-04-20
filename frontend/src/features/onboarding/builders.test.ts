import { describe, expect, it } from "vitest";

import { buildOnboardingArtifact } from "@/features/onboarding/builders";
import { createDashboardSettings } from "@/test/mocks/factories";

describe("buildOnboardingArtifact", () => {
  it("builds Codex CLI config with API-key env wiring", () => {
    const artifact = buildOnboardingArtifact({
      client: "codex_cli",
      deployment: "local",
      settings: createDashboardSettings({ apiKeyAuthEnabled: true }),
      browserOrigin: "http://127.0.0.1:2455",
      browserHostname: "127.0.0.1",
      runtimeConnectAddress: "10.0.0.8",
      hostOverride: "",
    });

    expect(artifact.endpointValue).toBe("http://127.0.0.1:2455/backend-api/codex");
    expect(artifact.snippet).toContain('env_key = "CODEX_LB_API_KEY"');
    expect(artifact.envVars).toHaveLength(1);
  });

  it("uses the resolved remote address for remote OpenCode setup", () => {
    const artifact = buildOnboardingArtifact({
      client: "opencode",
      deployment: "remote",
      settings: createDashboardSettings({ apiKeyAuthEnabled: false }),
      browserOrigin: "http://localhost:2455",
      browserHostname: "localhost",
      runtimeConnectAddress: "codex-lb.internal",
      hostOverride: "",
    });

    expect(artifact.endpointValue).toBe("http://codex-lb.internal:2455/v1");
    expect(artifact.snippet).toContain('"baseURL": "http://codex-lb.internal:2455/v1"');
    expect(artifact.envVars).toHaveLength(0);
  });
});
