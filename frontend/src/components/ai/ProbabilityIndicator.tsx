import React from 'react';

export interface ProbabilityIndicatorProps {
  probability: number; // 0 to 100
  confidence?: number;  // 0 to 100
  etaMinutes?: number;
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH';
}

export const ProbabilityIndicator: React.FC<ProbabilityIndicatorProps> = ({
  probability,
  confidence = 94,
  etaMinutes = 20,
  riskLevel = 'LOW',
}) => {
  const p = Math.min(100, Math.max(0, probability));

  const getColor = (val: number) => {
    if (val >= 80) return '#10B981';
    if (val >= 50) return '#F59E0B';
    return '#F43F5E';
  };

  const mainColor = getColor(p);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1.25rem',
        padding: '1.25rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '14px',
        border: '1px solid var(--pz-border-subtle)',
      }}
    >
      {/* Circular Radial Meter */}
      <div
        style={{
          position: 'relative',
          width: '76px',
          height: '76px',
          borderRadius: '50%',
          background: `conic-gradient(${mainColor} ${p * 3.6}deg, rgba(255, 255, 255, 0.08) 0deg)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          boxShadow: `0 0 16px -2px ${mainColor}40`,
        }}
      >
        <div
          style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            backgroundColor: '#0F131E',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '1rem',
              fontWeight: 700,
              color: '#FFFFFF',
              lineHeight: 1,
            }}
          >
            {p.toFixed(0)}%
          </span>
          <span style={{ fontSize: '0.625rem', color: 'var(--pz-text-muted)', marginTop: '2px' }}>
            Prob
          </span>
        </div>
      </div>

      {/* Narrative & Details */}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
          <span
            style={{
              fontSize: '0.6875rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: `${mainColor}20`,
              color: mainColor,
              border: `1px solid ${mainColor}40`,
            }}
          >
            {p >= 80 ? 'Guaranteed Available' : p >= 50 ? 'Moderate Availability' : 'High Surge Risk'}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)' }}>
            ETA: {etaMinutes}m
          </span>
        </div>

        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF', marginTop: '4px' }}>
          Arrival Assurance Score
        </h4>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '0.75rem', color: 'var(--pz-text-secondary)' }}>
          <span>Confidence: <strong style={{ color: 'var(--pz-secondary)' }}>{confidence}%</strong></span>
          <span>Risk: <strong style={{ color: riskLevel === 'HIGH' ? 'var(--pz-error)' : riskLevel === 'MEDIUM' ? 'var(--pz-warning)' : 'var(--pz-success)' }}>{riskLevel}</strong></span>
        </div>
      </div>
    </div>
  );
};
