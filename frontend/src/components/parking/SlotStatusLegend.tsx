import React from 'react';
import { CheckCircle2, Car, Wrench, Zap, Bike, Truck } from 'lucide-react';

export const SlotStatusLegend: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        padding: '0.75rem 1rem',
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        borderRadius: '10px',
        border: '1px solid var(--pz-border-subtle)',
        fontSize: '0.75rem',
      }}
      aria-label="Slot Status and Vehicle Type Legend"
    >
      {/* Status Indicators */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '12px' }}>
        <span style={{ color: 'var(--pz-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Status:
        </span>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--pz-success)' }}>
          <CheckCircle2 size={13} />
          <span>Available (Free)</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--pz-text-muted)' }}>
          <Car size={13} />
          <span>Occupied</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--pz-warning)' }}>
          <Car size={13} color="var(--pz-warning)" />
          <span>Reserved</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--pz-error)' }}>
          <Wrench size={13} />
          <span>Maintenance</span>
        </div>
      </div>

      {/* Vehicle Type Indicators */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '12px', borderLeft: '1px solid var(--pz-border-subtle)', paddingLeft: '12px' }}>
        <span style={{ color: 'var(--pz-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Type:
        </span>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--pz-text-secondary)' }}>
          <Car size={13} />
          <span>Car</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--pz-secondary)' }}>
          <Zap size={13} />
          <span>EV Charging</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--pz-accent)' }}>
          <Bike size={13} />
          <span>Bike / Moto</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--pz-warning)' }}>
          <Truck size={13} />
          <span>Truck / Van</span>
        </div>
      </div>
    </div>
  );
};
