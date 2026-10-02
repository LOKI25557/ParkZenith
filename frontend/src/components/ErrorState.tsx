
interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ 
  message = "An error occurred.", 
  onRetry 
}) => {
  return (
    <div className="error-state" style={{ padding: '2rem', textAlign: 'center' }}>
      <h3 style={{ color: 'red' }}>Error</h3>
      <p>{message}</p>
      {onRetry && (
        <button onClick={onRetry} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
          Retry
        </button>
      )}
    </div>
  );
};
