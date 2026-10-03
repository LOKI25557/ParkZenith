import React from 'react';
import { Card } from '../ui/Card';

export interface ParkingFeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  metric?: string;
  badge?: string;
}

export const ParkingFeatureCard: React.FC<ParkingFeatureCardProps> = ({
  icon,
  title,
  description,
  metric,
  badge,
}) => {
  return (
    <Card
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            backgroundColor: 'rgba(0, 229, 255, 0.1)',
            border: '1px solid rgba(0, 229, 255, 0.25)',
            color: 'var(--pz-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {icon}
        </div>
        {badge && (
          <span
            style={{
              fontSize: '0.6875rem',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: 'rgba(26, 91, 255, 0.2)',
              color: 'var(--pz-primary-light)',
              border: '1px solid rgba(26, 91, 255, 0.4)',
            }}
          >
            {badge}
          </span>
        )}
      </div>

      <h4 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
        {title}
      </h4>
      <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', lineHeight: 1.5 }}>
        {description}
      </p>

      {metric && (
        <div
          style={{
            marginTop: 'auto',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--pz-border-subtle)',
            fontFamily: 'var(--font-mono)',
            fontSize: '1.125rem',
            fontWeight: 700,
            color: 'var(--pz-secondary)',
          }}
        >
          {metric}
        </div>
      )}
    </Card>
  );
};
