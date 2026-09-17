'use client';

import React from 'react';
import { PostStatus } from '@/lib/types';
import { FileEdit, CheckCircle, Clock, Send, AlertTriangle } from 'lucide-react';

interface Props {
  status: PostStatus | string;
}

export const PostStatusBadge: React.FC<Props> = ({ status }) => {
  const normalized = (status || 'DRAFT').toUpperCase() as PostStatus;

  const configs = {
    DRAFT: {
      label: 'Draft',
      bg: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900/60 dark:border-slate-700/80 dark:text-slate-300',
      dot: 'bg-slate-400',
      icon: FileEdit,
    },
    APPROVED: {
      label: 'Approved',
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800/60 dark:text-emerald-300',
      dot: 'bg-emerald-500 dark:bg-emerald-400',
      icon: CheckCircle,
    },
    SCHEDULED: {
      label: 'Scheduled',
      bg: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/40 dark:border-sky-800/60 dark:text-sky-300',
      dot: 'bg-sky-500 dark:bg-sky-400',
      icon: Clock,
    },
    PUBLISHED: {
      label: 'Published',
      bg: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:border-indigo-800/60 dark:text-indigo-300',
      dot: 'bg-indigo-500 dark:bg-indigo-400',
      icon: Send,
    },
    FAILED: {
      label: 'Failed',
      bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:border-rose-800/60 dark:text-rose-300',
      dot: 'bg-rose-500 dark:bg-rose-400',
      icon: AlertTriangle,
    },
  };

  const config = configs[normalized] || configs.DRAFT;

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${config.bg}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      <span>{config.label}</span>
    </span>
  );
};
