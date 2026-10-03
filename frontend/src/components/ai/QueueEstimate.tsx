import React from 'react';
import { Timer, ArrowRightLeft, ShieldCheck } from 'lucide-react';

export interface QueueEstimateProps {
  waitTimeMinutes?: number;
  throughputRate?: number; // cars per minute
  gateName?: string;
  status?: string;
}

export const QueueEstimate: React.FC<QueueEstimateProps> = ({
  waitTimeMinutes = 2.4,
  throughputRate = 14.2,
  gateName = 'Gate B Express ALPR',
  status = 'Smooth Flow',
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        padding: '1.25rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '14px',
        border: '1px solid var(--pz-border-subtle)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Timer size={18} color="var(--pz-secondary)" />
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
            Gate Clearance Latency
          </span>
        </div>
        <span
          style={{
            fontSize: '0.6875rem',
            padding: '2px 8px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            color: 'var(--pz-success)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <ShieldCheck size={11} /> {status}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            color: '#00E5FF',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {waitTimeMinutes.toFixed(1)} <span style={{ fontSize: '0.9375rem', fontWeight: 500, color: 'var(--pz-text-secondary)' }}>min wait</span>
        </span>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.75rem',
          color: 'var(--pz-text-secondary)',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '0.5rem',
        }}
      >
        <span>{gateName}</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontFamily: 'var(--font-mono)' }}>
          <ArrowRightLeft size={12} color="var(--pz-text-muted)" /> {throughputRate} cars/min
        </span>
      </div>
    </div>
  );
};
