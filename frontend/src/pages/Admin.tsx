import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import { parkingApi } from '../api/parking';
import { reservationsApi } from '../api/reservations';
import { sessionsApi } from '../api/sessions';
import { paymentsApi } from '../api/payments';
import { aiApi } from '../api/ai';
import { useWebSocket } from '../hooks/useWebSocket';
import type {
  Facility,
  Zone,
  Slot,
  Availability,
  Reservation,
  ParkingSession,
  Payment,
  ParkingSlotStatus,
  VehicleType,
  AvailabilityPrediction,
  ZoneAnalytics,
  FacilityCreateRequest,
  FacilityUpdateRequest,
  ZoneCreateRequest,
  ZoneUpdateRequest,
  SlotCreateRequest,
  SlotUpdateRequest,
} from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { ConnectionStatusBadge } from '../components/parking/ConnectionStatusBadge';
import { LiveDataTimestamp } from '../components/parking/LiveDataTimestamp';
import { SlotGrid } from '../components/parking/SlotGrid';
import {
  Shield,
  LayoutDashboard,
  Building2,
  Grid,
  Radio,
  CalendarCheck,
  Clock,
  CreditCard,
  Brain,
  Search,
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  CheckCircle2,
  Activity,
  Sliders,
  StopCircle,
} from 'lucide-react';

type AdminTab =
  | 'overview'
  | 'facilities'
  | 'zones'
  | 'slots'
  | 'reservations'
  | 'sessions'
  | 'payments'
  | 'ai';

interface TelemetryEvent {
  id: string;
  time: string;
  text: string;
  color: string;
}

export const Admin: React.FC = () => {
  const { user } = useAuth();
  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  // Access Control Guard
  const isAdmin = Boolean(user?.is_superuser || user?.role === 'admin');

  // Active Tab
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');

  // Core Data
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [facilityAvailMap, setFacilityAvailMap] = useState<Record<number, Availability>>({});
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);

  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);

  const [slots, setSlots] = useState<Slot[]>([]);
  const [recentlyUpdatedSlotIds, setRecentlyUpdatedSlotIds] = useState<Set<number>>(new Set());

  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);

  // AI & Telemetry State
  const [aiDecision, setAiDecision] = useState<AvailabilityPrediction | null>(null);
  const [zoneAnalytics, setZoneAnalytics] = useState<ZoneAnalytics | null>(null);
  const [telemetryEvents, setTelemetryEvents] = useState<TelemetryEvent[]>([]);

  // Loading States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);

  // Filters & Search
  const [facilitySearch, setFacilitySearch] = useState<string>('');
  const [facilityStatusFilter, setFacilityStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [slotVehicleFilter, setSlotVehicleFilter] = useState<string>('all');
  const [reservationStatusFilter, setReservationStatusFilter] = useState<string>('all');
  const [sessionStatusFilter, setSessionStatusFilter] = useState<string>('all');

  // Modals & Dialogs
  const [isFacilityModalOpen, setIsFacilityModalOpen] = useState<boolean>(false);
  const [editingFacility, setEditingFacility] = useState<Facility | null>(null);
  const [facilityFormData, setFacilityFormData] = useState<FacilityCreateRequest>({
    name: '',
    address: '',
    city: '',
    state: '',
    total_slots: 50,
    operating_start_time: '06:00',
    operating_end_time: '23:00',
    is_active: true,
  });

  const [isZoneModalOpen, setIsZoneModalOpen] = useState<boolean>(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [zoneFormData, setZoneFormData] = useState<ZoneCreateRequest>({
    name: '',
    floor_number: 1,
    total_slots: 20,
    is_active: true,
  });

  const [isSlotModalOpen, setIsSlotModalOpen] = useState<boolean>(false);
  const [editingSlot, setEditingSlot] = useState<Slot | null>(null);
  const [slotFormData, setSlotFormData] = useState<SlotCreateRequest>({
    slot_number: '',
    status: 'available',
    vehicle_type: 'car',
    is_active: true,
  });

  // Deletion Confirmations
  const [deletingFacilityId, setDeletingFacilityId] = useState<number | null>(null);
  const [deletingZoneId, setDeletingZoneId] = useState<number | null>(null);
  const [deletingSlotId, setDeletingSlotId] = useState<number | null>(null);
  const [cancellingReservationId, setCancellingReservationId] = useState<number | null>(null);
  const [endingSessionId, setEndingSessionId] = useState<number | null>(null);

  // Real-time WebSocket integration
  const { latestMessage, connectionStatus, isStale, lastMessageAt, reconnect } =
    useWebSocket('*', selectedFacility?.id);

  // Helper map for facility names
  const facilityNameMap = useMemo(() => {
    const map: Record<number, string> = {};
    facilities.forEach((f) => {
      map[f.id] = f.name;
    });
    return map;
  }, [facilities]);

  // Load All Admin Data from Real Endpoints
  const loadAdminData = useCallback(async () => {
    try {
      setIsLoading(true);

      // 1. Facilities
      const facList = await parkingApi.getFacilities().catch(() => []);
      setFacilities(facList);

      const availMap: Record<number, Availability> = {};
      await Promise.all(
        facList.map(async (fac) => {
          try {
            const avail = await parkingApi.getFacilityAvailability(fac.id);
            availMap[fac.id] = avail;
          } catch {
            // ignore
          }
        })
      );
      setFacilityAvailMap(availMap);

      let currentFac = selectedFacility;
      if (!currentFac && facList.length > 0) {
        currentFac = facList[0];
        setSelectedFacility(currentFac);
      }

      // 2. Zones & Slots for selected facility
      if (currentFac) {
        const zoneList = await parkingApi.getZones(currentFac.id).catch(() => []);
        setZones(zoneList);

        let currentZone = selectedZone;
        if (!currentZone && zoneList.length > 0) {
          currentZone = zoneList[0];
          setSelectedZone(currentZone);
        }

        if (currentZone) {
          const slotList = await parkingApi.getSlots(currentZone.id).catch(() => []);
          setSlots(slotList);
        }

        // 3. AI prediction & Analytics for selected facility
        try {
          const pred = await aiApi.getPrediction(currentFac.id);
          setAiDecision(pred);
        } catch {
          setAiDecision(null);
        }

        try {
          const zAnalytics = await aiApi.getZoneAnalytics(currentFac.id);
          setZoneAnalytics(zAnalytics);
        } catch {
          setZoneAnalytics(null);
        }
      }

      // 4. System-wide Reservations (Admin superuser returns all records)
      try {
        const resList = await reservationsApi.getReservations();
        setReservations(Array.isArray(resList) ? resList : []);
      } catch {
        setReservations([]);
      }

      // 5. System-wide Sessions (Admin superuser returns all records)
      try {
        const sessList = await sessionsApi.getSessions();
        setSessions(Array.isArray(sessList) ? sessList : []);
      } catch {
        setSessions([]);
      }

      // 6. Payments
      try {
        const payList = await paymentsApi.getMyPayments();
        setPayments(Array.isArray(payList) ? payList : []);
      } catch {
        setPayments([]);
      }
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedFacility, selectedZone]);

  useEffect(() => {
    if (isAdmin) {
      loadAdminData();
    }
  }, [isAdmin, loadAdminData]);

  // Handle Real-Time WebSocket Telemetry
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

      setSlots((prev) =>
        prev.map((s) => (s.id === slotId ? { ...s, status: newStatus } : s))
      );

      // Append to live telemetry events log
      const newEvent: TelemetryEvent = {
        id: `ev-${Date.now()}-${Math.random()}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        text: `Slot #${latestMessage.slot_number || slotId} transitioned from ${oldStatus.toUpperCase()} → ${newStatus.toUpperCase()}`,
        color:
          newStatus === 'available'
            ? 'var(--pz-success)'
            : newStatus === 'occupied'
            ? 'var(--pz-secondary)'
            : 'var(--pz-warning)',
      };
      setTelemetryEvents((prev) => [newEvent, ...prev.slice(0, 19)]);
    }

    if (latestMessage.event === 'occupancy_updated' && latestMessage.data) {
      const occ = latestMessage.data;
      const targetFacId = latestMessage.facility_id || selectedFacility?.id;
      if (targetFacId) {
        setFacilityAvailMap((prev) => ({
          ...prev,
          [targetFacId]: {
            entity_id: targetFacId,
            total_slots: occ.total_slots || 0,
            available: occ.available_slots,
            occupied: occ.occupied_slots,
            reserved: occ.reserved_slots,
            occupancy_percentage: occ.occupancy_percentage,
          },
        }));
      }
    }
  }, [latestMessage, selectedFacility]);

  // Facility Switcher Handler
  const handleSelectFacility = async (fac: Facility) => {
    setSelectedFacility(fac);
    try {
      const zList = await parkingApi.getZones(fac.id);
      setZones(zList);
      if (zList.length > 0) {
        setSelectedZone(zList[0]);
        const sList = await parkingApi.getSlots(zList[0].id);
        setSlots(sList);
      } else {
        setSelectedZone(null);
        setSlots([]);
      }
    } catch {
      setZones([]);
      setSelectedZone(null);
      setSlots([]);
    }

    try {
      const pred = await aiApi.getPrediction(fac.id);
      setAiDecision(pred);
    } catch {
      setAiDecision(null);
    }

    try {
      const zAnalytics = await aiApi.getZoneAnalytics(fac.id);
      setZoneAnalytics(zAnalytics);
    } catch {
      setZoneAnalytics(null);
    }
  };

  // Zone Switcher Handler
  const handleSelectZone = async (zone: Zone) => {
    setSelectedZone(zone);
    try {
      const sList = await parkingApi.getSlots(zone.id);
      setSlots(sList);
    } catch {
      setSlots([]);
    }
  };

  // ==========================================
  // FACILITY CRUD OPERATIONS
  // ==========================================
  const handleOpenCreateFacility = () => {
    setEditingFacility(null);
    setFacilityFormData({
      name: '',
      address: '',
      city: '',
      state: '',
      total_slots: 50,
      operating_start_time: '06:00',
      operating_end_time: '23:00',
      is_active: true,
    });
    setIsFacilityModalOpen(true);
  };

  const handleOpenEditFacility = (fac: Facility) => {
    setEditingFacility(fac);
    setFacilityFormData({
      name: fac.name,
      address: fac.address,
      city: fac.city || '',
      state: fac.state || '',
      total_slots: fac.total_slots,
      operating_start_time: fac.operating_start_time || '06:00',
      operating_end_time: fac.operating_end_time || '23:00',
      is_active: fac.is_active,
    });
    setIsFacilityModalOpen(true);
  };

  const handleSaveFacility = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsActionLoading(true);
    try {
      if (editingFacility) {
        const updated = await parkingApi.updateFacility(editingFacility.id, facilityFormData as FacilityUpdateRequest);
        success(`Facility "${updated.name}" updated successfully.`, 'Facility Updated');
      } else {
        const created = await parkingApi.createFacility(facilityFormData);
        success(`Facility "${created.name}" created successfully.`, 'Facility Created');
      }
      setIsFacilityModalOpen(false);
      loadAdminData();
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      toastError(errorObj.response?.data?.detail || 'Failed to save facility.', 'Error');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmDeleteFacility = async () => {
    if (!deletingFacilityId) return;
    setIsActionLoading(true);
    try {
      await parkingApi.deleteFacility(deletingFacilityId);
      success('Facility deleted successfully.', 'Facility Removed');
      setDeletingFacilityId(null);
      if (selectedFacility?.id === deletingFacilityId) {
        setSelectedFacility(null);
      }
      loadAdminData();
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      toastError(errorObj.response?.data?.detail || 'Failed to delete facility.', 'Delete Failed');
    } finally {
      setIsActionLoading(false);
    }
  };

  // ==========================================
  // ZONE CRUD OPERATIONS
  // ==========================================
  const handleOpenCreateZone = () => {
    if (!selectedFacility) {
      toastError('Please select a facility first.', 'Action Required');
      return;
    }
    setEditingZone(null);
    setZoneFormData({
      name: '',
      floor_number: 1,
      total_slots: 20,
      is_active: true,
    });
    setIsZoneModalOpen(true);
  };

  const handleOpenEditZone = (zone: Zone) => {
    setEditingZone(zone);
    setZoneFormData({
      name: zone.name,
      floor_number: zone.floor_number || 1,
      total_slots: zone.total_slots,
      is_active: zone.is_active,
    });
    setIsZoneModalOpen(true);
  };

  const handleSaveZone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFacility) return;
    setIsActionLoading(true);
    try {
      if (editingZone) {
        const updated = await parkingApi.updateZone(editingZone.id, zoneFormData as ZoneUpdateRequest);
        success(`Zone "${updated.name}" updated successfully.`, 'Zone Updated');
      } else {
        const created = await parkingApi.createZone(selectedFacility.id, zoneFormData);
        success(`Zone "${created.name}" created successfully.`, 'Zone Created');
      }
      setIsZoneModalOpen(false);
      const zList = await parkingApi.getZones(selectedFacility.id);
      setZones(zList);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      toastError(errorObj.response?.data?.detail || 'Failed to save zone.', 'Error');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmDeleteZone = async () => {
    if (!deletingZoneId) return;
    setIsActionLoading(true);
    try {
      await parkingApi.deleteZone(deletingZoneId);
      success('Zone deleted successfully.', 'Zone Removed');
      setDeletingZoneId(null);
      if (selectedFacility) {
        const zList = await parkingApi.getZones(selectedFacility.id);
        setZones(zList);
        if (selectedZone?.id === deletingZoneId) {
          setSelectedZone(zList.length > 0 ? zList[0] : null);
        }
      }
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      toastError(errorObj.response?.data?.detail || 'Failed to delete zone.', 'Delete Failed');
    } finally {
      setIsActionLoading(false);
    }
  };

  // ==========================================
  // SLOT CRUD & LIVE OVERRIDE OPERATIONS
  // ==========================================
  const handleOpenCreateSlot = () => {
    if (!selectedZone) {
      toastError('Please select a zone first.', 'Action Required');
      return;
    }
    setEditingSlot(null);
    setSlotFormData({
      slot_number: `${selectedZone.name}-01`,
      status: 'available',
      vehicle_type: 'car',
      is_active: true,
    });
    setIsSlotModalOpen(true);
  };

  const handleOpenEditSlot = (slot: Slot) => {
    setEditingSlot(slot);
    setSlotFormData({
      slot_number: slot.slot_number,
      status: slot.status,
      vehicle_type: slot.vehicle_type,
      is_active: slot.is_active,
    });
    setIsSlotModalOpen(true);
  };

  const handleSaveSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedZone) return;
    setIsActionLoading(true);
    try {
      if (editingSlot) {
        const updated = await parkingApi.updateSlot(editingSlot.id, slotFormData as SlotUpdateRequest);
        success(`Slot #${updated.slot_number} updated successfully.`, 'Slot Updated');
      } else {
        const created = await parkingApi.createSlot(selectedZone.id, slotFormData);
        success(`Slot #${created.slot_number} created successfully.`, 'Slot Created');
      }
      setIsSlotModalOpen(false);
      const sList = await parkingApi.getSlots(selectedZone.id);
      setSlots(sList);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      toastError(errorObj.response?.data?.detail || 'Failed to save slot.', 'Error');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmDeleteSlot = async () => {
    if (!deletingSlotId) return;
    setIsActionLoading(true);
    try {
      await parkingApi.deleteSlot(deletingSlotId);
      success('Slot deleted successfully.', 'Slot Removed');
      setDeletingSlotId(null);
      if (selectedZone) {
        const sList = await parkingApi.getSlots(selectedZone.id);
        setSlots(sList);
      }
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      toastError(errorObj.response?.data?.detail || 'Failed to delete slot.', 'Delete Failed');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Live Telemetry Override for a Slot
  const handleOverrideSlotStatus = async (slotId: number, nextStatus: ParkingSlotStatus) => {
    try {
      const updated = await parkingApi.updateSlotStatus(slotId, nextStatus);
      setSlots((prev) =>
        prev.map((s) => (s.id === slotId ? { ...s, status: updated.status } : s))
      );
      success(`Slot #${updated.slot_number} overridden to ${nextStatus.toUpperCase()}`, 'Telemetry Override');
    } catch {
      toastError('Failed to override slot status.', 'Override Error');
    }
  };

  // ==========================================
  // RESERVATION & SESSION ACTIONS
  // ==========================================
  const handleConfirmCancelReservation = async () => {
    if (!cancellingReservationId) return;
    setIsActionLoading(true);
    try {
      await reservationsApi.cancelReservation(cancellingReservationId);
      success(`Reservation #${cancellingReservationId} cancelled by admin.`, 'Reservation Cancelled');
      setReservations((prev) =>
        prev.map((r) => (r.id === cancellingReservationId ? { ...r, status: 'cancelled' } : r))
      );
      setCancellingReservationId(null);
    } catch {
      toastError('Could not cancel reservation.', 'Action Failed');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmEndSession = async () => {
    if (!endingSessionId) return;
    setIsActionLoading(true);
    try {
      const ended = await sessionsApi.endSession(endingSessionId);
      success(`Session #${ended.id} concluded by admin. Gate barrier disengaged.`, 'Session Terminated');
      setSessions((prev) =>
        prev.map((s) => (s.id === endingSessionId ? { ...s, status: 'completed' } : s))
      );
      setEndingSessionId(null);
    } catch {
      toastError('Could not terminate session.', 'Action Failed');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Aggregated System Metrics (100% Real Backend Data)
  const systemMetrics = useMemo(() => {
    let totalCap = 0;
    let totalAvail = 0;
    let totalOcc = 0;
    let totalRes = 0;

    facilities.forEach((f) => {
      totalCap += f.total_slots || 0;
      const a = facilityAvailMap[f.id];
      if (a) {
        totalAvail += a.available;
        totalOcc += a.occupied;
        totalRes += a.reserved;
      }
    });

    const activeReservationsCount = reservations.filter(
      (r) => r.status === 'confirmed' || r.status === 'pending'
    ).length;

    const activeSessionsCount = sessions.filter((s) => s.status === 'active').length;

    let revenueSettled = 0;
    let revenuePending = 0;

    payments.forEach((p) => {
      const amt = Number(p.amount) || 0;
      if (p.payment_status === 'success' || p.payment_status === 'completed') {
        revenueSettled += amt;
      } else if (p.payment_status === 'pending') {
        revenuePending += amt;
      }
    });

    // Fall back to completed session fees if payments ledger is empty
    if (payments.length === 0) {
      sessions.forEach((s) => {
        if (s.status === 'completed' && s.fee_amount) {
          revenueSettled += Number(s.fee_amount);
        }
      });
    }

    return {
      totalFacilities: facilities.length,
      activeFacilities: facilities.filter((f) => f.is_active).length,
      totalCapacity: totalCap,
      totalAvailable: totalAvail,
      totalOccupied: totalOcc,
      totalReserved: totalRes,
      activeReservations: activeReservationsCount,
      activeSessions: activeSessionsCount,
      totalRevenueSettled: revenueSettled,
      totalRevenuePending: revenuePending,
    };
  }, [facilities, facilityAvailMap, reservations, sessions, payments]);

  // Unauthorized Barrier
  if (!isAdmin) {
    return (
      <div style={{ padding: '3rem 1.5rem', textAlign: 'center' }}>
        <EmptyState
          icon={<Shield size={36} color="var(--pz-error)" />}
          title="Administrative Access Restricted"
          description="You must be signed in with an authorized superuser administrator account to view the Operations Command Center."
          actionLabel="Return to User Cockpit"
          onAction={() => navigate('/dashboard')}
        />
      </div>
    );
  }

  if (isLoading && facilities.length === 0) {
    return <LoadingSpinner size="lg" label="Synchronizing administrative operations command..." />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* 1. Header & Navigation Ribbon */}
      <div>
        <Breadcrumb items={[{ label: 'Operations Command' }]} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginTop: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(192, 132, 252, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#C084FC',
                }}
              >
                <Shield size={20} />
              </div>
              <h1 className="text-page-title" style={{ fontSize: '1.75rem' }}>
                Parking Operations Management
              </h1>
            </div>
            <p className="text-body" style={{ marginTop: '4px' }}>
              Autonomous facility infrastructure, live sensor overrides, reservation dispatch, and AI monitoring.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <ConnectionStatusBadge status={connectionStatus} onReconnect={reconnect} showStaleNotice={false} />
            <LiveDataTimestamp timestamp={lastMessageAt} status={connectionStatus} isStale={isStale} />
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RefreshCw size={14} />}
              onClick={loadAdminData}
            >
              Sync Mesh
            </Button>
          </div>
        </div>
      </div>

      {/* 2. Operations Segmented Tab Navigation */}
      <div
        style={{
          display: 'flex',
          gap: '6px',
          overflowX: 'auto',
          paddingBottom: '4px',
          borderBottom: '1px solid var(--pz-border-subtle)',
        }}
      >
        {[
          { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={15} /> },
          { id: 'facilities', label: `Facilities (${facilities.length})`, icon: <Building2 size={15} /> },
          { id: 'zones', label: `Zones (${zones.length})`, icon: <Grid size={15} /> },
          { id: 'slots', label: `Slots & Live Ops (${slots.length})`, icon: <Radio size={15} /> },
          { id: 'reservations', label: `Reservations (${reservations.length})`, icon: <CalendarCheck size={15} /> },
          { id: 'sessions', label: `Sessions (${sessions.length})`, icon: <Clock size={15} /> },
          { id: 'payments', label: 'Billing & Ledger', icon: <CreditCard size={15} /> },
          { id: 'ai', label: 'AI Intelligence', icon: <Brain size={15} /> },
        ].map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as AdminTab)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                borderRadius: '8px',
                fontSize: '0.8125rem',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
                backgroundColor: isActive ? 'var(--pz-primary)' : 'transparent',
                color: isActive ? '#FFFFFF' : 'var(--pz-text-secondary)',
                boxShadow: isActive ? '0 0 16px rgba(26, 91, 255, 0.35)' : 'none',
                whiteSpace: 'nowrap',
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ========================================================= */}
      {/* TAB 1: OVERVIEW DASHBOARD                                 */}
      {/* ========================================================= */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Top 4 KPI Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
            <Card glow="purple">
              <span style={{ fontSize: '0.75rem', color: '#C084FC', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Connected Facilities
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                {systemMetrics.totalFacilities} Hubs
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-success)', display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                <CheckCircle2 size={13} /> {systemMetrics.activeFacilities} Open &amp; Operational
              </span>
            </Card>

            <Card glow="cyan">
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                System Free Bays
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                {systemMetrics.totalAvailable} / {systemMetrics.totalCapacity}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                {systemMetrics.totalOccupied} Occupied • {systemMetrics.totalReserved} Reserved
              </span>
            </Card>

            <Card>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Active Operations
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                {systemMetrics.activeSessions} Parked
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)', marginTop: '4px', display: 'block' }}>
                {systemMetrics.activeReservations} Upcoming Bookings
              </span>
            </Card>

            <Card>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Settled Revenue
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                ${systemMetrics.totalRevenueSettled.toFixed(2)}
              </div>
              <span style={{ fontSize: '0.75rem', color: systemMetrics.totalRevenuePending > 0 ? 'var(--pz-warning)' : 'var(--pz-text-muted)', marginTop: '4px', display: 'block' }}>
                ${systemMetrics.totalRevenuePending.toFixed(2)} Pending Settlement
              </span>
            </Card>
          </div>

          {/* Quick Actions & Live Telemetry Stream */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1.5rem' }}>
            {/* Left Deck (7 cols): Quick Action Center & Facility Cards */}
            <div style={{ gridColumn: 'span 7' }} className="admin-overview-col">
              <Card>
                <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '1rem' }}>
                  Operations Quick Dispatch
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                  <Button
                    variant="primary"
                    size="sm"
                    leftIcon={<Plus size={15} />}
                    onClick={handleOpenCreateFacility}
                  >
                    Add Facility
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Grid size={15} />}
                    onClick={() => setActiveTab('zones')}
                  >
                    Manage Zones
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Sliders size={15} />}
                    onClick={() => setActiveTab('slots')}
                  >
                    Bay Overrides
                  </Button>
                  <Button
                    variant="ai"
                    size="sm"
                    leftIcon={<Brain size={15} />}
                    onClick={() => setActiveTab('ai')}
                  >
                    AI Analytics
                  </Button>
                </div>

                <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--pz-border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
                      Connected Facilities Capacity
                    </span>
                    <Button variant="ghost" size="sm" onClick={() => setActiveTab('facilities')}>
                      View All &rarr;
                    </Button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {facilities.slice(0, 4).map((f) => {
                      const a = facilityAvailMap[f.id];
                      const occPct = a?.occupancy_percentage || 0;
                      return (
                        <div
                          key={f.id}
                          style={{
                            padding: '10px 12px',
                            borderRadius: '10px',
                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                            border: '1px solid var(--pz-border-subtle)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>
                              {f.name}
                            </span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block' }}>
                              {f.city || 'Smart Parking Hub'} • {f.total_slots} Total Bays
                            </span>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
                              {a ? a.available : '—'} Free
                            </span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>
                              {occPct}% occupied
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </Card>
            </div>

            {/* Right Deck (5 cols): Real-Time WebSocket Telemetry Log */}
            <div style={{ gridColumn: 'span 5' }} className="admin-overview-col">
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={18} color="var(--pz-secondary)" />
                    <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                      Live Telemetry Stream
                    </h3>
                  </div>
                  <span className="telemetry-pulse" />
                </div>

                <div
                  style={{
                    maxHeight: '360px',
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    fontSize: '0.75rem',
                  }}
                >
                  {telemetryEvents.length > 0 ? (
                    telemetryEvents.map((ev) => (
                      <div
                        key={ev.id}
                        style={{
                          padding: '8px 10px',
                          borderRadius: '8px',
                          backgroundColor: 'rgba(255, 255, 255, 0.02)',
                          borderLeft: `3px solid ${ev.color}`,
                        }}
                      >
                        <span style={{ color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {ev.time}
                        </span>
                        <p style={{ color: '#FFFFFF', marginTop: '2px' }}>{ev.text}</p>
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--pz-text-muted)' }}>
                      Listening to real-time WebSocket events. State overrides and sensor telemetry will appear here in real-time.
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: FACILITIES MANAGEMENT                              */}
      {/* ========================================================= */}
      {activeTab === 'facilities' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '240px' }}>
              <Input
                placeholder="Search facilities by name or address..."
                value={facilitySearch}
                onChange={(e) => setFacilitySearch(e.target.value)}
                leftIcon={<Search size={16} />}
              />
              <div style={{ width: '150px' }}>
                <Select
                  value={facilityStatusFilter}
                  onChange={(e) => setFacilityStatusFilter(e.target.value as 'all' | 'active' | 'inactive')}
                  options={[
                    { value: 'all', label: 'All Status' },
                    { value: 'active', label: 'Open' },
                    { value: 'inactive', label: 'Closed' },
                  ]}
                />
              </div>
            </div>

            <Button variant="primary" size="sm" leftIcon={<Plus size={15} />} onClick={handleOpenCreateFacility}>
              Create Facility
            </Button>
          </div>

          {/* Facilities Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--pz-border-subtle)', color: 'var(--pz-text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Facility</th>
                  <th style={{ padding: '10px 12px' }}>Location</th>
                  <th style={{ padding: '10px 12px' }}>Capacity</th>
                  <th style={{ padding: '10px 12px' }}>Availability</th>
                  <th style={{ padding: '10px 12px' }}>Operating Hours</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {facilities
                  .filter((f) => {
                    const matchText =
                      f.name.toLowerCase().includes(facilitySearch.toLowerCase()) ||
                      f.address.toLowerCase().includes(facilitySearch.toLowerCase());
                    const matchStatus =
                      facilityStatusFilter === 'all'
                        ? true
                        : facilityStatusFilter === 'active'
                        ? f.is_active
                        : !f.is_active;
                    return matchText && matchStatus;
                  })
                  .map((fac) => {
                    const a = facilityAvailMap[fac.id];
                    return (
                      <tr
                        key={fac.id}
                        style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', transition: 'background-color 0.15s' }}
                      >
                        <td style={{ padding: '12px' }}>
                          <span style={{ fontWeight: 600, color: '#FFFFFF', display: 'block' }}>{fac.name}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>ID #{fac.id}</span>
                        </td>
                        <td style={{ padding: '12px', color: 'var(--pz-text-secondary)' }}>
                          {fac.address}
                          {fac.city ? `, ${fac.city}` : ''}
                        </td>
                        <td style={{ padding: '12px', color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                          {fac.total_slots} Bays
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span style={{ color: '#10B981', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                            {a ? `${a.available} Free` : '—'}
                          </span>
                          <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>
                            {a ? `${a.occupancy_percentage}% occ` : ''}
                          </span>
                        </td>
                        <td style={{ padding: '12px', color: 'var(--pz-text-muted)' }}>
                          {fac.operating_start_time || '00:00'} - {fac.operating_end_time || '23:59'}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span
                            style={{
                              fontSize: '0.6875rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              backgroundColor: fac.is_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                              color: fac.is_active ? 'var(--pz-success)' : 'var(--pz-error)',
                            }}
                          >
                            {fac.is_active ? 'OPEN' : 'CLOSED'}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedFacility(fac);
                                setActiveTab('zones');
                              }}
                            >
                              Zones
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => handleOpenEditFacility(fac)}>
                              <Edit size={13} />
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => setDeletingFacilityId(fac.id)}
                            >
                              <Trash2 size={13} />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ========================================================= */}
      {/* TAB 3: ZONES MANAGEMENT                                   */}
      {/* ========================================================= */}
      {activeTab === 'zones' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>Facility:</span>
              <div style={{ width: '220px' }}>
                <Select
                  value={selectedFacility?.id || ''}
                  onChange={(e) => {
                    const found = facilities.find((f) => f.id === Number(e.target.value));
                    if (found) handleSelectFacility(found);
                  }}
                  options={facilities.map((f) => ({ value: f.id, label: f.name }))}
                />
              </div>
            </div>

            <Button variant="primary" size="sm" leftIcon={<Plus size={15} />} onClick={handleOpenCreateZone}>
              Create Zone
            </Button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--pz-border-subtle)', color: 'var(--pz-text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Zone</th>
                  <th style={{ padding: '10px 12px' }}>Facility</th>
                  <th style={{ padding: '10px 12px' }}>Floor</th>
                  <th style={{ padding: '10px 12px' }}>Capacity</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {zones.map((zone) => (
                  <tr key={zone.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '12px' }}>
                      <span style={{ fontWeight: 600, color: '#FFFFFF' }}>{zone.name}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>ID #{zone.id}</span>
                    </td>
                    <td style={{ padding: '12px', color: 'var(--pz-text-secondary)' }}>
                      {facilityNameMap[zone.facility_id] || selectedFacility?.name || 'Garage'}
                    </td>
                    <td style={{ padding: '12px', color: '#FFFFFF' }}>Floor {zone.floor_number ?? '1'}</td>
                    <td style={{ padding: '12px', color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                      {zone.total_slots} Slots
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span
                        style={{
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: zone.is_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                          color: zone.is_active ? 'var(--pz-success)' : 'var(--pz-error)',
                        }}
                      >
                        {zone.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedZone(zone);
                            setActiveTab('slots');
                          }}
                        >
                          Slots
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleOpenEditZone(zone)}>
                          <Edit size={13} />
                        </Button>
                        <Button variant="danger" size="sm" onClick={() => setDeletingZoneId(zone.id)}>
                          <Trash2 size={13} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ========================================================= */}
      {/* TAB 4: SLOTS & LIVE OPERATIONS                           */}
      {/* ========================================================= */}
      {activeTab === 'slots' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Controls Ribbon */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>Facility:</span>
                  <div style={{ width: '180px' }}>
                    <Select
                      value={selectedFacility?.id || ''}
                      onChange={(e) => {
                        const found = facilities.find((f) => f.id === Number(e.target.value));
                        if (found) handleSelectFacility(found);
                      }}
                      options={facilities.map((f) => ({ value: f.id, label: f.name }))}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>Zone:</span>
                  <div style={{ width: '160px' }}>
                    <Select
                      value={selectedZone?.id || ''}
                      onChange={(e) => {
                        const found = zones.find((z) => z.id === Number(e.target.value));
                        if (found) handleSelectZone(found);
                      }}
                      options={zones.map((z) => ({ value: z.id, label: z.name }))}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>Vehicle:</span>
                  <div style={{ width: '140px' }}>
                    <Select
                      value={slotVehicleFilter}
                      onChange={(e) => setSlotVehicleFilter(e.target.value)}
                      options={[
                        { value: 'all', label: 'All Types' },
                        { value: 'car', label: 'Car' },
                        { value: 'ev', label: 'EV' },
                        { value: 'bike', label: 'Bike' },
                      ]}
                    />
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <Button variant="primary" size="sm" leftIcon={<Plus size={15} />} onClick={handleOpenCreateSlot}>
                  Add Slot
                </Button>
              </div>
            </div>
          </Card>

          {/* Interactive Slot Grid for Selected Zone */}
          {selectedZone && (
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Radio size={18} color="var(--pz-secondary)" />
                  <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                    Live Bay Matrix: {selectedZone.name}
                  </h3>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)' }}>
                  Click slot status dropdown below to trigger hardware telemetry override
                </span>
              </div>

              <SlotGrid
                slots={slots.filter((s) => (slotVehicleFilter === 'all' ? true : s.vehicle_type === slotVehicleFilter))}
                zoneName={selectedZone.name}
                recentlyUpdatedSlotIds={recentlyUpdatedSlotIds}
              />
            </Card>
          )}

          {/* Slot Operations & Telemetry Override Table */}
          <Card>
            <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '1rem' }}>
              Slot Telemetry Overrides &amp; Management
            </h3>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--pz-border-subtle)', color: 'var(--pz-text-muted)' }}>
                    <th style={{ padding: '10px 12px' }}>Slot Bay</th>
                    <th style={{ padding: '10px 12px' }}>Vehicle Class</th>
                    <th style={{ padding: '10px 12px' }}>Current State</th>
                    <th style={{ padding: '10px 12px' }}>Live Telemetry Override</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {slots
                    .filter((s) => (slotVehicleFilter === 'all' ? true : s.vehicle_type === slotVehicleFilter))
                    .map((s) => (
                      <tr key={s.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '12px' }}>
                          <span style={{ fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                            {s.slot_number}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>
                            ID #{s.id}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textTransform: 'uppercase', color: 'var(--pz-text-secondary)' }}>
                          {s.vehicle_type}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <StatusBadge status={s.status} type="slot" />
                        </td>
                        <td style={{ padding: '12px' }}>
                          <div style={{ display: 'inline-flex', gap: '4px' }}>
                            {(['available', 'occupied', 'reserved', 'maintenance'] as ParkingSlotStatus[]).map((st) => (
                              <button
                                key={st}
                                onClick={() => handleOverrideSlotStatus(s.id, st)}
                                style={{
                                  padding: '3px 8px',
                                  borderRadius: '4px',
                                  fontSize: '0.6875rem',
                                  fontWeight: 600,
                                  textTransform: 'uppercase',
                                  cursor: 'pointer',
                                  border: s.status === st ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
                                  backgroundColor: s.status === st ? 'rgba(0, 229, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                                  color: s.status === st ? 'var(--pz-secondary)' : 'var(--pz-text-muted)',
                                }}
                              >
                                {st}
                              </button>
                            ))}
                          </div>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <Button variant="outline" size="sm" onClick={() => handleOpenEditSlot(s)}>
                              <Edit size={13} />
                            </Button>
                            <Button variant="danger" size="sm" onClick={() => setDeletingSlotId(s.id)}>
                              <Trash2 size={13} />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 5: RESERVATIONS MONITORING                            */}
      {/* ========================================================= */}
      {activeTab === 'reservations' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                System-Wide Reservation Registry
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                Authorized administrator overview of all active, upcoming, and cancelled booking records.
              </p>
            </div>

            <div style={{ width: '180px' }}>
              <Select
                value={reservationStatusFilter}
                onChange={(e) => setReservationStatusFilter(e.target.value)}
                options={[
                  { value: 'all', label: 'All Statuses' },
                  { value: 'confirmed', label: 'Confirmed' },
                  { value: 'pending', label: 'Pending' },
                  { value: 'completed', label: 'Completed' },
                  { value: 'cancelled', label: 'Cancelled' },
                ]}
              />
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--pz-border-subtle)', color: 'var(--pz-text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Booking ID</th>
                  <th style={{ padding: '10px 12px' }}>User ID</th>
                  <th style={{ padding: '10px 12px' }}>Bay Target</th>
                  <th style={{ padding: '10px 12px' }}>Start Time</th>
                  <th style={{ padding: '10px 12px' }}>End Time</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Admin Actions</th>
                </tr>
              </thead>
              <tbody>
                {reservations
                  .filter((r) => (reservationStatusFilter === 'all' ? true : r.status === reservationStatusFilter))
                  .map((res) => (
                    <tr key={res.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#FFFFFF' }}>
                        #{res.id}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--pz-text-secondary)' }}>User #{res.user_id}</td>
                      <td style={{ padding: '12px', color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                        Slot #{res.slot_id}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--pz-text-muted)' }}>
                        {new Date(res.reservation_start).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--pz-text-muted)' }}>
                        {new Date(res.reservation_end).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <StatusBadge status={res.status} type="reservation" />
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        {(res.status === 'confirmed' || res.status === 'pending') && (
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => setCancellingReservationId(res.id)}
                          >
                            Cancel
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ========================================================= */}
      {/* TAB 6: SESSIONS MONITORING                                */}
      {/* ========================================================= */}
      {activeTab === 'sessions' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                System-Wide Parking Sessions
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                Real-time active ingress sessions, gate clearances, and completed durations.
              </p>
            </div>

            <div style={{ width: '180px' }}>
              <Select
                value={sessionStatusFilter}
                onChange={(e) => setSessionStatusFilter(e.target.value)}
                options={[
                  { value: 'all', label: 'All Sessions' },
                  { value: 'active', label: 'Active In-Progress' },
                  { value: 'completed', label: 'Completed' },
                ]}
              />
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--pz-border-subtle)', color: 'var(--pz-text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Session ID</th>
                  <th style={{ padding: '10px 12px' }}>User ID</th>
                  <th style={{ padding: '10px 12px' }}>Bay Target</th>
                  <th style={{ padding: '10px 12px' }}>Check-In</th>
                  <th style={{ padding: '10px 12px' }}>Duration</th>
                  <th style={{ padding: '10px 12px' }}>Fee</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Admin Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions
                  .filter((s) => (sessionStatusFilter === 'all' ? true : s.status === sessionStatusFilter))
                  .map((sess) => (
                    <tr key={sess.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#FFFFFF' }}>
                        #{sess.id}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--pz-text-secondary)' }}>User #{sess.user_id}</td>
                      <td style={{ padding: '12px', color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                        Slot #{sess.slot_id}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--pz-text-muted)' }}>
                        {new Date(sess.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td style={{ padding: '12px', color: '#FFFFFF' }}>
                        {sess.duration_minutes ? `${sess.duration_minutes}m` : 'In Progress'}
                      </td>
                      <td style={{ padding: '12px', color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                        ${sess.fee_amount != null ? Number(sess.fee_amount).toFixed(2) : 'Accruing'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <StatusBadge status={sess.status} type="general" />
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        {sess.status === 'active' && (
                          <Button
                            variant="danger"
                            size="sm"
                            leftIcon={<StopCircle size={13} />}
                            onClick={() => setEndingSessionId(sess.id)}
                          >
                            End Session
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ========================================================= */}
      {/* TAB 7: BILLING & LEDGER MONITORING                        */}
      {/* ========================================================= */}
      {activeTab === 'payments' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
            <Card glow="purple">
              <span style={{ fontSize: '0.75rem', color: '#C084FC', textTransform: 'uppercase' }}>
                Total Revenue Settled
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                ${systemMetrics.totalRevenueSettled.toFixed(2)}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-success)', marginTop: '4px', display: 'block' }}>
                100% Real Payment Reconciliation
              </span>
            </Card>

            <Card>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                Pending Invoices
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: systemMetrics.totalRevenuePending > 0 ? 'var(--pz-warning)' : '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                ${systemMetrics.totalRevenuePending.toFixed(2)}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', marginTop: '4px', display: 'block' }}>
                Awaiting Gate Ingress Checkout
              </span>
            </Card>

            <Card>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                Payment Transactions
              </span>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                {payments.length} Records
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                PCI-DSS Secured Token Ledger
              </span>
            </Card>
          </div>

          <Card>
            <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '1rem' }}>
              Financial Transaction Ledger
            </h3>

            {payments.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--pz-border-subtle)', color: 'var(--pz-text-muted)' }}>
                      <th style={{ padding: '10px 12px' }}>Txn ID</th>
                      <th style={{ padding: '10px 12px' }}>Session</th>
                      <th style={{ padding: '10px 12px' }}>User ID</th>
                      <th style={{ padding: '10px 12px' }}>Amount</th>
                      <th style={{ padding: '10px 12px' }}>Method</th>
                      <th style={{ padding: '10px 12px' }}>Status</th>
                      <th style={{ padding: '10px 12px' }}>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((p) => (
                      <tr key={p.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>
                          #{p.id}
                        </td>
                        <td style={{ padding: '12px', color: 'var(--pz-secondary)' }}>
                          Session #{p.session_id}
                        </td>
                        <td style={{ padding: '12px', color: 'var(--pz-text-secondary)' }}>
                          User #{p.user_id}
                        </td>
                        <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#FFFFFF' }}>
                          ${Number(p.amount).toFixed(2)}
                        </td>
                        <td style={{ padding: '12px', textTransform: 'uppercase', color: 'var(--pz-text-muted)' }}>
                          {p.payment_method || 'CARD'}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <StatusBadge status={p.payment_status} type="payment" />
                        </td>
                        <td style={{ padding: '12px', color: 'var(--pz-text-muted)' }}>
                          {new Date(p.created_at).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--pz-text-secondary)' }}>
                No payment transactions recorded yet.
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 8: AI PREDICTIVE OPERATIONS                          */}
      {/* ========================================================= */}
      {activeTab === 'ai' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Brain size={18} color="#C084FC" />
                  <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                    AI Predictive Neural Operations
                  </h3>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                  Realtime LSTM capacity forecasts, gate latency models, and zone density matrix.
                </p>
              </div>

              <div style={{ width: '220px' }}>
                <Select
                  value={selectedFacility?.id || ''}
                  onChange={(e) => {
                    const found = facilities.find((f) => f.id === Number(e.target.value));
                    if (found) handleSelectFacility(found);
                  }}
                  options={facilities.map((f) => ({ value: f.id, label: f.name }))}
                />
              </div>
            </div>

            {aiDecision ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                <div style={{ padding: '14px', borderRadius: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--pz-border-subtle)' }}>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                    Arrival Certainty Horizon
                  </span>
                  <div style={{ fontSize: '1.625rem', fontWeight: 800, color: '#00E5FF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    {aiDecision.availability_probability != null ? `${aiDecision.availability_probability.toFixed(0)}%` : '--'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                    Confidence: {(aiDecision.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                <div style={{ padding: '14px', borderRadius: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--pz-border-subtle)' }}>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                    Occupancy Risk Level
                  </span>
                  <div
                    style={{
                      fontSize: '1.625rem',
                      fontWeight: 800,
                      fontFamily: 'var(--font-mono)',
                      marginTop: '4px',
                      color:
                        aiDecision.occupancy_risk === 'HIGH'
                          ? 'var(--pz-error)'
                          : aiDecision.occupancy_risk === 'MEDIUM'
                          ? 'var(--pz-warning)'
                          : 'var(--pz-success)',
                    }}
                  >
                    {aiDecision.occupancy_risk || 'OPTIMAL'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                    Dynamic threshold calibrated
                  </span>
                </div>

                <div style={{ padding: '14px', borderRadius: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--pz-border-subtle)' }}>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                    Gate Ingress Queue
                  </span>
                  <div style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    {aiDecision.queue_wait_minutes != null ? `${aiDecision.queue_wait_minutes.toFixed(1)}m` : '< 1m'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                    Throughput rate: Optimal
                  </span>
                </div>

                <div style={{ padding: '14px', borderRadius: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--pz-border-subtle)' }}>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase' }}>
                    Forecast Occupancy (+20m)
                  </span>
                  <div style={{ fontSize: '1.625rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                    {aiDecision.forecast_occupancy != null ? `${aiDecision.forecast_occupancy.toFixed(0)}%` : '--'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                    Current: {aiDecision.current_occupancy}%
                  </span>
                </div>
              </div>
            ) : (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--pz-text-muted)' }}>
                AI predictive analytics temporarily offline for this facility. Live IoT telemetry remains operational.
              </div>
            )}

            {/* Zone Analytics Matrix if available */}
            {zoneAnalytics && zoneAnalytics.zones && zoneAnalytics.zones.length > 0 && (
              <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--pz-border-subtle)' }}>
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.75rem' }}>
                  Zone Congestion Density
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                  {zoneAnalytics.zones.map((zItem) => (
                    <div
                      key={zItem.zone_id}
                      style={{
                        padding: '10px',
                        borderRadius: '8px',
                        backgroundColor: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--pz-border-subtle)',
                      }}
                    >
                      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#FFFFFF' }}>
                        Zone #{zItem.zone_id}
                      </span>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.75rem' }}>
                        <span style={{ color: 'var(--pz-text-muted)' }}>Density:</span>
                        <span style={{ color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                          {(zItem.density_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: CREATE / EDIT FACILITY                             */}
      {/* ========================================================= */}
      <Modal
        isOpen={isFacilityModalOpen}
        onClose={() => setIsFacilityModalOpen(false)}
        title={editingFacility ? 'Edit Parking Facility' : 'Create New Parking Facility'}
        description="Configure operational parameters, coordinates, and bay capacity."
        maxWidth="500px"
      >
        <form onSubmit={handleSaveFacility} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
              Facility Name *
            </label>
            <Input
              required
              value={facilityFormData.name}
              onChange={(e) => setFacilityFormData({ ...facilityFormData, name: e.target.value })}
              placeholder="e.g. Central Horizon Parking"
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
              Address *
            </label>
            <Input
              required
              value={facilityFormData.address}
              onChange={(e) => setFacilityFormData({ ...facilityFormData, address: e.target.value })}
              placeholder="e.g. 100 Innovation Boulevard"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                City
              </label>
              <Input
                value={facilityFormData.city || ''}
                onChange={(e) => setFacilityFormData({ ...facilityFormData, city: e.target.value })}
                placeholder="Metropolis"
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Total Bay Capacity *
              </label>
              <Input
                type="number"
                required
                min={1}
                value={facilityFormData.total_slots || 50}
                onChange={(e) => setFacilityFormData({ ...facilityFormData, total_slots: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Opens At
              </label>
              <Input
                type="time"
                value={facilityFormData.operating_start_time || '06:00'}
                onChange={(e) => setFacilityFormData({ ...facilityFormData, operating_start_time: e.target.value })}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Closes At
              </label>
              <Input
                type="time"
                value={facilityFormData.operating_end_time || '23:00'}
                onChange={(e) => setFacilityFormData({ ...facilityFormData, operating_end_time: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            <input
              type="checkbox"
              id="fac-active"
              checked={facilityFormData.is_active ?? true}
              onChange={(e) => setFacilityFormData({ ...facilityFormData, is_active: e.target.checked })}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="fac-active" style={{ fontSize: '0.8125rem', color: '#FFFFFF', cursor: 'pointer' }}>
              Facility Active &amp; Accepting Vehicles
            </label>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '1rem' }}>
            <Button variant="outline" type="button" onClick={() => setIsFacilityModalOpen(false)} style={{ flex: 1 }}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={isActionLoading} style={{ flex: 1 }}>
              {editingFacility ? 'Save Changes' : 'Create Facility'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ========================================================= */}
      {/* MODAL: CREATE / EDIT ZONE                                 */}
      {/* ========================================================= */}
      <Modal
        isOpen={isZoneModalOpen}
        onClose={() => setIsZoneModalOpen(false)}
        title={editingZone ? 'Edit Zone' : 'Create Zone'}
        description={`Facility: ${selectedFacility?.name || 'Selected Garage'}`}
        maxWidth="440px"
      >
        <form onSubmit={handleSaveZone} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
              Zone Name *
            </label>
            <Input
              required
              value={zoneFormData.name}
              onChange={(e) => setZoneFormData({ ...zoneFormData, name: e.target.value })}
              placeholder="e.g. Zone A (Express Deck)"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Floor Level
              </label>
              <Input
                type="number"
                value={zoneFormData.floor_number ?? 1}
                onChange={(e) => setZoneFormData({ ...zoneFormData, floor_number: Number(e.target.value) })}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Capacity (Bays)
              </label>
              <Input
                type="number"
                min={1}
                value={zoneFormData.total_slots ?? 20}
                onChange={(e) => setZoneFormData({ ...zoneFormData, total_slots: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="checkbox"
              id="zone-active"
              checked={zoneFormData.is_active ?? true}
              onChange={(e) => setZoneFormData({ ...zoneFormData, is_active: e.target.checked })}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="zone-active" style={{ fontSize: '0.8125rem', color: '#FFFFFF', cursor: 'pointer' }}>
              Zone Active
            </label>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '1rem' }}>
            <Button variant="outline" type="button" onClick={() => setIsZoneModalOpen(false)} style={{ flex: 1 }}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={isActionLoading} style={{ flex: 1 }}>
              {editingZone ? 'Save Changes' : 'Create Zone'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ========================================================= */}
      {/* MODAL: CREATE / EDIT SLOT                                 */}
      {/* ========================================================= */}
      <Modal
        isOpen={isSlotModalOpen}
        onClose={() => setIsSlotModalOpen(false)}
        title={editingSlot ? 'Edit Slot Bay' : 'Create New Slot Bay'}
        description={`Zone: ${selectedZone?.name || 'Selected Zone'}`}
        maxWidth="440px"
      >
        <form onSubmit={handleSaveSlot} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
              Slot Identifier *
            </label>
            <Input
              required
              value={slotFormData.slot_number}
              onChange={(e) => setSlotFormData({ ...slotFormData, slot_number: e.target.value })}
              placeholder="e.g. A-14 or EV-02"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Vehicle Class
              </label>
              <Select
                value={slotFormData.vehicle_type || 'car'}
                onChange={(e) => setSlotFormData({ ...slotFormData, vehicle_type: e.target.value as VehicleType })}
                options={[
                  { value: 'car', label: 'Car' },
                  { value: 'ev', label: 'EV Fast-Charge' },
                  { value: 'bike', label: 'Bike' },
                  { value: 'motorcycle', label: 'Motorcycle' },
                ]}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '4px' }}>
                Initial State
              </label>
              <Select
                value={slotFormData.status || 'available'}
                onChange={(e) => setSlotFormData({ ...slotFormData, status: e.target.value as ParkingSlotStatus })}
                options={[
                  { value: 'available', label: 'Available' },
                  { value: 'occupied', label: 'Occupied' },
                  { value: 'reserved', label: 'Reserved' },
                  { value: 'maintenance', label: 'Maintenance' },
                ]}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="checkbox"
              id="slot-active"
              checked={slotFormData.is_active ?? true}
              onChange={(e) => setSlotFormData({ ...slotFormData, is_active: e.target.checked })}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="slot-active" style={{ fontSize: '0.8125rem', color: '#FFFFFF', cursor: 'pointer' }}>
              Slot Active in Mesh
            </label>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '1rem' }}>
            <Button variant="outline" type="button" onClick={() => setIsSlotModalOpen(false)} style={{ flex: 1 }}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={isActionLoading} style={{ flex: 1 }}>
              {editingSlot ? 'Save Changes' : 'Create Slot'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Confirmation: Delete Facility */}
      <ConfirmationDialog
        isOpen={deletingFacilityId !== null}
        onClose={() => setDeletingFacilityId(null)}
        onConfirm={handleConfirmDeleteFacility}
        title="Delete Parking Facility"
        message="Are you sure you want to delete this parking facility? All associated zones, slot sensors, and historical telemetry will be permanently removed."
        confirmText="Delete Facility"
        cancelText="Cancel"
        variant="danger"
        isLoading={isActionLoading}
      />

      {/* Confirmation: Delete Zone */}
      <ConfirmationDialog
        isOpen={deletingZoneId !== null}
        onClose={() => setDeletingZoneId(null)}
        onConfirm={handleConfirmDeleteZone}
        title="Delete Parking Zone"
        message="Are you sure you want to delete this zone? All slots assigned to this zone will be deleted."
        confirmText="Delete Zone"
        cancelText="Cancel"
        variant="danger"
        isLoading={isActionLoading}
      />

      {/* Confirmation: Delete Slot */}
      <ConfirmationDialog
        isOpen={deletingSlotId !== null}
        onClose={() => setDeletingSlotId(null)}
        onConfirm={handleConfirmDeleteSlot}
        title="Delete Parking Bay"
        message="Are you sure you want to remove this slot sensor from the system mesh?"
        confirmText="Delete Bay"
        cancelText="Cancel"
        variant="danger"
        isLoading={isActionLoading}
      />

      {/* Confirmation: Cancel Reservation */}
      <ConfirmationDialog
        isOpen={cancellingReservationId !== null}
        onClose={() => setCancellingReservationId(null)}
        onConfirm={handleConfirmCancelReservation}
        title="Admin Reservation Cancellation"
        message={`Are you sure you want to cancel Reservation #${cancellingReservationId}? The assigned bay will be released back to the live public pool.`}
        confirmText="Cancel Reservation"
        cancelText="Keep Booking"
        variant="danger"
        isLoading={isActionLoading}
      />

      {/* Confirmation: End Session */}
      <ConfirmationDialog
        isOpen={endingSessionId !== null}
        onClose={() => setEndingSessionId(null)}
        onConfirm={handleConfirmEndSession}
        title="Admin Force End Session"
        message={`Are you sure you want to force-end Session #${endingSessionId}? The gate ingress barrier will disengage and the parking slot will be set to available.`}
        confirmText="End Session"
        cancelText="Keep Parked"
        variant="danger"
        isLoading={isActionLoading}
      />

      <style>{`
        @media (max-width: 1024px) {
          .admin-overview-col { grid-column: span 12 !important; }
        }
      `}</style>
    </div>
  );
};

export default Admin;
