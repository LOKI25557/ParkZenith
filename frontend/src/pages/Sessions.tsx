import React, { useEffect, useState, useMemo } from 'react';
import { sessionsApi } from '../api/sessions';
import { parkingApi } from '../api/parking';
import { paymentsApi } from '../api/payments';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import type { ParkingSession, Slot, Facility, Payment } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { Modal } from '../components/ui/Modal';
import {
  Car,
  StopCircle,
  Receipt,
  CheckCircle2,
  ShieldCheck,
  Download,
  Plus,
  Zap,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Sessions: React.FC = () => {
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [activeSession, setActiveSession] = useState<ParkingSession | null>(null);
  const [activeSlot, setActiveSlot] = useState<Slot | null>(null);
  const [activeFacility, setActiveFacility] = useState<Facility | null>(null);

  const [slotsMap, setSlotsMap] = useState<Record<number, Slot>>({});
  const [facilitiesMap, setFacilitiesMap] = useState<Record<number, Facility>>({});

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isEnding, setIsEnding] = useState<boolean>(false);
  const [isEndDialogOpen, setIsEndDialogOpen] = useState<boolean>(false);

  // Completed session summary for modal receipt
  const [completedSessionSummary, setCompletedSessionSummary] = useState<ParkingSession | null>(null);
  const [sessionPayment, setSessionPayment] = useState<Payment | null>(null);
  const [isSettling, setIsSettling] = useState<boolean>(false);

  // Live timer tick
  const [currentTime, setCurrentTime] = useState<number>(() => Date.now());

  const { success, error: toastError } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [history, active] = await Promise.all([
        sessionsApi.getSessions(),
        sessionsApi.getActiveSession().catch(() => null),
      ]);

      const list = Array.isArray(history) ? history : [];
      setSessions(list);

      const current = active || list.find((s) => s.status === 'active') || null;
      setActiveSession(current);

      // Load facilities
      try {
        const facList = await parkingApi.getFacilities();
        const fMap: Record<number, Facility> = {};
        facList.forEach((f) => {
          fMap[f.id] = f;
        });
        setFacilitiesMap(fMap);

        // Load slots for all sessions
        const sMap: Record<number, Slot> = {};
        await Promise.all(
          list.map(async (sess) => {
            try {
              if (!sMap[sess.slot_id]) {
                const s = await parkingApi.getSlot(sess.slot_id);
                sMap[sess.slot_id] = s;
              }
            } catch {
              // ignore slot resolution error
            }
          })
        );
        setSlotsMap(sMap);

        if (current) {
          const s = sMap[current.slot_id] || (await parkingApi.getSlot(current.slot_id).catch(() => null));
          if (s) {
            setActiveSlot(s);
            const z = await parkingApi.getZone(s.zone_id).catch(() => null);
            if (z && fMap[z.facility_id]) {
              setActiveFacility(fMap[z.facility_id]);
            }
          }
        }
      } catch {
        // ignore enrichment error
      }
    } catch (err) {
      console.error('Failed to load session data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Fetch real payment for the completed session receipt
  useEffect(() => {
    if (!completedSessionSummary) {
      setSessionPayment(null);
      return;
    }
    paymentsApi
      .getSessionPayment(completedSessionSummary.id)
      .then((p) => setSessionPayment(p))
      .catch(() => setSessionPayment(null));
  }, [completedSessionSummary]);

  // Update timer every second for live session
  useEffect(() => {
    if (!activeSession) return;
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [activeSession]);

  // Compute live duration and estimated fee
  const { formattedDuration, estimatedFee } = useMemo(() => {
    if (!activeSession) {
      return { elapsedSeconds: 0, formattedDuration: '0m 0s', estimatedFee: 2.0 };
    }

    const checkIn = new Date(activeSession.check_in_time).getTime();
    const diffSec = Math.max(0, Math.floor((currentTime - checkIn) / 1000));

    const hours = Math.floor(diffSec / 3600);
    const minutes = Math.floor((diffSec % 3600) / 60);
    const seconds = diffSec % 60;

    let durationStr = '';
    if (hours > 0) {
      durationStr = `${hours}h ${minutes}m ${seconds}s`;
    } else {
      durationStr = `${minutes}m ${seconds}s`;
    }

    // Backend PaymentService formula:
    // hours = durationMinutes / 60
    // fee = max(2.00, hours * 5.00)
    const durationMinutes = Math.max(1, Math.ceil(diffSec / 60));
    const fee = Math.max(2.0, (durationMinutes / 60.0) * 5.0);

    return {
      elapsedSeconds: diffSec,
      formattedDuration: durationStr,
      estimatedFee: fee,
    };
  }, [activeSession, currentTime]);

  const handleEndSession = async () => {
    if (!activeSession) return;
    setIsEnding(true);
    try {
      const completed = await sessionsApi.endSession(activeSession.id);
      success(
        `Session #${completed.id} completed. Total fee: $${completed.fee_amount?.toFixed(2)}.`,
        'Session Completed'
      );
      setActiveSession(null);
      setIsEndDialogOpen(false);
      setCompletedSessionSummary(completed);
      loadData();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Could not end session. Please retry.';
      toastError(msg, 'Session Error');
    } finally {
      setIsEnding(false);
    }
  };

  const handleSettlePayment = async () => {
    if (!sessionPayment) return;
    setIsSettling(true);
    try {
      const processed = await paymentsApi.processPayment(sessionPayment.id, {
        simulate_success: true,
      });
      setSessionPayment(processed);
      success(
        `Payment #${processed.id} settled successfully! Ref: ${processed.transaction_id}`,
        'Payment Confirmed'
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Could not settle payment.';
      toastError(msg, 'Payment Error');
    } finally {
      setIsSettling(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <Breadcrumb items={[{ label: 'Parking Sessions' }]} />
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '1rem', marginTop: '0.75rem' }}>
          <div>
            <h1 className="text-page-title">Parking Sessions</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              Live session telemetry, duration monitoring, and billing settlement.
            </p>
          </div>

          <Button
            variant="outline"
            leftIcon={<Plus size={16} />}
            onClick={() => navigate('/parking')}
          >
            Find Parking Bay
          </Button>
        </div>
      </div>

      {/* Prominent Active Session Card */}
      {activeSession ? (
        <Card
          glow="cyan"
          style={{
            padding: '2rem',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, rgba(26, 91, 255, 0.15) 0%, rgba(0, 229, 255, 0.08) 100%)',
            border: '2px solid var(--pz-secondary)',
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1.5rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span className="telemetry-pulse" />
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  ACTIVE REAL-TIME PARKING SESSION
                </span>
              </div>

              <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF' }}>
                {activeSlot?.slot_number ? `Bay ${activeSlot.slot_number}` : `Slot #${activeSession.slot_id}`} • {activeFacility?.name || 'Metropolis Smart Parking'}
              </h2>

              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
                Ingress check-in: {new Date(activeSession.check_in_time).toLocaleTimeString()} • ALPR Express Active
              </p>
            </div>

            {/* Live Accrued Fee & Timer */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '2rem' }}>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>Live Duration</span>
                <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  {formattedDuration}
                </span>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>Accrued Fee</span>
                <span style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  ${estimatedFee.toFixed(2)}
                </span>
              </div>

              <Button
                variant="danger"
                size="md"
                leftIcon={<StopCircle size={16} />}
                onClick={() => setIsEndDialogOpen(true)}
                isLoading={isEnding}
              >
                End Session &amp; Check Out
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {/* Session History Table */}
      <div>
        <h3 className="text-section-title" style={{ marginBottom: '1rem' }}>Session History</h3>

        {isLoading ? (
          <LoadingSpinner size="lg" label="Loading session records..." />
        ) : sessions.length === 0 ? (
          <EmptyState
            icon={<Car size={32} />}
            title="No Parking Sessions"
            description="You have not initiated any parking sessions yet."
            actionLabel="Find Parking Bay"
            onAction={() => navigate('/parking')}
          />
        ) : (
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--pz-border)', backgroundColor: 'rgba(255, 255, 255, 0.02)' }}>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>SESSION ID</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>FACILITY &amp; BAY</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>CHECK-IN</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>CHECK-OUT</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>DURATION</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>FEE</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>STATUS</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>RECEIPT</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((sess) => {
                    const slot = slotsMap[sess.slot_id];
                    const slotNumber = slot?.slot_number ? `Bay ${slot.slot_number}` : `Slot #${sess.slot_id}`;
                    const facilityName = facilitiesMap[1]?.name || 'Smart Parking Hub';

                    return (
                      <tr
                        key={sess.id}
                        style={{
                          borderBottom: '1px solid var(--pz-border-subtle)',
                          transition: 'background-color 0.15s',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', color: 'var(--pz-secondary)' }}>
                          #PS-{sess.id}
                        </td>
                        <td style={{ padding: '14px 18px', color: '#FFFFFF', fontWeight: 500 }}>
                          {slotNumber} • {facilityName}
                        </td>
                        <td style={{ padding: '14px 18px', color: 'var(--pz-text-secondary)' }}>
                          {new Date(sess.check_in_time).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td style={{ padding: '14px 18px', color: 'var(--pz-text-secondary)' }}>
                          {sess.check_out_time
                            ? new Date(sess.check_out_time).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
                            : 'Ongoing'}
                        </td>
                        <td style={{ padding: '14px 18px', color: 'var(--pz-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                          {sess.duration_minutes !== null && sess.duration_minutes !== undefined ? `${sess.duration_minutes}m` : 'Ongoing'}
                        </td>
                        <td style={{ padding: '14px 18px', fontWeight: 600, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                          ${sess.fee_amount !== null && sess.fee_amount !== undefined ? sess.fee_amount.toFixed(2) : '3.50'}
                        </td>
                        <td style={{ padding: '14px 18px' }}>
                          <StatusBadge status={sess.status} type="reservation" size="sm" />
                        </td>
                        <td style={{ padding: '14px 18px' }}>
                          <Button
                            variant="ghost"
                            size="sm"
                            leftIcon={<Receipt size={14} />}
                            onClick={() => setCompletedSessionSummary(sess)}
                          >
                            Receipt
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>

      {/* Confirmation Dialog before Ending Session */}
      <ConfirmationDialog
        isOpen={isEndDialogOpen}
        onClose={() => setIsEndDialogOpen(false)}
        onConfirm={handleEndSession}
        title="Check-Out &amp; End Session?"
        message="Are you sure you want to end your parking session? The barrier gate will be opened and your parking ledger finalized."
        confirmText="Yes, Check Out"
        variant="danger"
        isLoading={isEnding}
      />

      {/* Session Completed Receipt Modal */}
      {completedSessionSummary && (
        <Modal
          isOpen={true}
          onClose={() => setCompletedSessionSummary(null)}
          title="Parking Session Receipt"
          maxWidth="560px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '1.25rem' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'rgba(0, 230, 153, 0.12)',
                border: '2px solid var(--pz-success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--pz-success)',
              }}
            >
              <CheckCircle2 size={32} />
            </div>

            <div>
              <span
                style={{
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--pz-secondary)',
                  fontWeight: 700,
                }}
              >
                PARKZENITH SETTLED STATEMENT
              </span>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#FFFFFF', marginTop: '4px' }}>
                Session Completed
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-muted)' }}>
                REF #PS-{completedSessionSummary.id} • Verified via ALPR Ingress/Egress
              </p>
            </div>

            {/* Financial & Time Receipt Box */}
            <div
              style={{
                width: '100%',
                padding: '1.25rem',
                backgroundColor: 'var(--pz-bg-alt)',
                borderRadius: '14px',
                border: '1px solid var(--pz-border)',
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '12px',
                textAlign: 'left',
                fontSize: '0.875rem',
              }}
            >
              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>CHECK-IN TIME</span>
                <span style={{ fontWeight: 600, color: '#FFFFFF' }}>
                  {new Date(completedSessionSummary.check_in_time).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>CHECK-OUT TIME</span>
                <span style={{ fontWeight: 600, color: '#FFFFFF' }}>
                  {completedSessionSummary.check_out_time
                    ? new Date(completedSessionSummary.check_out_time).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
                    : 'Just now'}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>TOTAL DURATION</span>
                <span style={{ fontWeight: 700, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  {completedSessionSummary.duration_minutes !== null && completedSessionSummary.duration_minutes !== undefined
                    ? `${completedSessionSummary.duration_minutes} mins`
                    : '45 mins'}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>TOTAL FEE SETTLED</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  ${completedSessionSummary.fee_amount !== null && completedSessionSummary.fee_amount !== undefined
                    ? completedSessionSummary.fee_amount.toFixed(2)
                    : '5.00'}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>PARKING BAY</span>
                <span style={{ fontWeight: 600, color: '#FFFFFF' }}>
                  {slotsMap[completedSessionSummary.slot_id]?.slot_number
                    ? `Bay ${slotsMap[completedSessionSummary.slot_id].slot_number}`
                    : `Slot #${completedSessionSummary.slot_id}`}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>VEHICLE PLATE</span>
                <span style={{ fontWeight: 600, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  {user?.vehicle_number || 'REGISTERED'}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>TRANSACTION REF</span>
                <span style={{ fontWeight: 600, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  {sessionPayment?.transaction_id || (sessionPayment ? `PAY-#${sessionPayment.id}` : 'PENDING')}
                </span>
              </div>

              <div>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>PAYMENT STATUS</span>
                <div style={{ marginTop: '2px' }}>
                  <StatusBadge
                    status={sessionPayment?.payment_status || 'pending'}
                    type="payment"
                    size="sm"
                  />
                </div>
              </div>
            </div>

            {sessionPayment?.payment_status === 'pending' && (
              <div
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  backgroundColor: 'rgba(255, 179, 0, 0.1)',
                  border: '1px solid var(--pz-warning)',
                  borderRadius: '10px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div style={{ textAlign: 'left' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--pz-warning)', display: 'block' }}>
                    Payment Pending
                  </span>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)' }}>
                    Auto-debit pending authorization
                  </span>
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<Zap size={14} />}
                  onClick={handleSettlePayment}
                  isLoading={isSettling}
                >
                  Settle Now
                </Button>
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--pz-success)' }}>
              <ShieldCheck size={16} />
              <span>Ingress/Egress barrier gate cycle complete</span>
            </div>

            {/* Modal Actions */}
            <div style={{ width: '100%', display: 'flex', gap: '10px', marginTop: '0.5rem' }}>
              <Button
                variant="outline"
                size="md"
                leftIcon={<Download size={14} />}
                onClick={() => window.print()}
                style={{ flex: 1 }}
              >
                Print Receipt
              </Button>

              <Button
                variant="outline"
                size="md"
                onClick={() => {
                  setCompletedSessionSummary(null);
                  navigate('/payments');
                }}
                style={{ flex: 1 }}
              >
                Billing Ledger
              </Button>

              <Button
                variant="primary"
                size="md"
                onClick={() => {
                  setCompletedSessionSummary(null);
                  navigate('/parking');
                }}
                style={{ flex: 1 }}
              >
                Book Another
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default Sessions;
