import React from 'react';
import { Navigation, ExternalLink } from 'lucide-react';
import type { Facility } from '../../types';
import { getDirectionsUrl, type Coordinates } from '../../utils/navigation';

export interface NavigationButtonProps {
  facility: Pick<Facility, 'name' | 'address' | 'city' | 'latitude' | 'longitude'>;
  userLocation?: Coordinates | null;
  variant?: 'primary' | 'secondary' | 'outline' | 'icon';
  size?: 'sm' | 'md';
  className?: string;
  label?: string;
}

export const NavigationButton: React.FC<NavigationButtonProps> = ({
  facility,
  userLocation,
  variant = 'outline',
  size = 'sm',
  className = '',
  label = 'Get Directions',
}) => {
  const url = getDirectionsUrl(facility, userLocation);
  const isIcon = variant === 'icon';

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    borderRadius: '8px',
    fontWeight: 600,
    fontSize: size === 'sm' ? '0.75rem' : '0.875rem',
    textDecoration: 'none',
    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
    cursor: 'pointer',
    padding: isIcon ? (size === 'sm' ? '6px' : '8px') : size === 'sm' ? '6px 12px' : '8px 16px',
  };

  let variantStyle: React.CSSProperties = {};
  if (variant === 'primary') {
    variantStyle = {
      backgroundColor: 'var(--pz-primary)',
      color: '#FFFFFF',
      border: '1px solid transparent',
      boxShadow: '0 0 12px rgba(26, 91, 255, 0.35)',
    };
  } else if (variant === 'secondary') {
    variantStyle = {
      backgroundColor: 'rgba(0, 229, 255, 0.12)',
      color: 'var(--pz-secondary)',
      border: '1px solid rgba(0, 229, 255, 0.35)',
    };
  } else {
    // outline / icon
    variantStyle = {
      backgroundColor: 'rgba(255, 255, 255, 0.04)',
      color: 'var(--pz-text-secondary)',
      border: '1px solid var(--pz-border-subtle)',
    };
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      style={{ ...baseStyle, ...variantStyle }}
      className={`nav-btn-hover ${className}`}
      title={`Open directions to ${facility.name} in Google Maps`}
      aria-label={`Get directions to ${facility.name}`}
      onClick={(e) => e.stopPropagation()}
    >
      <Navigation size={size === 'sm' ? 13 : 15} color="var(--pz-secondary)" />
      {!isIcon && <span>{label}</span>}
      {!isIcon && <ExternalLink size={11} style={{ opacity: 0.6 }} />}
    </a>
  );
};
