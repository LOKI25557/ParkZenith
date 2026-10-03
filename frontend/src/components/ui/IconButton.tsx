import React from 'react';

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  ariaLabel: string;
}

export const IconButton: React.FC<IconButtonProps> = ({
  children,
  variant = 'ghost',
  size = 'md',
  ariaLabel,
  className = '',
  disabled,
  style,
  ...props
}) => {
  const getSize = () => {
    switch (size) {
      case 'sm':
        return { width: '32px', height: '32px', padding: '6px' };
      case 'lg':
        return { width: '48px', height: '48px', padding: '12px' };
      case 'md':
      default:
        return { width: '40px', height: '40px', padding: '8px' };
    }
  };

  const getVariant = () => {
    switch (variant) {
      case 'primary':
        return { background: 'var(--pz-primary)', color: '#FFFFFF', border: 'none' };
      case 'secondary':
        return { background: 'var(--pz-secondary)', color: '#090B10', border: 'none' };
      case 'outline':
        return { background: 'rgba(255,255,255,0.03)', color: 'var(--pz-text-primary)', border: '1px solid var(--pz-border)' };
      case 'danger':
        return { background: 'rgba(244, 63, 94, 0.15)', color: 'var(--pz-error)', border: '1px solid rgba(244, 63, 94, 0.3)' };
      case 'ghost':
      default:
        return { background: 'transparent', color: 'var(--pz-text-secondary)', border: 'none' };
    }
  };

  return (
    <button
      aria-label={ariaLabel}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '8px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        transition: 'all 0.2s ease',
        ...getSize(),
        ...getVariant(),
        ...style,
      }}
      className={`pz-icon-button ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
