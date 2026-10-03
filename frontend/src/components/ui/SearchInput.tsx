import React from 'react';
import { Search, X } from 'lucide-react';

export interface SearchInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  onClear?: () => void;
  shortcut?: string;
}

export const SearchInput: React.FC<SearchInputProps> = ({
  value,
  onChange,
  onClear,
  shortcut,
  placeholder = 'Search facilities, slots, or plate ID...',
  className = '',
  ...props
}) => {
  return (
    <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
      <Search
        size={18}
        style={{
          position: 'absolute',
          left: '12px',
          color: 'var(--pz-text-muted)',
          pointerEvents: 'none',
        }}
      />
      <input
        type="text"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={`pz-input ${className}`}
        style={{
          paddingLeft: '40px',
          paddingRight: shortcut || (value && onClear) ? '64px' : '14px',
          borderRadius: '9999px',
        }}
        {...props}
      />
      <div style={{
        position: 'absolute',
        right: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}>
        {value && onClear && (
          <button
            type="button"
            onClick={onClear}
            style={{
              color: 'var(--pz-text-muted)',
              display: 'flex',
              padding: '2px',
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.05)',
            }}
            aria-label="Clear search"
          >
            <X size={14} />
          </button>
        )}
        {shortcut && (
          <span style={{
            fontSize: '0.6875rem',
            fontFamily: 'var(--font-mono)',
            padding: '2px 6px',
            borderRadius: '4px',
            background: 'rgba(255, 255, 255, 0.08)',
            color: 'var(--pz-text-muted)',
            border: '1px solid var(--pz-border-subtle)',
          }}>
            {shortcut}
          </span>
        )}
      </div>
    </div>
  );
};
