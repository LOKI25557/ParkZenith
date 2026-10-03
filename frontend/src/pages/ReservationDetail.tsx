import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { StatusBadge } from '../components/ui/StatusBadge';
import { QrCode, ShieldCheck, ArrowLeft, Download } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const ReservationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '680px', margin: '0 auto' }}>
      <Breadcrumb
        items={[
          { label: 'Reservations', href: '/reservations' },
          { label: `Pass #${id}` },
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
          Metropolis Central Hub
        </h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
          Sector B Deck • Level 3 VIP &amp; EV
        </p>

        <div style={{ margin: '1.25rem 0' }}>
          <StatusBadge status="confirmed" type="reservation" size="md" />
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
          PERMIT ID: PZ-2026-REV-{id?.padStart(4, '0')}
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
              Slot B-08
            </span>
          </div>

          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Vehicle License Plate</span>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              {user?.vehicle_number || 'KA-01-MJ-5555'}
            </span>
          </div>

          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Start Time</span>
            <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
              Today, 14:00 EDT
            </span>
          </div>

          <div style={{ padding: '10px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Valid Until</span>
            <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
              Today, 18:00 EDT
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
      </Card>
    </div>
  );
};

export default ReservationDetail;
