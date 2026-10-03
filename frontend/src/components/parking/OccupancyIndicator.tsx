import React from 'react';

export interface OccupancyIndicatorProps {
  percentage: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const OccupancyIndicator: React.FC<OccupancyIndicatorProps> = ({
  percentage,
  size = 'md',
  showLabel = true,
}) => {
  const p = Math.min(100, Math.max(0, percentage));

  const getColor = (pct: number) => {
    if (pct < 60) return '#10B981';
    if (pct < 85) return '#F59E0B';
    return '#F43F5E';
  };

  const color = getColor(p);

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
      <div
        style={{
          width: size === 'sm' ? '32px' : size === 'lg' ? '64px' : '44px',
          height: size === 'sm' ? '32px' : size === 'lg' ? '64px' : '44px',
          borderRadius: '50%',
          border: `3px solid rgba(255, 255, 255, 0.08)`,
          borderTopColor: color,
          borderRightColor: color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: 'rotate(-45deg)',
        }}
      >
        <span
          style={{
            transform: 'rotate(45deg)',
            fontFamily: 'var(--font-mono)',
            fontSize: size === 'sm' ? '0.625rem' : size === 'lg' ? '1rem' : '0.75rem',
            fontWeight: 700,
            color,
          }}
        >
          {p.toFixed(0)}%
        </span>
      </div>
      {showLabel && (
        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block' }}>
            Occupancy
          </span>
          <span style={{ fontSize: '0.6875rem', color, fontWeight: 500 }}>
            {p < 60 ? 'Low Density' : p < 85 ? 'Moderate' : 'High Surge'}
          </span>
        </div>
      )}
    </div>
  );
};
