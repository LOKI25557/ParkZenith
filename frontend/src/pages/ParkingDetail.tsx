import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { parkingApi } from '../api/parking';
import { reservationsApi } from '../api/reservations';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import type { Facility, Zone, Slot, Availability, ParkingSlotStatus } from '../types';
import { SlotGrid } from '../components/parking/SlotGrid';
import { SlotDetailsPanel } from '../components/parking/SlotDetailsPanel';
import { AvailabilityIndicator } from '../components/parking/AvailabilityIndicator';
import { ConnectionStatusBadge } from '../components/parking/ConnectionStatusBadge';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { FormField } from '../components/ui/FormField';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import {
  MapPin,
  Clock,
  ShieldCheck,
  Layers,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  XCircle,
  Copy,
} from 'lucide-react';

export const ParkingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const facilityId = Number(id);
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const { success, error: toastError, info } = useToast();

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
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Facility-specific WebSocket connection with connectionStatus and reconnect helper
  const { latestMessage, connectionStatus, reconnect } = useWebSocket('*', facilityId || undefined);

  // Load facility, zones, and initial availability
  const loadFacilityData = useCallback(async () => {
    if (!facilityId || isNaN(facilityId)) {
      setError('Invalid facility ID specified.');
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Fetch facility details
      const fac = await parkingApi.getFacility(facilityId);
      setFacility(fac);

      // Fetch facility-level availability
      try {
        const avail = await parkingApi.getFacilityAvailability(facilityId);
        setAvailability(avail);
      } catch {
        setAvailability(null);
      }

      // Fetch zones
      try {
        const zList = await parkingApi.getZones(facilityId);
        setZones(zList);

        if (zList && zList.length > 0) {
          const firstZone = zList[0];
          setSelectedZone(firstZone);

          // Fetch slots for first zone
          setSlotsLoading(true);
          try {
            const sList = await parkingApi.getSlots(firstZone.id);
            setSlots(sList);
          } catch {
            setSlots([]);
          } finally {
            setSlotsLoading(false);
          }
        } else {
          setSelectedZone(null);
          setSlots([]);
        }
      } catch {
        setZones([]);
        setSlots([]);
      }
    } catch (err: any) {
      console.error('Error loading facility details:', err);
      if (err.response?.status === 404) {
        setError('The requested parking facility could not be found.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load facility data from network.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [facilityId]);

  useEffect(() => {
    loadFacilityData();
  }, [loadFacilityData]);

  // Handle incoming real-time telemetry events
  useEffect(() => {
    if (!latestMessage) return;

    // 1. Single slot status update event
    if (latestMessage.event === 'slot_status_changed' && latestMessage.slot_id) {
      const slotId = latestMessage.slot_id;
      const newStatus = latestMessage.new_status as ParkingSlotStatus;

      setSlots((prev) =>
        prev.map((s) => (s.id === slotId ? { ...s, status: newStatus } : s))
      );

      // If currently selected slot is changed to non-available by someone else, deselect it
      setSelectedSlot((prev) => {
        if (prev && prev.id === slotId && newStatus !== 'available') {
          info(`Slot #${prev.slot_number} was just occupied or reserved.`, 'Bay Telemetry Updated');
          return null;
        }
        return prev;
      });
    }

    // 2. Occupancy counters updated event
    if (latestMessage.event === 'occupancy_updated' && latestMessage.data) {
      const occData = latestMessage.data;
      setAvailability((prev) => {
        return {
          entity_id: facilityId,
          total_slots: occData.total_slots ?? prev?.total_slots ?? 0,
          available: occData.available_slots,
          occupied: occData.occupied_slots,
          reserved: occData.reserved_slots,
          occupancy_percentage: occData.occupancy_percentage,
        };
      });
    }

    // 3. Full parking snapshot event
    if (latestMessage.event === 'parking_snapshot' && latestMessage.data) {
      const snapData = latestMessage.data;
      setAvailability({
        entity_id: facilityId,
        total_slots: snapData.total_slots,
        available: snapData.available_slots,
        occupied: snapData.occupied_slots,
        reserved: snapData.reserved_slots,
        occupancy_percentage: snapData.occupancy_percentage,
      });

      // Update statuses of existing slots for active zone
      if (snapData.slots && Array.isArray(snapData.slots)) {
        const snapMap = new Map<number, ParkingSlotStatus>(snapData.slots.map((s: any) => [s.id, s.status as ParkingSlotStatus]));
        setSlots((prev) =>
          prev.map((s) => (snapMap.has(s.id) ? { ...s, status: snapMap.get(s.id)! } : s))
        );
      }
    }
  }, [latestMessage, facilityId, info]);

  // Handle deck / zone switching
  const handleZoneChange = async (zone: Zone) => {
    setSelectedZone(zone);
    setSelectedSlot(null); // Reset selection on zone transition
    setSlotsLoading(true);

    try {
      const sList = await parkingApi.getSlots(zone.id);
      setSlots(sList);
    } catch (err) {
      console.error('Failed to load slots for zone:', err);
      setSlots([]);
    } finally {
      setSlotsLoading(false);
    }
  };

  const handleSlotSelect = (slot: Slot) => {
    if (slot.status !== 'available') return;
    setSelectedSlot((prev) => (prev?.id === slot.id ? null : slot));
  };

  const handleInitiateReservation = (slotToReserve: Slot) => {
    if (!isAuthenticated) {
      info('Please sign in to complete a reservation.', 'Authentication Required');
      navigate(`/login?redirect=/parking/${facilityId}`);
      return;
    }
    setSelectedSlot(slotToReserve);
    setIsReserveModalOpen(true);
  };

  const handleConfirmReservation = async () => {
    if (!selectedSlot) return;

    if (!isAuthenticated) {
      navigate(`/login?redirect=/parking/${facilityId}`);
      return;
    }

    setIsSubmitting(true);

    try {
      const now = new Date();
      const end = new Date(now.getTime() + reserveHours * 60 * 60 * 1000);

      await reservationsApi.createReservation({
        slot_id: selectedSlot.id,
        reservation_start: now.toISOString(),
        reservation_end: end.toISOString(),
      });

      success(`Slot #${selectedSlot.slot_number} reserved successfully!`, 'Reservation Confirmed');
      setIsReserveModalOpen(false);

      // Optimistically mark as reserved
      setSlots((prev) =>
        prev.map((s) => (s.id === selectedSlot.id ? { ...s, status: 'reserved' } : s))
      );
      setSelectedSlot(null);

      // Refresh availability
      if (facilityId) {
        try {
          const updatedAvail = await parkingApi.getFacilityAvailability(facilityId);
          setAvailability(updatedAvail);
        } catch {
          // ignore
        }
      }

      navigate('/reservations');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to complete reservation. Please try again.';
      toastError(msg, 'Reservation Error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyAddressToClipboard = () => {
    if (!facility) return;
    const fullAddress = `${facility.address}${facility.city ? `, ${facility.city}` : ''}${facility.state ? ` ${facility.state}` : ''}`;
    navigator.clipboard?.writeText(fullAddress);
    info('Facility address copied to clipboard.', 'Address Copied');
  };

  if (isLoading) {
    return (
      <div style={{ padding: '3rem 0' }}>
        <LoadingSpinner size="lg" label="Connecting to facility telemetry sensors..." />
      </div>
    );
  }

  if (error || !facility) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <Breadcrumb
          items={[
            { label: 'Find Parking', href: '/parking' },
            { label: 'Facility Detail' },
          ]}
        />
        <ErrorState
          title="Facility Unavailable"
          message={error || "We couldn't retrieve information for this parking garage."}
          onRetry={loadFacilityData}
        />
        <div style={{ textAlign: 'center' }}>
          <Button
            variant="outline"
            leftIcon={<ArrowLeft size={16} />}
            onClick={() => navigate('/parking')}
          >
            Back to Parking Discovery
          </Button>
        </div>
      </div>
    );
  }

  const isOpen = facility.is_active;
  const operatingHours = facility.operating_start_time && facility.operating_end_time
    ? `${facility.operating_start_time} - ${facility.operating_end_time}`
    : 'Open 24/7';

  // Availability object fallback using real loaded slots if availability endpoint was empty
  const activeAvailability: Availability = availability || {
    entity_id: facility.id,
    total_slots: facility.total_slots || slots.length,
    available: slots.filter((s) => s.status === 'available').length,
    occupied: slots.filter((s) => s.status === 'occupied').length,
    reserved: slots.filter((s) => s.status === 'reserved').length,
    occupancy_percentage:
      slots.length > 0
        ? Math.round((slots.filter((s) => s.status === 'occupied').length / slots.length) * 100)
        : 0,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Breadcrumb Navigation & Top Actions */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <Breadcrumb
          items={[
            { label: 'Find Parking', href: '/parking' },
            { label: facility.name },
          ]}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ConnectionStatusBadge
            status={connectionStatus}
            onReconnect={reconnect}
            showStaleNotice={false}
          />

          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowLeft size={14} />}
            onClick={() => navigate('/parking')}
          >
            Back to Facilities
          </Button>
        </div>
      </div>

      {/* Facility Header Card */}
      <Card glow="cyan">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1.5rem' }}>
          <div style={{ flex: 1, minWidth: '280px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: isOpen ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                  color: isOpen ? 'var(--pz-success)' : 'var(--pz-error)',
                  border: `1px solid ${isOpen ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                }}
              >
                {isOpen ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                {isOpen ? 'OPERATIONAL' : 'INACTIVE'}
              </span>

              <span style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                ID #{facility.id}
              </span>
            </div>

            <h1 className="text-page-title" style={{ color: '#FFFFFF', marginBottom: '8px' }}>
              {facility.name}
            </h1>

            {facility.description && (
              <p style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', marginBottom: '10px', lineHeight: 1.5 }}>
                {facility.description}
              </p>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}>
                <MapPin size={15} color="var(--pz-secondary)" />
                {facility.address}
                {facility.city ? `, ${facility.city}` : ''}
                {facility.state ? ` ${facility.state}` : ''}
                {facility.postal_code ? ` ${facility.postal_code}` : ''}
              </p>

              <button
                type="button"
                onClick={copyAddressToClipboard}
                title="Copy address"
                aria-label="Copy address"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--pz-text-muted)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px',
                }}
              >
                <Copy size={13} />
              </button>
            </div>
          </div>

          {/* Operating hours & specs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-end', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={14} color="var(--pz-secondary)" /> Hours: {operatingHours}
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} color="var(--pz-success)" /> Telemetry Monitored
            </span>
          </div>
        </div>
      </Card>

      {/* Live Availability Telemetry Summary */}
      <AvailabilityIndicator
        availability={activeAvailability}
        facilityName={facility.name}
        zoneName={selectedZone?.name}
        connectionStatus={connectionStatus}
        onReconnect={reconnect}
      />

      {/* Zone Switcher */}
      {zones.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--pz-secondary)" />
            <span style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', fontWeight: 600 }}>
              Select Deck / Zone:
            </span>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {zones.map((z) => {
              const isSelected = selectedZone?.id === z.id;
              return (
                <button
                  key={z.id}
                  type="button"
                  onClick={() => handleZoneChange(z)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '10px',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    backgroundColor: isSelected ? 'var(--pz-primary)' : 'rgba(255, 255, 255, 0.04)',
                    color: '#FFFFFF',
                    border: isSelected ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  aria-pressed={isSelected}
                >
                  {z.name}
                  {z.floor_number !== undefined ? ` (Fl. ${z.floor_number})` : ''}
                  {z.total_slots ? ` • ${z.total_slots} Bays` : ''}
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div
          style={{
            padding: '1rem',
            borderRadius: '12px',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--pz-border-subtle)',
            color: 'var(--pz-text-secondary)',
            fontSize: '0.875rem',
          }}
        >
          No individual deck zones configured for this facility.
        </div>
      )}

      {/* Selected Slot Details Panel */}
      {selectedSlot && (
        <SlotDetailsPanel
          slot={selectedSlot}
          zone={selectedZone}
          facilityName={facility.name}
          onClose={() => setSelectedSlot(null)}
          onReserve={handleInitiateReservation}
        />
      )}

      {/* Live Slot Grid Matrix */}
      {slotsLoading ? (
        <div style={{ padding: '2rem 0' }}>
          <LoadingSpinner size="md" label="Loading bay telemetry for selected zone..." />
        </div>
      ) : slots.length === 0 ? (
        <EmptyState
          icon={<Layers size={28} />}
          title="No Bays Configured"
          description={
            selectedZone
              ? `No parking bays are registered in "${selectedZone.name}" yet.`
              : "No parking bays are currently mapped for this facility in the database."
          }
        />
      ) : (
        <SlotGrid
          slots={slots}
          selectedSlot={selectedSlot}
          onSlotSelect={handleSlotSelect}
          zoneName={selectedZone?.name || facility.name}
        />
      )}

      {/* Reservation Confirmation Modal */}
      <Modal
        isOpen={isReserveModalOpen}
        onClose={() => setIsReserveModalOpen(false)}
        title="Reserve Parking Bay"
        description="Select duration and confirm your reservation."
      >
        {selectedSlot && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div
              style={{
                padding: '1rem',
                backgroundColor: 'rgba(26, 91, 255, 0.12)',
                borderRadius: '12px',
                border: '1px solid rgba(26, 91, 255, 0.3)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Target Space
                </span>
                <h4 style={{ fontSize: '1.375rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  Slot #{selectedSlot.slot_number}
                </h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', textTransform: 'capitalize' }}>
                  Type: {selectedSlot.vehicle_type}
                </span>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>Status</span>
                <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--pz-success)', display: 'block' }}>
                  Available
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
              <span>Slot will be locked for user: <strong>{user?.email || 'Active Account'}</strong></span>
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
