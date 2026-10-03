import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reservationsApi } from '../api/reservations';
import { sessionsApi } from '../api/sessions';
import { parkingApi } from '../api/parking';
import { useToast } from '../components/ui/Toast';
import type { Reservation, Facility, Slot } from '../types';
import { ReservationCard } from '../components/parking/ReservationCard';
import { Tabs } from '../components/ui/Tabs';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { CalendarCheck, Plus } from 'lucide-react';

const Reservations: React.FC = () => {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [facilitiesMap, setFacilitiesMap] = useState<Record<number, Facility>>({});
  const [slotsMap, setSlotsMap] = useState<Record<number, Slot>>({});
  const [activeTab, setActiveTab] = useState<string>('all');
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  const loadReservations = async () => {
    try {
      setIsLoading(true);
      const data = await reservationsApi.getReservations();
      const list = Array.isArray(data) ? data : [];
      setReservations(list);

      // Load facilities for name resolution
      try {
        const facList = await parkingApi.getFacilities();
        const fMap: Record<number, Facility> = {};
        facList.forEach((f) => {
          fMap[f.id] = f;
        });
        setFacilitiesMap(fMap);

        // Fetch slots referenced in user reservations
        const sMap: Record<number, Slot> = {};
        await Promise.all(
          list.map(async (r) => {
            try {
              if (!sMap[r.slot_id]) {
                const s = await parkingApi.getSlot(r.slot_id);
                sMap[r.slot_id] = s;
              }
            } catch {
              // ignore slot resolution error
            }
          })
        );
        setSlotsMap(sMap);
      } catch {
        // ignore enrichment error
      }
    } catch (err) {
      console.error('Failed to load reservations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReservations();
  }, []);

  const handleConfirmCancel = async () => {
    if (!cancellingId) return;
    setIsCancelling(true);
    try {
      await reservationsApi.cancelReservation(cancellingId);
      success('Reservation cancelled successfully.', 'Cancelled');
      setReservations((prev) =>
        prev.map((r) => (r.id === cancellingId ? { ...r, status: 'cancelled' } : r))
      );
      setCancellingId(null);
    } catch {
      toastError('Failed to cancel reservation.', 'Error');
    } finally {
      setIsCancelling(false);
    }
  };

  const handleCheckIn = async (res: Reservation) => {
    try {
      await sessionsApi.startSession({
        slot_id: res.slot_id,
        reservation_id: res.id,
      });
      success(`Checked in to Slot #${slotsMap[res.slot_id]?.slot_number || res.slot_id}!`, 'Check-In Active');
      navigate('/sessions');
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Could not start parking session.';
      toastError(detail, 'Check-In Failed');
    }
  };

  const filteredReservations = reservations.filter((r) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'active') return r.status === 'confirmed' || r.status === 'pending' || r.status === 'active';
    if (activeTab === 'completed') return r.status === 'completed';
    if (activeTab === 'cancelled') return r.status === 'cancelled';
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <Breadcrumb items={[{ label: 'Reservations' }]} />
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '1rem', marginTop: '0.75rem' }}>
          <div>
            <h1 className="text-page-title">My Reservations</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              Manage your confirmed parking bay holds and digital access passes.
            </p>
          </div>

          <Button
            variant="primary"
            leftIcon={<Plus size={16} />}
            onClick={() => navigate('/reservations/new')}
          >
            New Reservation
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: 'all', label: 'All Bookings', badge: reservations.length },
          { id: 'active', label: 'Upcoming & Active' },
          { id: 'completed', label: 'Completed' },
          { id: 'cancelled', label: 'Cancelled' },
        ]}
      />

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner size="lg" label="Retrieving bookings..." />
      ) : filteredReservations.length === 0 ? (
        <EmptyState
          icon={<CalendarCheck size={32} />}
          title="No Reservations Found"
          description="You don't have any parking space reservations in this category."
          actionLabel="Find &amp; Reserve Parking"
          onAction={() => navigate('/parking')}
        />
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '1.25rem',
          }}
        >
          {filteredReservations.map((res) => {
            const slot = slotsMap[res.slot_id];
            const facilityName =
              (slot?.zone_id && facilitiesMap[1]?.name) ||
              facilitiesMap[1]?.name ||
              'Smart Parking Facility';
            const slotNumber = slot?.slot_number ? slot.slot_number : `#${res.slot_id}`;

            return (
              <ReservationCard
                key={res.id}
                reservation={res}
                facilityName={facilityName}
                slotNumber={slotNumber}
                onCancel={(id) => setCancellingId(id)}
                onViewPass={() => navigate(`/reservations/${res.id}`)}
                onCheckIn={handleCheckIn}
              />
            );
          })}
        </div>
      )}

      {/* Cancellation Dialog */}
      <ConfirmationDialog
        isOpen={cancellingId !== null}
        onClose={() => setCancellingId(null)}
        onConfirm={handleConfirmCancel}
        title="Cancel Reservation?"
        message="Are you sure you want to release this parking bay? Your guaranteed slot hold will be vacated."
        confirmText="Yes, Cancel Hold"
        variant="danger"
        isLoading={isCancelling}
      />
    </div>
  );
};

export default Reservations;

