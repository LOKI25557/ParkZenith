import React from 'react';
import type { Slot, Zone } from '../../types';
import { Button } from '../ui/Button';
import { CheckCircle2, Car, Zap, Bike, Truck, ArrowRight, X } from 'lucide-react';

export interface SlotDetailsPanelProps {
  slot: Slot | null;
  zone?: Zone | null;
  facilityName?: string;
  onClose: () => void;
  onReserve: (slot: Slot) => void;
}

export const SlotDetailsPanel: React.FC<SlotDetailsPanelProps> = ({
  slot,
  zone,
  facilityName,
  onClose,
  onReserve,
}) => {
  if (!slot) return null;

  const isAvailable = slot.status === 'available';

  const getVehicleDisplay = () => {
    switch (slot.vehicle_type) {
      case 'ev':
        return { label: 'Electric Vehicle (EV)', icon: <Zap size={14} color="var(--pz-secondary)" /> };
      case 'bike':
      case 'motorcycle':
      case 'bicycle':
        return { label: 'Motorcycle / Two-Wheeler', icon: <Bike size={14} color="var(--pz-accent)" /> };
      case 'truck':
        return { label: 'Heavy / Oversized Vehicle', icon: <Truck size={14} color="var(--pz-warning)" /> };
      case 'car':
      default:
        return { label: 'Standard Passenger Car', icon: <Car size={14} color="var(--pz-text-secondary)" /> };
    }
  };

  const vehicleInfo = getVehicleDisplay();

  return (
    <div
      style={{
        padding: '1.25rem',
        borderRadius: '14px',
        backgroundColor: 'rgba(26, 91, 255, 0.08)',
        border: '1.5px solid var(--pz-secondary)',
        boxShadow: '0 8px 32px rgba(0, 229, 255, 0.12)',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '1rem',
        animation: 'fadeIn 0.2s ease-out',
      }}
      role="region"
      aria-label="Selected Slot Telemetry"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            width: '54px',
            height: '54px',
            borderRadius: '12px',
            backgroundColor: 'rgba(0, 229, 255, 0.15)',
            border: '1px solid var(--pz-secondary)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span style={{ fontSize: '0.625rem', color: 'var(--pz-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
            BAY
          </span>
          <span style={{ fontSize: '1.125rem', fontWeight: 800, color: '#FFFFFF' }}>
            {slot.slot_number}
          </span>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: isAvailable ? 'var(--pz-success)' : 'var(--pz-text-muted)',
                backgroundColor: isAvailable ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                padding: '2px 8px',
                borderRadius: '9999px',
                border: isAvailable ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--pz-border-subtle)',
              }}
            >
              <CheckCircle2 size={12} />
              {slot.status.toUpperCase()}
            </span>

            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              {vehicleInfo.icon}
              {vehicleInfo.label}
            </span>
          </div>

          <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)', margin: 0 }}>
            {zone?.name ? `Zone: ${zone.name}` : ''}
            {zone?.floor_number !== undefined ? ` • Floor ${zone.floor_number}` : ''}
            {facilityName ? ` • ${facilityName}` : ''}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: '8px',
            borderRadius: '8px',
            backgroundColor: 'transparent',
            border: '1px solid var(--pz-border-subtle)',
            color: 'var(--pz-text-muted)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title="Deselect bay"
          aria-label="Deselect bay"
        >
          <X size={16} />
        </button>

        <Button
          variant="primary"
          size="sm"
          disabled={!isAvailable}
          rightIcon={<ArrowRight size={14} />}
          onClick={() => onReserve(slot)}
        >
          Reserve Bay #{slot.slot_number}
        </Button>
      </div>
    </div>
  );
};
