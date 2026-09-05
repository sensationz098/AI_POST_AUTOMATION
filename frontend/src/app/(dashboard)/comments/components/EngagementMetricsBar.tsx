'use client';

import React from 'react';
import { MessageSquare, MessageCircle, CornerDownRight, AlertCircle } from 'lucide-react';

interface MetricsProps {
  topLevelCount: number;
  replyCount: number;
  totalInteractions: number;
  unrepliedCount?: number;
  repliedCount?: number;
  title?: string;
  subtitle?: string;
  label?: string;
  loading?: boolean;
}

export default function EngagementMetricsBar({
  topLevelCount,
  replyCount,
  totalInteractions,
  unrepliedCount,
  repliedCount,
  title,
  subtitle,
  label = 'Scoped Engagement Overview',
  loading = false,
}: MetricsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 bg-slate-900/60 rounded-xl border border-slate-800/80"></div>
        ))}
      </div>
    );
  }

  const displayTitle = title || label || 'Account-Level Engagement Metrics';
  const displaySubtitle = subtitle !== undefined ? subtitle : (title ? undefined : 'Scoped by Account Selector');

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-slate-400 font-semibold px-0.5">
        <span className="uppercase tracking-wider text-[11px] text-slate-400 font-bold flex items-center space-x-1.5">
          <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
          <span>{displayTitle}</span>
        </span>
        {displaySubtitle && (
          <span className="text-[10px] text-slate-500 font-mono">{displaySubtitle}</span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {/* 1. Top-Level Conversations */}
        <div className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-3.5 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Conversations</p>
            <p className="text-xl font-extrabold text-slate-100 mt-0.5">{topLevelCount}</p>
            <p className="text-[10px] text-slate-500">Top-level threads</p>
          </div>
          <div className="w-9 h-9 rounded-lg bg-blue-950/80 border border-blue-800/80 flex items-center justify-center text-blue-400">
            <MessageSquare className="w-4 h-4" />
          </div>
        </div>

        {/* 2. Nested Replies */}
        <div className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-3.5 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">Nested Replies</p>
            <p className="text-xl font-extrabold text-indigo-300 mt-0.5">{replyCount}</p>
            <p className="text-[10px] text-slate-500">Meta & owner replies</p>
          </div>
          <div className="w-9 h-9 rounded-lg bg-indigo-950/80 border border-indigo-800/80 flex items-center justify-center text-indigo-400">
            <CornerDownRight className="w-4 h-4" />
          </div>
        </div>

        {/* 3. Total Interactions */}
        <div className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-3.5 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Total Interactions</p>
            <p className="text-xl font-extrabold text-emerald-300 mt-0.5">{totalInteractions}</p>
            <p className="text-[10px] text-slate-500">Threads + replies</p>
          </div>
          <div className="w-9 h-9 rounded-lg bg-emerald-950/80 border border-emerald-800/80 flex items-center justify-center text-emerald-400">
            <MessageCircle className="w-4 h-4" />
          </div>
        </div>

        {/* 4. Unreplied / Attention Count */}
        <div className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-3.5 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
              {unrepliedCount !== undefined ? 'Unreplied Threads' : 'Moderation Status'}
            </p>
            <p className="text-xl font-extrabold text-amber-300 mt-0.5">
              {unrepliedCount !== undefined ? unrepliedCount : 'Active'}
            </p>
            <p className="text-[10px] text-slate-500">
              {unrepliedCount !== undefined ? 'Awaiting response' : 'System synchronized'}
            </p>
          </div>
          <div className="w-9 h-9 rounded-lg bg-amber-950/80 border border-amber-800/80 flex items-center justify-center text-amber-400">
            <AlertCircle className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
}
