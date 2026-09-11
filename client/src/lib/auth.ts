import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { getToken } from "@/lib/api/http";

export function isAuthenticated(): boolean {
  return !!getToken();
}

/** Redirects to /login when there is no stored token. Call at the top of any protected route component. */
export function useAuthGuard() {
  const navigate = useNavigate();
  useEffect(() => {
    if (!isAuthenticated()) navigate({ to: "/login" });
  }, [navigate]);
}
