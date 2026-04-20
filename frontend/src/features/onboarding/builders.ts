import { resolveRuntimeConnectAddress } from "@/lib/runtime-connect-address";
import type {
  OnboardingClient,
  OnboardingDeployment,
  PublicOnboardingBootstrap,
} from "@/features/onboarding/schemas";

export type OnboardingBuildInput = {
  client: OnboardingClient;
  deployment: OnboardingDeployment;
  bootstrap: PublicOnboardingBootstrap;
  browserOrigin: string;
  browserHostname: string;
  runtimeConnectAddress: string | null;
  hostOverride: string;
};

export type OnboardingConfigArtifact = {
  title: string;
  summary: string;
  endpointLabel: string;
  endpointValue: string;
  fileLabel: string;
  snippetLanguage: string;
  snippet: string;
  envVars: Array<{ key: string; value: string; description: string }>;
  notes: string[];
};

function buildApiKeyEnvVars(
  bootstrap: PublicOnboardingBootstrap,
): OnboardingConfigArtifact["envVars"] {
  if (!bootstrap.apiKeyAuthEnabled) {
    return [];
  }

  return [
    {
      key: "CODEX_LB_API_KEY",
      value: "sk-clb-...",
      description: "API key created from the codex-lb APIs page.",
    },
  ];
}

function buildBaseOrigin(input: OnboardingBuildInput): string {
  const url = new URL(input.browserOrigin);
  const resolvedRemoteHost = resolveRuntimeConnectAddress(
    input.browserHostname,
    input.runtimeConnectAddress,
  );
  const host = input.deployment === "local"
    ? url.hostname
    : input.hostOverride.trim() || resolvedRemoteHost;
  const portSuffix = url.port ? `:${url.port}` : "";
  return `${url.protocol}//${host}${portSuffix}`;
}

function buildCommonNotes(
  input: OnboardingBuildInput,
  endpointPath: string,
): string[] {
  const notes: string[] = [];
  if (input.bootstrap.apiKeyAuthEnabled) {
    notes.push("This server currently requires a dashboard-generated API key for client traffic.");
  } else {
    notes.push("API-key auth is currently disabled, so client traffic can connect without an Authorization header.");
  }

  if (input.deployment === "reverse_proxy") {
    notes.push(`Expose ${endpointPath} through the reverse proxy without rewriting the upstream path.`);
  }

  return notes;
}

export function buildOnboardingArtifact(
  input: OnboardingBuildInput,
): OnboardingConfigArtifact {
  const baseOrigin = buildBaseOrigin(input);

  if (input.client === "codex_cli") {
    const endpointValue = `${baseOrigin}/backend-api/codex`;
    const envVars = buildApiKeyEnvVars(input.bootstrap);
    const snippetLines = [
      'model = "gpt-5.4"',
      'model_reasoning_effort = "high"',
      'model_provider = "codex-lb"',
      "",
      "[model_providers.codex-lb]",
      'name = "OpenAI"',
      `base_url = "${endpointValue}"`,
      'wire_api = "responses"',
      "supports_websockets = true",
      "requires_openai_auth = true",
      ...(input.bootstrap.apiKeyAuthEnabled
        ? ['env_key = "CODEX_LB_API_KEY"']
        : []),
    ];

    return {
      title: "Codex CLI",
      summary: "Use the Responses wire API against the codex-lb backend Codex endpoint.",
      endpointLabel: "Base URL",
      endpointValue,
      fileLabel: "~/.codex/config.toml",
      snippetLanguage: "toml",
      snippet: snippetLines.join("\n"),
      envVars,
      notes: [
        ...buildCommonNotes(input, "/backend-api/codex"),
        "If Codex streaming is unreliable behind a reverse proxy, verify websocket upgrade forwarding for /backend-api/codex/responses.",
      ],
    };
  }

  if (input.client === "opencode") {
    const endpointValue = `${baseOrigin}/v1`;
    const config = {
      $schema: "https://opencode.ai/config.json",
      provider: {
        openai: {
          options: {
            baseURL: endpointValue,
            ...(input.bootstrap.apiKeyAuthEnabled
              ? { apiKey: "{env:CODEX_LB_API_KEY}" }
              : {}),
          },
        },
      },
    };

    return {
      title: "OpenCode",
      summary: "Use the built-in openai provider with a baseURL override to the codex-lb v1 endpoint.",
      endpointLabel: "Base URL",
      endpointValue,
      fileLabel: "~/.config/opencode/opencode.json",
      snippetLanguage: "json",
      snippet: JSON.stringify(config, null, 2),
      envVars: buildApiKeyEnvVars(input.bootstrap),
      notes: buildCommonNotes(input, "/v1"),
    };
  }

  const endpointValue = `${baseOrigin}/v1`;
  const curlLines = [
    "curl \\",
    `  ${input.bootstrap.apiKeyAuthEnabled ? '-H "Authorization: Bearer $CODEX_LB_API_KEY" \\' : ""}`,
    `  "${endpointValue}/models"`,
  ].filter(Boolean);

  return {
    title: "OpenAI-compatible client",
    summary: "Point any OpenAI-compatible SDK or curl workflow at the codex-lb v1 endpoint.",
    endpointLabel: "Base URL",
    endpointValue,
    fileLabel: "Example request",
    snippetLanguage: "bash",
    snippet: curlLines.join("\n"),
    envVars: buildApiKeyEnvVars(input.bootstrap),
    notes: buildCommonNotes(input, "/v1"),
  };
}
