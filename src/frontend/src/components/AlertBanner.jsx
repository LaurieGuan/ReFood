export function AlertBanner({ children, onDismiss }) {
  return (
    <div className="error-banner" role="alert">
      {children}
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Fermer">
          ×
        </button>
      )}
    </div>
  );
}
