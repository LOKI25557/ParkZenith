import React, { useEffect, useState, useMemo } from 'react';
import { paymentsApi } from '../api/payments';
import { useToast } from '../components/ui/Toast';
import type { Payment, PaymentMethod } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Tabs } from '../components/ui/Tabs';
import {
  CreditCard,
  Receipt,
  CheckCircle2,
  Download,
  ShieldCheck,
  AlertCircle,
  Clock,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Payments: React.FC = () => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [selectedReceipt, setSelectedReceipt] = useState<Payment | null>(null);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Settlement processing modal state
  const [settlingPayment, setSettlingPayment] = useState<Payment | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>('card');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  const loadPayments = async () => {
    try {
      setIsLoading(true);
      const data = await paymentsApi.getMyPayments();
      setPayments(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load user payments:', err);
      setPayments([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPayments();
  }, []);

  // Compute Financial Summaries
  const { totalSettled, pendingTotal, pendingCount, settledCount } = useMemo(() => {
    let settled = 0;
    let pending = 0;
    let pCount = 0;
    let sCount = 0;

    payments.forEach((p) => {
      const amt = Number(p.amount) || 0;
      if (p.payment_status === 'success' || p.payment_status === 'completed') {
        settled += amt;
        sCount += 1;
      } else if (p.payment_status === 'pending') {
        pending += amt;
        pCount += 1;
      }
    });

    return {
      totalSettled: settled,
      pendingTotal: pending,
      pendingCount: pCount,
      settledCount: sCount,
    };
  }, [payments]);

  // Handle Processing a Pending Payment
  const handleProcessPayment = async () => {
    if (!settlingPayment) return;
    setIsProcessing(true);
    try {
      const processed = await paymentsApi.processPayment(settlingPayment.id, {
        simulate_success: true,
        payment_method: selectedMethod,
      });

      success(
        `Payment of $${Number(processed.amount).toFixed(2)} processed successfully!`,
        'Payment Settled'
      );

      setPayments((prev) =>
        prev.map((p) => (p.id === processed.id ? processed : p))
      );

      setSettlingPayment(null);
      setSelectedReceipt(processed);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to process payment.';
      toastError(detail, 'Processing Error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Filtered Payments
  const filteredPayments = useMemo(() => {
    return payments.filter((p) => {
      if (activeTab === 'all') return true;
      if (activeTab === 'success') {
        return p.payment_status === 'success' || p.payment_status === 'completed';
      }
      if (activeTab === 'pending') {
        return p.payment_status === 'pending';
      }
      if (activeTab === 'refunded') {
        return p.payment_status === 'refunded';
      }
      return true;
    });
  }, [payments, activeTab]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <Breadcrumb items={[{ label: 'Payments & Billing' }]} />
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '1rem', marginTop: '0.75rem' }}>
          <div>
            <h1 className="text-page-title">Billing &amp; Payments</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              Transaction history, automated ALPR billing, and digital payment receipts.
            </p>
          </div>

          <Button
            variant="outline"
            leftIcon={<Receipt size={16} />}
            onClick={() => navigate('/sessions')}
          >
            View Parking Sessions
          </Button>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
        <Card glow="cyan">
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Total Settled (All Time)
          </span>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#00E5FF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            ${totalSettled.toFixed(2)}
          </div>
          <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
            {settledCount} Settled Transactions
          </span>
        </Card>

        {pendingTotal > 0 ? (
          <Card
            style={{
              borderColor: 'var(--pz-warning)',
              background: 'linear-gradient(135deg, rgba(255, 179, 0, 0.1) 0%, rgba(255, 179, 0, 0.03) 100%)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-warning)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                  Outstanding Balance
                </span>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--pz-warning)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                  ${pendingTotal.toFixed(2)}
                </div>
                <span style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                  {pendingCount} Pending Invoice{pendingCount > 1 ? 's' : ''}
                </span>
              </div>
              <AlertCircle size={24} color="var(--pz-warning)" />
            </div>
          </Card>
        ) : (
          <Card>
            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Outstanding Balance
            </span>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--pz-success)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
              $0.00
            </div>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-success)', marginTop: '4px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={13} /> All invoices up to date
            </span>
          </Card>
        )}

        <Card>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Ingress &amp; Egress Express Billing
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
            <CreditCard size={20} color="var(--pz-secondary)" />
            <span style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF' }}>
              Auto-Debit Ready
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-success)', marginTop: '4px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={12} /> ALPR Smart Toll Active
          </span>
        </Card>
      </div>

      {/* Pending Settlement Alert Banner if any pending invoices exist */}
      {pendingCount > 0 && (
        <div
          style={{
            padding: '1.25rem 1.5rem',
            backgroundColor: 'rgba(255, 179, 0, 0.08)',
            border: '1.5px solid var(--pz-warning)',
            borderRadius: '16px',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                backgroundColor: 'rgba(255, 179, 0, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--pz-warning)',
              }}
            >
              <Clock size={20} />
            </div>
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                Pending Session Settlement
              </h4>
              <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', margin: '2px 0 0 0' }}>
                You have {pendingCount} completed parking session with an unsettled fee of ${pendingTotal.toFixed(2)}.
              </p>
            </div>
          </div>

          <Button
            variant="primary"
            size="sm"
            rightIcon={<ArrowRight size={14} />}
            onClick={() => {
              const pending = payments.find((p) => p.payment_status === 'pending');
              if (pending) setSettlingPayment(pending);
            }}
          >
            Settle Balance Now
          </Button>
        </div>
      )}

      {/* Filtering Tabs */}
      <Tabs
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: 'all', label: 'All Transactions', badge: payments.length },
          { id: 'success', label: 'Settled' },
          { id: 'pending', label: 'Pending', badge: pendingCount > 0 ? pendingCount : undefined },
          { id: 'refunded', label: 'Refunded' },
        ]}
      />

      {/* Transactions Table */}
      <div>
        <h3 className="text-section-title" style={{ marginBottom: '1rem' }}>Transaction Ledger</h3>

        {isLoading ? (
          <LoadingSpinner size="lg" label="Loading billing ledger..." />
        ) : filteredPayments.length === 0 ? (
          <EmptyState
            icon={<Receipt size={36} />}
            title="No Billing Records Found"
            description="You don't have any payment transactions in this category."
            actionLabel="Find Parking Bay"
            onAction={() => navigate('/parking')}
          />
        ) : (
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--pz-border)', backgroundColor: 'rgba(255, 255, 255, 0.02)' }}>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>TRANSACTION ID</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>SESSION</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>DATE</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>METHOD</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>AMOUNT</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>STATUS</th>
                    <th style={{ padding: '14px 18px', color: 'var(--pz-text-muted)', fontWeight: 600 }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPayments.map((p) => {
                    const isPending = p.payment_status === 'pending';
                    const amountVal = Number(p.amount) || 0;

                    return (
                      <tr
                        key={p.id}
                        style={{ borderBottom: '1px solid var(--pz-border-subtle)', transition: 'background 0.15s' }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', color: 'var(--pz-secondary)' }}>
                          {p.transaction_id || `TXN-PENDING-#${p.id}`}
                        </td>
                        <td style={{ padding: '14px 18px', color: '#FFFFFF', fontWeight: 500 }}>
                          Session #{p.session_id}
                        </td>
                        <td style={{ padding: '14px 18px', color: 'var(--pz-text-secondary)' }}>
                          {p.paid_at
                            ? new Date(p.paid_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
                            : new Date(p.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td style={{ padding: '14px 18px', textTransform: 'uppercase', color: 'var(--pz-text-secondary)', fontSize: '0.8125rem' }}>
                          {p.payment_method}
                        </td>
                        <td style={{ padding: '14px 18px', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                          ${amountVal.toFixed(2)}
                        </td>
                        <td style={{ padding: '14px 18px' }}>
                          <StatusBadge status={p.payment_status} type="payment" size="sm" />
                        </td>
                        <td style={{ padding: '14px 18px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {isPending ? (
                              <Button
                                variant="primary"
                                size="sm"
                                leftIcon={<Zap size={14} />}
                                onClick={() => setSettlingPayment(p)}
                              >
                                Settle
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                leftIcon={<Receipt size={14} />}
                                onClick={() => setSelectedReceipt(p)}
                              >
                                Receipt
                              </Button>
                            )}
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
      </div>

      {/* Settle Payment Modal */}
      {settlingPayment && (
        <Modal
          isOpen={true}
          onClose={() => setSettlingPayment(null)}
          title="Settle Parking Fee"
          description={`Complete billing settlement for Parking Session #${settlingPayment.session_id}.`}
          maxWidth="480px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div
              style={{
                textAlign: 'center',
                padding: '1.25rem',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '12px',
                border: '1px solid var(--pz-border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Amount Due
              </span>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#00E5FF', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                ${Number(settlingPayment.amount).toFixed(2)}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '4px', display: 'block' }}>
                Invoice Ref #PAY-{settlingPayment.id} • Session #{settlingPayment.session_id}
              </span>
            </div>

            <div>
              <label style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--pz-text-muted)', display: 'block', marginBottom: '8px' }}>
                SELECT PAYMENT METHOD
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {(['card', 'upi', 'online', 'cash'] as PaymentMethod[]).map((method) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => setSelectedMethod(method)}
                    style={{
                      padding: '12px',
                      borderRadius: '10px',
                      backgroundColor: selectedMethod === method ? 'rgba(0, 229, 255, 0.15)' : 'var(--pz-bg-alt)',
                      border: selectedMethod === method ? '2px solid var(--pz-secondary)' : '1px solid var(--pz-border)',
                      color: selectedMethod === method ? 'var(--pz-secondary)' : '#FFFFFF',
                      fontWeight: 600,
                      fontSize: '0.875rem',
                      textTransform: 'uppercase',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {method}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
              <Button
                variant="outline"
                onClick={() => setSettlingPayment(null)}
                style={{ flex: 1 }}
                disabled={isProcessing}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleProcessPayment}
                isLoading={isProcessing}
                style={{ flex: 1 }}
                leftIcon={<CheckCircle2 size={16} />}
              >
                Authorize &amp; Pay
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Digital Receipt Modal */}
      {selectedReceipt && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedReceipt(null)}
          title="Payment Receipt"
          description="Official electronic invoice record from ParkZenith Telemetry."
          maxWidth="520px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div
              style={{
                textAlign: 'center',
                padding: '1.25rem',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '14px',
                border: '1px solid var(--pz-border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Amount Settled
              </span>
              <div style={{ fontSize: '2.25rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                ${Number(selectedReceipt.amount).toFixed(2)}
              </div>
              <div style={{ marginTop: '6px' }}>
                <StatusBadge status={selectedReceipt.payment_status} type="payment" size="sm" />
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                fontSize: '0.8125rem',
                backgroundColor: 'var(--pz-bg-alt)',
                padding: '1rem',
                borderRadius: '12px',
                border: '1px solid var(--pz-border-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--pz-text-secondary)' }}>
                <span>Transaction Ref:</span>
                <span style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {selectedReceipt.transaction_id || `TXN-PENDING-#${selectedReceipt.id}`}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--pz-text-secondary)' }}>
                <span>Parking Session:</span>
                <span style={{ color: '#FFFFFF', fontWeight: 600 }}>Session #{selectedReceipt.session_id}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--pz-text-secondary)' }}>
                <span>Payment Method:</span>
                <span style={{ color: '#FFFFFF', textTransform: 'uppercase', fontWeight: 600 }}>
                  {selectedReceipt.payment_method}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--pz-text-secondary)' }}>
                <span>Settled Timestamp:</span>
                <span style={{ color: '#FFFFFF' }}>
                  {selectedReceipt.paid_at
                    ? new Date(selectedReceipt.paid_at).toLocaleString()
                    : new Date(selectedReceipt.created_at).toLocaleString()}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--pz-success)' }}>
              <ShieldCheck size={16} />
              <span>Verified electronic ALPR barrier payment receipt</span>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
              <Button
                variant="outline"
                onClick={() => setSelectedReceipt(null)}
                style={{ flex: 1 }}
              >
                Close
              </Button>
              <Button
                variant="primary"
                leftIcon={<Download size={14} />}
                onClick={() => window.print()}
                style={{ flex: 1 }}
              >
                Print / Save PDF
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default Payments;
