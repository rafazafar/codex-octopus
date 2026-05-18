import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccountListItem } from "@/features/accounts/components/account-list-item";
import { createAccountSummary } from "@/test/mocks/factories";

describe("AccountListItem", () => {
  it("renders neutral quota track when secondary remaining percent is unknown", () => {
    const account = createAccountSummary({
      usage: {
        primaryRemainingPercent: 82,
        secondaryRemainingPercent: null,
      },
    });

    render(<AccountListItem account={account} selected={false} onSelect={vi.fn()} />);

    expect(screen.getByTestId("mini-quota-track")).toHaveClass("bg-muted");
    expect(screen.queryByTestId("mini-quota-fill")).not.toBeInTheDocument();
  });

  it("renders quota fill when secondary remaining percent is available", () => {
    const account = createAccountSummary({
      usage: {
        primaryRemainingPercent: 82,
        secondaryRemainingPercent: 73,
      },
    });

    render(<AccountListItem account={account} selected={false} onSelect={vi.fn()} />);

    expect(screen.getByTestId("mini-quota-fill")).toHaveStyle({ width: "73%" });
  });

  it("renders plan in the subtitle without routing tiers", () => {
    const account = createAccountSummary({ planType: "plus" });

    render(<AccountListItem account={account} selected={false} onSelect={vi.fn()} />);

    expect(screen.getByText(/Plus/)).toBeInTheDocument();
    expect(screen.queryByText(/Gold|Silver|Bronze|Default bronze/)).not.toBeInTheDocument();
  });

  it("shows kiro provider label for kiro accounts", () => {
    const account = createAccountSummary({ provider: "kiro", email: "kiro@example.com" });

    render(<AccountListItem account={account} selected={false} onSelect={vi.fn()} />);

    expect(screen.getByText("Kiro")).toBeInTheDocument();
  });

  it("does not show provider label for openai accounts", () => {
    const account = createAccountSummary({ provider: "openai", email: "openai@example.com" });

    render(<AccountListItem account={account} selected={false} onSelect={vi.fn()} />);

    expect(screen.queryByText("Kiro")).not.toBeInTheDocument();
    expect(screen.queryByText("OpenAI")).not.toBeInTheDocument();
  });
});
