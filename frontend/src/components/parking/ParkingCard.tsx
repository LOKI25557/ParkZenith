import React from 'react';
import type { Facility, Availability } from '../../types';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { MapPin, Clock, ArrowRight, ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';
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
  distanceKm,
  hourlyRate,
}) => {
  const navigate = useNavigate();

  const total = availability?.total_slots ?? facility.total_slots ?? 0;
  const available = availability?.available;
  const occupancyPct = availability?.occupancy_percentage ?? (
    total > 0 && available !== undefined ? Math.round(((total - available) / total) * 100) : 0
  );

  const getOccupancyColor = (pct: number) => {
    if (pct < 60) return 'var(--pz-success)';
    if (pct < 85) return 'var(--pz-warning)';
    return 'var(--pz-error)';
  };

  const isOpen = facility.is_active;

  // Format operating hours
  const operatingHours = facility.operating_start_time && facility.operating_end_time
    ? `${facility.operating_start_time} - ${facility.operating_end_time}`
    : '24/7 Access';

  return (
    <Card
      interactive
      onClick={() => navigate(`/parking/${facility.id}`)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
        padding: '1.25rem',
      }}
    >
      <div>
        {/* Top Badges / Status */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: '9999px',
                backgroundColor: isOpen ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
                color: isOpen ? 'var(--pz-success)' : 'var(--pz-error)',
                border: `1px solid ${isOpen ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
              }}
            >
              {isOpen ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
              {isOpen ? 'OPEN' : 'CLOSED'}
            </span>

            {distanceKm !== undefined && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  padding: '3px 8px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(0, 229, 255, 0.08)',
                  color: 'var(--pz-secondary)',
                  border: '1px solid rgba(0, 229, 255, 0.2)',
                }}
              >
                <MapPin size={11} /> {distanceKm.toFixed(1)} km
              </span>
            )}
          </div>

          <span
            style={{
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              color: available !== undefined ? getOccupancyColor(occupancyPct) : 'var(--pz-text-muted)',
            }}
          >
            {available !== undefined ? (
              available === 0 ? 'Full' : `${available} Bays Open`
            ) : (
              'Syncing...'
            )}
          </span>
        </div>

        {/* Facility Title & Address */}
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.375rem', lineHeight: 1.3 }}>
          {facility.name}
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--pz-text-secondary)', marginBottom: '1rem', lineHeight: 1.4 }}>
          {facility.address}
          {facility.city ? `, ${facility.city}` : ''}
          {facility.state ? ` ${facility.state}` : ''}
        </p>

        {/* Real Metrics Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '10px',
            padding: '10px',
            marginBottom: '1rem',
            border: '1px solid var(--pz-border-subtle)',
            textAlign: 'center',
          }}
        >
          <div>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Available
            </span>
            <span
              style={{
                fontSize: '1.125rem',
                fontWeight: 700,
                color: available !== undefined ? (available > 0 ? 'var(--pz-success)' : 'var(--pz-error)') : 'var(--pz-text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {available !== undefined ? available : '—'}
            </span>
          </div>

          <div>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Total
            </span>
            <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {total}
            </span>
          </div>

          <div>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {hourlyRate !== undefined ? 'Rate' : 'Occupancy'}
            </span>
            <span style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
              {hourlyRate !== undefined ? `₹${hourlyRate}/h` : `${occupancyPct.toFixed(0)}%`}
            </span>
          </div>
        </div>

        {/* Telemetry Progress Bar */}
        {availability && (
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--pz-text-muted)', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
              <span>Live Density</span>
              <span>{occupancyPct.toFixed(0)}% full</span>
            </div>
            <div style={{ height: '5px', borderRadius: '9999px', backgroundColor: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
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
        )}

        {/* Feature indicators */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', color: 'var(--pz-text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={11} /> {operatingHours}
          </span>
          <span style={{ fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.04)', color: 'var(--pz-text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={11} color="var(--pz-secondary)" /> Connected
          </span>
        </div>
      </div>

      {/* Footer CTA Buttons */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '0.875rem',
          marginTop: 'auto',
          gap: '8px',
        }}
      >
        <Button
          variant="outline"
          size="sm"
          style={{ flex: 1 }}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/parking/${facility.id}`);
          }}
        >
          View Details
        </Button>

        <Button
          variant="primary"
          size="sm"
          style={{ flex: 1 }}
          rightIcon={<ArrowRight size={14} />}
          disabled={!isOpen || (available !== undefined && available === 0)}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/parking/${facility.id}`);
          }}
        >
          {available === 0 ? 'Full' : 'Reserve'}
        </Button>
      </div>
    </Card>
  );
};
