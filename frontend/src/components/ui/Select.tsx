import React from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string | number;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  error?: boolean;
}

export const Select: React.FC<SelectProps> = ({
  options,
  error,
  className = '',
  style,
  ...props
}) => {
  return (
    <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
      <select
        className={`pz-input ${className}`}
        style={{
          appearance: 'none',
          paddingRight: '36px',
          borderColor: error ? 'var(--pz-error)' : undefined,
          cursor: 'pointer',
          ...style,
        }}
        {...props}
      >
        {options.map((opt) => (
          <option
            key={opt.value}
            value={opt.value}
            style={{ background: 'var(--pz-bg-elevated)', color: 'var(--pz-text-primary)' }}
          >
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={16}
        style={{
          position: 'absolute',
          right: '12px',
          color: 'var(--pz-text-muted)',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};
