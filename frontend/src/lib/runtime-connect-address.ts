const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

export function resolveRuntimeConnectAddress(
  hostname: string,
  runtimeAddress: string | null,
): string {
  const normalizedRuntimeAddress = runtimeAddress?.trim() ?? "";
  if (normalizedRuntimeAddress) {
    return normalizedRuntimeAddress;
  }

  const normalized = hostname.trim().toLowerCase();
  if (!normalized || LOOPBACK_HOSTS.has(normalized)) {
    return "<codex-lb-ip-or-dns>";
  }

  return hostname;
}
