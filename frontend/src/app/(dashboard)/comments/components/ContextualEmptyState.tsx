'use client';

import React from 'react';
import { MessageSquare, FileText, Target, CheckCircle2, ShieldAlert } from 'lucide-react';

interface EmptyStateProps {
  type?: 'posts' | 'ads' | 'unreplied' | 'general' | 'error';
  title?: string;
  description?: string;
  onResetFilters?: () => void;
}

export default function ContextualEmptyState({
  type = 'general',
  title,
  description,
  onResetFilters,
}: EmptyStateProps) {
  let defaultTitle = 'No Conversations Found';
  let defaultDescription = 'There are no active conversations for the selected account filter.';
  let icon = <MessageSquare className="w-8 h-8 text-slate-500 mx-auto" />;

  if (type === 'unreplied') {
    defaultTitle = "You're All Caught Up!";
    defaultDescription = 'No unreplied customer conversations for this account.';
    icon = <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />;
  } else if (type === 'posts') {
    defaultTitle = 'No Organic Posts Recorded';
    defaultDescription = 'No organic posts match your platform or search filter for this account.';
    icon = <FileText className="w-8 h-8 text-blue-400 mx-auto" />;
  } else if (type === 'ads') {
    defaultTitle = 'No Meta Ads Found';
    defaultDescription = 'No Meta ads with active comments found for this account.';
    icon = <Target className="w-8 h-8 text-purple-400 mx-auto" />;
  } else if (type === 'error') {
    defaultTitle = 'Unable to Load Engagement Data';
    defaultDescription = 'An error occurred while fetching data for the selected social account.';
    icon = <ShieldAlert className="w-8 h-8 text-rose-400 mx-auto" />;
  }

  return (
    <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-3 max-w-lg mx-auto">
      {icon}
      <h4 className="text-sm font-bold text-slate-200">{title || defaultTitle}</h4>
      <p className="text-xs text-slate-400 leading-relaxed max-w-md mx-auto">
        {description || defaultDescription}
      </p>

      {onResetFilters && (
        <div className="pt-2">
          <button
            onClick={onResetFilters}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
          >
            Reset Filters
          </button>
        </div>
      )}
    </div>
  );
}
