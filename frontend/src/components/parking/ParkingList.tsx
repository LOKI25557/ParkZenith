import React from 'react';
import type { Facility, Availability } from '../../types';
import { ParkingCard } from './ParkingCard';
import { ParkingEmptyState } from './ParkingEmptyState';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { ErrorState } from '../ErrorState';
import { calculateHaversineDistanceKm, type Coordinates } from '../../utils/navigation';

export interface ParkingListProps {
  facilities: Facility[];
  availabilities: Record<number, Availability>;
  isLoading: boolean;
  error?: string | null;
  hasFilters: boolean;
  searchQuery?: string;
  selectedFacilityId?: number | null;
  userLocation?: Coordinates | null;
  layout?: 'grid' | 'compact';
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
  selectedFacilityId,
  userLocation,
  layout = 'grid',
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

  const gridColumns =
    layout === 'compact'
      ? 'repeat(auto-fill, minmax(280px, 1fr))'
      : 'repeat(auto-fill, minmax(320px, 1fr))';

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: gridColumns,
        gap: layout === 'compact' ? '1rem' : '1.5rem',
      }}
    >
      {facilities.map((fac) => {
        // Calculate real distance only when user location exists
        const distanceKm =
          userLocation && fac.latitude != null && fac.longitude != null
            ? calculateHaversineDistanceKm(userLocation, {
                latitude: Number(fac.latitude),
                longitude: Number(fac.longitude),
              }) ?? undefined
            : undefined;

        return (
          <div key={fac.id} id={`facility-card-${fac.id}`}>
            <ParkingCard
              facility={fac}
              availability={availabilities[fac.id]}
              distanceKm={distanceKm}
              userLocation={userLocation}
              isSelected={selectedFacilityId === fac.id}
            />
          </div>
        );
      })}
    </div>
  );
};
