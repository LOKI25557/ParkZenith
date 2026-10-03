import React, { useEffect, useState } from 'react';
import { sessionsApi } from '../api/sessions';
import { useToast } from '../components/ui/Toast';
import type { ParkingSession } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Car, StopCircle, Receipt } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Sessions: React.FC = () => {
  const [sessions, setSessions] = useState<ParkingSession[]>([]);
  const [activeSession, setActiveSession] = useState<ParkingSession | null>(null);
  const [elapsedMinutes, setElapsedMinutes] = useState(42);
  const [isLoading, setIsLoading] = useState(true);
  const [isEnding, setIsEnding] = useState(false);

  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      const data = await sessionsApi.getSessions();
      const list = Array.isArray(data) ? data : [];
      setSessions(list);
      const ongoing = list.find((s) => s.status === 'active');
      setActiveSession(ongoing || null);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  // Duration timer ticker for active session
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedMinutes((prev) => prev + 1);
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  const handleEndSession = async () => {
    if (!activeSession) return;
    setIsEnding(true);
    try {
      await sessionsApi.endSession(activeSession.id);
      success('Parking session ended. Proceeding to payment ledger.', 'Session Completed');
      setActiveSession(null);
      loadSessions();
      navigate('/payments');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Could not end session. Please retry.';
      toastError(msg, 'Session Error');
    } finally {
      setIsEnding(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <Breadcrumb items={[{ label: 'Parking Sessions' }]} />
        <h1 className="text-page-title" style={{ marginTop: '0.75rem' }}>Parking Sessions</h1>
        <p className="text-body" style={{ marginTop: '4px' }}>
          Live session telemetry, duration monitoring, and billing settlement.
        </p>
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
                Slot #{activeSession.slot_id} • Metropolis Central
              </h2>

              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
                Ingress check-in: {new Date(activeSession.check_in_time).toLocaleTimeString()} • ALPR Confirmed
              </p>
            </div>

            {/* Live Accrued Fee & Timer */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>Duration</span>
                <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                  {elapsedMinutes}m
                </span>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>Accrued Fee</span>
                <span style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  ${(3.50 * (elapsedMinutes / 60)).toFixed(2)}
                </span>
              </div>

              <Button
                variant="danger"
                size="md"
                leftIcon={<StopCircle size={16} />}
                onClick={handleEndSession}
                isLoading={isEnding}
              >
                End Session &amp; Pay
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
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>DURATION</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>FEE</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>STATUS</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((sess) => (
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
                        Slot #{sess.slot_id} • Metropolis Hub
                      </td>
                      <td style={{ padding: '14px 18px', color: 'var(--pz-text-secondary)' }}>
                        {new Date(sess.check_in_time).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td style={{ padding: '14px 18px', color: 'var(--pz-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                        {sess.duration_minutes ? `${sess.duration_minutes}m` : 'Ongoing'}
                      </td>
                      <td style={{ padding: '14px 18px', fontWeight: 600, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                        ${sess.fee_amount ? sess.fee_amount.toFixed(2) : '3.50'}
                      </td>
                      <td style={{ padding: '14px 18px' }}>
                        <StatusBadge status={sess.status} type="reservation" size="sm" />
                      </td>
                      <td style={{ padding: '14px 18px' }}>
                        <Button
                          variant="ghost"
                          size="sm"
                          leftIcon={<Receipt size={14} />}
                          onClick={() => navigate('/payments')}
                        >
                          Receipt
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Sessions;
