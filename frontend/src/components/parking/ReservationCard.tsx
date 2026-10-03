import React from 'react';
import type { Reservation } from '../../types';
import { Card } from '../ui/Card';
import { StatusBadge } from '../ui/StatusBadge';
import { Button } from '../ui/Button';
import { Calendar, Clock, MapPin, XCircle, QrCode, PlayCircle } from 'lucide-react';

export interface ReservationCardProps {
  reservation: Reservation;
  facilityName?: string;
  slotNumber?: string;
  onCancel?: (id: number) => void;
  onViewPass?: (reservation: Reservation) => void;
  onCheckIn?: (reservation: Reservation) => void;
}

export const ReservationCard: React.FC<ReservationCardProps> = ({
  reservation,
  facilityName = 'Metropolis Garage',
  slotNumber,
  onCancel,
  onViewPass,
  onCheckIn,
}) => {
  const startDate = new Date(reservation.reservation_start);
  const endDate = new Date(reservation.reservation_end);

  const formattedDate = startDate.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const formattedTime = `${startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - ${endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

  const isCancellable = reservation.status === 'confirmed' || reservation.status === 'pending';

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--pz-text-muted)' }}>
            RESERVATION #{reservation.id}
          </span>
          <h4 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
            {facilityName}
          </h4>
        </div>
        <StatusBadge status={reservation.status} type="reservation" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
          <Calendar size={14} color="var(--pz-secondary)" />
          <span>{formattedDate}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
          <Clock size={14} color="var(--pz-secondary)" />
          <span>{formattedTime}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
          <MapPin size={14} color="var(--pz-secondary)" />
          <span>Slot {slotNumber || `#${reservation.slot_id}`}</span>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '8px',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '0.75rem',
          marginTop: '0.25rem',
        }}
      >
        {onCheckIn && (reservation.status === 'confirmed' || reservation.status === 'active') && (
          <Button
            variant="primary"
            size="sm"
            leftIcon={<PlayCircle size={14} />}
            onClick={() => onCheckIn(reservation)}
          >
            Check In
          </Button>
        )}
        {onViewPass && (
          <Button
            variant="outline"
            size="sm"
            leftIcon={<QrCode size={14} />}
            onClick={() => onViewPass(reservation)}
          >
            Digital Pass
          </Button>
        )}
        {isCancellable && onCancel && (
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<XCircle size={14} />}
            onClick={() => onCancel(reservation.id)}
            style={{ color: 'var(--pz-error)' }}
          >
            Cancel
          </Button>
        )}
      </div>
    </Card>
  );
};
