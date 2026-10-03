import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: 'cyan' | 'purple' | 'emerald' | 'none';
  interactive?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  glow = 'none',
  interactive = false,
  className = '',
  style,
  ...props
}) => {
  const getGlowClass = () => {
    switch (glow) {
      case 'cyan': return 'border-glow-cyan';
      case 'purple': return 'border-glow-purple';
      case 'emerald': return 'border-glow-emerald';
      case 'none':
      default: return '';
    }
  };

  return (
    <div
      className={`glass-card ${interactive ? 'glass-card-interactive' : ''} ${getGlowClass()} ${className}`}
      style={{
        padding: '1.5rem',
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
};
