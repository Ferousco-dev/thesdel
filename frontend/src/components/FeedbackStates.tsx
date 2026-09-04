interface LoadingProps {
  message?: string;
}

export function LoadingState({ message = "Loading…" }: LoadingProps) {
  return (
    <div style={{ padding: "4rem 2rem", textAlign: "center", color: "var(--color-text-secondary)" }}>
      <p>{message}</p>
    </div>
  );
}

interface EmptyProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ title, description, actionLabel, onAction }: EmptyProps) {
  return (
    <div style={{ padding: "4rem 2rem", textAlign: "center", border: "2px dashed var(--color-border)", borderRadius: "var(--radius-lg)" }}>
      <h3 style={{ fontSize: "var(--font-size-h2)", marginBottom: "0.5rem" }}>{title}</h3>
      <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--font-size-caption)", marginBottom: "1.5rem" }}>{description}</p>
      {actionLabel && onAction && (
        <button type="button" className="btn btn--ghost" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}

interface ErrorProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorProps) {
  return (
    <div style={{ padding: "2rem", textAlign: "center", color: "var(--color-error)" }}>
      <p style={{ marginBottom: "1rem" }}>{message}</p>
      {onRetry && (
        <button type="button" className="btn btn--ghost" onClick={onRetry} style={{ borderColor: "var(--color-error)", color: "var(--color-error)" }}>
          Try Again
        </button>
      )}
    </div>
  );
}
