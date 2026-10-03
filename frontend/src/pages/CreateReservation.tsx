import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { parkingApi } from '../api/parking';
import { reservationsApi } from '../api/reservations';
import { sessionsApi } from '../api/sessions';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import type { Facility, Zone, Slot, Reservation } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { StatusBadge } from '../components/ui/StatusBadge';
import {
  Calendar,
  Clock,
  MapPin,
  CheckCircle2,
  ShieldCheck,
  ArrowLeft,
  Car,
  QrCode,
  PlayCircle,
  AlertTriangle,
  Zap,
} from 'lucide-react';

export const CreateReservation: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error: toastError } = useToast();

  const facilityIdParam = searchParams.get('facility_id');
  const slotIdParam = searchParams.get('slot_id');

  // Loaded metadata
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(
    facilityIdParam ? Number(facilityIdParam) : null
  );
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<number | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(
    slotIdParam ? Number(slotIdParam) : null
  );

  const [facility, setFacility] = useState<Facility | null>(null);
  const [slot, setSlot] = useState<Slot | null>(null);

  // Timing State
  const [isImmediate, setIsImmediate] = useState<boolean>(true);
  const [customStart, setCustomStart] = useState<string>('');
  const [durationHours, setDurationHours] = useState<number>(2);

  // Execution States
  const [isLoadingMetadata, setIsLoadingMetadata] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isCheckingIn, setIsCheckingIn] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [createdReservation, setCreatedReservation] = useState<Reservation | null>(null);

  // 1. Initial Load: Facilities and Slot Info
  useEffect(() => {
    let isMounted = true;
    const loadInitial = async () => {
      try {
        setIsLoadingMetadata(true);
        const facList = await parkingApi.getFacilities();
        if (!isMounted) return;
        setFacilities(facList);

        if (facilityIdParam) {
          const fac = await parkingApi.getFacility(Number(facilityIdParam));
          if (!isMounted) return;
          setFacility(fac);
        }

        if (slotIdParam) {
          const s = await parkingApi.getSlot(Number(slotIdParam));
          if (!isMounted) return;
          setSlot(s);
          setSelectedSlotId(s.id);
          setSelectedZoneId(s.zone_id);

          // If facility not explicitly passed, find it from zone
          if (!facilityIdParam) {
            const z = await parkingApi.getZone(s.zone_id);
            if (!isMounted) return;
            const fac = await parkingApi.getFacility(z.facility_id);
            if (!isMounted) return;
            setFacility(fac);
            setSelectedFacilityId(fac.id);
          }
        }
      } catch (err) {
        console.error('Failed to load reservation target metadata:', err);
      } finally {
        if (isMounted) setIsLoadingMetadata(false);
      }
    };

    loadInitial();
    return () => {
      isMounted = false;
    };
  }, [facilityIdParam, slotIdParam]);

  // 2. Zone & Slot Cascading if user changes facility
  useEffect(() => {
    if (!selectedFacilityId) return;
    const fetchZones = async () => {
      try {
        const zList = await parkingApi.getZones(selectedFacilityId);
        setZones(zList);
        if (zList.length > 0 && (!selectedZoneId || !zList.some((z) => z.id === selectedZoneId))) {
          setSelectedZoneId(zList[0].id);
        }
        const fac = await parkingApi.getFacility(selectedFacilityId);
        setFacility(fac);
      } catch (err) {
        console.error('Failed to fetch zones for facility:', err);
      }
    };
    fetchZones();
  }, [selectedFacilityId]);

  useEffect(() => {
    if (!selectedZoneId) return;
    const fetchSlots = async () => {
      try {
        const sList = await parkingApi.getSlots(selectedZoneId);
        setSlots(sList);
        if (selectedSlotId) {
          const current = sList.find((s) => s.id === selectedSlotId);
          if (current) setSlot(current);
        }
      } catch (err) {
        console.error('Failed to fetch slots for zone:', err);
      }
    };
    fetchSlots();
  }, [selectedZoneId, selectedSlotId]);

  // Compute calculated start and end times
  const { startTime, endTime } = useMemo(() => {
    let start: Date;
    if (isImmediate || !customStart) {
      // Start 2 minutes in the future to ensure validity
      start = new Date(Date.now() + 2 * 60 * 1000);
    } else {
      start = new Date(customStart);
    }

    const durationMs = durationHours * 60 * 60 * 1000;
    const end = new Date(start.getTime() + durationMs);

    return { startTime: start, endTime: end };
  }, [isImmediate, customStart, durationHours]);

  // Hourly base rate from facility or system standard $5.00
  const hourlyRate = 5.0;
  const estimatedCost = useMemo(() => {
    return Math.max(2.0, durationHours * hourlyRate);
  }, [durationHours, hourlyRate]);

  // Handle Form Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedSlotId) {
      setErrorMessage('Please select a valid parking slot.');
      return;
    }

    if (endTime <= startTime) {
      setErrorMessage('Reservation end time must be after start time.');
      return;
    }

    if (startTime.getTime() < Date.now() - 60000) {
      setErrorMessage('Reservation start time cannot be in the past.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        slot_id: selectedSlotId,
        reservation_start: startTime.toISOString(),
        reservation_end: endTime.toISOString(),
      };

      const result = await reservationsApi.createReservation(payload);
      setCreatedReservation(result);
      success(
        `Bay #${slot?.slot_number || result.slot_id} reserved successfully!`,
        'Booking Confirmed'
      );
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 409) {
        setErrorMessage(
          detail || 'This slot is already reserved for this time window. Please pick another slot or adjust the hours.'
        );
      } else if (status === 400) {
        setErrorMessage(detail || 'Invalid reservation request. Check the time parameters.');
      } else {
        setErrorMessage('Failed to create reservation. Please check your network and try again.');
      }
      toastError(detail || 'Reservation could not be completed.', 'Hold Failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Immediate Check-in Action from Confirmation Screen
  const handleDirectCheckIn = async () => {
    if (!createdReservation) return;
    setIsCheckingIn(true);
    try {
      await sessionsApi.startSession({
        slot_id: createdReservation.slot_id,
        reservation_id: createdReservation.id,
      });
      success('Vehicle ingress confirmed. Realtime parking session started!', 'Check-In Complete');
      navigate('/sessions');
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Could not initiate session check-in.';
      toastError(detail, 'Check-In Error');
    } finally {
      setIsCheckingIn(false);
    }
  };

  if (isLoadingMetadata) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', padding: '2rem 0' }}>
        <Breadcrumb
          items={[
            { label: 'Parking Facilities', href: '/parking' },
            { label: 'New Reservation' },
          ]}
        />
        <LoadingSpinner size="lg" label="Preparing reservation parameters..." />
      </div>
    );
  }

  // Confirmation Success View
  if (createdReservation) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '640px', margin: '0 auto' }}>
        <Breadcrumb
          items={[
            { label: 'Reservations', href: '/reservations' },
            { label: `Confirmed Pass #${createdReservation.id}` },
          ]}
        />

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
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: 'rgba(0, 230, 153, 0.12)',
              border: '2px solid var(--pz-success)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--pz-success)',
              marginBottom: '1rem',
            }}
          >
            <CheckCircle2 size={36} />
          </div>

          <span
            style={{
              fontSize: '0.6875rem',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--pz-secondary)',
              fontWeight: 700,
            }}
          >
            PARKZENITH FAST-PASS CONFIRMED
          </span>

          <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', marginTop: '6px' }}>
            {facility?.name || 'Metropolis Smart Parking'}
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
            {facility?.address || 'Verified Smart Facility'}
          </p>

          <div style={{ margin: '1rem 0' }}>
            <StatusBadge status="confirmed" type="reservation" size="md" />
          </div>

          {/* QR Code Container */}
          <div
            style={{
              padding: '1.25rem',
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              boxShadow: '0 0 24px rgba(0, 229, 255, 0.25)',
              margin: '0.75rem 0',
            }}
          >
            <QrCode size={160} color="#090B10" />
          </div>

          <span style={{ fontSize: '0.8125rem', fontFamily: 'var(--font-mono)', color: 'var(--pz-text-muted)' }}>
            PERMIT REF: PZ-2026-REV-{createdReservation.id.toString().padStart(4, '0')}
          </span>

          {/* Booking Summary Grid */}
          <div
            style={{
              width: '100%',
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px',
              marginTop: '1.5rem',
              borderTop: '1px dashed var(--pz-border)',
              paddingTop: '1.25rem',
              textAlign: 'left',
            }}
          >
            <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
              <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Reserved Bay</span>
              <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                {slot?.slot_number ? `Bay ${slot.slot_number}` : `Slot #${createdReservation.slot_id}`}
              </span>
            </div>

            <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
              <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Vehicle Plate</span>
              <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                {user?.vehicle_number || 'AUTO-DETECT'}
              </span>
            </div>

            <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
              <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Valid From</span>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
                {new Date(createdReservation.reservation_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
              <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Valid Until</span>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
                {new Date(createdReservation.reservation_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div
            style={{
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              marginTop: '1.75rem',
            }}
          >
            <Button
              variant="primary"
              size="lg"
              leftIcon={<PlayCircle size={18} />}
              onClick={handleDirectCheckIn}
              isLoading={isCheckingIn}
            >
              Check-In &amp; Start Parking Now
            </Button>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <Button
                variant="outline"
                size="md"
                onClick={() => navigate(`/reservations/${createdReservation.id}`)}
              >
                View Full Pass
              </Button>
              <Button
                variant="ghost"
                size="md"
                onClick={() => navigate('/reservations')}
              >
                My Reservations
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // Reservation Creation Form View
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '780px', margin: '0 auto' }}>
      <div>
        <Breadcrumb
          items={[
            { label: 'Parking Facilities', href: '/parking' },
            ...(facility ? [{ label: facility.name, href: `/parking/${facility.id}` }] : []),
            { label: 'Reserve Parking Bay' },
          ]}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '0.75rem' }}>
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowLeft size={16} />}
            onClick={() => (facility ? navigate(`/parking/${facility.id}`) : navigate('/parking'))}
          >
            Back
          </Button>
          <div>
            <h1 className="text-page-title">Reserve Parking Bay</h1>
            <p className="text-body" style={{ marginTop: '2px' }}>
              Confirm your dedicated parking space hold with real-time barrier access.
            </p>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div
          style={{
            padding: '1rem 1.25rem',
            backgroundColor: 'rgba(255, 59, 48, 0.1)',
            border: '1px solid var(--pz-error)',
            borderRadius: '12px',
            color: 'var(--pz-error)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '0.875rem',
          }}
        >
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Selected Bay Information Card */}
        <Card
          glow="cyan"
          style={{
            padding: '1.5rem',
            borderRadius: '18px',
            backgroundColor: 'var(--pz-surface)',
          }}
        >
          <span
            style={{
              fontSize: '0.6875rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--pz-secondary)',
              display: 'block',
              marginBottom: '6px',
            }}
          >
            TARGET PARKING SPACE
          </span>

          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
            <div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#FFFFFF' }}>
                {slot?.slot_number ? `Bay ${slot.slot_number}` : 'Select a Slot'}
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                <MapPin size={14} color="var(--pz-secondary)" />
                {facility?.name || 'Loading facility...'} • {facility?.address || 'Central'}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {slot && (
                <span
                  style={{
                    padding: '4px 10px',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    backgroundColor: 'rgba(0, 229, 255, 0.12)',
                    color: 'var(--pz-secondary)',
                    border: '1px solid rgba(0, 229, 255, 0.3)',
                    textTransform: 'uppercase',
                  }}
                >
                  {slot.vehicle_type}
                </span>
              )}
              <StatusBadge status={slot?.status || 'available'} type="slot" />
            </div>
          </div>

          {/* Slot Picker if not already pre-selected */}
          {(!slotIdParam || !slot) && (
            <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid var(--pz-border-subtle)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-text-muted)', display: 'block', marginBottom: '6px' }}>
                  FACILITY
                </label>
                <select
                  value={selectedFacilityId || ''}
                  onChange={(e) => setSelectedFacilityId(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--pz-bg-alt)',
                    border: '1px solid var(--pz-border)',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    fontSize: '0.875rem',
                  }}
                >
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-text-muted)', display: 'block', marginBottom: '6px' }}>
                  ZONE / DECK
                </label>
                <select
                  value={selectedZoneId || ''}
                  onChange={(e) => setSelectedZoneId(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--pz-bg-alt)',
                    border: '1px solid var(--pz-border)',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    fontSize: '0.875rem',
                  }}
                >
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-text-muted)', display: 'block', marginBottom: '6px' }}>
                  BAY NUMBER
                </label>
                <select
                  value={selectedSlotId || ''}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    setSelectedSlotId(id);
                    const s = slots.find((item) => item.id === id);
                    if (s) setSlot(s);
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--pz-bg-alt)',
                    border: '1px solid var(--pz-border)',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    fontSize: '0.875rem',
                  }}
                >
                  <option value="">Select bay...</option>
                  {slots.map((s) => (
                    <option key={s.id} value={s.id} disabled={s.status !== 'available'}>
                      Slot {s.slot_number} ({s.status})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </Card>

        {/* Schedule & Duration Card */}
        <Card style={{ padding: '1.5rem', borderRadius: '18px' }}>
          <h3 className="text-section-title" style={{ marginBottom: '1.25rem' }}>
            Reservation Schedule
          </h3>

          {/* Start Option Toggles */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '1.25rem' }}>
            <button
              type="button"
              onClick={() => setIsImmediate(true)}
              style={{
                padding: '12px',
                borderRadius: '12px',
                backgroundColor: isImmediate ? 'rgba(0, 229, 255, 0.1)' : 'var(--pz-bg-alt)',
                border: isImmediate ? '2px solid var(--pz-secondary)' : '1px solid var(--pz-border)',
                color: isImmediate ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
                fontWeight: 600,
                fontSize: '0.875rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Zap size={16} />
              Immediate Hold (Next 5 mins)
            </button>

            <button
              type="button"
              onClick={() => setIsImmediate(false)}
              style={{
                padding: '12px',
                borderRadius: '12px',
                backgroundColor: !isImmediate ? 'rgba(0, 229, 255, 0.1)' : 'var(--pz-bg-alt)',
                border: !isImmediate ? '2px solid var(--pz-secondary)' : '1px solid var(--pz-border)',
                color: !isImmediate ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
                fontWeight: 600,
                fontSize: '0.875rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Calendar size={16} />
              Schedule Specific Time
            </button>
          </div>

          {/* Custom Date Time Picker if not immediate */}
          {!isImmediate && (
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--pz-text-muted)', display: 'block', marginBottom: '6px' }}>
                START TIME
              </label>
              <input
                type="datetime-local"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  backgroundColor: 'var(--pz-bg-alt)',
                  border: '1px solid var(--pz-border)',
                  borderRadius: '10px',
                  color: '#FFFFFF',
                  fontSize: '0.875rem',
                }}
                required={!isImmediate}
              />
            </div>
          )}

          {/* Duration Chips */}
          <div>
            <label style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--pz-text-muted)', display: 'block', marginBottom: '8px' }}>
              PARKING DURATION
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))', gap: '8px' }}>
              {[1, 2, 3, 4, 8].map((hours) => (
                <button
                  key={hours}
                  type="button"
                  onClick={() => setDurationHours(hours)}
                  style={{
                    padding: '10px 8px',
                    borderRadius: '10px',
                    backgroundColor: durationHours === hours ? 'rgba(0, 229, 255, 0.15)' : 'var(--pz-bg-alt)',
                    border: durationHours === hours ? '2px solid var(--pz-secondary)' : '1px solid var(--pz-border)',
                    color: durationHours === hours ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
                    fontWeight: 700,
                    fontSize: '0.875rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {hours} {hours === 1 ? 'Hour' : 'Hours'}
                </button>
              ))}
            </div>
          </div>

          {/* Timeline Summary Box */}
          <div
            style={{
              marginTop: '1.25rem',
              padding: '1rem',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              border: '1px dashed var(--pz-border)',
              borderRadius: '12px',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '1rem',
            }}
          >
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>START HOLD</span>
              <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                {startTime.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', color: 'var(--pz-secondary)' }}>
              <Clock size={16} />
              <span style={{ fontSize: '0.8125rem', fontWeight: 700, marginLeft: '4px' }}>
                {durationHours} Hours Hold
              </span>
            </div>

            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>EXPIRES AT</span>
              <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                {endTime.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        </Card>

        {/* Vehicle & Access Security */}
        <Card style={{ padding: '1.5rem', borderRadius: '18px' }}>
          <h3 className="text-section-title" style={{ marginBottom: '1rem' }}>
            Vehicle &amp; Ingress Validation
          </h3>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: 'var(--pz-bg-alt)', borderRadius: '12px', border: '1px solid var(--pz-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Car size={24} color="var(--pz-secondary)" />
              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>REGISTERED VEHICLE PLATE</span>
                <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  {user?.vehicle_number || 'KA-01-MJ-5555'}
                </span>
              </div>
            </div>

            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-success)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldCheck size={14} /> ALPR Ready
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid var(--pz-border-subtle)' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>ESTIMATED PARKING CHARGE</span>
              <span style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                ${estimatedCost.toFixed(2)}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', marginLeft: '6px' }}>
                (${hourlyRate.toFixed(2)}/hr base rate)
              </span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              leftIcon={<CheckCircle2 size={18} />}
              isLoading={isSubmitting}
              disabled={!selectedSlotId}
            >
              Confirm &amp; Reserve Bay
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
};

export default CreateReservation;
