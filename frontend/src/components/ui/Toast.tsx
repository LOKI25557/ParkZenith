import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType, title?: string) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = 'info', title?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  }, [removeToast]);

  const success = useCallback((message: string, title?: string) => addToast(message, 'success', title), [addToast]);
  const error = useCallback((message: string, title?: string) => addToast(message, 'error', title), [addToast]);
  const info = useCallback((message: string, title?: string) => addToast(message, 'info', title), [addToast]);
  const warning = useCallback((message: string, title?: string) => addToast(message, 'warning', title), [addToast]);

  return (
    <ToastContext.Provider value={{ toast: addToast, success, error, info, warning }}>
      {children}
      <div
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          maxWidth: '380px',
          width: '100%',
          pointerEvents: 'none',
        }}
      >
        {toasts.map((t) => {
          const getIcon = () => {
            switch (t.type) {
              case 'success': return <CheckCircle2 size={18} color="var(--pz-success)" />;
              case 'error': return <AlertCircle size={18} color="var(--pz-error)" />;
              case 'warning': return <AlertCircle size={18} color="var(--pz-warning)" />;
              case 'info':
              default: return <Info size={18} color="var(--pz-secondary)" />;
            }
          };

          return (
            <div
              key={t.id}
              style={{
                pointerEvents: 'auto',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '12px 16px',
                backgroundColor: 'rgba(19, 23, 34, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderLeft: `4px solid ${
                  t.type === 'success' ? 'var(--pz-success)' :
                  t.type === 'error' ? 'var(--pz-error)' :
                  t.type === 'warning' ? 'var(--pz-warning)' : 'var(--pz-secondary)'
                }`,
                borderRadius: '8px',
                boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
                backdropFilter: 'blur(12px)',
                animation: 'float-subtle 0.3s ease-out',
              }}
            >
              <span style={{ marginTop: '2px', display: 'inline-flex' }}>{getIcon()}</span>
              <div style={{ flex: 1 }}>
                {t.title && (
                  <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--pz-text-primary)' }}>
                    {t.title}
                  </h4>
                )}
                <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                  {t.message}
                </p>
              </div>
              <button
                onClick={() => removeToast(t.id)}
                style={{
                  color: 'var(--pz-text-muted)',
                  display: 'flex',
                  padding: '2px',
                }}
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
