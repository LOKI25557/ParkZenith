import React, { useState } from 'react';
import { Grid, Layers } from 'lucide-react';

export interface ZoneCongestion {
  id: string;
  name: string;
  occupancyPct: number;
  availableBays: number;
  totalBays: number;
  description: string;
}

export interface HeatMapContainerProps {
  zones?: ZoneCongestion[];
  onZoneSelect?: (zone: ZoneCongestion) => void;
}

export const HeatMapContainer: React.FC<HeatMapContainerProps> = ({
  zones = [
    { id: '1', name: 'Zone A (North Deck)', occupancyPct: 45, availableBays: 44, totalBays: 80, description: 'Standard Bays • Low Density' },
    { id: '2', name: 'Zone B (VIP & EV Hub)', occupancyPct: 82, availableBays: 11, totalBays: 60, description: '350kW DC Fast Charge • Active Demand' },
    { id: '3', name: 'Zone C (Direct Concourse)', occupancyPct: 94, availableBays: 3, totalBays: 50, description: 'Sub-30m Elevator Access • Critical Surge' },
    { id: '4', name: 'Zone D (Rooftop Deck)', occupancyPct: 22, availableBays: 78, totalBays: 100, description: 'Overheight / Open Air • Ample Space' },
  ],
  onZoneSelect,
}) => {
  const [selectedZone, setSelectedZone] = useState<string>(zones[0]?.id || '1');

  const getZoneColor = (pct: number) => {
    if (pct < 50) return { border: '#10B981', bg: 'rgba(16, 185, 129, 0.12)', label: 'Low Congestion' };
    if (pct < 85) return { border: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', label: 'Moderate' };
    return { border: '#F43F5E', bg: 'rgba(244, 63, 94, 0.15)', label: 'Critical Capacity' };
  };

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Grid size={18} color="var(--pz-secondary)" />
          <h4 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
            Live Zone Congestion Heat Map
          </h4>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <Layers size={13} /> Multi-deck Spatial Density
        </span>
      </div>

      {/* Interactive 4-Zone Matrix */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '12px',
        }}
      >
        {zones.map((zone) => {
          const isSelected = selectedZone === zone.id;
          const status = getZoneColor(zone.occupancyPct);

          return (
            <div
              key={zone.id}
              onClick={() => {
                setSelectedZone(zone.id);
                if (onZoneSelect) onZoneSelect(zone);
              }}
              style={{
                padding: '1rem',
                borderRadius: '12px',
                backgroundColor: status.bg,
                border: isSelected ? '2px solid var(--pz-secondary)' : `1px solid ${status.border}40`,
                boxShadow: isSelected ? '0 0 16px rgba(0, 229, 255, 0.25)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
                  {zone.name}
                </span>
                <span
                  style={{
                    fontSize: '0.875rem',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                    color: status.border,
                  }}
                >
                  {zone.occupancyPct}%
                </span>
              </div>

              <p style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginBottom: '8px' }}>
                {zone.description}
              </p>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--pz-text-muted)' }}>
                  {zone.availableBays} of {zone.totalBays} open
                </span>
                <span style={{ color: status.border, fontWeight: 500 }}>
                  {status.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
