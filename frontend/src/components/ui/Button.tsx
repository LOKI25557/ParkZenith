import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'ai';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return {
          background: 'linear-gradient(135deg, #1A5BFF 0%, #004DEA 100%)',
          color: '#FFFFFF',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          boxShadow: '0 4px 14px 0 rgba(26, 91, 255, 0.35)',
        };
      case 'secondary':
        return {
          background: 'linear-gradient(135deg, #00E5FF 0%, #00B4D8 100%)',
          color: '#090B10',
          border: '1px solid rgba(0, 229, 255, 0.4)',
          boxShadow: '0 4px 14px 0 rgba(0, 229, 255, 0.3)',
          fontWeight: 600,
        };
      case 'outline':
        return {
          background: 'rgba(255, 255, 255, 0.03)',
          color: '#FFFFFF',
          border: '1px solid var(--pz-border)',
        };
      case 'ghost':
        return {
          background: 'transparent',
          color: 'var(--pz-text-secondary)',
          border: '1px solid transparent',
        };
      case 'danger':
        return {
          background: 'linear-gradient(135deg, #F43F5E 0%, #E11D48 100%)',
          color: '#FFFFFF',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          boxShadow: '0 4px 14px 0 rgba(244, 63, 94, 0.3)',
        };
      case 'success':
        return {
          background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
          color: '#FFFFFF',
          border: '1px solid rgba(16, 185, 129, 0.4)',
          boxShadow: '0 4px 14px 0 rgba(16, 185, 129, 0.3)',
        };
      case 'ai':
        return {
          background: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
          color: '#FFFFFF',
          border: '1px solid rgba(139, 92, 246, 0.4)',
          boxShadow: '0 4px 16px 0 rgba(139, 92, 246, 0.35)',
        };
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return { padding: '0.4rem 0.75rem', fontSize: '0.8125rem', borderRadius: '6px' };
      case 'lg':
        return { padding: '0.85rem 1.75rem', fontSize: '1.0625rem', borderRadius: '12px' };
      case 'md':
      default:
        return { padding: '0.625rem 1.25rem', fontSize: '0.9375rem', borderRadius: '8px' };
    }
  };

  return (
    <button
      disabled={disabled || isLoading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        fontWeight: 500,
        ...getVariantStyles(),
        ...getSizeStyles(),
      }}
      className={`pz-button ${className}`}
      {...props}
    >
      {isLoading ? (
        <span
          style={{
            width: '16px',
            height: '16px',
            border: '2px solid rgba(255, 255, 255, 0.3)',
            borderTopColor: '#FFFFFF',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
      ) : leftIcon ? (
        <span style={{ display: 'inline-flex', alignItems: 'center' }}>{leftIcon}</span>
      ) : null}
      <span>{children}</span>
      {!isLoading && rightIcon && (
        <span style={{ display: 'inline-flex', alignItems: 'center' }}>{rightIcon}</span>
      )}
    </button>
  );
};
