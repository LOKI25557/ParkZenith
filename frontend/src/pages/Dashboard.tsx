import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import { parkingApi } from '../api/parking';
import { sessionsApi } from '../api/sessions';
import { reservationsApi } from '../api/reservations';
import { paymentsApi } from '../api/payments';
import { aiApi } from '../api/ai';
import { useWebSocket } from '../hooks/useWebSocket';
import type {
  Facility,
  Availability,
  ParkingSession,
  Reservation,
  Slot,
  Zone,
  Payment,
  ParkingSlotStatus,
  AvailabilityPrediction,
} from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { StatusBadge } from '../components/ui/StatusBadge';
import { SlotGrid } from '../components/parking/SlotGrid';
import { ReservationCard } from '../components/parking/ReservationCard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { ConnectionStatusBadge } from '../components/parking/ConnectionStatusBadge';
import { LiveDataTimestamp } from '../components/parking/LiveDataTimestamp';
import { NavigationButton } from '../components/maps/NavigationButton';
import {
  CalendarCheck,
  Brain,
  Search,
  ArrowRight,
  Activity,
  Map as MapIcon,
  Car,
  Clock,
  CreditCard,
  User as UserIcon,
  ShieldCheck,
  StopCircle,
  PlayCircle,
  Compass,
  CheckCircle2,
} from 'lucide-react';

interface DerivedActivity {
  id: string;
  type: 'reservation' | 'session' | 'payment';
  title: string;
  description: string;
  timestamp: string;
  statusColor: string;
}

function formatRelativeTime(dateString?: string | null): string {
  if (!dateString) return 'Recent';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Recent';
    const now = Date.now();
    const diffSec = Math.floor((now - date.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}h ago`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay === 1) return 'Yesterday';
    if (diffDay < 7) return `${diffDay}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return 'Recent';
  }
}

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  // Core Data Collections
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [facilityAvailMap, setFacilityAvailMap] = useState<Record<number, Availability>>({});
  const [facilitySlots, setFacilitySlots] = useState<Slot[]>([]);
  const [slotsMap, setSlotsMap] = useState<Record<number, Slot>>({});
  const [slotToFacilityMap, setSlotToFacilityMap] = useState<Record<number, Facility>>({});

  // User State
  const [activeSession, setActiveSession] = useState<ParkingSession | null>(null);
  const [activeSlot, setActiveSlot] = useState<Slot | null>(null);
  const [activeZone, setActiveZone] = useState<Zone | null>(null);
  const [activeFacility, setActiveFacility] = useState<Facility | null>(null);
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);

  // AI & Telemetry
  const [aiDecision, setAiDecision] = useState<AvailabilityPrediction | null>(null);
  const [isAiLoading, setIsAiLoading] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [recentlyUpdatedSlotIds, setRecentlyUpdatedSlotIds] = useState<Set<number>>(new Set());

  // Dialog & Action States
  const [isEndSessionDialogOpen, setIsEndSessionDialogOpen] = useState<boolean>(false);
  const [isEndingSession, setIsEndingSession] = useState<boolean>(false);
  const [cancellingReservationId, setCancellingReservationId] = useState<number | null>(null);
  const [isCancellingReservation, setIsCancellingReservation] = useState<boolean>(false);

  // Live timer tick for active session
  const [currentTime, setCurrentTime] = useState<number>(() => Date.now());

  // Real-time WebSocket hook subscribed to selected facility events
  const { latestMessage, connectionStatus, isStale, lastMessageAt, reconnect } =
    useWebSocket('*', selectedFacility?.id);

  // Active session live timer
  useEffect(() => {
    if (!activeSession) return;
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [activeSession]);

  // Compute live duration and estimated fee for active session
  const { formattedDuration, estimatedFee } = useMemo(() => {
    if (!activeSession) {
      return { elapsedSeconds: 0, formattedDuration: '0m 0s', estimatedFee: 2.0 };
    }

    const checkIn = new Date(activeSession.check_in_time).getTime();
    const diffSec = Math.max(0, Math.floor((currentTime - checkIn) / 1000));

    const hours = Math.floor(diffSec / 3600);
    const minutes = Math.floor((diffSec % 3600) / 60);
    const seconds = diffSec % 60;

    const durationStr = hours > 0 ? `${hours}h ${minutes}m ${seconds}s` : `${minutes}m ${seconds}s`;

    // Standard PaymentService formula:
    // durationMinutes = Math.ceil(diffSec / 60)
    // fee = max(2.00, (durationMinutes / 60.0) * 5.0)
    const durationMinutes = Math.max(1, Math.ceil(diffSec / 60));
    const fee = Math.max(2.0, (durationMinutes / 60.0) * 5.0);

    return {
      elapsedSeconds: diffSec,
      formattedDuration: durationStr,
      estimatedFee: fee,
    };
  }, [activeSession, currentTime]);

  // Handle facility selection for the live visualizer
  const handleSelectFacility = useCallback(async (fac: Facility) => {
    setSelectedFacility(fac);

    try {
      const avail = await parkingApi.getFacilityAvailability(fac.id);
      setAvailability(avail);
    } catch {
      setAvailability(null);
    }

    try {
      const zones = await parkingApi.getZones(fac.id);
      if (zones && zones.length > 0) {
        const slots = await parkingApi.getSlots(zones[0].id);
        setFacilitySlots(slots);
      } else {
        setFacilitySlots([]);
      }
    } catch {
      setFacilitySlots([]);
    }

    setIsAiLoading(true);
    try {
      const pred = await aiApi.getPrediction(fac.id);
      setAiDecision(pred);
    } catch {
      setAiDecision(null);
    } finally {
      setIsAiLoading(false);
    }
  }, []);

  // Fetch initial dashboard data across all domains
  const loadDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);

      // 1. Load Facilities
      let facs: Facility[] = [];
      const fMap: Record<number, Facility> = {};
      try {
        facs = await parkingApi.getFacilities();
        setFacilities(facs);
        facs.forEach((f) => {
          fMap[f.id] = f;
        });
      } catch (err) {
        console.error('Failed to load facilities:', err);
      }

      // Initial Selected Facility
      if (facs.length > 0) {
        const firstFac = facs[0];
        setSelectedFacility(firstFac);

        // Fetch Availability for the first facility
        try {
          const avail = await parkingApi.getFacilityAvailability(firstFac.id);
          setAvailability(avail);
        } catch {
          setAvailability(null);
        }

        // Fetch Availability for top 4 facilities
        const availMap: Record<number, Availability> = {};
        await Promise.all(
          facs.slice(0, 4).map(async (f) => {
            try {
              const a = await parkingApi.getFacilityAvailability(f.id);
              availMap[f.id] = a;
            } catch {
              // ignore
            }
          })
        );
        setFacilityAvailMap(availMap);

        // Fetch Zones & Slots for the monitored garage
        try {
          const zones = await parkingApi.getZones(firstFac.id);
          if (zones && zones.length > 0) {
            const slots = await parkingApi.getSlots(zones[0].id);
            setFacilitySlots(slots);
          } else {
            setFacilitySlots([]);
          }
        } catch {
          setFacilitySlots([]);
        }

        // Fetch AI Prediction for the monitored garage
        try {
          const pred = await aiApi.getPrediction(firstFac.id);
          setAiDecision(pred);
        } catch {
          setAiDecision(null);
        }
      }

      // 2. Load User Sessions (Active and Past History)
      let sessionList: ParkingSession[] = [];
      try {
        const [sessList, active] = await Promise.all([
          sessionsApi.getSessions().catch(() => []),
          sessionsApi.getActiveSession().catch(() => null),
        ]);
        sessionList = Array.isArray(sessList) ? sessList : [];
        setSessions(sessionList);

        const currentActive = active || sessionList.find((s) => s.status === 'active') || null;
        setActiveSession(currentActive);

        // Resolve active session slot and zone
        if (currentActive) {
          try {
            const slot = await parkingApi.getSlot(currentActive.slot_id);
            setActiveSlot(slot);
            if (slot) {
              const zone = await parkingApi.getZone(slot.zone_id).catch(() => null);
              setActiveZone(zone);
              if (zone) {
                const fac = await parkingApi.getFacility(zone.facility_id).catch(() => null);
                if (fac) setActiveFacility(fac);
              }
            }
          } catch {
            // ignore slot resolution error
          }
        } else {
          setActiveSlot(null);
          setActiveZone(null);
          setActiveFacility(null);
        }
      } catch (err) {
        console.error('Failed to load user sessions:', err);
      }

      // 3. Load User Reservations & Enrich Slots and Facilities
      try {
        const resList = await reservationsApi.getReservations().catch(() => []);
        const validReservations = Array.isArray(resList) ? resList : [];
        setReservations(validReservations);

        // Cache slots and facility associations referenced in reservations and sessions
        const sMap: Record<number, Slot> = {};
        const sToFMap: Record<number, Facility> = {};

        const allSlotIds = new Set<number>();
        validReservations.forEach((r) => allSlotIds.add(r.slot_id));
        sessionList.forEach((s) => allSlotIds.add(s.slot_id));

        await Promise.all(
          Array.from(allSlotIds).map(async (slotId) => {
            try {
              const s = await parkingApi.getSlot(slotId);
              sMap[slotId] = s;
              const z = await parkingApi.getZone(s.zone_id).catch(() => null);
              if (z) {
                const fac = fMap[z.facility_id] || (await parkingApi.getFacility(z.facility_id).catch(() => null));
                if (fac) {
                  sToFMap[slotId] = fac;
                }
              }
            } catch {
              // ignore
            }
          })
        );
        setSlotsMap((prev) => ({ ...prev, ...sMap }));
        setSlotToFacilityMap((prev) => ({ ...prev, ...sToFMap }));
      } catch (err) {
        console.error('Failed to load reservations:', err);
      }

      // 4. Load User Payments
      try {
        const payList = await paymentsApi.getMyPayments().catch(() => []);
        setPayments(Array.isArray(payList) ? payList : []);
      } catch (err) {
        console.error('Failed to load payments:', err);
      }
    } catch (err) {
      console.error('Unexpected dashboard load failure:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Real-time WebSocket synchronization
  useEffect(() => {
    if (!latestMessage) return;

    if (latestMessage.event === 'slot_status_changed' && latestMessage.slot_id) {
      const slotId = latestMessage.slot_id;
      const newStatus = latestMessage.new_status as ParkingSlotStatus;
      const oldStatus = latestMessage.old_status as ParkingSlotStatus;

      setRecentlyUpdatedSlotIds((prev) => {
        const next = new Set(prev);
        next.add(slotId);
        return next;
      });

      setTimeout(() => {
        setRecentlyUpdatedSlotIds((prev) => {
          const next = new Set(prev);
          next.delete(slotId);
          return next;
        });
      }, 1600);

      setFacilitySlots((prev) =>
        prev.map((s) => (s.id === slotId ? { ...s, status: newStatus } : s))
      );

      if (oldStatus !== newStatus) {
        setAvailability((prev) => {
          if (!prev) return prev;
          let avail = prev.available;
          let occ = prev.occupied;
          let res = prev.reserved;

          if (oldStatus === 'available') avail = Math.max(0, avail - 1);
          else if (oldStatus === 'occupied') occ = Math.max(0, occ - 1);
          else if (oldStatus === 'reserved') res = Math.max(0, res - 1);

          if (newStatus === 'available') avail += 1;
          else if (newStatus === 'occupied') occ += 1;
          else if (newStatus === 'reserved') res += 1;

          const total = prev.total_slots || (avail + occ + res);
          const pct = total > 0 ? Math.round(((total - avail) / total) * 100) : prev.occupancy_percentage;

          return {
            ...prev,
            available: avail,
            occupied: occ,
            reserved: res,
            occupancy_percentage: pct,
          };
        });
      }
    }

    if (latestMessage.event === 'occupancy_updated' && latestMessage.data) {
      const occ = latestMessage.data;
      const updatedAvail: Availability = {
        entity_id: selectedFacility?.id || 0,
        total_slots: occ.total_slots || 0,
        available: occ.available_slots,
        occupied: occ.occupied_slots,
        reserved: occ.reserved_slots,
        occupancy_percentage: occ.occupancy_percentage,
      };

      setAvailability(updatedAvail);

      if (selectedFacility?.id) {
        setFacilityAvailMap((prev) => ({
          ...prev,
          [selectedFacility.id]: updatedAvail,
        }));
      }
    }

    if (latestMessage.event === 'parking_snapshot' && latestMessage.data) {
      const snap = latestMessage.data;
      const snapshotAvail: Availability = {
        entity_id: selectedFacility?.id || 0,
        total_slots: snap.total_slots,
        available: snap.available_slots,
        occupied: snap.occupied_slots,
        reserved: snap.reserved_slots,
        occupancy_percentage: snap.occupancy_percentage,
      };

      setAvailability(snapshotAvail);

      if (selectedFacility?.id) {
        setFacilityAvailMap((prev) => ({
          ...prev,
          [selectedFacility.id]: snapshotAvail,
        }));
      }

      if (snap.slots && Array.isArray(snap.slots)) {
        const snapMap = new Map<number, ParkingSlotStatus>(
          snap.slots.map((s: { id: number; status: string }) => [s.id, s.status as ParkingSlotStatus])
        );
        setFacilitySlots((prev) =>
          prev.map((s) => (snapMap.has(s.id) ? { ...s, status: snapMap.get(s.id)! } : s))
        );
      }
    }
  }, [latestMessage, selectedFacility]);

  // End Session Action
  const handleEndSession = async () => {
    if (!activeSession) return;
    setIsEndingSession(true);
    try {
      const completed = await sessionsApi.endSession(activeSession.id);
      success(
        `Session #${completed.id} ended. Accrued fee: $${completed.fee_amount?.toFixed(2) || estimatedFee.toFixed(2)}. Ingress barrier disengaged.`,
        'Session Completed'
      );
      setActiveSession(null);
      setIsEndSessionDialogOpen(false);
      loadDashboardData();
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      const msg = errorObj.response?.data?.detail || 'Could not end parking session. Please retry.';
      toastError(msg, 'Session Error');
    } finally {
      setIsEndingSession(false);
    }
  };

  // Check In to an Upcoming Reservation
  const handleCheckInReservation = async (res: Reservation) => {
    try {
      await sessionsApi.startSession({
        slot_id: res.slot_id,
        reservation_id: res.id,
      });
      success(`Checked in to Slot #${slotsMap[res.slot_id]?.slot_number || res.slot_id}!`, 'Check-In Active');
      loadDashboardData();
      navigate('/sessions');
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      const msg = errorObj.response?.data?.detail || 'Could not start parking session.';
      toastError(msg, 'Check-In Failed');
    }
  };

  // Cancel Reservation Action
  const handleConfirmCancelReservation = async () => {
    if (!cancellingReservationId) return;
    setIsCancellingReservation(true);
    try {
      await reservationsApi.cancelReservation(cancellingReservationId);
      success('Reservation cancelled successfully.', 'Booking Cancelled');
      setReservations((prev) =>
        prev.map((r) => (r.id === cancellingReservationId ? { ...r, status: 'cancelled' } : r))
      );
      setCancellingReservationId(null);
    } catch {
      toastError('Failed to cancel reservation.', 'Action Failed');
    } finally {
      setIsCancellingReservation(false);
    }
  };

  // Filter Upcoming Active Reservations
  const upcomingReservations = useMemo(() => {
    return reservations
      .filter((r) => r.status === 'confirmed' || r.status === 'pending')
      .sort((a, b) => new Date(a.reservation_start).getTime() - new Date(b.reservation_start).getTime());
  }, [reservations]);

  const nextUpcomingReservation = upcomingReservations.length > 0 ? upcomingReservations[0] : null;

  // Recent Completed Sessions (History)
  const recentCompletedSessions = useMemo(() => {
    return sessions
      .filter((s) => s.status === 'completed')
      .sort((a, b) => {
        const timeA = new Date(a.check_out_time || a.check_in_time).getTime();
        const timeB = new Date(b.check_out_time || b.check_in_time).getTime();
        return timeB - timeA;
      })
      .slice(0, 3);
  }, [sessions]);

  // Financial Statistics
  const { totalSettled, pendingTotal, pendingCount } = useMemo(() => {
    let settled = 0;
    let pending = 0;
    let pCount = 0;

    payments.forEach((p) => {
      const amt = Number(p.amount) || 0;
      if (p.payment_status === 'success' || p.payment_status === 'completed') {
        settled += amt;
      } else if (p.payment_status === 'pending') {
        pending += amt;
        pCount += 1;
      }
    });

    // Fall back to completed sessions fees if no explicit payment records exist
    if (payments.length === 0) {
      sessions.forEach((s) => {
        if (s.status === 'completed' && s.fee_amount) {
          settled += Number(s.fee_amount);
        }
      });
    }

    return { totalSettled: settled, pendingTotal: pending, pendingCount: pCount };
  }, [payments, sessions]);

  // Latest payment record
  const latestPayment = useMemo(() => {
    if (payments.length === 0) return null;
    return [...payments].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0];
  }, [payments]);

  // Derived Activity Feed strictly from real data
  const derivedActivities = useMemo(() => {
    const items: DerivedActivity[] = [];

    // 1. Reservations
    reservations.forEach((r) => {
      const fName = slotToFacilityMap[r.slot_id]?.name || 'Garage';
      const sNum = slotsMap[r.slot_id]?.slot_number || `#${r.slot_id}`;

      if (r.status === 'cancelled') {
        items.push({
          id: `res-cancel-${r.id}`,
          type: 'reservation',
          title: 'Reservation Cancelled',
          description: `Booking #${r.id} at ${fName} (${sNum}) was cancelled`,
          timestamp: r.reservation_end || r.reservation_start,
          statusColor: 'var(--pz-error)',
        });
      } else {
        items.push({
          id: `res-${r.id}`,
          type: 'reservation',
          title: `Reservation ${r.status === 'confirmed' ? 'Confirmed' : 'Created'}`,
          description: `Bay ${sNum} booked at ${fName}`,
          timestamp: r.reservation_start,
          statusColor: r.status === 'confirmed' ? 'var(--pz-success)' : 'var(--pz-secondary)',
        });
      }
    });

    // 2. Sessions
    sessions.forEach((s) => {
      const sObj = slotsMap[s.slot_id];
      const sNum = sObj?.slot_number || `#${s.slot_id}`;

      if (s.status === 'active') {
        items.push({
          id: `sess-active-${s.id}`,
          type: 'session',
          title: 'Vehicle Parked (Active)',
          description: `Ingress at Bay ${sNum}`,
          timestamp: s.check_in_time,
          statusColor: 'var(--pz-secondary)',
        });
      } else if (s.status === 'completed') {
        items.push({
          id: `sess-comp-${s.id}`,
          type: 'session',
          title: 'Parking Completed',
          description: `Bay ${sNum} • ${s.duration_minutes ? `${s.duration_minutes}m` : 'Completed'} • $${s.fee_amount?.toFixed(2) || '0.00'}`,
          timestamp: s.check_out_time || s.check_in_time,
          statusColor: 'var(--pz-success)',
        });
      }
    });

    // 3. Payments
    payments.forEach((p) => {
      const amt = Number(p.amount) || 0;
      if (p.payment_status === 'success' || p.payment_status === 'completed') {
        items.push({
          id: `pay-${p.id}`,
          type: 'payment',
          title: 'Payment Settled',
          description: `$${amt.toFixed(2)} via ${(p.payment_method || 'card').toUpperCase()}`,
          timestamp: p.paid_at || p.created_at,
          statusColor: 'var(--pz-success)',
        });
      } else if (p.payment_status === 'pending') {
        items.push({
          id: `pay-pend-${p.id}`,
          type: 'payment',
          title: 'Pending Invoice',
          description: `$${amt.toFixed(2)} awaiting settlement`,
          timestamp: p.created_at,
          statusColor: 'var(--pz-warning)',
        });
      }
    });

    return items
      .filter((item) => item.timestamp)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 4);
  }, [reservations, sessions, payments, slotToFacilityMap, slotsMap]);

  if (isLoading && !selectedFacility) {
    return <LoadingSpinner size="lg" label="Synchronizing autonomous command hub..." />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* 1. Mission Control Welcome Banner & User Identity */}
      <div
        className="glass-card"
        style={{
          padding: '1.75rem 2rem',
          borderRadius: '20px',
          background: 'linear-gradient(135deg, rgba(26, 91, 255, 0.15) 0%, rgba(0, 229, 255, 0.08) 100%)',
          border: '1px solid rgba(0, 229, 255, 0.25)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <Avatar name={user?.full_name || user?.email || 'Driver'} size="lg" status="online" />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
              <span
                style={{
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  color: 'var(--pz-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                ✦ AUTONOMOUS COCKPIT SYNCHRONIZED
              </span>
              {user?.is_superuser && (
                <span
                  style={{
                    fontSize: '0.625rem',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(192, 132, 252, 0.2)',
                    color: '#C084FC',
                  }}
                >
                  ADMIN
                </span>
              )}
            </div>

            <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
              Welcome back, {user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'Driver'}
            </h2>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                flexWrap: 'wrap',
                marginTop: '4px',
                fontSize: '0.8125rem',
                color: 'var(--pz-text-secondary)',
              }}
            >
              <span>
                Vehicle:{' '}
                <strong style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  {user?.vehicle_number || 'None registered'}
                </strong>
              </span>
              <span>•</span>
              <span style={{ color: 'var(--pz-success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={14} /> ALPR Fast-Pass Active
              </span>
              {user?.created_at && (
                <>
                  <span>•</span>
                  <span style={{ color: 'var(--pz-text-muted)' }}>
                    Member since {new Date(user.created_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions Bar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Search size={15} />}
            onClick={() => navigate('/parking')}
          >
            Find Parking
          </Button>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<MapIcon size={15} />}
            onClick={() => navigate('/parking?view=map')}
          >
            Map View
          </Button>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<CalendarCheck size={15} />}
            onClick={() => navigate('/reservations')}
          >
            Bookings
          </Button>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Clock size={15} />}
            onClick={() => navigate('/sessions')}
          >
            Sessions
          </Button>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<CreditCard size={15} />}
            onClick={() => navigate('/payments')}
          >
            Payments
          </Button>
          <Button
            variant="ai"
            size="sm"
            leftIcon={<Brain size={15} />}
            onClick={() => navigate('/predictions')}
          >
            AI Intel
          </Button>
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<UserIcon size={15} />}
            onClick={() => navigate('/profile')}
          >
            Profile
          </Button>
        </div>
      </div>

      {/* 2. Primary Parking State Hero Card */}
      {activeSession ? (
        <div
          className="glass-card"
          style={{
            padding: '1.5rem 2rem',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.12) 0%, rgba(26, 91, 255, 0.08) 100%)',
            border: '1px solid rgba(0, 229, 255, 0.35)',
            boxShadow: '0 0 30px rgba(0, 229, 255, 0.1)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                backgroundColor: 'rgba(0, 229, 255, 0.15)',
                border: '1px solid rgba(0, 229, 255, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--pz-secondary)',
              }}
            >
              <Car size={30} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span
                  style={{
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(0, 229, 255, 0.15)',
                    color: 'var(--pz-secondary)',
                    letterSpacing: '0.04em',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#00E5FF',
                      animation: 'pulse-glow 1.5s infinite',
                    }}
                  />
                  ACTIVE PARKING SESSION
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>
                  Session #{activeSession.id}
                </span>
              </div>

              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#FFFFFF' }}>
                {activeFacility?.name || 'Monitored Garage'} • Slot #{activeSlot?.slot_number || activeSession.slot_id}
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                {activeZone ? `Zone ${activeZone.name} • ` : ''}Checked in at{' '}
                {new Date(activeSession.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                  Elapsed Duration
                </span>
                <div style={{ fontSize: '1.375rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  {formattedDuration}
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                  Accrued Fee
                </span>
                <div style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  ${estimatedFee.toFixed(2)}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {activeFacility && (
                <NavigationButton facility={activeFacility} variant="outline" size="md" label="Directions" />
              )}
              <Button
                variant="danger"
                size="md"
                leftIcon={<StopCircle size={16} />}
                onClick={() => setIsEndSessionDialogOpen(true)}
              >
                End Session &amp; Pay
              </Button>
            </div>
          </div>
        </div>
      ) : nextUpcomingReservation ? (
        <div
          className="glass-card"
          style={{
            padding: '1.5rem 2rem',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(26, 91, 255, 0.08) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--pz-success)',
              }}
            >
              <CalendarCheck size={30} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span
                  style={{
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: 'var(--pz-success)',
                    letterSpacing: '0.04em',
                  }}
                >
                  UPCOMING RESERVATION CONFIRMED
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>
                  Reservation #{nextUpcomingReservation.id}
                </span>
              </div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#FFFFFF' }}>
                {slotToFacilityMap[nextUpcomingReservation.slot_id]?.name || 'Garage'} • Slot #
                {slotsMap[nextUpcomingReservation.slot_id]?.slot_number || nextUpcomingReservation.slot_id}
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                Scheduled for{' '}
                {new Date(nextUpcomingReservation.reservation_start).toLocaleDateString(undefined, {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                })}{' '}
                at{' '}
                {new Date(nextUpcomingReservation.reservation_start).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {slotToFacilityMap[nextUpcomingReservation.slot_id] && (
              <NavigationButton
                facility={slotToFacilityMap[nextUpcomingReservation.slot_id]}
                variant="outline"
                size="md"
                label="Directions"
              />
            )}
            <Button
              variant="primary"
              size="md"
              leftIcon={<PlayCircle size={16} />}
              onClick={() => handleCheckInReservation(nextUpcomingReservation)}
            >
              Check In Now
            </Button>
          </div>
        </div>
      ) : (
        <div
          className="glass-card"
          style={{
            padding: '1.25rem 1.75rem',
            borderRadius: '16px',
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--pz-border-subtle)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--pz-border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--pz-text-muted)',
              }}
            >
              <Compass size={22} />
            </div>
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF' }}>
                Vehicle Parked Off-Grid
              </h4>
              <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                No active parking session or reservation. Reserve ahead or explore live parking across connected hubs.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<MapIcon size={14} />}
              onClick={() => navigate('/parking?view=map')}
            >
              Live Parking Map
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Search size={14} />}
              onClick={() => navigate('/parking')}
            >
              Find Parking Bay
            </Button>
          </div>
        </div>
      )}

      {/* 3. Real Personal Key Metrics Row (4 Cards) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1.25rem' }}>
        {/* Metric 1: Current Parking State */}
        <Card
          glow={activeSession ? 'cyan' : 'none'}
          style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Parking State
              </span>
              <Car size={16} color={activeSession ? 'var(--pz-secondary)' : 'var(--pz-text-muted)'} />
            </div>

            {activeSession ? (
              <div>
                <span style={{ fontSize: '1.625rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  Slot #{activeSlot?.slot_number || activeSession.slot_id}
                </span>
                <span style={{ fontSize: '0.8125rem', color: 'var(--pz-secondary)', display: 'block', marginTop: '2px' }}>
                  In Progress • ${estimatedFee.toFixed(2)} accrued
                </span>
              </div>
            ) : nextUpcomingReservation ? (
              <div>
                <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF' }}>
                  Slot #{slotsMap[nextUpcomingReservation.slot_id]?.slot_number || nextUpcomingReservation.slot_id}
                </span>
                <span style={{ fontSize: '0.8125rem', color: 'var(--pz-success)', display: 'block', marginTop: '2px' }}>
                  Next Booking Scheduled
                </span>
              </div>
            ) : (
              <div>
                <span style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--pz-text-secondary)' }}>
                  Off-Grid
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block', marginTop: '2px' }}>
                  Ready to park
                </span>
              </div>
            )}
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(activeSession ? '/sessions' : '/parking')}
              style={{ width: '100%', color: 'var(--pz-secondary)' }}
            >
              {activeSession ? 'View Active Session →' : 'Park Now →'}
            </Button>
          </div>
        </Card>

        {/* Metric 2: Upcoming Bookings */}
        <Card style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Upcoming Bookings
              </span>
              <CalendarCheck size={16} color="var(--pz-secondary)" />
            </div>

            <div style={{ fontSize: '1.625rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {upcomingReservations.length} Active
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
              {upcomingReservations.length > 0
                ? `Next: Slot #${slotsMap[upcomingReservations[0].slot_id]?.slot_number || upcomingReservations[0].slot_id}`
                : 'No bookings scheduled'}
            </span>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            <Button variant="ghost" size="sm" onClick={() => navigate('/reservations')} style={{ width: '100%' }}>
              View Bookings &rarr;
            </Button>
          </div>
        </Card>

        {/* Metric 3: Completed Visits */}
        <Card style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Completed Visits
              </span>
              <Clock size={16} color="var(--pz-success)" />
            </div>

            <div style={{ fontSize: '1.625rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {sessions.filter((s) => s.status === 'completed').length}
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
              {sessions.length > 0 ? `${sessions.length} total lifetime sessions` : 'No past sessions'}
            </span>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            <Button variant="ghost" size="sm" onClick={() => navigate('/sessions')} style={{ width: '100%' }}>
              Parking History &rarr;
            </Button>
          </div>
        </Card>

        {/* Metric 4: Lifetime Parking Spend */}
        <Card style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Total Settled Spend
              </span>
              <CreditCard size={16} color="var(--pz-secondary)" />
            </div>

            <div style={{ fontSize: '1.625rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              ${totalSettled.toFixed(2)}
            </div>
            <span style={{ fontSize: '0.8125rem', color: pendingCount > 0 ? 'var(--pz-warning)' : 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
              {pendingCount > 0 ? `$${pendingTotal.toFixed(2)} pending balance` : 'All charges settled'}
            </span>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            <Button variant="ghost" size="sm" onClick={() => navigate('/payments')} style={{ width: '100%' }}>
              Billing &amp; Invoices &rarr;
            </Button>
          </div>
        </Card>
      </div>

      {/* 4. Main Grid: Left Column (8 cols) + Right Deck (4 cols) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1.5rem' }}>
        {/* Left Column (8 cols) */}
        <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} className="dashboard-main-col">
          {/* Section A: Monitored Facility Live Telemetry & Interactive Visualizer */}
          <Card>
            {selectedFacility && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '8px',
                  marginBottom: '1rem',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--pz-text-muted)' }}>
                      Monitored Hub:
                    </span>
                    <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#FFFFFF' }}>
                      {selectedFacility.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)' }}>
                    {selectedFacility.address}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                    <ConnectionStatusBadge status={connectionStatus} onReconnect={reconnect} showStaleNotice={false} />
                    <LiveDataTimestamp timestamp={lastMessageAt} status={connectionStatus} isStale={isStale} />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    rightIcon={<ArrowRight size={14} />}
                    onClick={() => navigate(`/parking/${selectedFacility.id}`)}
                  >
                    Facility Details
                  </Button>
                </div>
              </div>
            )}

            {/* Live Availability Bar */}
            {selectedFacility && (
              <div style={{ marginBottom: '1.25rem', padding: '12px 14px', borderRadius: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--pz-border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
                      {availability ? availability.available : '—'}
                    </span>
                    <span style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)' }}>
                      / {availability?.total_slots ?? selectedFacility.total_slots} Free Bays
                    </span>
                  </div>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {availability?.occupancy_percentage ?? 0}% Occupied
                  </span>
                </div>

                {(() => {
                  const occPct = availability?.occupancy_percentage ?? 0;
                  const barColor = occPct > 85 ? '#F43F5E' : occPct > 65 ? '#F59E0B' : '#10B981';
                  return (
                    <div style={{ height: '6px', borderRadius: '9999px', backgroundColor: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${Math.min(100, Math.max(0, occPct))}%`,
                          height: '100%',
                          backgroundColor: barColor,
                          borderRadius: '9999px',
                          transition: 'width 0.5s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.3s ease',
                        }}
                      />
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Live Interactive Slot Grid */}
            {selectedFacility && (
              <SlotGrid
                slots={facilitySlots}
                zoneName={selectedFacility.name}
                recentlyUpdatedSlotIds={recentlyUpdatedSlotIds}
                onSlotSelect={() => {
                  navigate(`/parking/${selectedFacility.id}`);
                }}
              />
            )}

            {/* Quick Facility Switcher */}
            {facilities.length > 1 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)' }}>
                <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>Switch Garage:</span>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {facilities.slice(0, 4).map((f) => (
                    <button
                      key={f.id}
                      onClick={() => handleSelectFacility(f)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        backgroundColor: selectedFacility?.id === f.id ? 'var(--pz-primary)' : 'rgba(255,255,255,0.04)',
                        color: '#FFFFFF',
                        border: '1px solid var(--pz-border-subtle)',
                        cursor: 'pointer',
                        transition: 'background-color 0.2s',
                      }}
                    >
                      {f.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Section B: Upcoming Bookings (Reservations) */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CalendarCheck size={18} color="var(--pz-secondary)" />
                <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                  Upcoming Reservations
                </h3>
                <span
                  style={{
                    fontSize: '0.6875rem',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(0, 229, 255, 0.1)',
                    color: 'var(--pz-secondary)',
                    fontWeight: 700,
                  }}
                >
                  {upcomingReservations.length}
                </span>
              </div>

              <Button
                variant="outline"
                size="sm"
                rightIcon={<ArrowRight size={14} />}
                onClick={() => navigate('/reservations')}
              >
                View All ({reservations.length})
              </Button>
            </div>

            {upcomingReservations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {upcomingReservations.slice(0, 2).map((res) => (
                  <ReservationCard
                    key={res.id}
                    reservation={res}
                    facility={slotToFacilityMap[res.slot_id]}
                    facilityName={slotToFacilityMap[res.slot_id]?.name || 'Garage'}
                    slotNumber={slotsMap[res.slot_id]?.slot_number}
                    onCancel={(id) => setCancellingReservationId(id)}
                    onCheckIn={(r) => handleCheckInReservation(r)}
                    onViewPass={(r) => navigate(`/reservations/${r.id}`)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<CalendarCheck size={28} color="var(--pz-secondary)" />}
                title="No upcoming bookings"
                description="Reserve a parking space in advance for guaranteed parking and automatic gate entry."
                actionLabel="Find a Parking Space"
                onAction={() => navigate('/parking')}
              />
            )}
          </Card>

          {/* Section C: Recent Parking History (Sessions) */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={18} color="var(--pz-success)" />
                <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                  Recent Parking History
                </h3>
              </div>

              <Button
                variant="outline"
                size="sm"
                rightIcon={<ArrowRight size={14} />}
                onClick={() => navigate('/sessions')}
              >
                Full Session History ({sessions.length})
              </Button>
            </div>

            {recentCompletedSessions.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {recentCompletedSessions.map((sess) => {
                  const checkIn = new Date(sess.check_in_time);
                  const checkOut = sess.check_out_time ? new Date(sess.check_out_time) : null;
                  const dateStr = checkIn.toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  });
                  const timeRangeStr = `${checkIn.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - ${
                    checkOut ? checkOut.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Ended'
                  }`;

                  return (
                    <div
                      key={sess.id}
                      style={{
                        padding: '1rem',
                        borderRadius: '12px',
                        backgroundColor: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--pz-border-subtle)',
                        display: 'flex',
                        flexWrap: 'wrap',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '1rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div
                          style={{
                            width: '38px',
                            height: '38px',
                            borderRadius: '10px',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--pz-success)',
                          }}
                        >
                          <CheckCircle2 size={18} />
                        </div>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                              Bay #{slotsMap[sess.slot_id]?.slot_number || sess.slot_id}
                            </span>
                            <StatusBadge status={sess.status} type="general" />
                          </div>
                          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
                            {dateStr} • {timeRangeStr}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontSize: '1rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                            ${Number(sess.fee_amount || 0).toFixed(2)}
                          </span>
                          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>
                            {sess.duration_minutes ? `${sess.duration_minutes} mins` : 'Completed'}
                          </span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate('/sessions')}
                          style={{ fontSize: '0.75rem' }}
                        >
                          View Receipt
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div
                style={{
                  textAlign: 'center',
                  padding: '2rem 1rem',
                  color: 'var(--pz-text-secondary)',
                  border: '1px dashed var(--pz-border-subtle)',
                  borderRadius: '12px',
                }}
              >
                <p style={{ fontSize: '0.875rem' }}>No completed parking sessions yet.</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', marginTop: '4px' }}>
                  Your past parking records and receipts will automatically appear here.
                </p>
              </div>
            )}
          </Card>
        </div>

        {/* Right Column (4 cols) */}
        <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} className="dashboard-side-col">
          {/* Card 1: AI Predictive Intelligence Summary */}
          <Card glow="purple">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Brain size={18} color="#C084FC" />
                <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF' }}>
                  Predictive Intel
                </h4>
              </div>
              <span
                style={{
                  fontSize: '0.625rem',
                  padding: '2px 6px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(192, 132, 252, 0.15)',
                  color: '#C084FC',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                }}
              >
                AI PREDICTION
              </span>
            </div>

            {isAiLoading ? (
              <div style={{ padding: '1.5rem 0', textAlign: 'center' }}>
                <LoadingSpinner size="sm" label="Calibrating neural forecast..." />
              </div>
            ) : aiDecision ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Arrival certainty */}
                <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--pz-border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>Arrival Certainty (+20m)</span>
                    <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#00E5FF', fontFamily: 'var(--font-mono)' }}>
                      {aiDecision.availability_probability != null ? `${aiDecision.availability_probability.toFixed(0)}%` : '--'}
                    </span>
                  </div>
                </div>

                {/* Queue wait & Occupancy Risk */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                  <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)' }}>Gate Queue</span>
                    <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {aiDecision.queue_wait_minutes != null ? `${aiDecision.queue_wait_minutes.toFixed(1)} mins` : '< 1 min'}
                    </div>
                  </div>
                  <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)' }}>Risk Index</span>
                    <div
                      style={{
                        fontSize: '0.9375rem',
                        fontWeight: 600,
                        fontFamily: 'var(--font-mono)',
                        marginTop: '2px',
                        color:
                          aiDecision.occupancy_risk === 'HIGH'
                            ? 'var(--pz-error)'
                            : aiDecision.occupancy_risk === 'MEDIUM'
                            ? 'var(--pz-warning)'
                            : 'var(--pz-success)',
                      }}
                    >
                      {aiDecision.occupancy_risk ? `${aiDecision.occupancy_risk}` : 'OPTIMAL'}
                    </div>
                  </div>
                </div>

                <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
                    <span style={{ color: 'var(--pz-text-secondary)' }}>Forecast Occupancy</span>
                    <span style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {aiDecision.forecast_occupancy != null ? `${aiDecision.forecast_occupancy.toFixed(0)}%` : '--'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(255, 255, 255, 0.02)', textAlign: 'center', color: 'var(--pz-text-muted)', fontSize: '0.75rem' }}>
                AI predictive forecast temporarily offline for this facility. Live sensor telemetry is active.
              </div>
            )}

            <Button
              variant="ai"
              size="sm"
              onClick={() => navigate('/predictions')}
              style={{ width: '100%', marginTop: '1rem' }}
              rightIcon={<ArrowRight size={14} />}
            >
              Open Predictions Hub
            </Button>
          </Card>

          {/* Card 2: Billing & Payment Summary */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CreditCard size={18} color="var(--pz-secondary)" />
                <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF' }}>Billing &amp; Payments</h4>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/payments')}
                style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)' }}
              >
                Manage &rarr;
              </Button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '1rem' }}>
              <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--pz-border-subtle)' }}>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>Lifetime Settled</span>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  ${totalSettled.toFixed(2)}
                </div>
              </div>
              <div
                style={{
                  padding: '10px',
                  borderRadius: '10px',
                  backgroundColor: pendingCount > 0 ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${pendingCount > 0 ? 'rgba(245, 158, 11, 0.3)' : 'var(--pz-border-subtle)'}`,
                }}
              >
                <span style={{ fontSize: '0.6875rem', color: pendingCount > 0 ? 'var(--pz-warning)' : 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                  {pendingCount > 0 ? 'Pending Balance' : 'Outstanding'}
                </span>
                <div
                  style={{
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: pendingCount > 0 ? 'var(--pz-warning)' : 'var(--pz-success)',
                    fontFamily: 'var(--font-mono)',
                    marginTop: '2px',
                  }}
                >
                  ${pendingTotal.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Latest Payment Record */}
            {latestPayment ? (
              <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--pz-border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)' }}>Latest Settlement</span>
                  <StatusBadge status={latestPayment.payment_status} type="payment" />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                    ${Number(latestPayment.amount).toFixed(2)}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>
                    {(latestPayment.payment_method || 'card').toUpperCase()} • {formatRelativeTime(latestPayment.paid_at || latestPayment.created_at)}
                  </span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--pz-text-muted)', fontSize: '0.75rem' }}>
                No payment records found yet.
              </div>
            )}
          </Card>

          {/* Card 3: Derived Personal Activity Stream */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="var(--pz-secondary)" />
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                  Personal Activity Stream
                </h4>
              </div>
              <span className="telemetry-pulse" />
            </div>

            {derivedActivities.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {derivedActivities.map((act) => (
                  <div
                    key={act.id}
                    style={{
                      padding: '10px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                      borderLeft: `3px solid ${act.statusColor}`,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#FFFFFF' }}>
                        {act.title}
                      </span>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {formatRelativeTime(act.timestamp)}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                      {act.description}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '1.25rem', color: 'var(--pz-text-muted)', fontSize: '0.75rem' }}>
                No recent activity recorded yet. As you make bookings and park, your personal activity will stream here.
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* 5. Connected Facilities Discovery Strip */}
      <Card style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>Connected Garages</h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
              Real-time telemetry and capacity across active locations.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<MapIcon size={14} />}
              onClick={() => navigate('/parking?view=map')}
            >
              Interactive Map
            </Button>
            <Button
              variant="outline"
              size="sm"
              rightIcon={<ArrowRight size={14} />}
              onClick={() => navigate('/parking')}
            >
              View All Garages ({facilities.length})
            </Button>
          </div>
        </div>

        {facilities.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--pz-text-secondary)', fontSize: '0.875rem' }}>
            No parking facilities currently connected.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem' }}>
            {facilities.slice(0, 3).map((fac) => {
              const facAvail = facilityAvailMap[fac.id];
              return (
                <div
                  key={fac.id}
                  onClick={() => navigate(`/parking/${fac.id}`)}
                  style={{
                    padding: '1rem',
                    borderRadius: '12px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--pz-border-subtle)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '0.75rem',
                    transition: 'border-color 0.2s, transform 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--pz-secondary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--pz-border-subtle)')}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                        {fac.name}
                      </span>
                      <span
                        style={{
                          fontSize: '0.6875rem',
                          fontWeight: 600,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: fac.is_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                          color: fac.is_active ? 'var(--pz-success)' : 'var(--pz-error)',
                        }}
                      >
                        {fac.is_active ? 'OPEN' : 'CLOSED'}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)' }}>
                      {fac.address} {fac.city ? `• ${fac.city}` : ''}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.5rem', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--pz-text-muted)' }}>
                      {facAvail?.available !== undefined ? `${facAvail.available} Bays Open` : `${fac.total_slots || 0} Total Bays`}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <NavigationButton facility={fac} variant="outline" size="sm" label="Go" />
                      <span style={{ color: 'var(--pz-secondary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                        Explore &rarr;
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Confirmation Dialog: End Session & Pay */}
      <ConfirmationDialog
        isOpen={isEndSessionDialogOpen}
        onClose={() => setIsEndSessionDialogOpen(false)}
        onConfirm={handleEndSession}
        title="End Parking Session & Settle"
        message={`Are you sure you want to conclude your active parking session for Bay #${activeSlot?.slot_number || activeSession?.slot_id}? Accrued fee: $${estimatedFee.toFixed(2)}. Ingress barrier will disengage upon completion.`}
        confirmText="End & Settle"
        cancelText="Keep Parked"
        variant="danger"
        isLoading={isEndingSession}
      />

      {/* Confirmation Dialog: Cancel Reservation */}
      <ConfirmationDialog
        isOpen={cancellingReservationId !== null}
        onClose={() => setCancellingReservationId(null)}
        onConfirm={handleConfirmCancelReservation}
        title="Cancel Parking Reservation"
        message="Are you sure you want to cancel this booking? The reserved bay will be immediately released back to the live public pool."
        confirmText="Cancel Reservation"
        cancelText="Keep Reservation"
        variant="danger"
        isLoading={isCancellingReservation}
      />

      <style>{`
        @media (max-width: 1024px) {
          .dashboard-main-col { grid-column: span 12 !important; }
          .dashboard-side-col { grid-column: span 12 !important; }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;
