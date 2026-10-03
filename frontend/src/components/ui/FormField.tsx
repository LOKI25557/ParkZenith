import React from 'react';

export interface FormFieldProps {
  label?: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
  id?: string;
}

export const FormField: React.FC<FormFieldProps> = ({
  label,
  error,
  hint,
  required,
  children,
  id,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', width: '100%', marginBottom: '1rem' }}>
      {label && (
        <label
          htmlFor={id}
          style={{
            fontSize: '0.875rem',
            fontWeight: 500,
            color: 'var(--pz-text-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--pz-error)' }}>*</span>}
        </label>
      )}
      {children}
      {error && (
        <span
          role="alert"
          style={{
            fontSize: '0.75rem',
            color: 'var(--pz-error)',
            marginTop: '2px',
          }}
        >
          {error}
        </span>
      )}
      {!error && hint && (
        <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>
          {hint}
        </span>
      )}
    </div>
  );
};
