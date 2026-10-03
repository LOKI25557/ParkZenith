import React from 'react';
import { Info, AlertCircle, CheckCircle, CloudRain, Lightbulb } from 'lucide-react';

export interface InsightCardProps {
  type?: 'weather' | 'traffic' | 'system' | 'recommendation';
  severity?: 'INFO' | 'WARNING' | 'SUCCESS';
  message: string;
  factor?: string;
}

export const InsightCard: React.FC<InsightCardProps> = ({
  type = 'system',
  severity = 'INFO',
  message,
  factor,
}) => {
  const getIcon = () => {
    switch (type) {
      case 'weather': return <CloudRain size={16} color="#38BDF8" />;
      case 'traffic': return <AlertCircle size={16} color="var(--pz-warning)" />;
      case 'recommendation': return <Lightbulb size={16} color="var(--pz-secondary)" />;
      case 'system':
      default:
        return severity === 'WARNING'
          ? <AlertCircle size={16} color="var(--pz-warning)" />
          : severity === 'SUCCESS'
          ? <CheckCircle size={16} color="var(--pz-success)" />
          : <Info size={16} color="var(--pz-secondary)" />;
    }
  };

  const getBorderColor = () => {
    switch (severity) {
      case 'WARNING': return 'rgba(245, 158, 11, 0.3)';
      case 'SUCCESS': return 'rgba(16, 185, 129, 0.3)';
      case 'INFO':
      default: return 'rgba(0, 229, 255, 0.25)';
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '12px 14px',
        backgroundColor: 'rgba(15, 19, 30, 0.7)',
        borderRadius: '12px',
        border: `1px solid ${getBorderColor()}`,
      }}
    >
      <div style={{ marginTop: '2px', display: 'flex', flexShrink: 0 }}>
        {getIcon()}
      </div>
      <div style={{ flex: 1 }}>
        {factor && (
          <span
            style={{
              fontSize: '0.6875rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--pz-secondary)',
              display: 'block',
              marginBottom: '2px',
            }}
          >
            {factor}
          </span>
        )}
        <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', lineHeight: 1.45 }}>
          {message}
        </p>
      </div>
    </div>
  );
};
