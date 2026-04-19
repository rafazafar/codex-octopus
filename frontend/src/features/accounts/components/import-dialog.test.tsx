import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImportDialog } from "@/features/accounts/components/import-dialog";

describe("ImportDialog", () => {
  it("describes the multi-format all-or-nothing import flow", () => {
    render(
      <ImportDialog
        open
        busy={false}
        error={null}
        onOpenChange={vi.fn()}
        onImport={vi.fn(async () => {})}
      />,
    );

    expect(screen.getByText("Import accounts JSON")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Accepts auth.json and compatible portable account exports. If any record is invalid, nothing will be imported.",
      ),
    ).toBeInTheDocument();
  });
});
