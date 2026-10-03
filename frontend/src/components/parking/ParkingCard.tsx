import React from 'react';
import type { Facility, Availability } from '../../types';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { MapPin, Clock, ArrowRight, ShieldCheck, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface ParkingCardProps {
  facility: Facility;
  availability?: Availability | null;
  distanceKm?: number;
  hourlyRate?: number;
}

export const ParkingCard: React.FC<ParkingCardProps> = ({
  facility,
  availability,
  distanceKm = 0.8,
  hourlyRate = 3.50,
}) => {
  const navigate = useNavigate();

  const total = availability?.total_slots || facility.total_slots || 100;
  const available = availability?.available ?? Math.round(total * 0.35);
  const occupancyPct = availability?.occupancy_percentage ?? Math.round(((total - available) / total) * 100);

  const getOccupancyColor = (pct: number) => {
    if (pct < 60) return 'var(--pz-success)';
    if (pct < 85) return 'var(--pz-warning)';
    return 'var(--pz-error)';
  };

  return (
    <Card
      interactive
      onClick={() => navigate(`/parking/${facility.id}`)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
      }}
    >
      <div>
        {/* Top Badges */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.75rem',
              fontWeight: 500,
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: 'rgba(0, 229, 255, 0.1)',
              color: 'var(--pz-secondary)',
              border: '1px solid rgba(0, 229, 255, 0.25)',
            }}
          >
            <MapPin size={12} /> {distanceKm.toFixed(1)} km away
          </span>

          <span
            style={{
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              color: getOccupancyColor(occupancyPct),
            }}
          >
            {available} Bays Open
          </span>
        </div>

        {/* Facility Title & Location */}
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.375rem' }}>
          {facility.name}
        </h3>
        <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginBottom: '1.25rem', lineHeight: 1.4 }}>
          {facility.address} {facility.city ? `• ${facility.city}` : ''}
        </p>

        {/* Telemetry Progress Bar */}
        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--pz-text-muted)', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
            <span>Live Occupancy</span>
            <span>{occupancyPct.toFixed(0)}% full</span>
          </div>
          <div style={{ height: '6px', borderRadius: '9999px', backgroundColor: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
            <div
              style={{
                width: `${occupancyPct}%`,
                height: '100%',
                backgroundColor: getOccupancyColor(occupancyPct),
                borderRadius: '9999px',
                transition: 'width 0.4s ease',
              }}
            />
          </div>
        </div>

        {/* Features Chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '1.5rem' }}>
          <span style={{ fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', color: 'var(--pz-text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={11} /> 24/7 Access
          </span>
          <span style={{ fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', color: 'var(--pz-text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Zap size={11} color="var(--pz-secondary)" /> EV Charging
          </span>
          <span style={{ fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', color: 'var(--pz-text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={11} color="var(--pz-success)" /> ALPR Express
          </span>
        </div>
      </div>

      {/* Footer Pricing & CTA */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '1rem',
          marginTop: 'auto',
        }}
      >
        <div>
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
            ${hourlyRate.toFixed(2)}
          </span>
          <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}> / hour</span>
        </div>

        <Button
          variant="primary"
          size="sm"
          rightIcon={<ArrowRight size={14} />}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/parking/${facility.id}`);
          }}
        >
          View Slots
        </Button>
      </div>
    </Card>
  );
};
