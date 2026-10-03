import React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({ items }) => {
  return (
    <nav aria-label="Breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <Link
        to="/dashboard"
        style={{
          display: 'flex',
          alignItems: 'center',
          color: 'var(--pz-text-muted)',
          transition: 'color 0.2s',
        }}
      >
        <Home size={14} />
      </Link>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <React.Fragment key={index}>
            <ChevronRight size={12} color="var(--pz-text-muted)" />
            {isLast || !item.href ? (
              <span style={{ fontSize: '0.8125rem', color: '#FFFFFF', fontWeight: 500 }}>
                {item.label}
              </span>
            ) : (
              <Link
                to={item.href}
                style={{
                  fontSize: '0.8125rem',
                  color: 'var(--pz-text-secondary)',
                  transition: 'color 0.2s',
                }}
              >
                {item.label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
