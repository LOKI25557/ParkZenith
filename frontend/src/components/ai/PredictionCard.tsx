import React from 'react';
import { Sparkles, Brain, ArrowRight } from 'lucide-react';
import { Button } from '../ui/Button';

export interface PredictionCardProps {
  probability: number;
  expectedFreeSlots: number;
  forecastOccupancy: number;
  etaMinutes?: number;
  facilityName?: string;
  onReserveHold?: () => void;
}

export const PredictionCard: React.FC<PredictionCardProps> = ({
  probability,
  expectedFreeSlots,
  forecastOccupancy,
  etaMinutes = 20,
  facilityName = 'Downtown Central',
  onReserveHold,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        padding: '1.5rem',
        backgroundColor: 'rgba(20, 24, 38, 0.85)',
        borderRadius: '16px',
        border: '1px solid rgba(139, 92, 246, 0.4)',
        boxShadow: '0 12px 32px -4px rgba(139, 92, 246, 0.15)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={20} color="#C084FC" />
          <h4 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
            Neural Predictive Insight
          </h4>
        </div>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '0.6875rem',
            padding: '2px 8px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(139, 92, 246, 0.2)',
            color: '#C084FC',
            border: '1px solid rgba(139, 92, 246, 0.4)',
          }}
        >
          <Sparkles size={11} /> LSTM v4.9 Active
        </span>
      </div>

      <div>
        <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
          Forecast for <strong>{facilityName}</strong> at ETA (+{etaMinutes} mins)
        </span>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
          <span style={{ fontSize: '2rem', fontWeight: 800, color: '#00E5FF', fontFamily: 'var(--font-heading)' }}>
            {probability.toFixed(0)}%
          </span>
          <span style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)' }}>
            Arrival Availability Probability
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--pz-border-subtle)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Expected Free Bays</span>
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
            {expectedFreeSlots}
          </span>
        </div>

        <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--pz-border-subtle)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Forecast Occupancy</span>
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
            {forecastOccupancy.toFixed(0)}%
          </span>
        </div>
      </div>

      {onReserveHold && (
        <Button
          variant="ai"
          onClick={onReserveHold}
          rightIcon={<ArrowRight size={14} />}
          style={{ width: '100%', marginTop: '0.25rem' }}
        >
          Lock Guaranteed Predictive Slot
        </Button>
      )}
    </div>
  );
};
