import React from 'react';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  label,
}) => {
  const getDims = () => {
    switch (size) {
      case 'sm': return 20;
      case 'lg': return 48;
      case 'md':
      default: return 32;
    }
  };
  const d = getDims();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          width: `${d}px`,
          height: `${d}px`,
          border: '3px solid rgba(0, 229, 255, 0.15)',
          borderTopColor: 'var(--pz-secondary)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      {label && (
        <span style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', fontWeight: 500 }}>
          {label}
        </span>
      )}
    </div>
  );
};
