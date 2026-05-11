import { useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type ImportDialogProps = {
  open: boolean;
  busy: boolean;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onImport: (file: File) => Promise<void>;
  onOpenOauth?: () => void;
  initialMode?: "oauth" | "paste" | "file";
};

export function ImportDialog({
  open,
  busy,
  error,
  onOpenChange,
  onImport,
  onOpenOauth,
  initialMode,
}: ImportDialogProps) {
  const resolvedInitialMode = initialMode ?? (onOpenOauth ? "oauth" : "file");
  const [file, setFile] = useState<File | null>(null);
  const [jsonText, setJsonText] = useState("");
  const [mode, setMode] = useState<"oauth" | "paste" | "file">(resolvedInitialMode);
  const [pasteError, setPasteError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (mode === "paste") {
      const trimmed = jsonText.trim();
      if (!trimmed) {
        setPasteError("Paste account JSON before importing.");
        return;
      }
      try {
        JSON.parse(trimmed);
      } catch {
        setPasteError("Paste valid JSON before importing.");
        return;
      }
      await onImport(new File([trimmed], "pasted-account.json", { type: "application/json" }));
      onOpenChange(false);
      setJsonText("");
      setPasteError(null);
      return;
    }

    if (mode !== "file" || !file) {
      return;
    }
    await onImport(file);
    onOpenChange(false);
    setFile(null);
  };

  const openOauth = () => {
    if (!onOpenOauth) {
      return;
    }
    onOpenChange(false);
    onOpenOauth();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add account</DialogTitle>
          <DialogDescription>
            Sign in with OAuth or import JSON. If any JSON record is invalid, nothing will be imported.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <Tabs value={mode} onValueChange={(value) => setMode(value as "oauth" | "paste" | "file")}>
            <TabsList className={onOpenOauth ? "grid w-full grid-cols-3" : "grid w-full grid-cols-2"}>
              {onOpenOauth ? <TabsTrigger value="oauth">OAuth</TabsTrigger> : null}
              <TabsTrigger value="paste">Paste JSON</TabsTrigger>
              <TabsTrigger value="file">Upload JSON</TabsTrigger>
            </TabsList>

            {onOpenOauth ? (
              <TabsContent value="oauth" className="space-y-3">
                <div className="rounded-lg border bg-muted/20 p-3">
                  <p className="text-sm font-medium">Use browser or device authorization.</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Best when adding a fresh account from this dashboard.
                  </p>
                </div>
              </TabsContent>
            ) : null}

            <TabsContent value="paste" className="space-y-2">
              <Label htmlFor="account-json-text">JSON</Label>
              <textarea
                id="account-json-text"
                value={jsonText}
                onChange={(event) => {
                  setJsonText(event.target.value);
                  setPasteError(null);
                }}
                placeholder='{"access_token":"...","id_token":"...","refresh_token":"","account_id":"..."}'
                className="min-h-48 w-full resize-y rounded-md border bg-background px-3 py-2 font-mono text-xs shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                spellCheck={false}
              />
              {pasteError ? <p className="text-xs text-destructive">{pasteError}</p> : null}
            </TabsContent>

            <TabsContent value="file" className="space-y-2">
              <Label htmlFor="auth-json-file">File</Label>
              <Input
                id="auth-json-file"
                type="file"
                accept="application/json,.json"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </TabsContent>
          </Tabs>

          {error ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            {mode === "oauth" && onOpenOauth ? (
              <Button type="button" onClick={openOauth}>
                Continue with OAuth
              </Button>
            ) : (
              <Button type="submit" disabled={busy || (mode === "file" ? !file : !jsonText.trim())}>
                Import
              </Button>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
