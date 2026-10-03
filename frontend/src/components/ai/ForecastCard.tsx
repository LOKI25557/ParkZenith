import React from 'react';
import { LineChart, Clock } from 'lucide-react';

export interface ForecastCardProps {
  currentOccupancy: number;
  prediction15: number;
  prediction30: number;
  prediction60: number;
  confidence?: number;
}

export const ForecastCard: React.FC<ForecastCardProps> = ({
  currentOccupancy,
  prediction15,
  prediction30,
  prediction60,
  confidence = 94,
}) => {
  const getTrendColor = (curr: number, pred: number) => {
    const diff = pred - curr;
    if (diff > 5) return 'var(--pz-error)';
    if (diff < -5) return 'var(--pz-success)';
    return 'var(--pz-secondary)';
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        padding: '1.25rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '14px',
        border: '1px solid var(--pz-border-subtle)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <LineChart size={18} color="var(--pz-secondary)" />
          <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
            Neural Temporal Horizon
          </h4>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)' }}>
          {confidence}% Confidence
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', textAlign: 'center' }}>
        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Now</span>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
            {currentOccupancy.toFixed(0)}%
          </span>
        </div>

        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>+15m</span>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: getTrendColor(currentOccupancy, prediction15), fontFamily: 'var(--font-mono)' }}>
            {prediction15.toFixed(0)}%
          </span>
        </div>

        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>+30m</span>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: getTrendColor(currentOccupancy, prediction30), fontFamily: 'var(--font-mono)' }}>
            {prediction30.toFixed(0)}%
          </span>
        </div>

        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>+60m</span>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: getTrendColor(currentOccupancy, prediction60), fontFamily: 'var(--font-mono)' }}>
            {prediction60.toFixed(0)}%
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--pz-text-secondary)' }}>
        <Clock size={12} color="var(--pz-secondary)" />
        <span>LSTM auto-recalibrates every 60 seconds with IoT sensor telemetry.</span>
      </div>
    </div>
  );
};
