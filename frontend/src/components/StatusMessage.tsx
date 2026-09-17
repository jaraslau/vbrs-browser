import type { ReactNode } from "react";

/** Accessible message shown while a request is in flight. */
export function LoadingMessage() {
  return (
    <p role="status" className="status-message" aria-live="polite">
      Loading…
    </p>
  );
}

/** Accessible error message with an optional retry action. */
export function ErrorMessage({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="error-message">
      <p>{message}</p>
      {onRetry !== undefined && (
        <button type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Accessible empty/no-results message. */
export function EmptyMessage({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="empty-message">
      {children}
    </p>
  );
}