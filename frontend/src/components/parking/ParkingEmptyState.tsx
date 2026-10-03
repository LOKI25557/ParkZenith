import React from 'react';
import { EmptyState } from '../ui/EmptyState';
import { MapPin } from 'lucide-react';

export interface ParkingEmptyStateProps {
  hasFilters: boolean;
  searchQuery?: string;
  onClearFilters?: () => void;
}

export const ParkingEmptyState: React.FC<ParkingEmptyStateProps> = ({
  hasFilters,
  searchQuery,
  onClearFilters,
}) => {
  return (
    <EmptyState
      icon={<MapPin size={32} />}
      title={hasFilters ? "No Parking Facilities Match Filters" : "No Parking Facilities Found"}
      description={
        hasFilters
          ? searchQuery
            ? `No facilities matched "${searchQuery}" with the selected filter criteria.`
            : "No parking facilities matched your selected filters. Try broadening your criteria."
          : "There are currently no parking facilities registered in the ParkZenith network."
      }
      actionLabel={hasFilters && onClearFilters ? "Clear All Filters" : undefined}
      onAction={hasFilters ? onClearFilters : undefined}
    />
  );
};
