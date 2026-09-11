import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { LoginPage } from "@/pages/LoginPage";
import { useLogin } from "@/hooks/useAuth";
import { setToken } from "@/lib/api/http";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export const Route = createFileRoute("/login")({
  component: LoginRoute,
});

function LoginRoute() {
  useDocumentTitle("Sign In");
  const navigate = useNavigate();
  const loginMutation = useLogin();

  function handleSubmit(email: string, password: string) {
    loginMutation.mutate(
      { email, password },
      {
        onSuccess: (data) => {
          setToken(data.access_token);
          navigate({ to: "/dashboard" });
        },
      },
    );
  }

  return (
    <LoginPage
      onSubmit={handleSubmit}
      isSubmitting={loginMutation.isPending}
      error={loginMutation.error?.message}
    />
  );
}
