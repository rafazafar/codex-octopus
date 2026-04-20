import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, Cable, Server } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { CopyButton } from "@/components/copy-button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import {
  getOnboardingBootstrap,
  getOnboardingValidationSettings,
  runOnboardingChecks,
} from "@/features/onboarding/api";
import { buildOnboardingArtifact } from "@/features/onboarding/builders";
import type {
  OnboardingCheck,
  OnboardingClient,
  OnboardingDeployment,
} from "@/features/onboarding/schemas";

const CLIENT_LABELS: Record<OnboardingClient, string> = {
  codex_cli: "Codex CLI",
  opencode: "OpenCode",
  openai_compatible: "OpenAI-compatible",
};

const DEPLOYMENT_LABELS: Record<OnboardingDeployment, string> = {
  local: "Local machine",
  remote: "Remote server",
  reverse_proxy: "Behind reverse proxy",
};

const CHECK_STYLES: Record<OnboardingCheck["status"], string> = {
  success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  error: "border-destructive/20 bg-destructive/10 text-destructive",
  info: "border-primary/20 bg-primary/10 text-foreground",
};

export function OnboardingPage() {
  const [client, setClient] = useState<OnboardingClient>("codex_cli");
  const [deployment, setDeployment] = useState<OnboardingDeployment>("local");
  const [hostOverride, setHostOverride] = useState("");
  const [lastValidatedKey, setLastValidatedKey] = useState<string | null>(null);
  const authenticated = useAuthStore((state) => state.authenticated);
  const authInitialized = useAuthStore((state) => state.initialized);

  const bootstrapQuery = useQuery({
    queryKey: ["onboarding", "bootstrap"],
    queryFn: getOnboardingBootstrap,
  });
  const validationSettingsQuery = useQuery({
    queryKey: ["onboarding", "validation-settings"],
    queryFn: getOnboardingValidationSettings,
    enabled: authenticated,
  });

  const validationMutation = useMutation({
    mutationFn: async () => {
      if (!validationSettingsQuery.data) {
        return [];
      }
      return runOnboardingChecks(client, validationSettingsQuery.data);
    },
  });

  const artifact = useMemo(() => {
    if (!bootstrapQuery.data || typeof window === "undefined") {
      return null;
    }

    return buildOnboardingArtifact({
      client,
      deployment,
      bootstrap: bootstrapQuery.data,
      browserOrigin: window.location.origin,
      browserHostname: window.location.hostname,
      runtimeConnectAddress: bootstrapQuery.data.connectAddress,
      hostOverride,
    });
  }, [bootstrapQuery.data, client, deployment, hostOverride]);

  const selectionKey = useMemo(
    () => [client, deployment, hostOverride.trim()].join("::"),
    [client, deployment, hostOverride],
  );

  const validationChecks =
    lastValidatedKey === selectionKey ? validationMutation.data ?? [] : [];
  const validationError =
    lastValidatedKey === selectionKey &&
    validationMutation.error instanceof Error
      ? validationMutation.error.message
      : null;

  const handleRunChecks = async () => {
    await validationMutation.mutateAsync();
    setLastValidatedKey(selectionKey);
  };

  return (
    <div className="animate-fade-in-up space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Onboarding</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Generate client config, confirm runtime assumptions, and catch setup mistakes before the first request.
        </p>
      </div>

      {bootstrapQuery.error instanceof Error ? (
        <AlertMessage variant="error">{bootstrapQuery.error.message}</AlertMessage>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <Card className="gap-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Cable className="h-4 w-4 text-primary" />
              Setup choices
            </CardTitle>
            <CardDescription>
              Pick the client and deployment shape you want to configure.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>Client</Label>
              <Tabs value={client} onValueChange={(value) => setClient(value as OnboardingClient)}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="codex_cli">Codex CLI</TabsTrigger>
                  <TabsTrigger value="opencode">OpenCode</TabsTrigger>
                  <TabsTrigger value="openai_compatible">OpenAI-compatible</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            <div className="space-y-2">
              <Label htmlFor="deployment-shape">Deployment</Label>
              <Select
                value={deployment}
                onValueChange={(value) => setDeployment(value as OnboardingDeployment)}
              >
                <SelectTrigger id="deployment-shape">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="local">{DEPLOYMENT_LABELS.local}</SelectItem>
                  <SelectItem value="remote">{DEPLOYMENT_LABELS.remote}</SelectItem>
                  <SelectItem value="reverse_proxy">{DEPLOYMENT_LABELS.reverse_proxy}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {deployment !== "local" ? (
              <div className="space-y-2">
                <Label htmlFor="host-override">Public host override</Label>
                <Input
                  id="host-override"
                  placeholder="Optional host or DNS name"
                  value={hostOverride}
                  onChange={(event) => setHostOverride(event.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty to use the runtime-detected connect address.
                </p>
              </div>
            ) : null}

            {bootstrapQuery.data ? (
              <div className="rounded-lg border bg-muted/20 p-3 text-xs text-muted-foreground">
                <p>
                  <span className="font-medium text-foreground">API key auth:</span>{" "}
                  {bootstrapQuery.data.apiKeyAuthEnabled ? "Enabled" : "Disabled"}
                </p>
                <p className="mt-1">
                  <span className="font-medium text-foreground">Runtime connect address:</span>{" "}
                  {bootstrapQuery.data.connectAddress || "<unavailable>"}
                </p>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="gap-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BookOpen className="h-4 w-4 text-primary" />
                Generated config
              </CardTitle>
              <CardDescription>
                Use this output as the starting point for {CLIENT_LABELS[client]}.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!artifact ? (
                <p className="text-sm text-muted-foreground">Loading onboarding data...</p>
              ) : (
                <>
                  <div className="rounded-lg border bg-muted/20 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {artifact.endpointLabel}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <code className="rounded bg-background px-2 py-1 text-sm">{artifact.endpointValue}</code>
                      <CopyButton value={artifact.endpointValue} label="Copy URL" />
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">{artifact.summary}</p>
                  </div>

                  {artifact.envVars.length > 0 ? (
                    <div className="space-y-2">
                      <h2 className="text-sm font-semibold">Env vars</h2>
                      {artifact.envVars.map((item) => (
                        <div key={item.key} className="rounded-lg border bg-muted/20 p-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <code className="rounded bg-background px-2 py-1 text-sm">{`${item.key}=${item.value}`}</code>
                            <CopyButton value={`${item.key}=${item.value}`} label={`Copy ${item.key}`} />
                          </div>
                          <p className="mt-2 text-xs text-muted-foreground">{item.description}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h2 className="text-sm font-semibold">{artifact.fileLabel}</h2>
                        <p className="text-xs text-muted-foreground">
                          Generated for {CLIENT_LABELS[client]} on {DEPLOYMENT_LABELS[deployment].toLowerCase()}.
                        </p>
                      </div>
                      <CopyButton value={artifact.snippet} label="Copy snippet" />
                    </div>
                    <pre className="overflow-x-auto rounded-lg border bg-muted/20 p-3 text-xs">
                      <code>{artifact.snippet}</code>
                    </pre>
                  </div>

                  <div className="space-y-2">
                    <h2 className="text-sm font-semibold">Notes</h2>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {artifact.notes.map((note) => (
                        <li key={note} className="rounded-lg border bg-muted/20 px-3 py-2">
                          {note}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card className="gap-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Server className="h-4 w-4 text-primary" />
                Validation
              </CardTitle>
              <CardDescription>
                {authenticated
                  ? "Run quick checks against the selected client endpoint before leaving the dashboard."
                  : "Live checks are available after dashboard sign-in. Public onboarding remains view-only."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {authenticated ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    onClick={() => void handleRunChecks()}
                    disabled={
                      !bootstrapQuery.data ||
                      !validationSettingsQuery.data ||
                      validationMutation.isPending
                    }
                  >
                    {validationMutation.isPending ? "Running checks..." : "Run checks"}
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    Uses `/health/ready` and the client-specific model list endpoint.
                  </span>
                </div>
              ) : (
                <div className="rounded-lg border bg-muted/20 px-3 py-2 text-xs font-medium text-muted-foreground">
                  {authInitialized
                    ? "Sign in to the dashboard to run readiness and endpoint checks."
                    : "Checking dashboard session status..."}
                </div>
              )}

              {validationError ? (
                <AlertMessage variant="error">{validationError}</AlertMessage>
              ) : null}

              <div className="space-y-2">
                {validationChecks.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {!authenticated
                      ? "Public onboarding can generate configuration, but validation stays disabled until a dashboard session is active."
                      : lastValidatedKey && lastValidatedKey !== selectionKey
                      ? "Selection changed. Run checks again to validate the current client and deployment shape."
                      : "No checks run yet. Start with readiness, model-list reachability, and auth guidance."}
                  </p>
                ) : (
                  validationChecks.map((check) => (
                    <div key={check.id} className={`rounded-lg border px-3 py-3 text-sm ${CHECK_STYLES[check.status]}`}>
                      <p className="font-medium">{check.label}</p>
                      <p className="mt-1">{check.detail}</p>
                      {check.remediation ? (
                        <p className="mt-2 text-xs opacity-90">{check.remediation}</p>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
