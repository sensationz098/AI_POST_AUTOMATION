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
      bg: 'bg-slate-900/60 border-slate-700/80 text-slate-300',
      dot: 'bg-slate-400',
      icon: FileEdit,
    },
    APPROVED: {
      label: 'Approved',
      bg: 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300',
      dot: 'bg-emerald-400',
      icon: CheckCircle,
    },
    SCHEDULED: {
      label: 'Scheduled',
      bg: 'bg-sky-950/40 border-sky-800/60 text-sky-300',
      dot: 'bg-sky-400',
      icon: Clock,
    },
    PUBLISHED: {
      label: 'Published',
      bg: 'bg-indigo-950/40 border-indigo-800/60 text-indigo-300',
      dot: 'bg-indigo-400',
      icon: Send,
    },
    FAILED: {
      label: 'Failed',
      bg: 'bg-rose-950/40 border-rose-800/60 text-rose-300',
      dot: 'bg-rose-400',
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
