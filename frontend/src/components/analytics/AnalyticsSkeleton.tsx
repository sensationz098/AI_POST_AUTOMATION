'use client';

import React from 'react';

export const KpiGridSkeleton: React.FC = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div
          key={i}
          className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-3 animate-pulse"
        >
          <div className="flex items-center justify-between">
            <div className="h-3 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800/60" />
          </div>
          <div className="space-y-1.5">
            <div className="h-6 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-3 w-16 bg-slate-100 dark:bg-slate-800/60 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
};

export const ChartSkeleton: React.FC = () => {
  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-5 shadow-xs space-y-4 animate-pulse">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/60 pb-3">
        <div className="space-y-1.5">
          <div className="h-4 w-44 bg-slate-200 dark:bg-slate-800 rounded" />
          <div className="h-3 w-64 bg-slate-100 dark:bg-slate-800/60 rounded" />
        </div>
        <div className="flex items-center space-x-3">
          <div className="h-3 w-16 bg-slate-100 dark:bg-slate-800/60 rounded" />
          <div className="h-3 w-20 bg-slate-100 dark:bg-slate-800/60 rounded" />
        </div>
      </div>
      <div className="h-72 w-full bg-slate-50 dark:bg-slate-900/40 rounded-lg flex items-end p-4 space-x-4">
        {[40, 65, 30, 80, 50, 90, 75, 60, 85, 45, 70, 95].map((height, i) => (
          <div
            key={i}
            className="flex-1 bg-slate-200 dark:bg-slate-800/80 rounded-t"
            style={{ height: `${height}%` }}
          />
        ))}
      </div>
    </div>
  );
};

export const PlatformBreakdownSkeleton: React.FC = () => {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 w-36 bg-slate-200 dark:bg-slate-800 rounded" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-800" />
                <div className="space-y-1">
                  <div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
                  <div className="h-2.5 w-12 bg-slate-100 dark:bg-slate-800/60 rounded" />
                </div>
              </div>
              <div className="h-4 w-12 bg-slate-100 dark:bg-slate-800 rounded" />
            </div>
            <div className="grid grid-cols-2 gap-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60">
              {[1, 2, 3, 4].map((j) => (
                <div key={j} className="space-y-1">
                  <div className="h-2.5 w-14 bg-slate-100 dark:bg-slate-800/60 rounded" />
                  <div className="h-3.5 w-10 bg-slate-200 dark:bg-slate-800 rounded" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const TableSkeleton: React.FC = () => {
  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-5 shadow-xs space-y-4 animate-pulse">
      <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/60 pb-3">
        <div className="h-4 w-36 bg-slate-200 dark:bg-slate-800 rounded" />
        <div className="h-8 w-44 bg-slate-100 dark:bg-slate-800 rounded" />
      </div>
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="flex items-center justify-between py-2.5 border-b border-slate-100 dark:border-slate-800/40 last:border-0"
          >
            <div className="flex items-center space-x-3 flex-1 min-w-0 pr-4">
              <div className="w-12 h-12 rounded-lg bg-slate-200 dark:bg-slate-800 flex-shrink-0" />
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="h-3.5 w-3/4 bg-slate-200 dark:bg-slate-800 rounded" />
                <div className="h-2.5 w-1/3 bg-slate-100 dark:bg-slate-800/60 rounded" />
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <div className="h-3 w-12 bg-slate-100 dark:bg-slate-800/60 rounded hidden sm:block" />
              <div className="h-3 w-12 bg-slate-100 dark:bg-slate-800/60 rounded hidden md:block" />
              <div className="h-3 w-12 bg-slate-100 dark:bg-slate-800/60 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
