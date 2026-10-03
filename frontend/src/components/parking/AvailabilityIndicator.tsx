import React from 'react';
import type { Availability } from '../../types';
import type { ConnectionStatus } from '../../services/websocket';
import { ConnectionStatusBadge } from './ConnectionStatusBadge';

export interface AvailabilityIndicatorProps {
  availability: Availability;
  facilityName?: string;
  zoneName?: string;
  connectionStatus?: ConnectionStatus;
  onReconnect?: () => void;
}

export const AvailabilityIndicator: React.FC<AvailabilityIndicatorProps> = ({
  availability,
  facilityName,
  zoneName,
  connectionStatus,
  onReconnect,
}) => {
  const { total_slots, available, occupied, reserved, occupancy_percentage } = availability;

  const pct = typeof occupancy_percentage === 'number'
    ? occupancy_percentage
    : (total_slots > 0 ? (occupied / total_slots) * 100 : 0);

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
      role="region"
      aria-label="Live Availability Summary"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--pz-text-muted)' }}>
            Live Telemetry {zoneName ? `• ${zoneName}` : ''}
          </span>
          <h4 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#FFFFFF', marginTop: '2px', margin: 0 }}>
            {facilityName || 'Current Facility'}
          </h4>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {connectionStatus && (
            <ConnectionStatusBadge status={connectionStatus} onReconnect={onReconnect} />
          )}

          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '1.5rem', fontWeight: 800, color: statusColor, fontFamily: 'var(--font-mono)' }}>
              {pct.toFixed(0)}%
            </span>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block', textTransform: 'uppercase' }}>
              Occupied
            </span>
          </div>
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
        title={`Available: ${available}, Occupied: ${occupied}, Reserved: ${reserved}`}
      >
        <div
          style={{
            width: `${total_slots > 0 ? (available / total_slots) * 100 : 0}%`,
            backgroundColor: '#10B981',
            transition: 'width 0.4s ease',
          }}
        />
        <div
          style={{
            width: `${total_slots > 0 ? (occupied / total_slots) * 100 : 0}%`,
            backgroundColor: '#64748B',
            transition: 'width 0.4s ease',
          }}
        />
        <div
          style={{
            width: `${total_slots > 0 ? (reserved / total_slots) * 100 : 0}%`,
            backgroundColor: '#F59E0B',
            transition: 'width 0.4s ease',
          }}
        />
      </div>

      {/* 4-Column Authoritative Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', textAlign: 'center' }}>
        <div style={{ padding: '8px 4px', borderRadius: '8px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
          <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
            {available}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-success)', display: 'block', fontWeight: 600 }}>
            Available
          </span>
        </div>

        <div style={{ padding: '8px 4px', borderRadius: '8px', backgroundColor: 'rgba(100, 116, 139, 0.1)', border: '1px solid var(--pz-border-subtle)' }}>
          <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--pz-text-primary)', fontFamily: 'var(--font-mono)' }}>
            {occupied}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-secondary)', display: 'block' }}>
            Occupied
          </span>
        </div>

        <div style={{ padding: '8px 4px', borderRadius: '8px', backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
          <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#F59E0B', fontFamily: 'var(--font-mono)' }}>
            {reserved}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-warning)', display: 'block' }}>
            Reserved
          </span>
        </div>

        <div style={{ padding: '8px 4px', borderRadius: '8px', backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--pz-border-subtle)' }}>
          <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
            {total_slots}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>
            Total Bays
          </span>
        </div>
      </div>
    </div>
  );
};
