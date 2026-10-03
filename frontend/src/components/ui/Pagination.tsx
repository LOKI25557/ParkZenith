import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
}) => {
  if (totalPages <= 1) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginTop: '1.5rem' }}>
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '34px',
          height: '34px',
          borderRadius: '8px',
          border: '1px solid var(--pz-border)',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          color: currentPage <= 1 ? 'var(--pz-text-muted)' : 'var(--pz-text-primary)',
          cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
        }}
        aria-label="Previous Page"
      >
        <ChevronLeft size={16} />
      </button>

      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
        const isCurrent = page === currentPage;
        return (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              fontSize: '0.875rem',
              fontWeight: 500,
              border: isCurrent ? '1px solid var(--pz-primary)' : '1px solid var(--pz-border)',
              backgroundColor: isCurrent ? 'var(--pz-primary)' : 'rgba(255, 255, 255, 0.03)',
              color: isCurrent ? '#FFFFFF' : 'var(--pz-text-secondary)',
              cursor: 'pointer',
            }}
          >
            {page}
          </button>
        );
      })}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '34px',
          height: '34px',
          borderRadius: '8px',
          border: '1px solid var(--pz-border)',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          color: currentPage >= totalPages ? 'var(--pz-text-muted)' : 'var(--pz-text-primary)',
          cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
        }}
        aria-label="Next Page"
      >
        <ChevronRight size={16} />
      </button>
    </div>
  );
};
