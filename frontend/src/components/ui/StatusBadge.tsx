import React from 'react';
import { Badge } from './Badge';

export type ParkingStatusType = 'available' | 'occupied' | 'reserved' | 'maintenance' | 'disabled';
export type ReservationStatusType = 'pending' | 'confirmed' | 'cancelled' | 'completed' | 'active' | 'expired';
export type PaymentStatusType = 'pending' | 'completed' | 'failed' | 'refunded';

export interface StatusBadgeProps {
  status: ParkingStatusType | ReservationStatusType | PaymentStatusType | string;
  type?: 'slot' | 'reservation' | 'payment' | 'general';
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  type: _type = 'general',
  size = 'md',
}) => {
  const normalized = status.toLowerCase();

  const getConfig = () => {
    switch (normalized) {
      case 'available':
        return { variant: 'success' as const, label: 'Available', pulse: true };
      case 'occupied':
        return { variant: 'neutral' as const, label: 'Occupied', pulse: false };
      case 'reserved':
        return { variant: 'warning' as const, label: 'Reserved', pulse: false };
      case 'maintenance':
        return { variant: 'error' as const, label: 'Maintenance', pulse: false };
      case 'disabled':
        return { variant: 'info' as const, label: 'Accessible', pulse: false };

      // Reservation & Session
      case 'active':
        return { variant: 'secondary' as const, label: 'Active Now', pulse: true };
      case 'confirmed':
        return { variant: 'success' as const, label: 'Confirmed', pulse: false };
      case 'completed':
        return { variant: 'primary' as const, label: 'Completed', pulse: false };
      case 'cancelled':
        return { variant: 'error' as const, label: 'Cancelled', pulse: false };
      case 'expired':
        return { variant: 'neutral' as const, label: 'Expired', pulse: false };

      // Payment
      case 'paid':
      case 'success':
        return { variant: 'success' as const, label: 'Success', pulse: false };
      case 'failed':
        return { variant: 'error' as const, label: 'Failed', pulse: false };
      case 'pending':
        return { variant: 'warning' as const, label: 'Pending', pulse: true };
      case 'refunded':
        return { variant: 'info' as const, label: 'Refunded', pulse: false };

      default:
        return { variant: 'neutral' as const, label: status, pulse: false };
    }
  };

  const config = getConfig();

  return (
    <Badge variant={config.variant} size={size} pulse={config.pulse}>
      {config.label}
    </Badge>
  );
};
