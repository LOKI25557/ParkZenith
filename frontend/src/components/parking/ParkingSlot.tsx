import React from 'react';
import type { Slot, ParkingSlotStatus, VehicleType } from '../../types';
import { Car, Zap, Wrench, ShieldAlert, CheckCircle2, Bike, Truck } from 'lucide-react';

export interface ParkingSlotProps {
  slot: Slot;
  isSelected?: boolean;
  onSelect?: (slot: Slot) => void;
  disabled?: boolean;
  isRecentlyUpdated?: boolean;
}

export const ParkingSlot: React.FC<ParkingSlotProps> = ({
  slot,
  isSelected = false,
  onSelect,
  disabled = false,
  isRecentlyUpdated = false,
}) => {
  const isAvailable = slot.status === 'available';

  const getStatusColor = (status: ParkingSlotStatus) => {
    switch (status) {
      case 'available':
        return {
          bg: isSelected ? 'rgba(0, 229, 255, 0.18)' : 'rgba(16, 185, 129, 0.12)',
          border: isSelected ? 'var(--pz-secondary)' : 'rgba(16, 185, 129, 0.35)',
          text: isSelected ? 'var(--pz-secondary)' : '#10B981',
          glow: isSelected ? '0 0 16px rgba(0, 229, 255, 0.45)' : 'none',
          statusText: 'FREE',
        };
      case 'occupied':
        return {
          bg: 'rgba(100, 116, 139, 0.08)',
          border: 'rgba(100, 116, 139, 0.25)',
          text: 'var(--pz-text-muted)',
          glow: 'none',
          statusText: 'OCCUPIED',
        };
      case 'reserved':
        return {
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          text: '#F59E0B',
          glow: 'none',
          statusText: 'RESERVED',
        };
      case 'maintenance':
        return {
          bg: 'rgba(244, 63, 94, 0.12)',
          border: 'rgba(244, 63, 94, 0.35)',
          text: '#F43F5E',
          glow: 'none',
          statusText: 'MAINT',
        };
      default:
        return {
          bg: 'rgba(255, 255, 255, 0.04)',
          border: 'var(--pz-border-subtle)',
          text: 'var(--pz-text-secondary)',
          glow: 'none',
          statusText: 'BLOCKED',
        };
    }
  };

  const colors = getStatusColor(slot.status);

  const getVehicleIcon = (type: VehicleType) => {
    switch (type) {
      case 'ev':
        return (
          <span title="EV Charging Bay" style={{ display: 'inline-flex' }}>
            <Zap size={13} color="var(--pz-secondary)" />
          </span>
        );
      case 'bike':
      case 'motorcycle':
      case 'bicycle':
        return (
          <span title="Two-Wheeler Bay" style={{ display: 'inline-flex' }}>
            <Bike size={13} color="var(--pz-accent)" />
          </span>
        );
      case 'truck':
        return (
          <span title="Heavy Vehicle Bay" style={{ display: 'inline-flex' }}>
            <Truck size={13} color="var(--pz-warning)" />
          </span>
        );
      case 'car':
      default:
        return (
          <span title="Standard Vehicle Bay" style={{ display: 'inline-flex' }}>
            <Car size={13} color="currentColor" />
          </span>
        );
    }
  };

  const getStatusIcon = () => {
    switch (slot.status) {
      case 'available':
        return <CheckCircle2 size={14} color={isSelected ? 'var(--pz-secondary)' : 'var(--pz-success)'} />;
      case 'occupied':
        return <Car size={14} color="var(--pz-text-muted)" />;
      case 'reserved':
        return <Car size={14} color="var(--pz-warning)" />;
      case 'maintenance':
        return <Wrench size={14} color="var(--pz-error)" />;
      default:
        return <ShieldAlert size={14} />;
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
        justifyContent: 'space-between',
        padding: '10px 6px',
        borderRadius: '10px',
        backgroundColor: colors.bg,
        border: `1.5px solid ${colors.border}`,
        boxShadow: colors.glow,
        cursor: isAvailable ? 'pointer' : 'not-allowed',
        opacity: isAvailable ? 1 : 0.65,
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        minWidth: '76px',
        minHeight: '82px',
        transform: isSelected ? 'scale(1.05)' : 'none',
        outline: isSelected ? '2px solid var(--pz-secondary)' : 'none',
        outlineOffset: '2px',
      }}
      aria-label={`Slot ${slot.slot_number}, ${slot.vehicle_type}, ${slot.status}${isSelected ? ', selected' : ''}${isRecentlyUpdated ? ', recently updated' : ''}`}
      aria-pressed={isSelected}
      aria-live={isRecentlyUpdated ? 'polite' : 'off'}
      className={`parking-slot-item ${isRecentlyUpdated ? 'slot-recently-updated' : ''}`}
    >
      {/* Top Header Row with Status & Vehicle icons */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '0 2px' }}>
        <span style={{ display: 'inline-flex' }}>{getStatusIcon()}</span>
        <span style={{ display: 'inline-flex' }}>{getVehicleIcon(slot.vehicle_type)}</span>
      </div>

      {/* Center Slot Number */}
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          fontSize: '0.9375rem',
          color: isSelected ? '#FFFFFF' : colors.text,
          letterSpacing: '0.02em',
          marginTop: '2px',
        }}
      >
        {slot.slot_number}
      </span>

      {/* Bottom Status Text Pill */}
      <span
        style={{
          fontSize: '0.5625rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: colors.text,
          backgroundColor: 'rgba(0, 0, 0, 0.25)',
          padding: '2px 5px',
          borderRadius: '4px',
          width: '100%',
          textAlign: 'center',
        }}
      >
        {colors.statusText}
      </span>
    </button>
  );
};
