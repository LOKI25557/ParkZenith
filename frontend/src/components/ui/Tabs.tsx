import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: string | number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = '',
}) => {
  return (
    <div
      role="tablist"
      className={`pz-tabs ${className}`}
      style={{
        display: 'inline-flex',
        padding: '4px',
        backgroundColor: 'rgba(15, 19, 30, 0.75)',
        border: '1px solid var(--pz-border-subtle)',
        borderRadius: '10px',
        gap: '4px',
        maxWidth: '100%',
        overflowX: 'auto',
      }}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '0.875rem',
              fontWeight: 500,
              color: isActive ? '#FFFFFF' : 'var(--pz-text-secondary)',
              backgroundColor: isActive ? 'rgba(26, 91, 255, 0.35)' : 'transparent',
              border: isActive ? '1px solid rgba(26, 91, 255, 0.5)' : '1px solid transparent',
              boxShadow: isActive ? '0 2px 8px rgba(0, 0, 0, 0.25)' : 'none',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
            }}
          >
            {tab.icon && <span style={{ display: 'inline-flex' }}>{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                style={{
                  fontSize: '0.6875rem',
                  padding: '1px 6px',
                  borderRadius: '9999px',
                  backgroundColor: isActive ? 'var(--pz-primary)' : 'rgba(255, 255, 255, 0.1)',
                  color: '#FFFFFF',
                }}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
