import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  error,
  leftIcon,
  rightIcon,
  className = '',
  style,
  ...props
}, ref) => {
  return (
    <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
      {leftIcon && (
        <span style={{
          position: 'absolute',
          left: '12px',
          color: 'var(--pz-text-muted)',
          display: 'inline-flex',
          pointerEvents: 'none',
        }}>
          {leftIcon}
        </span>
      )}
      <input
        ref={ref}
        className={`pz-input ${className}`}
        style={{
          paddingLeft: leftIcon ? '40px' : '14px',
          paddingRight: rightIcon ? '40px' : '14px',
          borderColor: error ? 'var(--pz-error)' : undefined,
          boxShadow: error ? '0 0 0 2px rgba(244, 63, 94, 0.2)' : undefined,
          ...style,
        }}
        {...props}
      />
      {rightIcon && (
        <span style={{
          position: 'absolute',
          right: '12px',
          color: 'var(--pz-text-muted)',
          display: 'inline-flex',
          alignItems: 'center',
        }}>
          {rightIcon}
        </span>
      )}
    </div>
  );
});

Input.displayName = 'Input';
