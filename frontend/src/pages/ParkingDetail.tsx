import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { parkingApi } from '../api/parking';
import { reservationsApi } from '../api/reservations';
import { useWebSocket } from '../hooks/useWebSocket';
import { useToast } from '../components/ui/Toast';
import type { Facility, Zone, Slot, Availability } from '../types';
import { SlotGrid } from '../components/parking/SlotGrid';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { FormField } from '../components/ui/FormField';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import {
  MapPin,
  Clock,
  Zap,
  ShieldCheck,
  Layers,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

const generateDefaultSlots = (_facId?: number): Slot[] => {
  const list: Slot[] = [];
  const statuses: Slot['status'][] = ['available', 'occupied', 'available', 'reserved', 'available', 'occupied', 'available', 'maintenance'];
  for (let i = 1; i <= 24; i++) {
    list.push({
      id: i,
      zone_id: 1,
      slot_number: `C-${i < 10 ? '0' + i : i}`,
      status: statuses[(i - 1) % statuses.length],
      vehicle_type: 'car',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }
  return list;
};

const ParkingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const facilityId = Number(id);
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [facility, setFacility] = useState<Facility | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [isReserveModalOpen, setIsReserveModalOpen] = useState(false);
  const [reserveHours, setReserveHours] = useState(2);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Facility-specific WebSocket connection
  const { latestMessage } = useWebSocket('*', facilityId);

  // Fetch facility details, zones, and availability
  useEffect(() => {
    if (!facilityId) return;

    const loadData = async () => {
      try {
        setIsLoading(true);
        const fac = await parkingApi.getFacility(facilityId);
        setFacility(fac);

        try {
          const avail = await parkingApi.getFacilityAvailability(facilityId);
          setAvailability(avail);
        } catch {
          // Fallback
          setAvailability({
            entity_id: facilityId,
            total_slots: fac.total_slots || 60,
            available: Math.round((fac.total_slots || 60) * 0.4),
            occupied: Math.round((fac.total_slots || 60) * 0.5),
            reserved: Math.round((fac.total_slots || 60) * 0.1),
            occupancy_percentage: 60.0,
          });
        }

        const zList = await parkingApi.getZones(facilityId);
        setZones(zList);

        if (zList && zList.length > 0) {
          const firstZone = zList[0];
          setSelectedZone(firstZone);
          const sList = await parkingApi.getSlots(firstZone.id);
          setSlots(sList);
        } else {
          // Generate default slots if zone is empty
          setSlots(generateDefaultSlots(facilityId));
        }
      } catch (err) {
        console.error('Error loading facility details:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [facilityId]);

  // Handle incoming real-time events
  useEffect(() => {
    if (!latestMessage) return;

    if (latestMessage.event === 'slot_status_changed' && latestMessage.slot_id) {
      setSlots((prev) =>
        prev.map((s) =>
          s.id === latestMessage.slot_id ? { ...s, status: latestMessage.new_status } : s
        )
      );
    }

    if (latestMessage.event === 'occupancy_updated' && latestMessage.data) {
      setAvailability((prev) =>
        prev
          ? {
              ...prev,
              available: latestMessage.data.available_slots,
              occupied: latestMessage.data.occupied_slots,
              reserved: latestMessage.data.reserved_slots,
              occupancy_percentage: latestMessage.data.occupancy_percentage,
            }
          : null
      );
    }
  }, [latestMessage]);

  const handleZoneChange = async (zone: Zone) => {
    setSelectedZone(zone);
    try {
      const sList = await parkingApi.getSlots(zone.id);
      setSlots(sList);
    } catch {
      setSlots(generateDefaultSlots(facilityId));
    }
  };

  const handleSlotSelect = (slot: Slot) => {
    if (slot.status === 'available') {
      setSelectedSlot(slot);
      setIsReserveModalOpen(true);
    }
  };

  const handleConfirmReservation = async () => {
    if (!selectedSlot) return;
    setIsSubmitting(true);

    try {
      const now = new Date();
      const end = new Date(now.getTime() + reserveHours * 60 * 60 * 1000);

      await reservationsApi.createReservation({
        slot_id: selectedSlot.id,
        reservation_start: now.toISOString(),
        reservation_end: end.toISOString(),
      });

      success(`Slot ${selectedSlot.slot_number} reserved successfully!`, 'Reservation Confirmed');
      setIsReserveModalOpen(false);

      // Optimistically mark as reserved
      setSlots((prev) =>
        prev.map((s) => (s.id === selectedSlot.id ? { ...s, status: 'reserved' } : s))
      );

      navigate('/reservations');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to complete reservation. Please try again.';
      toastError(msg, 'Reservation Error');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading && !facility) {
    return <LoadingSpinner size="lg" label="Connecting to facility sub-meter telemetry..." />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Breadcrumb Navigation */}
      <Breadcrumb
        items={[
          { label: 'Find Parking', href: '/parking' },
          { label: facility?.name || 'Facility Detail' },
        ]}
      />

      {/* Facility Header Card */}
      <Card glow="cyan">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ✦ SUB-METER AR SENSING HUB
              </span>
              <span className="telemetry-pulse" />
            </div>

            <h1 className="text-page-title" style={{ color: '#FFFFFF' }}>
              {facility?.name || 'Metropolis Central Garage'}
            </h1>

            <p style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
              <MapPin size={16} color="var(--pz-secondary)" />
              {facility?.address} {facility?.city ? `• ${facility.city}` : ''}
            </p>
          </div>

          {/* Rate & Live Availability */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                $3.50
              </span>
              <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)', display: 'block' }}>/ hour</span>
            </div>

            <div style={{ padding: '10px 16px', borderRadius: '12px', backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', textAlign: 'center' }}>
              <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)', display: 'block' }}>
                {availability?.available ?? 18}
              </span>
              <span style={{ fontSize: '0.6875rem', color: 'var(--pz-success)', textTransform: 'uppercase', fontWeight: 600 }}>
                Free Bays
              </span>
            </div>
          </div>
        </div>

        {/* Feature Badges */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '1.5rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '1.25rem' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
            <Clock size={14} color="var(--pz-secondary)" /> 24/7 Monitored Access
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
            <Zap size={14} color="var(--pz-secondary)" /> 350kW DC Ultra-Fast EV Charger
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
            <ShieldCheck size={14} color="var(--pz-success)" /> ALPR Express Automatic Lift
          </span>
        </div>
      </Card>

      {/* Zone Switcher */}
      {zones.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--pz-secondary)" />
          <span style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', fontWeight: 500 }}>Select Deck / Sector:</span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {zones.map((z) => (
              <button
                key={z.id}
                onClick={() => handleZoneChange(z)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  backgroundColor: selectedZone?.id === z.id ? 'var(--pz-primary)' : 'rgba(255, 255, 255, 0.04)',
                  color: '#FFFFFF',
                  border: '1px solid var(--pz-border-subtle)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {z.name} ({z.total_slots || 30} Bays)
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Live Slot Grid Matrix */}
      <SlotGrid
        slots={slots}
        selectedSlot={selectedSlot}
        onSlotSelect={handleSlotSelect}
        zoneName={selectedZone?.name || 'Main Deck'}
      />

      {/* Reservation Confirmation Modal */}
      <Modal
        isOpen={isReserveModalOpen}
        onClose={() => setIsReserveModalOpen(false)}
        title="Reserve Parking Bay"
        description="Lock this space with guaranteed license plate entry sync."
      >
        {selectedSlot && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ padding: '1rem', backgroundColor: 'rgba(26, 91, 255, 0.12)', borderRadius: '12px', border: '1px solid rgba(26, 91, 255, 0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Target Space
                </span>
                <h4 style={{ fontSize: '1.375rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  Slot #{selectedSlot.slot_number}
                </h4>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>Estimated Rate</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', display: 'block', fontFamily: 'var(--font-mono)' }}>
                  ${(3.50 * reserveHours).toFixed(2)}
                </span>
              </div>
            </div>

            <FormField label="Reservation Duration">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                {[1, 2, 4, 8].map((hrs) => (
                  <button
                    key={hrs}
                    type="button"
                    onClick={() => setReserveHours(hrs)}
                    style={{
                      padding: '10px',
                      borderRadius: '8px',
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      backgroundColor: reserveHours === hrs ? 'var(--pz-primary)' : 'rgba(255, 255, 255, 0.04)',
                      color: '#FFFFFF',
                      border: reserveHours === hrs ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
                      cursor: 'pointer',
                    }}
                  >
                    {hrs} {hrs === 1 ? 'hr' : 'hrs'}
                  </button>
                ))}
              </div>
            </FormField>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
              <Sparkles size={14} color="var(--pz-secondary)" />
              <span>ALPR Fast-Pass will automatically lift barrier upon entry.</span>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
              <Button
                variant="outline"
                onClick={() => setIsReserveModalOpen(false)}
                style={{ flex: 1 }}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirmReservation}
                isLoading={isSubmitting}
                style={{ flex: 1 }}
                rightIcon={<ArrowRight size={16} />}
              >
                Confirm Reservation
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ParkingDetail;
