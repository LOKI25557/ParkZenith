import React from 'react';
import { SearchInput } from '../ui/SearchInput';
import { Select } from '../ui/Select';
import { Filter, CheckCircle2, Clock } from 'lucide-react';

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
}) => {
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
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '1rem',
        }}
      >
        <div style={{ flex: 1, minWidth: '260px' }}>
          <SearchInput
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onClear={() => onSearchChange('')}
            placeholder="Search by facility name, address, or city..."
          />
        </div>

        <div style={{ width: '200px' }}>
          <Select
            value={selectedSort}
            onChange={(e) => onSortChange(e.target.value)}
            options={[
              { value: 'default', label: 'Default Order' },
              { value: 'availability', label: 'Most Available Bays' },
              { value: 'capacity', label: 'Largest Capacity' },
              { value: 'occupancy', label: 'Lowest Occupancy' },
              { value: 'name', label: 'Name (A - Z)' },
            ]}
          />
        </div>
      </div>

      {/* Filter Toggle Buttons */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '8px',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '0.875rem',
        }}
      >
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
            backgroundColor: activeOnly ? 'rgba(0, 229, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
            border: activeOnly ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
            color: activeOnly ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          Open / Active Only
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
            backgroundColor: roundTheClock ? 'rgba(168, 85, 247, 0.15)' : 'rgba(255, 255, 255, 0.03)',
            border: roundTheClock ? '1px solid #A855F7' : '1px solid var(--pz-border-subtle)',
            color: roundTheClock ? '#D8B4FE' : 'var(--pz-text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <Clock size={13} /> 24/7 Access
        </button>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            style={{
              marginLeft: 'auto',
              fontSize: '0.8125rem',
              color: 'var(--pz-text-muted)',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Reset all filters
          </button>
        )}
      </div>
    </div>
  );
};
