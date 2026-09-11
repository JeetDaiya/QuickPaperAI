import { createFileRoute, Navigate } from "@tanstack/react-router";
import { isAuthenticated } from "@/lib/auth";

export const Route = createFileRoute("/")({
  component: () => <Navigate to={isAuthenticated() ? "/dashboard" : "/login"} />,
});
