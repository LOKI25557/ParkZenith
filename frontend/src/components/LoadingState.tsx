import React from 'react';
import { LoadingSpinner } from './ui/LoadingSpinner';

export interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ 
  message = "Loading real-time telemetry..." 
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '260px',
        width: '100%',
      }}
    >
      <LoadingSpinner size="md" label={message} />
    </div>
  );
};
