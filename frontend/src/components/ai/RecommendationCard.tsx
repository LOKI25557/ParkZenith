import React from 'react';
import { Sparkles, MapPin, ArrowRight } from 'lucide-react';
import { Button } from '../ui/Button';

export interface RecommendationCardProps {
  rank: number;
  facilityName: string;
  matchScore: number; // 0-100
  distanceKm: number;
  openBays: number;
  estimatedCost: number;
  reason?: string;
  onSelect?: () => void;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  rank,
  facilityName,
  matchScore,
  distanceKm,
  openBays,
  estimatedCost,
  reason,
  onSelect,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.875rem',
        padding: '1.25rem',
        backgroundColor: 'rgba(15, 19, 30, 0.7)',
        borderRadius: '14px',
        border: rank === 1 ? '1px solid rgba(139, 92, 246, 0.4)' : '1px solid var(--pz-border-subtle)',
        boxShadow: rank === 1 ? '0 8px 24px -4px rgba(139, 92, 246, 0.2)' : 'none',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: rank === 1 ? 'var(--pz-primary)' : 'rgba(255, 255, 255, 0.1)',
              color: '#FFFFFF',
              fontSize: '0.75rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {rank}
          </span>
          <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF' }}>
            {facilityName}
          </h4>
        </div>

        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(139, 92, 246, 0.18)',
            color: '#C084FC',
            border: '1px solid rgba(139, 92, 246, 0.4)',
          }}
        >
          <Sparkles size={11} /> {matchScore}% Match
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <MapPin size={13} color="var(--pz-secondary)" /> {distanceKm.toFixed(1)} km
        </span>
        <span style={{ color: 'var(--pz-success)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
          {openBays} Bays Free
        </span>
        <span style={{ color: '#FFFFFF', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
          ${estimatedCost.toFixed(2)}/hr
        </span>
      </div>

      {reason && (
        <p style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', lineHeight: 1.4 }}>
          {reason}
        </p>
      )}

      {onSelect && (
        <div style={{ borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem', marginTop: '0.25rem' }}>
          <Button
            variant={rank === 1 ? 'ai' : 'outline'}
            size="sm"
            onClick={onSelect}
            rightIcon={<ArrowRight size={14} />}
            style={{ width: '100%' }}
          >
            Select &amp; Lock Bay
          </Button>
        </div>
      )}
    </div>
  );
};
