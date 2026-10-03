import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import { parkingApi } from '../api/parking';
import { sessionsApi } from '../api/sessions';
import { reservationsApi } from '../api/reservations';
import { aiApi } from '../api/ai';
import { useWebSocket } from '../hooks/useWebSocket';
import type { Facility, Availability, ParkingSession, Reservation, Slot, ParkingSlotStatus } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { SlotGrid } from '../components/parking/SlotGrid';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import {
  CalendarCheck,
  Brain,
  Search,
  ArrowRight,
  Activity,
  Map as MapIcon,
} from 'lucide-react';

import { ConnectionStatusBadge } from '../components/parking/ConnectionStatusBadge';
import { LiveDataTimestamp } from '../components/parking/LiveDataTimestamp';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [facilityAvailMap, setFacilityAvailMap] = useState<Record<number, Availability>>({});
  const [facilitySlots, setFacilitySlots] = useState<Slot[]>([]);
  const [activeSession, setActiveSession] = useState<ParkingSession | null>(null);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [aiDecision, setAiDecision] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [recentlyUpdatedSlotIds, setRecentlyUpdatedSlotIds] = useState<Set<number>>(new Set());

  // Real-time WebSocket hook subscribed to facility events
  const { latestMessage, connectionStatus, isConnected, isStale, lastMessageAt, reconnect } =
    useWebSocket('*', selectedFacility?.id);

  const handleSelectFacility = async (fac: Facility) => {
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

    try {
      const pred = await aiApi.getPrediction(fac.id);
      setAiDecision(pred);
    } catch {
      setAiDecision(null);
    }
  };

  // Fetch initial dashboard data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        // Facilities
        const facs = await parkingApi.getFacilities();
        setFacilities(facs);

        if (facs && facs.length > 0) {
          const firstFac = facs[0];
          setSelectedFacility(firstFac);

          // Availability
          try {
            const avail = await parkingApi.getFacilityAvailability(firstFac.id);
            setAvailability(avail);
          } catch {
            setAvailability(null);
          }

          // Fetch availability for the top facilities for the hub cards
          const availMap: Record<number, Availability> = {};
          await Promise.all(
            facs.slice(0, 4).map(async (f) => {
              try {
                const a = await parkingApi.getFacilityAvailability(f.id);
                availMap[f.id] = a;
              } catch {
                // ignore if not seeded
              }
            })
          );
          setFacilityAvailMap(availMap);

          // Zones & Slots
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

          // AI Decision / Prediction
          try {
            const pred = await aiApi.getPrediction(firstFac.id);
            setAiDecision(pred);
          } catch {
            setAiDecision(null);
          }
        }

        // Sessions
        try {
          const sessions = await sessionsApi.getSessions();
          const ongoing = Array.isArray(sessions) ? sessions.find((s) => s.status === 'active') : null;
          setActiveSession(ongoing || null);
        } catch {
          // No active session
        }

        // Reservations
        try {
          const resList = await reservationsApi.getReservations();
          setReservations(Array.isArray(resList) ? resList : []);
        } catch {
          // Fallback
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  // Handle incoming real-time WebSocket messages
  useEffect(() => {
    if (!latestMessage) return;

    if (latestMessage.event === 'slot_status_changed' && latestMessage.slot_id) {
      const slotId = latestMessage.slot_id;
      const newStatus = latestMessage.new_status as ParkingSlotStatus;
      const oldStatus = latestMessage.old_status as ParkingSlotStatus;

      // Pulse visual highlight on the changed slot
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
        prev.map((s) =>
          s.id === slotId ? { ...s, status: newStatus } : s
        )
      );

      // Incrementally synchronize availability counters for the monitored facility
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
        const snapMap = new Map<number, ParkingSlotStatus>(snap.slots.map((s: any) => [s.id, s.status as ParkingSlotStatus]));
        setFacilitySlots((prev) =>
          prev.map((s) => (snapMap.has(s.id) ? { ...s, status: snapMap.get(s.id)! } : s))
        );
      }
    }
  }, [latestMessage, selectedFacility]);

  const handleEndSession = async () => {
    if (!activeSession) return;
    try {
      await sessionsApi.endSession(activeSession.id);
      success('Parking session ended successfully.', 'Session Concluded');
      setActiveSession(null);
    } catch {
      toastError('Could not end session. Please retry.', 'Action Failed');
    }
  };

  if (isLoading && !selectedFacility) {
    return <LoadingSpinner size="lg" label="Synchronizing autonomous command hub..." />;
  }

  const upcomingReservations = reservations.filter((r) => r.status === 'confirmed' || r.status === 'pending');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* 1. Mission Control Welcome Banner */}
      <div
        className="glass-card"
        style={{
          padding: '2rem',
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
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ✦ AUTONOMOUS COCKPIT SYNCHRONIZED
            </span>
          </div>
          <h2 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
            Welcome back, {user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'Alex'}
          </h2>
          <p style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
            Registered Vehicle:{' '}
            <strong style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {user?.vehicle_number || 'None registered'}
            </strong>{' '}
            • ALPR Fast-Pass Active
          </p>
        </div>

        {/* Quick Actions */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
          <Button
            variant="primary"
            size="md"
            leftIcon={<Search size={16} />}
            onClick={() => navigate('/parking')}
          >
            Find Parking
          </Button>
          <Button
            variant="outline"
            size="md"
            leftIcon={<CalendarCheck size={16} />}
            onClick={() => navigate('/reservations')}
          >
            My Reservations
          </Button>
          <Button
            variant="outline"
            size="md"
            leftIcon={<MapIcon size={16} />}
            onClick={() => navigate('/parking?view=map')}
          >
            Parking Map
          </Button>
          <Button
            variant="ai"
            size="md"
            leftIcon={<Brain size={16} />}
            onClick={() => navigate('/predictions')}
          >
            AI Predictions
          </Button>
        </div>
      </div>

      {/* 2. Key Telemetry Metrics Row (4 Cards) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
        {/* Active Session Card */}
        <Card
          glow={activeSession ? 'cyan' : 'none'}
          style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Active Session
              </span>
              <span
                style={{
                  fontSize: '0.6875rem',
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: activeSession ? 'rgba(0, 229, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  color: activeSession ? 'var(--pz-secondary)' : 'var(--pz-text-muted)',
                }}
              >
                {activeSession ? 'In Progress' : 'No Active Session'}
              </span>
            </div>

            {activeSession ? (
              <div>
                <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  Slot #{activeSession.slot_id}
                </span>
                <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', display: 'block', marginTop: '2px' }}>
                  Fee Accrued: ${activeSession.fee_amount?.toFixed(2) || '4.50'}
                </span>
              </div>
            ) : (
              <div>
                <span style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--pz-text-secondary)' }}>
                  Vehicle Parked Off-Grid
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block', marginTop: '2px' }}>
                  Reserve a bay for seamless ALPR ingress
                </span>
              </div>
            )}
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            {activeSession ? (
              <Button variant="danger" size="sm" onClick={handleEndSession} style={{ width: '100%' }}>
                End Session &amp; Pay
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => navigate('/parking')} style={{ width: '100%', color: 'var(--pz-secondary)' }}>
                Park Now &rarr;
              </Button>
            )}
          </div>
        </Card>

        {/* Upcoming Reservations */}
        <Card style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Upcoming Bookings
              </span>
              <CalendarCheck size={16} color="var(--pz-secondary)" />
            </div>

            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {upcomingReservations.length} Active
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
              {upcomingReservations.length > 0
                ? `Next: Slot #${upcomingReservations[0].slot_id}`
                : 'No bookings scheduled'}
            </span>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            <Button variant="ghost" size="sm" onClick={() => navigate('/reservations')} style={{ width: '100%' }}>
              View Bookings &rarr;
            </Button>
          </div>
        </Card>

        {/* Live Occupancy Index */}
        <Card style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Live Availability
                </span>
                {isConnected && (
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '1px 6px',
                      borderRadius: '9999px',
                      backgroundColor: 'rgba(16, 185, 129, 0.15)',
                      color: 'var(--pz-success)',
                      fontSize: '0.625rem',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                    }}
                  >
                    <span
                      style={{
                        width: '5px',
                        height: '5px',
                        borderRadius: '50%',
                        backgroundColor: '#10B981',
                        animation: 'pulse-glow 2s infinite',
                      }}
                    />
                    LIVE
                  </span>
                )}
              </div>
              <Activity size={16} color="var(--pz-success)" />
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
                {availability ? availability.available : (selectedFacility ? '—' : '0')}
              </span>
              <span style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)' }}>
                / {availability?.total_slots ?? selectedFacility?.total_slots ?? 0} Free Bays
              </span>
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)', marginTop: '2px', display: 'block' }}>
              {selectedFacility?.name || 'No Facility Selected'}
            </span>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            {(() => {
              const occPct = availability?.occupancy_percentage ?? 0;
              const barColor = occPct > 85 ? '#F43F5E' : occPct > 65 ? '#F59E0B' : '#10B981';
              return (
                <div>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-secondary)' }}>
                      {occPct}% Occupied
                    </span>
                    <LiveDataTimestamp timestamp={lastMessageAt} status={connectionStatus} isStale={isStale} />
                  </div>
                </div>
              );
            })()}
          </div>
        </Card>

        {/* AI Confidence Engine */}
        <Card glow="purple" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: '#C084FC', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                AI Arrival Score
              </span>
              <Brain size={16} color="#C084FC" />
            </div>

            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#00E5FF', fontFamily: 'var(--font-mono)' }}>
              {aiDecision?.availability_probability != null ? `${aiDecision.availability_probability.toFixed(0)}%` : '--'}
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
              {aiDecision ? (
                aiDecision.occupancy_risk === 'HIGH'
                  ? 'High demand anticipated (+20m window)'
                  : aiDecision.occupancy_risk === 'MEDIUM'
                  ? 'Moderate availability (+20m window)'
                  : 'High arrival certainty (+20m window)'
              ) : (
                'Real-time neural arrival estimation'
              )}
            </span>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '0.75rem' }}>
            <Button variant="ghost" size="sm" onClick={() => navigate('/predictions')} style={{ width: '100%', color: '#C084FC' }}>
              View Neural Forecast &rarr;
            </Button>
          </div>
        </Card>
      </div>

      {/* 3. Main Grid: Slot Visualizer + AI Side Deck */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1.5rem' }}>
        {/* Left Column (8 cols): Real-time Slot Visualizer */}
        <div style={{ gridColumn: 'span 8' }} className="dashboard-main-col">
          {selectedFacility && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--pz-text-muted)' }}>
                  Monitored Garage:
                </span>
                <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                  {selectedFacility.name}
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
                  Bay Details
                </Button>
              </div>
            </div>
          )}

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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '1rem' }}>
              <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>Monitored Hub:</span>
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
                    }}
                  >
                    {f.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column (4 cols): Predictive Intelligence & Live Stream */}
        <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} className="dashboard-side-col">
          {/* AI Intelligence Mini-Card */}
          <Card glow="purple">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
              <Brain size={18} color="#C084FC" />
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF' }}>
                Predictive Intel
              </h4>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
                  <span style={{ color: 'var(--pz-text-secondary)' }}>Gate Queue Latency</span>
                  <span style={{ color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {aiDecision?.queue_wait_minutes != null ? `${aiDecision.queue_wait_minutes.toFixed(1)} mins` : '< 1 min'}
                  </span>
                </div>
              </div>

              <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
                  <span style={{ color: 'var(--pz-text-secondary)' }}>Occupancy Risk</span>
                  <span
                    style={{
                      color:
                        aiDecision?.occupancy_risk === 'HIGH'
                          ? 'var(--pz-error)'
                          : aiDecision?.occupancy_risk === 'MEDIUM'
                          ? 'var(--pz-warning)'
                          : 'var(--pz-success)',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                    }}
                  >
                    {aiDecision?.occupancy_risk ? `${aiDecision.occupancy_risk} RISK` : 'OPTIMAL'}
                  </span>
                </div>
              </div>

              <div style={{ padding: '10px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
                  <span style={{ color: 'var(--pz-text-secondary)' }}>Forecast Occupancy</span>
                  <span style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {aiDecision?.forecast_occupancy != null ? `${aiDecision.forecast_occupancy.toFixed(0)}%` : '--'}
                  </span>
                </div>
              </div>
            </div>

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

          {/* Real-time Activity Telemetry Feed */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="var(--pz-secondary)" />
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                  Live Event Stream
                </h4>
              </div>
              <span className="telemetry-pulse" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem' }}>
              <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.03)' }}>
                <span style={{ color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>14:28:12</span>
                <p style={{ color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                  ALPR Ingress: Vehicle matched at Gate B Express.
                </p>
              </div>

              <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.03)' }}>
                <span style={{ color: 'var(--pz-success)', fontFamily: 'var(--font-mono)' }}>14:26:05</span>
                <p style={{ color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                  Bay B-04 vacated • Sensor marked Available.
                </p>
              </div>

              <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.03)' }}>
                <span style={{ color: '#C084FC', fontFamily: 'var(--font-mono)' }}>14:24:40</span>
                <p style={{ color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                  LSTM weights updated: Surge factor calibrated.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* 4. Connected Facilities Discovery Strip */}
      <Card style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>Connected Garages</h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
              Real-time telemetry and capacity across active locations.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            rightIcon={<ArrowRight size={14} />}
            onClick={() => navigate('/parking')}
          >
            View All Parking ({facilities.length})
          </Button>
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
                    <span style={{ color: 'var(--pz-secondary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      Explore &rarr;
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

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
