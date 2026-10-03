import React, { useState } from 'react';
import type { Slot } from '../../types';
import { ParkingSlot } from './ParkingSlot';
import { Layers, ShieldCheck, Car, Clock, AlertTriangle } from 'lucide-react';

export interface SlotGridProps {
  slots: Slot[];
  selectedSlot?: Slot | null;
  onSlotSelect?: (slot: Slot) => void;
  zoneName?: string;
}

export const SlotGrid: React.FC<SlotGridProps> = ({
  slots,
  selectedSlot,
  onSlotSelect,
  zoneName = 'Main Deck',
}) => {
  const [filter, setFilter] = useState<'all' | 'available' | 'occupied' | 'reserved'>('all');

  const filteredSlots = slots.filter((s) => {
    if (filter === 'all') return true;
    return s.status === filter;
  });

  const availableCount = slots.filter((s) => s.status === 'available').length;
  const occupiedCount = slots.filter((s) => s.status === 'occupied').length;
  const reservedCount = slots.filter((s) => s.status === 'reserved').length;
  const maintenanceCount = slots.filter((s) => s.status === 'maintenance').length;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        padding: '1.5rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '16px',
        border: '1px solid var(--pz-border-subtle)',
      }}
    >
      {/* Top Header & Telemetry Legend */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          borderBottom: '1px solid var(--pz-border-subtle)',
          paddingBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--pz-secondary)" />
          <h4 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
            {zoneName} Slot Matrix
          </h4>
          <span
            style={{
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: 'rgba(0, 229, 255, 0.12)',
              color: 'var(--pz-secondary)',
              border: '1px solid rgba(0, 229, 255, 0.3)',
            }}
          >
            {slots.length} Total Bays
          </span>
        </div>

        {/* Status Counters */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <button
            onClick={() => setFilter('all')}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              backgroundColor: filter === 'all' ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: filter === 'all' ? '#FFFFFF' : 'var(--pz-text-secondary)',
              border: '1px solid var(--pz-border-subtle)',
            }}
          >
            All ({slots.length})
          </button>
          <button
            onClick={() => setFilter('available')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              backgroundColor: filter === 'available' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
              color: 'var(--pz-success)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
            }}
          >
            <ShieldCheck size={12} /> Free ({availableCount})
          </button>
          <button
            onClick={() => setFilter('occupied')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              backgroundColor: filter === 'occupied' ? 'rgba(100, 116, 139, 0.2)' : 'transparent',
              color: 'var(--pz-text-secondary)',
              border: '1px solid var(--pz-border-subtle)',
            }}
          >
            <Car size={12} /> Occupied ({occupiedCount})
          </button>
          <button
            onClick={() => setFilter('reserved')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              backgroundColor: filter === 'reserved' ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
              color: 'var(--pz-warning)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
            }}
          >
            <Clock size={12} /> Reserved ({reservedCount})
          </button>
          {maintenanceCount > 0 && (
            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                color: 'var(--pz-error)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
              }}
            >
              <AlertTriangle size={12} /> Maint ({maintenanceCount})
            </span>
          )}
        </div>
      </div>

      {/* Grid of Slots */}
      {filteredSlots.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--pz-text-muted)' }}>
          No parking bays match the selected filter.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(76px, 1fr))',
            gap: '10px',
          }}
        >
          {filteredSlots.map((slot) => (
            <ParkingSlot
              key={slot.id}
              slot={slot}
              isSelected={selectedSlot?.id === slot.id}
              onSelect={onSlotSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};
