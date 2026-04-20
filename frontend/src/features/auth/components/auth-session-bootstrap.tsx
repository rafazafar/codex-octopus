import { useEffect, type PropsWithChildren } from "react";

import { useAuthStore } from "@/features/auth/hooks/use-auth";

export function AuthSessionBootstrap({ children }: PropsWithChildren) {
  const refreshSessionStable = useAuthStore((state) => state.refreshSession);

  useEffect(() => {
    void refreshSessionStable();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <>{children}</>;
}
