import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { reservationsApi } from '../api/reservations';
import { sessionsApi } from '../api/sessions';
import { parkingApi } from '../api/parking';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import type { Reservation, Slot, Facility, Zone } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { StatusBadge } from '../components/ui/StatusBadge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import {
  QrCode,
  ShieldCheck,
  ArrowLeft,
  Download,
  PlayCircle,
  XCircle,
  CalendarCheck,
} from 'lucide-react';

const ReservationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error: toastError } = useToast();

  const [reservation, setReservation] = useState<Reservation | null>(null);
  const [slot, setSlot] = useState<Slot | null>(null);
  const [facility, setFacility] = useState<Facility | null>(null);
  const [zone, setZone] = useState<Zone | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCheckingIn, setIsCheckingIn] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const loadDetails = async () => {
      if (!id || isNaN(Number(id))) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const res = await reservationsApi.getReservation(Number(id));
        if (!isMounted) return;
        setReservation(res);

        // Fetch slot details
        try {
          const s = await parkingApi.getSlot(res.slot_id);
          if (!isMounted) return;
          setSlot(s);

          // Fetch zone details
          const z = await parkingApi.getZone(s.zone_id);
          if (!isMounted) return;
          setZone(z);

          // Fetch facility details
          const f = await parkingApi.getFacility(z.facility_id);
          if (!isMounted) return;
          setFacility(f);
        } catch {
          // If detailed hierarchy resolution fails, continue with base reservation info
        }
      } catch (err) {
        console.error('Failed to load reservation pass details:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadDetails();
    return () => {
      isMounted = false;
    };
  }, [id]);

  const handleCheckIn = async () => {
    if (!reservation) return;
    setIsCheckingIn(true);
    try {
      await sessionsApi.startSession({
        slot_id: reservation.slot_id,
        reservation_id: reservation.id,
      });
      success('Vehicle ingress confirmed. Realtime parking session started!', 'Check-In Complete');
      navigate('/sessions');
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to check in to parking session.';
      toastError(detail, 'Check-In Error');
    } finally {
      setIsCheckingIn(false);
    }
  };

  const handleConfirmCancel = async () => {
    if (!reservation) return;
    setIsCancelling(true);
    try {
      const updated = await reservationsApi.cancelReservation(reservation.id);
      setReservation(updated);
      success('Reservation successfully cancelled and slot released.', 'Cancelled');
      setIsCancelDialogOpen(false);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to cancel reservation.';
      toastError(detail, 'Cancellation Error');
    } finally {
      setIsCancelling(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '680px', margin: '0 auto', padding: '2rem 0' }}>
        <Breadcrumb
          items={[
            { label: 'Reservations', href: '/reservations' },
            { label: `Pass #${id}` },
          ]}
        />
        <LoadingSpinner size="lg" label="Retrieving digital parking pass..." />
      </div>
    );
  }

  if (!reservation) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '680px', margin: '0 auto' }}>
        <Breadcrumb
          items={[
            { label: 'Reservations', href: '/reservations' },
            { label: 'Pass Not Found' },
          ]}
        />
        <EmptyState
          icon={<CalendarCheck size={36} />}
          title="Reservation Pass Not Found"
          description={`We could not locate a booking with ID #${id}. It may have expired or been removed.`}
          actionLabel="Return to My Reservations"
          onAction={() => navigate('/reservations')}
        />
      </div>
    );
  }

  const isCancellable = reservation.status === 'confirmed' || reservation.status === 'pending';
  const canCheckIn = reservation.status === 'confirmed' || reservation.status === 'active';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '680px', margin: '0 auto' }}>
      <Breadcrumb
        items={[
          { label: 'Reservations', href: '/reservations' },
          { label: `Pass #${reservation.id}` },
        ]}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={16} />}
          onClick={() => navigate('/reservations')}
        >
          Back to Bookings
        </Button>

        <Button
          variant="outline"
          size="sm"
          leftIcon={<Download size={14} />}
          onClick={() => window.print()}
        >
          Print / Save Pass
        </Button>
      </div>

      {/* Digital Fast-Pass Ticket Card */}
      <Card
        glow="cyan"
        style={{
          padding: '2.5rem 2rem',
          borderRadius: '24px',
          background: 'linear-gradient(180deg, #131722 0%, #0F131E 100%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          position: 'relative',
        }}
      >
        <span
          style={{
            fontSize: '0.6875rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--pz-secondary)',
            fontWeight: 700,
            marginBottom: '4px',
          }}
        >
          PARKZENITH FAST-PASS DIGITAL PERMIT
        </span>

        <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF' }}>
          {facility?.name || 'Metropolis Smart Parking'}
        </h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
          {zone ? `${zone.name} Deck` : 'Smart Deck'} • {facility?.address || 'Secure Ingress Terminal'}
        </p>

        <div style={{ margin: '1.25rem 0' }}>
          <StatusBadge status={reservation.status} type="reservation" size="md" />
        </div>

        {/* QR Code Container */}
        <div
          style={{
            padding: '1.5rem',
            backgroundColor: '#FFFFFF',
            borderRadius: '16px',
            boxShadow: '0 0 24px rgba(0, 229, 255, 0.3)',
            margin: '1rem 0',
          }}
        >
          <QrCode size={180} color="#090B10" />
        </div>

        <span style={{ fontSize: '0.8125rem', fontFamily: 'var(--font-mono)', color: 'var(--pz-text-muted)', letterSpacing: '0.08em' }}>
          PERMIT ID: PZ-2026-REV-{reservation.id.toString().padStart(4, '0')}
        </span>

        {/* Plate & Slot Grid Details */}
        <div
          style={{
            width: '100%',
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '12px',
            marginTop: '2rem',
            borderTop: '1px dashed var(--pz-border)',
            paddingTop: '1.5rem',
            textAlign: 'left',
          }}
        >
          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Reserved Bay</span>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
              {slot?.slot_number ? `Bay ${slot.slot_number}` : `Slot #${reservation.slot_id}`}
            </span>
          </div>

          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Vehicle License Plate</span>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {user?.vehicle_number || 'KA-01-MJ-5555'}
            </span>
          </div>

          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Valid From</span>
            <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
              {new Date(reservation.reservation_start).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>

          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Valid Until</span>
            <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
              {new Date(reservation.reservation_end).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        </div>

        <div
          style={{
            marginTop: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.8125rem',
            color: 'var(--pz-success)',
          }}
        >
          <ShieldCheck size={16} />
          <span>Automatic License Plate (ALPR) Express Ingress Active</span>
        </div>

        {/* Primary Action Buttons */}
        <div style={{ width: '100%', marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {canCheckIn && (
            <Button
              variant="primary"
              size="lg"
              leftIcon={<PlayCircle size={18} />}
              onClick={handleCheckIn}
              isLoading={isCheckingIn}
            >
              Check-In &amp; Start Parking Session
            </Button>
          )}

          {isCancellable && (
            <Button
              variant="ghost"
              size="md"
              leftIcon={<XCircle size={16} />}
              onClick={() => setIsCancelDialogOpen(true)}
              style={{ color: 'var(--pz-error)' }}
            >
              Cancel Reservation
            </Button>
          )}
        </div>
      </Card>

      {/* Cancellation Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={isCancelDialogOpen}
        onClose={() => setIsCancelDialogOpen(false)}
        onConfirm={handleConfirmCancel}
        title="Cancel This Reservation?"
        message="Are you sure you want to release this parking space? Your guaranteed hold will be removed."
        confirmText="Yes, Cancel Hold"
        variant="danger"
        isLoading={isCancelling}
      />
    </div>
  );
};

export default ReservationDetail;
