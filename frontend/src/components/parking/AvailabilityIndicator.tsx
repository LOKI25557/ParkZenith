import React from 'react';
import type { Availability } from '../../types';

export interface AvailabilityIndicatorProps {
  availability: Availability;
  facilityName?: string;
}

export const AvailabilityIndicator: React.FC<AvailabilityIndicatorProps> = ({
  availability,
  facilityName,
}) => {
  const { total_slots, available, occupied, reserved, occupancy_percentage } = availability;

  const pct = occupancy_percentage || (total_slots > 0 ? (occupied / total_slots) * 100 : 0);

  const getStatusColor = (percentage: number) => {
    if (percentage < 60) return '#10B981';
    if (percentage < 85) return '#F59E0B';
    return '#F43F5E';
  };

  const statusColor = getStatusColor(pct);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        padding: '1.25rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '16px',
        border: '1px solid var(--pz-border-subtle)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--pz-text-muted)' }}>
            Live Facility Telemetry
          </span>
          <h4 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
            {facilityName || 'Current Facility'}
          </h4>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '1.5rem', fontWeight: 700, color: statusColor, fontFamily: 'var(--font-mono)' }}>
            {pct.toFixed(0)}%
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>
            Occupied
          </span>
        </div>
      </div>

      {/* Multicolored Capacity Segment Bar */}
      <div
        style={{
          display: 'flex',
          height: '10px',
          width: '100%',
          borderRadius: '9999px',
          overflow: 'hidden',
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
        }}
      >
        <div
          title={`Available: ${available}`}
          style={{
            width: `${total_slots > 0 ? (available / total_slots) * 100 : 0}%`,
            backgroundColor: '#10B981',
            transition: 'width 0.5s ease',
          }}
        />
        <div
          title={`Occupied: ${occupied}`}
          style={{
            width: `${total_slots > 0 ? (occupied / total_slots) * 100 : 0}%`,
            backgroundColor: '#64748B',
            transition: 'width 0.5s ease',
          }}
        />
        <div
          title={`Reserved: ${reserved}`}
          style={{
            width: `${total_slots > 0 ? (reserved / total_slots) * 100 : 0}%`,
            backgroundColor: '#F59E0B',
            transition: 'width 0.5s ease',
          }}
        />
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', textAlign: 'center' }}>
        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
            {available}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-secondary)', display: 'block' }}>
            Available
          </span>
        </div>

        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(100, 116, 139, 0.1)', border: '1px solid var(--pz-border-subtle)' }}>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--pz-text-primary)', fontFamily: 'var(--font-mono)' }}>
            {occupied}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-secondary)', display: 'block' }}>
            Occupied
          </span>
        </div>

        <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#F59E0B', fontFamily: 'var(--font-mono)' }}>
            {reserved}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-secondary)', display: 'block' }}>
            Reserved
          </span>
        </div>
      </div>
    </div>
  );
};
