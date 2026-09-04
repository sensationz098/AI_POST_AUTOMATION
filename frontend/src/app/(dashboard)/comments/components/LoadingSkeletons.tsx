'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

export function MetricsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="h-20 bg-slate-900/60 rounded-xl border border-slate-800/80 p-3.5 space-y-2">
          <div className="h-3 w-16 bg-slate-800 rounded"></div>
          <div className="h-6 w-10 bg-slate-800 rounded"></div>
        </div>
      ))}
    </div>
  );
}

export function ThreadSkeleton() {
  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 space-y-3 animate-pulse">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-full bg-slate-800 flex-shrink-0"></div>
        <div className="space-y-1.5 flex-1">
          <div className="h-3 w-28 bg-slate-800 rounded"></div>
          <div className="h-2.5 w-20 bg-slate-800/70 rounded"></div>
        </div>
      </div>
      <div className="h-14 bg-slate-950/70 rounded-xl border border-slate-800/60"></div>
    </div>
  );
}

export function PostSkeleton() {
  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 space-y-3 animate-pulse">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-full bg-slate-800 flex-shrink-0"></div>
        <div className="space-y-1.5 flex-1">
          <div className="h-3 w-36 bg-slate-800 rounded"></div>
          <div className="h-2.5 w-24 bg-slate-800/70 rounded"></div>
        </div>
      </div>
      <div className="h-36 bg-slate-950 rounded-xl"></div>
      <div className="h-4 w-3/4 bg-slate-800 rounded"></div>
    </div>
  );
}

export function FeedLoadingView({ label = 'Loading conversations...' }: { label?: string }) {
  return (
    <div className="py-16 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-3">
      <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
      <p className="text-xs text-slate-400 font-medium">{label}</p>
    </div>
  );
}
