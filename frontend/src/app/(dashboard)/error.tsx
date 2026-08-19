'use client';

import React, { useEffect } from 'react';
import { RefreshCw, AlertTriangle } from 'lucide-react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Dashboard runtime error caught by boundary:', error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-4">
        <AlertTriangle className="w-8 h-8" />
      </div>

      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
        Something went wrong
      </h2>
      
      <p className="text-xs text-[var(--text-secondary)] max-w-md mb-6 leading-relaxed">
        {error.message || 'An unexpected error occurred while loading this dashboard view. Click below to reload.'}
      </p>

      <div className="flex items-center space-x-3">
        <button
          onClick={() => reset()}
          className="btn-primary text-xs flex items-center space-x-2 py-2.5 px-4"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Reload Page View</span>
        </button>

        <button
          onClick={() => {
            if (typeof window !== 'undefined') window.location.href = '/dashboard';
          }}
          className="btn-secondary text-xs py-2.5 px-4"
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
