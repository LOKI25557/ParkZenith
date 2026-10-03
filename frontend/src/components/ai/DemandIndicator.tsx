import React from 'react';
import { TrendingUp, AlertTriangle } from 'lucide-react';

export interface DemandIndicatorProps {
  multiplier?: number; // e.g. 1.25x
  level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  peakTime?: string;
  expectedIncreasePct?: number;
}

export const DemandIndicator: React.FC<DemandIndicatorProps> = ({
  multiplier = 1.15,
  level = 'MEDIUM',
  peakTime = '17:30',
  expectedIncreasePct = 35,
}) => {
  const getColor = () => {
    switch (level) {
      case 'CRITICAL': return '#F43F5E';
      case 'HIGH': return '#FB7185';
      case 'MEDIUM': return '#F59E0B';
      case 'LOW':
      default: return '#10B981';
    }
  };

  const color = getColor();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        padding: '1.25rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '14px',
        border: `1px solid ${color}30`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingUp size={18} color={color} />
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
            Dynamic Demand Surge Index
          </span>
        </div>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.875rem',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '6px',
            backgroundColor: `${color}20`,
            color: color,
            border: `1px solid ${color}40`,
          }}
        >
          {multiplier.toFixed(2)}x
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-heading)' }}>
          {level} SURGE
        </span>
        <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
          (+{expectedIncreasePct}% volume)
        </span>
      </div>

      {peakTime && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: 'var(--pz-text-muted)',
            borderTop: '1px solid var(--pz-border-subtle)',
            paddingTop: '0.5rem',
          }}
        >
          <AlertTriangle size={13} color={color} />
          <span>Peak compression anticipated at <strong>{peakTime}</strong></span>
        </div>
      )}
    </div>
  );
};
