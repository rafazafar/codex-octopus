import { get } from "@/lib/api-client";
import { SystemHealthResponseSchema } from "@/features/system-health/schemas";

const SYSTEM_HEALTH_PATH = "/api/system-health";

export function getSystemHealth() {
  return get(SYSTEM_HEALTH_PATH, SystemHealthResponseSchema);
}
