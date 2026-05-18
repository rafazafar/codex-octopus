import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ImportDialog } from "@/features/accounts/components/import-dialog";

describe("ImportDialog", () => {
  it("describes the add account options", () => {
    render(
      <ImportDialog
        open
        busy={false}
        error={null}
        onOpenChange={vi.fn()}
        onImport={vi.fn(async () => {})}
        onOpenOauth={vi.fn()}
      />,
    );

    expect(screen.getByText("Add account")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sign in with OAuth or import JSON. If any JSON record is invalid, nothing will be imported.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "OAuth" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Paste JSON" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Upload JSON" })).toBeInTheDocument();
  });

  it("imports pasted JSON as a file", async () => {
    const user = userEvent.setup();
    const importedFiles: File[] = [];
    const onImport = vi.fn(async (file: File) => {
      importedFiles.push(file);
    });
    const onOpenChange = vi.fn();
    const json = '{"access_token":"access","id_token":"id","refresh_token":"","account_id":"acc"}';

    render(
      <ImportDialog
        open
        busy={false}
        error={null}
        initialMode="paste"
        onOpenChange={onOpenChange}
        onImport={onImport}
        onOpenOauth={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("JSON"), { target: { value: json } });
    await user.click(screen.getByRole("button", { name: "Import" }));

    expect(onImport).toHaveBeenCalledTimes(1);
    const file = importedFiles[0];
    expect(file.name).toBe("pasted-account.json");
    await expect(file.text()).resolves.toBe(json);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("opens OAuth flow from the OAuth option", async () => {
    const user = userEvent.setup();
    const onOpenOauth = vi.fn();
    const onOpenChange = vi.fn();

    render(
      <ImportDialog
        open
        busy={false}
        error={null}
        initialMode="oauth"
        onOpenChange={onOpenChange}
        onImport={vi.fn(async () => {})}
        onOpenOauth={onOpenOauth}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Continue with OAuth" }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onOpenOauth).toHaveBeenCalledTimes(1);
  });

  it("submits kiro provider import payload as a JSON file", async () => {
    const user = userEvent.setup();
    const importedFiles: File[] = [];
    const onImport = vi.fn(async (file: File) => {
      importedFiles.push(file);
    });
    const onOpenChange = vi.fn();

    render(
      <ImportDialog
        open
        busy={false}
        error={null}
        onOpenChange={onOpenChange}
        onImport={onImport}
      />,
    );

    await user.click(screen.getByRole("tab", { name: "Kiro" }));
    await user.type(screen.getByLabelText("Access Token"), "kiro-access");
    await user.type(screen.getByLabelText("Refresh Token"), "kiro-refresh");
    await user.click(screen.getByRole("button", { name: "Import" }));

    expect(onImport).toHaveBeenCalledTimes(1);
    const file = importedFiles[0];
    expect(file.name).toBe("kiro-account.json");
    const parsed = JSON.parse(await file.text());
    expect(parsed.provider).toBe("kiro");
    expect(parsed.accessToken).toBe("kiro-access");
    expect(parsed.refreshToken).toBe("kiro-refresh");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

});
