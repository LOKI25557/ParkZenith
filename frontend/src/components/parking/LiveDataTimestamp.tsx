import React, { useEffect, useState, useMemo } from 'react';
import { Clock, RefreshCw, AlertTriangle } from 'lucide-react';
import type { ConnectionStatus } from '../../types';

export interface LiveDataTimestampProps {
  timestamp?: Date | string | null;
  status?: ConnectionStatus;
  onRefresh?: () => void;
  isStale?: boolean;
  prefix?: string;
  className?: string;
}

export const LiveDataTimestamp: React.FC<LiveDataTimestampProps> = ({
  timestamp,
  status,
  onRefresh,
  isStale = false,
  prefix = 'Updated',
}) => {
  const [relativeText, setRelativeText] = useState<string>('just now');

  const parsedDate = useMemo(() => {
    if (!timestamp) return null;
    return typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  }, [timestamp]);

  useEffect(() => {
    const updateRelative = () => {
      if (!parsedDate) {
        setRelativeText('awaiting telemetry');
        return;
      }

      const diffMs = Date.now() - parsedDate.getTime();
      const diffSec = Math.floor(diffMs / 1000);

      if (diffSec < 8) {
        setRelativeText('just now');
      } else if (diffSec < 60) {
        setRelativeText(`${diffSec}s ago`);
      } else if (diffSec < 3600) {
        const mins = Math.floor(diffSec / 60);
        setRelativeText(`${mins}m ago`);
      } else {
        const hours = Math.floor(diffSec / 3600);
        setRelativeText(`${hours}h ago`);
      }
    };

    updateRelative();
    const interval = setInterval(updateRelative, 5000);
    return () => clearInterval(interval);
  }, [parsedDate]);

  const isDisconnectedOrOffline = status === 'disconnected' || status === 'offline';
  const showStaleWarning = isStale || isDisconnectedOrOffline;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '0.75rem',
        color: showStaleWarning ? 'var(--pz-warning)' : 'var(--pz-text-muted)',
      }}
      aria-live="polite"
      title={parsedDate ? `Last synchronized at ${parsedDate.toLocaleTimeString()}` : 'Awaiting live stream'}
    >
      {showStaleWarning ? (
        <AlertTriangle size={12} color="var(--pz-warning)" />
      ) : (
        <Clock size={12} color="var(--pz-text-muted)" />
      )}

      <span>
        {prefix} {relativeText}
        {showStaleWarning && ' (stale)'}
      </span>

      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          title="Manually refresh telemetry"
          style={{
            background: 'transparent',
            border: 'none',
            padding: '2px',
            color: 'var(--pz-secondary)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            opacity: 0.8,
            transition: 'opacity 0.15s ease',
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.opacity = '1')}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.opacity = '0.8')}
        >
          <RefreshCw size={11} />
        </button>
      )}
    </div>
  );
};
