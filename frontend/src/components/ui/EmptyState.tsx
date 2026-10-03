import React from 'react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '3rem 1.5rem',
        borderRadius: '16px',
        border: '1px dashed var(--pz-border)',
        backgroundColor: 'rgba(255, 255, 255, 0.01)',
      }}
    >
      {icon && (
        <div
          style={{
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            backgroundColor: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--pz-border-subtle)',
            color: 'var(--pz-text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '1rem',
          }}
        >
          {icon}
        </div>
      )}
      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--pz-text-primary)' }}>
        {title}
      </h3>
      <p
        style={{
          fontSize: '0.875rem',
          color: 'var(--pz-text-secondary)',
          marginTop: '0.375rem',
          maxWidth: '400px',
          lineHeight: 1.5,
        }}
      >
        {description}
      </p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction} style={{ marginTop: '1.25rem' }}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
