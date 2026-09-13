import { createRootRoute, Outlet, type ErrorComponentProps } from "@tanstack/react-router";

function RootErrorComponent({ error }: ErrorComponentProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-surface">
      <div className="w-full max-w-[480px] bg-surface-container-lowest border border-outline-variant rounded stamp-shadow p-8 text-center flex flex-col items-center gap-4">
        <h1 className="font-label-md text-label-md font-bold text-on-surface">
          Something went wrong
        </h1>
        <p className="text-on-surface-variant text-sm">
          {error instanceof Error ? error.message : "An unexpected error occurred."}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="py-2.5 px-6 bg-primary-container text-on-primary rounded font-label-md text-label-md font-bold hover:bg-primary transition-all duration-200"
        >
          Reload page
        </button>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  component: () => <Outlet />,
  errorComponent: RootErrorComponent,
});
