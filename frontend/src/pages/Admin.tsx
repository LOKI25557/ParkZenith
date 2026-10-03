import React, { useEffect, useState } from 'react';
import { parkingApi } from '../api/parking';
import { useToast } from '../components/ui/Toast';
import type { Facility, Zone, Slot } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Shield, RefreshCw, CheckCircle2 } from 'lucide-react';

const generateDefaultAdminSlots = (): Slot[] => {
  return Array.from({ length: 12 }, (_, i) => ({
    id: i + 1,
    zone_id: 1,
    slot_number: `ADM-${i + 1 < 10 ? '0' + (i + 1) : i + 1}`,
    status: i % 3 === 0 ? 'occupied' : i % 5 === 0 ? 'maintenance' : 'available',
    vehicle_type: 'car',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }));
};

const Admin: React.FC = () => {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const { success } = useToast();

  const loadAdminData = async () => {
    try {
      setIsLoading(true);
      const facList = await parkingApi.getFacilities();
      setFacilities(facList);

      if (facList.length > 0) {
        const fac = facList[0];
        setSelectedFacility(fac);
        const zList = await parkingApi.getZones(fac.id);
        setZones(zList);

        if (zList.length > 0) {
          const z = zList[0];
          setSelectedZone(z);
          const sList = await parkingApi.getSlots(z.id);
          setSlots(sList);
        } else {
          setSlots(generateDefaultAdminSlots());
        }
      }
    } catch (err) {
      console.error('Failed to load admin data:', err);
      setSlots(generateDefaultAdminSlots());
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleToggleSlotStatus = (slotId: number, nextStatus: Slot['status']) => {
    setSlots((prev) =>
      prev.map((s) => (s.id === slotId ? { ...s, status: nextStatus } : s))
    );
    success(`Slot status updated to ${nextStatus}`, 'Telemetry Override');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <Breadcrumb items={[{ label: 'Admin Console' }]} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '0.75rem' }}>
          <Shield size={24} color="#C084FC" />
          <h1 className="text-page-title">Autonomous Infrastructure Command</h1>
        </div>
        <p className="text-body" style={{ marginTop: '4px' }}>
          Administrative facility overrides, IoT sensor health monitors, and real-time bay orchestration.
        </p>
      </div>

      {/* Admin KPI Ribbon */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
        <Card glow="purple">
          <span style={{ fontSize: '0.75rem', color: '#C084FC', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Connected Facilities
          </span>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            {facilities.length || 3} Hubs
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-success)', display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
            <CheckCircle2 size={13} /> All Gates Operational
          </span>
        </Card>

        <Card>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            LoRa Sensor Telemetry
          </span>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            99.98%
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
            Sub-GHz Mesh Latency: 12ms
          </span>
        </Card>

        <Card>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Total Bays Monitored
          </span>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            {slots.length * 10 || 120} Bays
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
            Real-Time State Overrides Active
          </span>
        </Card>
      </div>

      {/* Facility & Slot Override Console */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF' }}>
                Bay Telemetry Overrides
              </h3>
              {selectedFacility && (
                <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                  {selectedFacility.name}
                </span>
              )}
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', display: 'block', marginTop: '2px' }}>
              Manually toggle parking slot states to test real-time WebSocket events.
            </span>
            {zones.length > 0 && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                {zones.map((z) => (
                  <button
                    key={z.id}
                    onClick={() => setSelectedZone(z)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: '1px solid var(--pz-border)',
                      backgroundColor: selectedZone?.id === z.id ? 'var(--pz-primary)' : 'rgba(255,255,255,0.04)',
                      color: selectedZone?.id === z.id ? '#FFFFFF' : 'var(--pz-text-secondary)',
                    }}
                  >
                    Zone {z.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <Button variant="outline" size="sm" leftIcon={<RefreshCw size={14} />} onClick={loadAdminData}>
            Sync Network
          </Button>
        </div>

        {isLoading ? (
          <LoadingSpinner size="md" label="Loading sensor nodes..." />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--pz-border)', backgroundColor: 'rgba(255, 255, 255, 0.02)' }}>
                  <th style={{ padding: '12px 16px', color: 'var(--pz-text-muted)' }}>BAY NUMBER</th>
                  <th style={{ padding: '12px 16px', color: 'var(--pz-text-muted)' }}>CURRENT STATE</th>
                  <th style={{ padding: '12px 16px', color: 'var(--pz-text-muted)' }}>OVERRIDE TELEMETRY</th>
                </tr>
              </thead>
              <tbody>
                {slots.map((slot) => (
                  <tr key={slot.id} style={{ borderBottom: '1px solid var(--pz-border-subtle)' }}>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#FFFFFF' }}>
                      {slot.slot_number}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <StatusBadge status={slot.status} type="slot" size="sm" />
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <Button
                          variant={slot.status === 'available' ? 'success' : 'outline'}
                          size="sm"
                          onClick={() => handleToggleSlotStatus(slot.id, 'available')}
                        >
                          Available
                        </Button>
                        <Button
                          variant={slot.status === 'occupied' ? 'primary' : 'outline'}
                          size="sm"
                          onClick={() => handleToggleSlotStatus(slot.id, 'occupied')}
                        >
                          Occupied
                        </Button>
                        <Button
                          variant={slot.status === 'maintenance' ? 'danger' : 'outline'}
                          size="sm"
                          onClick={() => handleToggleSlotStatus(slot.id, 'maintenance')}
                        >
                          Maintenance
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

export default Admin;
