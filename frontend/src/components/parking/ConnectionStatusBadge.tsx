import React from 'react';
import type { ConnectionStatus } from '../../services/websocket';
import { RefreshCw, Wifi, WifiOff, Lock } from 'lucide-react';

export interface ConnectionStatusBadgeProps {
  status: ConnectionStatus;
  onReconnect?: () => void;
  showStaleNotice?: boolean;
}

export const ConnectionStatusBadge: React.FC<ConnectionStatusBadgeProps> = ({
  status,
  onReconnect,
  showStaleNotice = true,
}) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'connected':
        return {
          bg: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: 'var(--pz-success)',
          text: 'Live Telemetry',
          icon: <Wifi size={13} />,
          dot: '#10B981',
          pulse: true,
          notice: null,
        };
      case 'connecting':
        return {
          bg: 'rgba(0, 229, 255, 0.1)',
          border: '1px solid rgba(0, 229, 255, 0.25)',
          color: 'var(--pz-secondary)',
          text: 'Connecting...',
          icon: <RefreshCw size={13} className="spin-animation" />,
          dot: 'var(--pz-secondary)',
          pulse: false,
          notice: null,
        };
      case 'reconnecting':
        return {
          bg: 'rgba(245, 158, 11, 0.12)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          color: 'var(--pz-warning)',
          text: 'Reconnecting...',
          icon: <RefreshCw size={13} className="spin-animation" />,
          dot: '#F59E0B',
          pulse: true,
          notice: 'Reconnecting to bay telemetry stream...',
        };
      case 'unauthorized':
        return {
          bg: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid var(--pz-border-subtle)',
          color: 'var(--pz-text-secondary)',
          text: 'Live Sync (Sign in to enable)',
          icon: <Lock size={12} />,
          dot: '#64748B',
          pulse: false,
          notice: 'Sign in to stream live sub-meter telemetry.',
        };
      case 'disconnected':
      default:
        return {
          bg: 'rgba(244, 63, 94, 0.08)',
          border: '1px solid rgba(244, 63, 94, 0.25)',
          color: 'var(--pz-text-muted)',
          text: 'Offline',
          icon: <WifiOff size={13} />,
          dot: '#64748B',
          pulse: false,
          notice: 'Live telemetry unavailable. Showing last known state.',
        };
    }
  };

  const config = getBadgeConfig();

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            backgroundColor: config.bg,
            border: config.border,
            color: config.color,
            fontSize: '0.75rem',
            fontWeight: 600,
            letterSpacing: '0.02em',
          }}
          title={config.notice || config.text}
        >
          <span
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              backgroundColor: config.dot,
              display: 'inline-block',
              boxShadow: config.pulse ? `0 0 8px ${config.dot}` : 'none',
              animation: config.pulse ? 'pulse-glow 2s infinite' : 'none',
            }}
          />
          {config.icon}
          <span>{config.text}</span>
        </div>

        {status === 'disconnected' && onReconnect && (
          <button
            type="button"
            onClick={onReconnect}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.6875rem',
              fontWeight: 500,
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--pz-border-subtle)',
              color: 'var(--pz-secondary)',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={11} /> Reconnect
          </button>
        )}
      </div>

      {showStaleNotice && config.notice && status !== 'connected' && (
        <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', fontStyle: 'italic' }}>
          {config.notice}
        </span>
      )}
    </div>
  );
};
