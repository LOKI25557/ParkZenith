import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info' | 'ai' | 'neutral';
  size?: 'sm' | 'md';
  pulse?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  pulse = false,
  className = '',
  style,
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return { background: 'rgba(26, 91, 255, 0.15)', color: '#B7C4FF', border: '1px solid rgba(26, 91, 255, 0.35)' };
      case 'secondary':
        return { background: 'rgba(0, 229, 255, 0.12)', color: '#00E5FF', border: '1px solid rgba(0, 229, 255, 0.35)' };
      case 'success':
        return { background: 'rgba(16, 185, 129, 0.15)', color: '#10B981', border: '1px solid rgba(16, 185, 129, 0.35)' };
      case 'warning':
        return { background: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B', border: '1px solid rgba(245, 158, 11, 0.35)' };
      case 'error':
        return { background: 'rgba(244, 63, 94, 0.15)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.35)' };
      case 'info':
        return { background: 'rgba(14, 165, 233, 0.15)', color: '#38BDF8', border: '1px solid rgba(14, 165, 233, 0.35)' };
      case 'ai':
        return { background: 'rgba(139, 92, 246, 0.18)', color: '#C084FC', border: '1px solid rgba(139, 92, 246, 0.4)' };
      case 'neutral':
      default:
        return { background: 'rgba(255, 255, 255, 0.05)', color: 'var(--pz-text-secondary)', border: '1px solid var(--pz-border-subtle)' };
    }
  };

  return (
    <span
      className={`pz-badge ${pulse ? 'animate-pulse-glow' : ''} ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        borderRadius: '9999px',
        fontWeight: 500,
        fontFamily: 'var(--font-sans)',
        fontSize: size === 'sm' ? '0.6875rem' : '0.75rem',
        padding: size === 'sm' ? '2px 8px' : '4px 10px',
        whiteSpace: 'nowrap',
        ...getVariantStyles(),
        ...style,
      }}
    >
      {pulse && (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: 'currentColor',
          }}
        />
      )}
      {children}
    </span>
  );
};
