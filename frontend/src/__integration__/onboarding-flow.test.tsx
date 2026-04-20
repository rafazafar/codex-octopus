import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/utils";

describe("onboarding flow integration", () => {
  it("renders onboarding and updates generated config when the client changes", async () => {
    const user = userEvent.setup({ delay: null });

    window.history.pushState({}, "", "/onboarding");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Onboarding" })).toBeInTheDocument();
    expect(screen.getByText("~/.codex/config.toml")).toBeInTheDocument();
    expect(screen.getByText(/env_key = "CODEX_LB_API_KEY"/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Run checks" }));
    expect(await screen.findByText("Server readiness")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "OpenCode" }));

    expect(await screen.findByText("~/.config/opencode/opencode.json")).toBeInTheDocument();
    expect(screen.getByText(/"baseURL": "http:\/\/localhost:3000\/v1"/)).toBeInTheDocument();
    expect(
      screen.getByText(/Selection changed. Run checks again to validate the current client/i),
    ).toBeInTheDocument();
  });

  it("surfaces targeted auth guidance during validation", async () => {
    const user = userEvent.setup({ delay: null });

    window.history.pushState({}, "", "/onboarding");
    renderWithProviders(<App />);

    expect(await screen.findByRole("heading", { name: "Onboarding" })).toBeInTheDocument();
    expect(await screen.findByText(/Runtime connect address:/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Run checks" }));

    expect(await screen.findByText("Server readiness")).toBeInTheDocument();
    expect(
      await screen.findByText("Model endpoint auth"),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Onboarding" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });
});
