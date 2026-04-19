import { del, download, get, post } from "@/lib/api-client";

import {
  AccountActionResponseSchema,
  AccountImportResponseSchema,
  AccountsResponseSchema,
  AccountTrendsResponseSchema,
  ManualOauthCallbackRequestSchema,
  ManualOauthCallbackResponseSchema,
  OauthCompleteRequestSchema,
  OauthCompleteResponseSchema,
  OauthStartRequestSchema,
  OauthStartResponseSchema,
  OauthStatusResponseSchema,
  RuntimeConnectAddressResponseSchema,
} from "@/features/accounts/schemas";

const ACCOUNTS_BASE_PATH = "/api/accounts";
const OAUTH_BASE_PATH = "/api/oauth";

export function listAccounts() {
  return get(ACCOUNTS_BASE_PATH, AccountsResponseSchema);
}

export function importAccount(file: File) {
  const formData = new FormData();
  formData.append("auth_json", file);
  return post(`${ACCOUNTS_BASE_PATH}/import`, AccountImportResponseSchema, {
    body: formData,
  });
}

export async function exportAccounts() {
  const { blob, filename } = await download(`${ACCOUNTS_BASE_PATH}/export`);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename ?? "codex_accounts.json";
  anchor.rel = "noopener";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export function pauseAccount(accountId: string) {
  return post(
    `${ACCOUNTS_BASE_PATH}/${encodeURIComponent(accountId)}/pause`,
    AccountActionResponseSchema,
  );
}

export function reactivateAccount(accountId: string) {
  return post(
    `${ACCOUNTS_BASE_PATH}/${encodeURIComponent(accountId)}/reactivate`,
    AccountActionResponseSchema,
  );
}

export function getAccountTrends(accountId: string) {
  return get(
    `${ACCOUNTS_BASE_PATH}/${encodeURIComponent(accountId)}/trends`,
    AccountTrendsResponseSchema,
  );
}

export function deleteAccount(accountId: string) {
  return del(
    `${ACCOUNTS_BASE_PATH}/${encodeURIComponent(accountId)}`,
    AccountActionResponseSchema,
  );
}

export function startOauth(payload: unknown) {
  const validated = OauthStartRequestSchema.parse(payload);
  return post(`${OAUTH_BASE_PATH}/start`, OauthStartResponseSchema, {
    body: validated,
  });
}

export function getOauthStatus() {
  return get(`${OAUTH_BASE_PATH}/status`, OauthStatusResponseSchema);
}

export function completeOauth(payload?: unknown) {
  const validated = OauthCompleteRequestSchema.parse(payload ?? {});
  return post(`${OAUTH_BASE_PATH}/complete`, OauthCompleteResponseSchema, {
    body: validated,
  });
}
export function submitManualOauthCallback(payload: unknown) {
  const validated = ManualOauthCallbackRequestSchema.parse(payload);
  return post(`${OAUTH_BASE_PATH}/manual-callback`, ManualOauthCallbackResponseSchema, {
    body: validated,
  });
}

export function getRuntimeConnectAddress() {
  return get("/api/settings/runtime/connect-address", RuntimeConnectAddressResponseSchema);
}
