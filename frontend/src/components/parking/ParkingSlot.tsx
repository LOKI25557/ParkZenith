import React from 'react';
import type { Slot, ParkingSlotStatus } from '../../types';
import { Car, Zap, Wrench, ShieldAlert, CheckCircle2 } from 'lucide-react';

export interface ParkingSlotProps {
  slot: Slot;
  isSelected?: boolean;
  onSelect?: (slot: Slot) => void;
  disabled?: boolean;
}

export const ParkingSlot: React.FC<ParkingSlotProps> = ({
  slot,
  isSelected = false,
  onSelect,
  disabled = false,
}) => {
  const isAvailable = slot.status === 'available';

  const getStatusColor = (status: ParkingSlotStatus) => {
    switch (status) {
      case 'available':
        return {
          bg: 'rgba(16, 185, 129, 0.12)',
          border: isSelected ? 'var(--pz-secondary)' : 'rgba(16, 185, 129, 0.4)',
          text: '#10B981',
          glow: isSelected ? '0 0 16px rgba(0, 229, 255, 0.5)' : 'none',
        };
      case 'occupied':
        return {
          bg: 'rgba(100, 116, 139, 0.08)',
          border: 'rgba(100, 116, 139, 0.25)',
          text: 'var(--pz-text-muted)',
          glow: 'none',
        };
      case 'reserved':
        return {
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.4)',
          text: '#F59E0B',
          glow: 'none',
        };
      case 'maintenance':
        return {
          bg: 'rgba(244, 63, 94, 0.12)',
          border: 'rgba(244, 63, 94, 0.4)',
          text: '#F43F5E',
          glow: 'none',
        };
      default:
        return {
          bg: 'rgba(255, 255, 255, 0.04)',
          border: 'var(--pz-border-subtle)',
          text: 'var(--pz-text-secondary)',
          glow: 'none',
        };
    }
  };

  const colors = getStatusColor(slot.status);

  const getStatusIcon = () => {
    switch (slot.status) {
      case 'available':
        return <CheckCircle2 size={16} color="var(--pz-success)" />;
      case 'occupied':
        return <Car size={16} color="var(--pz-text-muted)" />;
      case 'reserved':
        return <Car size={16} color="var(--pz-warning)" />;
      case 'maintenance':
        return <Wrench size={16} color="var(--pz-error)" />;
      default:
        return <ShieldAlert size={16} />;
    }
  };

  return (
    <button
      type="button"
      onClick={() => isAvailable && onSelect && onSelect(slot)}
      disabled={disabled || !isAvailable}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '12px 8px',
        borderRadius: '10px',
        backgroundColor: colors.bg,
        border: `1px solid ${colors.border}`,
        boxShadow: colors.glow,
        cursor: isAvailable ? 'pointer' : 'default',
        opacity: isAvailable ? 1 : 0.75,
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        minWidth: '68px',
        minHeight: '74px',
        transform: isSelected ? 'scale(1.05)' : 'none',
      }}
      aria-label={`Slot ${slot.slot_number}, Status: ${slot.status}`}
      className="parking-slot-item"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
        {getStatusIcon()}
        {slot.vehicle_type === 'car' && (
          <span title="EV Equipped" style={{ display: 'inline-flex' }}>
            <Zap size={11} color="var(--pz-secondary)" />
          </span>
        )}
      </div>
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          fontSize: '0.875rem',
          color: colors.text,
          letterSpacing: '0.02em',
        }}
      >
        {slot.slot_number}
      </span>
      <span
        style={{
          fontSize: '0.625rem',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          color: colors.text,
          marginTop: '2px',
        }}
      >
        {slot.status}
      </span>
    </button>
  );
};
