import React from 'react';
import type { Facility, Availability } from '../../types';
import { ParkingCard } from './ParkingCard';
import { ParkingEmptyState } from './ParkingEmptyState';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { ErrorState } from '../ErrorState';

export interface ParkingListProps {
  facilities: Facility[];
  availabilities: Record<number, Availability>;
  isLoading: boolean;
  error?: string | null;
  hasFilters: boolean;
  searchQuery?: string;
  onRetry?: () => void;
  onClearFilters?: () => void;
}

export const ParkingList: React.FC<ParkingListProps> = ({
  facilities,
  availabilities,
  isLoading,
  error,
  hasFilters,
  searchQuery,
  onRetry,
  onClearFilters,
}) => {
  if (isLoading) {
    return (
      <div style={{ padding: '3rem 0' }}>
        <LoadingSpinner size="lg" label="Searching connected garages..." />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to Load Facilities"
        message={error}
        onRetry={onRetry}
      />
    );
  }

  if (facilities.length === 0) {
    return (
      <ParkingEmptyState
        hasFilters={hasFilters}
        searchQuery={searchQuery}
        onClearFilters={onClearFilters}
      />
    );
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: '1.5rem',
      }}
    >
      {facilities.map((fac) => (
        <ParkingCard
          key={fac.id}
          facility={fac}
          availability={availabilities[fac.id]}
        />
      ))}
    </div>
  );
};
