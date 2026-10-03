import React, { useState, useMemo } from 'react';
import type { Slot } from '../../types';
import { ParkingSlot } from './ParkingSlot';
import { SlotStatusLegend } from './SlotStatusLegend';
import { Layers, ShieldCheck, Car, Clock, Zap, Bike, Filter } from 'lucide-react';

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
  const [statusFilter, setStatusFilter] = useState<'all' | 'available' | 'occupied' | 'reserved'>('all');
  const [vehicleFilter, setVehicleFilter] = useState<string>('all');

  // Real-time authoritative counters from actual slot array
  const availableCount = useMemo(() => slots.filter((s) => s.status === 'available').length, [slots]);
  const occupiedCount = useMemo(() => slots.filter((s) => slots.length > 0 && s.status === 'occupied').length, [slots]);
  const reservedCount = useMemo(() => slots.filter((s) => slots.length > 0 && s.status === 'reserved').length, [slots]);
  const maintenanceCount = useMemo(() => slots.filter((s) => slots.length > 0 && s.status === 'maintenance').length, [slots]);

  const evCount = useMemo(() => slots.filter((s) => s.vehicle_type === 'ev').length, [slots]);
  const bikeCount = useMemo(() => slots.filter((s) => s.vehicle_type === 'bike' || s.vehicle_type === 'motorcycle').length, [slots]);

  const filteredSlots = useMemo(() => {
    return slots.filter((slot) => {
      // Status filter
      if (statusFilter !== 'all' && slot.status !== statusFilter) {
        return false;
      }
      // Vehicle type filter
      if (vehicleFilter !== 'all') {
        if (vehicleFilter === 'bike') {
          if (slot.vehicle_type !== 'bike' && slot.vehicle_type !== 'motorcycle') return false;
        } else if (slot.vehicle_type !== vehicleFilter) {
          return false;
        }
      }
      return true;
    });
  }, [slots, statusFilter, vehicleFilter]);

  const hasActiveFilters = statusFilter !== 'all' || vehicleFilter !== 'all';

  const resetFilters = () => {
    setStatusFilter('all');
    setVehicleFilter('all');
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
        padding: '1.5rem',
        backgroundColor: 'rgba(15, 19, 30, 0.65)',
        borderRadius: '16px',
        border: '1px solid var(--pz-border-subtle)',
      }}
      role="region"
      aria-label={`${zoneName} Slot Matrix`}
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
          <h4 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
            {zoneName} Bay Matrix
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

        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          <button
            type="button"
            onClick={() => setStatusFilter('all')}
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              backgroundColor: statusFilter === 'all' ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: statusFilter === 'all' ? '#FFFFFF' : 'var(--pz-text-secondary)',
              border: '1px solid var(--pz-border-subtle)',
              cursor: 'pointer',
            }}
          >
            All ({slots.length})
          </button>

          <button
            type="button"
            onClick={() => setStatusFilter('available')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              backgroundColor: statusFilter === 'available' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
              color: 'var(--pz-success)',
              border: statusFilter === 'available' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid var(--pz-border-subtle)',
              cursor: 'pointer',
            }}
          >
            <ShieldCheck size={12} /> Free ({availableCount})
          </button>

          <button
            type="button"
            onClick={() => setStatusFilter('occupied')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              backgroundColor: statusFilter === 'occupied' ? 'rgba(100, 116, 139, 0.2)' : 'transparent',
              color: 'var(--pz-text-secondary)',
              border: statusFilter === 'occupied' ? '1px solid rgba(100, 116, 139, 0.4)' : '1px solid var(--pz-border-subtle)',
              cursor: 'pointer',
            }}
          >
            <Car size={12} /> Occupied ({occupiedCount})
          </button>

          <button
            type="button"
            onClick={() => setStatusFilter('reserved')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              backgroundColor: statusFilter === 'reserved' ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
              color: 'var(--pz-warning)',
              border: statusFilter === 'reserved' ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--pz-border-subtle)',
              cursor: 'pointer',
            }}
          >
            <Clock size={12} /> Reserved ({reservedCount})
          </button>

          {maintenanceCount > 0 && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                color: 'var(--pz-error)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
              }}
            >
              Maint ({maintenanceCount})
            </span>
          )}
        </div>
      </div>

      {/* Vehicle Type Filter Bar & Reset */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          fontSize: '0.8125rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Filter size={12} /> Vehicle Type:
          </span>

          <button
            type="button"
            onClick={() => setVehicleFilter('all')}
            style={{
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              backgroundColor: vehicleFilter === 'all' ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
              color: vehicleFilter === 'all' ? '#FFFFFF' : 'var(--pz-text-secondary)',
              border: '1px solid var(--pz-border-subtle)',
              cursor: 'pointer',
            }}
          >
            All Types
          </button>

          <button
            type="button"
            onClick={() => setVehicleFilter('car')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              backgroundColor: vehicleFilter === 'car' ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
              color: vehicleFilter === 'car' ? '#FFFFFF' : 'var(--pz-text-secondary)',
              border: '1px solid var(--pz-border-subtle)',
              cursor: 'pointer',
            }}
          >
            <Car size={12} /> Standard Car
          </button>

          {evCount > 0 && (
            <button
              type="button"
              onClick={() => setVehicleFilter('ev')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                backgroundColor: vehicleFilter === 'ev' ? 'rgba(0, 229, 255, 0.15)' : 'transparent',
                color: vehicleFilter === 'ev' ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
                border: vehicleFilter === 'ev' ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
                cursor: 'pointer',
              }}
            >
              <Zap size={12} /> EV Bays ({evCount})
            </button>
          )}

          {bikeCount > 0 && (
            <button
              type="button"
              onClick={() => setVehicleFilter('bike')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                backgroundColor: vehicleFilter === 'bike' ? 'rgba(217, 70, 239, 0.15)' : 'transparent',
                color: vehicleFilter === 'bike' ? 'var(--pz-accent)' : 'var(--pz-text-secondary)',
                border: vehicleFilter === 'bike' ? '1px solid var(--pz-accent)' : '1px solid var(--pz-border-subtle)',
                cursor: 'pointer',
              }}
            >
              <Bike size={12} /> Two-Wheeler ({bikeCount})
            </button>
          )}
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={resetFilters}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--pz-text-muted)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Reset bay filters
          </button>
        )}
      </div>

      {/* Visual Status Legend */}
      <SlotStatusLegend />

      {/* Aisle Concept Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          padding: '4px 0',
          fontSize: '0.6875rem',
          color: 'var(--pz-text-muted)',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          borderBottom: '1px dashed rgba(255, 255, 255, 0.1)',
        }}
      >
        <span>◀ DRIVEWAY / ENTRY AISLE ▶</span>
      </div>

      {/* Grid of Slots */}
      {filteredSlots.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--pz-text-secondary)' }}>
          <p style={{ margin: 0, fontSize: '0.875rem' }}>
            No parking bays match the selected filters.
          </p>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={resetFilters}
              style={{
                marginTop: '0.5rem',
                padding: '4px 12px',
                borderRadius: '6px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--pz-border-subtle)',
                color: 'var(--pz-secondary)',
                fontSize: '0.75rem',
                cursor: 'pointer',
              }}
            >
              Show all bays ({slots.length})
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(82px, 1fr))',
            gap: '12px',
            padding: '4px',
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
