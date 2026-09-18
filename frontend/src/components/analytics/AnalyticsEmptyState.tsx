'use client';

import React from 'react';
import Link from 'next/link';
import { BarChart3, Share2, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  actionHref?: string;
  icon?: 'chart' | 'share' | 'sparkles' | 'error';
  onRetry?: () => void;
}

export const AnalyticsEmptyState: React.FC<EmptyStateProps> = ({
  title = 'No analytics data for this period',
  description = 'Try selecting a wider date range or connect another social account to start tracking performance.',
  actionText,
  actionHref,
  icon = 'chart',
  onRetry,
}) => {
  const renderIcon = () => {
    switch (icon) {
      case 'share':
        return <Share2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />;
      case 'sparkles':
        return <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400" />;
      case 'chart':
      default:
        return <BarChart3 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />;
    }
  };

  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-8 text-center space-y-3 shadow-xs max-w-lg mx-auto my-4">
      <div className="w-11 h-11 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/60 dark:border-indigo-800/50 flex items-center justify-center mx-auto shadow-xs">
        {renderIcon()}
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
        <p className="text-xs text-slate-600 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
          {description}
        </p>
      </div>
      <div className="pt-2 flex items-center justify-center space-x-3">
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs transition-colors shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        )}
        {actionText && actionHref && (
          <Link
            href={actionHref}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs transition-colors shadow-xs"
          >
            <span>{actionText}</span>
          </Link>
        )}
      </div>
    </div>
  );
};
