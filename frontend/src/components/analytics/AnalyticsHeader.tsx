'use client';

import React from 'react';
import { 
  Calendar, 
  Filter, 
  RefreshCw, 
  Layers, 
  Share2,
  Instagram,
  Facebook,
  Youtube
} from 'lucide-react';
import { 
  AnalyticsFilterState, 
  DatePreset, 
  PlatformFilter 
} from '@/lib/analyticsApi';
import { SocialAccount } from '@/lib/types';

interface AnalyticsHeaderProps {
  filters: AnalyticsFilterState;
  onFilterChange: (updater: Partial<AnalyticsFilterState>) => void;
  onRefresh: () => void;
  isLoading: boolean;
  socialAccounts?: SocialAccount[];
}

export const AnalyticsHeader: React.FC<AnalyticsHeaderProps> = ({
  filters,
  onFilterChange,
  onRefresh,
  isLoading,
  socialAccounts = [],
}) => {
  const handlePresetChange = (preset: DatePreset) => {
    const today = new Date();
    const formatDate = (d: Date) => d.toISOString().split('T')[0];

    if (preset === 'today') {
      const todayStr = formatDate(today);
      onFilterChange({ preset, startDate: todayStr, endDate: todayStr });
    } else if (preset === '7d') {
      const start = new Date(today);
      start.setDate(today.getDate() - 7);
      onFilterChange({ preset, startDate: formatDate(start), endDate: formatDate(today) });
    } else if (preset === '30d') {
      const start = new Date(today);
      start.setDate(today.getDate() - 30);
      onFilterChange({ preset, startDate: formatDate(start), endDate: formatDate(today) });
    } else if (preset === '90d') {
      const start = new Date(today);
      start.setDate(today.getDate() - 90);
      onFilterChange({ preset, startDate: formatDate(start), endDate: formatDate(today) });
    } else if (preset === 'custom') {
      onFilterChange({ preset });
    }
  };

  return (
    <div className="flex flex-col gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
      {/* Title & Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              Social Analytics
            </h1>
            <span className="inline-flex items-center space-x-1.5 text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/60">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
              <span>Performance Insights</span>
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Real-time audience growth, cross-platform engagement, and granular post-level performance telemetry.
          </p>
        </div>

        {/* Global Action & Refresh */}
        <div className="flex items-center space-x-2 self-start md:self-auto">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 dark:bg-[#111827] dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium transition-colors shadow-xs disabled:opacity-50"
            title="Refresh Analytics Telemetry"
            aria-label="Refresh Analytics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-600 dark:text-indigo-400' : 'text-slate-500'}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar: Presets, Custom Range, Platform, Account Selector */}
      <div className="flex flex-wrap items-center gap-2.5 pt-1">
        {/* Date Preset Buttons */}
        <div className="inline-flex items-center bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 rounded-lg p-1 shadow-xs">
          {(
            [
              { id: 'today', label: 'Today' },
              { id: '7d', label: '7D' },
              { id: '30d', label: '30D' },
              { id: '90d', label: '90D' },
              { id: 'custom', label: 'Custom' },
            ] as const
          ).map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetChange(preset.id)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                filters.preset === preset.id
                  ? 'bg-indigo-600 text-white shadow-xs font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        {/* Custom Date Pickers (Shown if Custom preset selected) */}
        {filters.preset === 'custom' && (
          <div className="flex items-center space-x-2 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 px-3 py-1 rounded-lg shadow-xs text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            <input
              type="date"
              value={filters.startDate || ''}
              onChange={(e) => onFilterChange({ startDate: e.target.value })}
              className="bg-transparent text-slate-700 dark:text-slate-300 focus:outline-none cursor-pointer text-xs"
              title="Start Date"
            />
            <span className="text-slate-400">to</span>
            <input
              type="date"
              value={filters.endDate || ''}
              onChange={(e) => onFilterChange({ endDate: e.target.value })}
              className="bg-transparent text-slate-700 dark:text-slate-300 focus:outline-none cursor-pointer text-xs"
              title="End Date"
            />
          </div>
        )}

        {/* Platform Filter */}
        <div className="flex items-center space-x-2 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-lg shadow-xs">
          <Filter className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
          <select
            value={filters.platform}
            onChange={(e) => onFilterChange({ platform: e.target.value as PlatformFilter })}
            className="bg-transparent text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer"
            aria-label="Filter by social platform"
          >
            <option value="all" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
              All Platforms
            </option>
            <option value="instagram" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
              Instagram
            </option>
            <option value="facebook" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
              Facebook
            </option>
            <option value="youtube" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
              YouTube
            </option>
          </select>
        </div>

        {/* Social Account Selector (if social accounts available) */}
        {socialAccounts.length > 0 && (
          <div className="flex items-center space-x-2 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-lg shadow-xs">
            <Share2 className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
            <select
              value={filters.socialAccountId === undefined ? 'all' : String(filters.socialAccountId)}
              onChange={(e) => {
                const val = e.target.value;
                onFilterChange({
                  socialAccountId: val === 'all' ? 'all' : Number(val),
                });
              }}
              className="bg-transparent text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer max-w-[180px] truncate"
              aria-label="Filter by social account"
            >
              <option value="all" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                All Accounts ({socialAccounts.length})
              </option>
              {socialAccounts.map((acc) => (
                <option
                  key={acc.id}
                  value={acc.id}
                  className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                >
                  {acc.platform.toUpperCase()}: {acc.account_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
};
