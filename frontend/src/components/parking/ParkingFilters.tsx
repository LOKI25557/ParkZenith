import React from 'react';
import { SearchInput } from '../ui/SearchInput';
import { Select } from '../ui/Select';
import {
  Filter,
  CheckCircle2,
  Clock,
  Crosshair,
  MapPin,
  X,
  LayoutGrid,
  Map as MapIcon,
  Columns,
} from 'lucide-react';
import type { Coordinates } from '../../utils/navigation';

export interface ParkingFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedSort: string;
  onSortChange: (sort: string) => void;
  availableOnly: boolean;
  onToggleAvailableOnly: () => void;
  activeOnly: boolean;
  onToggleActiveOnly: () => void;
  roundTheClock: boolean;
  onToggleRoundTheClock: () => void;
  hasActiveFilters: boolean;
  onClearFilters: () => void;
  // Geolocation integration
  userLocation?: Coordinates | null;
  onRequestLocation?: () => void;
  onClearLocation?: () => void;
  isLocating?: boolean;
  locationError?: string | null;
  // View mode switcher
  viewMode?: 'split' | 'list' | 'map';
  onViewModeChange?: (mode: 'split' | 'list' | 'map') => void;
}

export const ParkingFilters: React.FC<ParkingFiltersProps> = ({
  searchQuery,
  onSearchChange,
  selectedSort,
  onSortChange,
  availableOnly,
  onToggleAvailableOnly,
  activeOnly,
  onToggleActiveOnly,
  roundTheClock,
  onToggleRoundTheClock,
  hasActiveFilters,
  onClearFilters,
  userLocation,
  onRequestLocation,
  onClearLocation,
  isLocating = false,
  locationError,
  viewMode = 'split',
  onViewModeChange,
}) => {
  const sortOptions = [
    { value: 'default', label: 'Default Order' },
    ...(userLocation ? [{ value: 'distance', label: 'Nearest First (GPS)' }] : []),
    { value: 'availability', label: 'Most Available Bays' },
    { value: 'capacity', label: 'Largest Capacity' },
    { value: 'occupancy', label: 'Lowest Occupancy' },
    { value: 'name', label: 'Name (A - Z)' },
  ];

  return (
    <div
      className="glass-panel"
      style={{
        padding: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      {/* Top Search, Sort & View Mode Switcher */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '1rem',
        }}
      >
        {/* Search Input */}
        <div style={{ flex: 1, minWidth: '260px' }}>
          <SearchInput
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onClear={() => onSearchChange('')}
            placeholder="Search by facility name, address, or city..."
          />
        </div>

        {/* Sort Select */}
        <div style={{ width: '210px' }}>
          <Select
            value={selectedSort}
            onChange={(e) => onSortChange(e.target.value)}
            options={sortOptions}
          />
        </div>

        {/* View Mode Toggle Button Group */}
        {onViewModeChange && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '3px',
              borderRadius: '10px',
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--pz-border-subtle)',
            }}
          >
            <button
              type="button"
              onClick={() => onViewModeChange('list')}
              aria-label="Cards list view"
              title="Cards Grid View"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 10px',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: viewMode === 'list' ? 'var(--pz-primary)' : 'transparent',
                color: viewMode === 'list' ? '#FFFFFF' : 'var(--pz-text-secondary)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <LayoutGrid size={14} />
              <span className="hidden-mobile">Cards</span>
            </button>

            <button
              type="button"
              onClick={() => onViewModeChange('split')}
              aria-label="Split cards and map view"
              title="Split View (Cards & Map)"
              className="split-view-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 10px',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: viewMode === 'split' ? 'var(--pz-primary)' : 'transparent',
                color: viewMode === 'split' ? '#FFFFFF' : 'var(--pz-text-secondary)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Columns size={14} />
              <span className="hidden-mobile">Split</span>
            </button>

            <button
              type="button"
              onClick={() => onViewModeChange('map')}
              aria-label="Map only view"
              title="Full Map View"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 10px',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: viewMode === 'map' ? 'var(--pz-primary)' : 'transparent',
                color: viewMode === 'map' ? '#FFFFFF' : 'var(--pz-text-secondary)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <MapIcon size={14} />
              <span className="hidden-mobile">Map</span>
            </button>
          </div>
        )}
      </div>

      {/* Filter Toggle Buttons & Location Action */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '0.875rem',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--pz-text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginRight: '4px',
            }}
          >
            <Filter size={13} /> Quick Filters:
          </span>

          <button
            type="button"
            onClick={onToggleAvailableOnly}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.8125rem',
              fontWeight: 500,
              backgroundColor: availableOnly ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: availableOnly ? '1px solid var(--pz-success)' : '1px solid var(--pz-border-subtle)',
              color: availableOnly ? 'var(--pz-success)' : 'var(--pz-text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <CheckCircle2 size={13} /> Only Available Bays
          </button>

          <button
            type="button"
            onClick={onToggleActiveOnly}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.8125rem',
              fontWeight: 500,
              backgroundColor: activeOnly ? 'rgba(0, 229, 255, 0.12)' : 'rgba(255, 255, 255, 0.03)',
              border: activeOnly ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
              color: activeOnly ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Clock size={13} /> Open Facilities Only
          </button>

          <button
            type="button"
            onClick={onToggleRoundTheClock}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.8125rem',
              fontWeight: 500,
              backgroundColor: roundTheClock ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: roundTheClock ? '1px solid #8B5CF6' : '1px solid var(--pz-border-subtle)',
              color: roundTheClock ? '#C084FC' : 'var(--pz-text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            24/7 Access
          </button>

          {/* User Location Geolocation Button */}
          {onRequestLocation && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              {userLocation ? (
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    backgroundColor: 'rgba(0, 229, 255, 0.15)',
                    border: '1px solid var(--pz-secondary)',
                    color: 'var(--pz-secondary)',
                  }}
                >
                  <MapPin size={13} /> GPS Location Active
                  {onClearLocation && (
                    <button
                      type="button"
                      onClick={onClearLocation}
                      aria-label="Clear location"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--pz-secondary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        padding: 0,
                        marginLeft: '4px',
                      }}
                    >
                      <X size={13} />
                    </button>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  onClick={onRequestLocation}
                  disabled={isLocating}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '0.8125rem',
                    fontWeight: 500,
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--pz-border-subtle)',
                    color: 'var(--pz-text-secondary)',
                    cursor: isLocating ? 'wait' : 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  title="Enable location to view real distances to facilities"
                >
                  <Crosshair size={13} className={isLocating ? 'animate-spin' : ''} />
                  {isLocating ? 'Acquiring GPS...' : 'Use My Location'}
                </button>
              )}
            </div>
          )}
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--pz-text-muted)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              textDecoration: 'underline',
              padding: '4px 8px',
            }}
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Geolocation notice/error if denied */}
      {locationError && (
        <div
          style={{
            fontSize: '0.75rem',
            color: 'var(--pz-warning)',
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            padding: '6px 12px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>⚠ {locationError}</span>
        </div>
      )}
    </div>
  );
};
