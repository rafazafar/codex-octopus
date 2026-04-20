import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import { exportAccounts } from "@/features/accounts/api";

describe("exportAccounts", () => {
  const originalCreateObjectUrl = URL.createObjectURL;
  const originalRevokeObjectUrl = URL.revokeObjectURL;

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => "blob:portable-export");
    URL.revokeObjectURL = vi.fn();
  });

  it("downloads the exported portable JSON file", async () => {
    const click = vi.fn();
    const appendSpy = vi.spyOn(document.body, "append");
    const removeSpy = vi.spyOn(HTMLAnchorElement.prototype, "remove").mockImplementation(() => {});
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const element = document.createElementNS("http://www.w3.org/1999/xhtml", tagName) as HTMLElement;
      if (tagName === "a") {
        Object.defineProperty(element, "click", {
          value: click,
        });
      }
      return element;
    });

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("[]", {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="codex_accounts_2026-04-20.json"',
          "Content-Type": "application/json",
        },
      }),
    );

    await exportAccounts();

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/accounts/export",
      expect.objectContaining({ method: "GET", credentials: "same-origin" }),
    );
    expect(appendSpy).toHaveBeenCalledTimes(1);
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalledTimes(1);
    expect(removeSpy).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:portable-export");

    createElementSpy.mockRestore();
    appendSpy.mockRestore();
    removeSpy.mockRestore();
    fetchSpy.mockRestore();
  });

  it("surfaces API errors for failed exports", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "export_failed", message: "Export failed" } }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(exportAccounts()).rejects.toBeInstanceOf(ApiError);

    fetchSpy.mockRestore();
  });

  afterAll(() => {
    URL.createObjectURL = originalCreateObjectUrl;
    URL.revokeObjectURL = originalRevokeObjectUrl;
  });
});
