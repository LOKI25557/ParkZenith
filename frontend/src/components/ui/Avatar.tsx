import React from 'react';

export interface AvatarProps {
  name?: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  status?: 'online' | 'offline' | 'busy';
}

export const Avatar: React.FC<AvatarProps> = ({
  name = 'User',
  src,
  size = 'md',
  status,
}) => {
  const getDims = () => {
    switch (size) {
      case 'sm': return 28;
      case 'lg': return 48;
      case 'xl': return 64;
      case 'md':
      default: return 36;
    }
  };
  const d = getDims();

  const getInitials = (n: string) => {
    return n
      .split(' ')
      .map((part) => part[0])
      .join('')
      .toUpperCase()
      .substring(0, 2);
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block', width: `${d}px`, height: `${d}px` }}>
      {src ? (
        <img
          src={src}
          alt={name}
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            objectFit: 'cover',
            border: '2px solid rgba(0, 229, 255, 0.4)',
          }}
        />
      ) : (
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1A5BFF 0%, #8B5CF6 100%)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 600,
            fontSize: `${d * 0.4}px`,
            border: '2px solid rgba(255, 255, 255, 0.15)',
          }}
        >
          {getInitials(name)}
        </div>
      )}
      {status && (
        <span
          style={{
            position: 'absolute',
            bottom: 0,
            right: 0,
            width: `${Math.max(8, d * 0.28)}px`,
            height: `${Math.max(8, d * 0.28)}px`,
            borderRadius: '50%',
            border: '2px solid #090B10',
            backgroundColor:
              status === 'online' ? 'var(--pz-success)' :
              status === 'busy' ? 'var(--pz-warning)' : 'var(--pz-text-muted)',
          }}
        />
      )}
    </div>
  );
};
