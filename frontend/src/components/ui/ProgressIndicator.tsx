import React from 'react';

export interface ProgressIndicatorProps {
  value: number; // 0 to 100
  color?: 'cyan' | 'emerald' | 'purple' | 'amber' | 'rose';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  value,
  color = 'cyan',
  size = 'md',
  showLabel = false,
}) => {
  const clamped = Math.min(100, Math.max(0, value));

  const getColor = () => {
    switch (color) {
      case 'emerald': return '#10B981';
      case 'purple': return '#8B5CF6';
      case 'amber': return '#F59E0B';
      case 'rose': return '#F43F5E';
      case 'cyan':
      default: return '#00E5FF';
    }
  };

  const getHeight = () => {
    switch (size) {
      case 'sm': return '4px';
      case 'lg': return '10px';
      case 'md':
      default: return '6px';
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {showLabel && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '0.75rem',
          color: 'var(--pz-text-secondary)',
          marginBottom: '4px',
          fontFamily: 'var(--font-mono)',
        }}>
          <span>Progress</span>
          <span>{clamped.toFixed(1)}%</span>
        </div>
      )}
      <div
        style={{
          width: '100%',
          height: getHeight(),
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '9999px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${clamped}%`,
            height: '100%',
            backgroundColor: getColor(),
            borderRadius: '9999px',
            transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
            boxShadow: `0 0 10px ${getColor()}`,
          }}
        />
      </div>
    </div>
  );
};
