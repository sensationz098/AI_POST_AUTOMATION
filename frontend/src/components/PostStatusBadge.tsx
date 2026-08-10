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
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
      dot: 'bg-amber-400',
      icon: FileEdit,
    },
    APPROVED: {
      label: 'Approved',
      bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
      dot: 'bg-emerald-400',
      icon: CheckCircle,
    },
    SCHEDULED: {
      label: 'Scheduled',
      bg: 'bg-blue-500/10 border-blue-500/30 text-blue-300',
      dot: 'bg-blue-400',
      icon: Clock,
    },
    PUBLISHED: {
      label: 'Published',
      bg: 'bg-indigo-500/15 border-indigo-500/35 text-indigo-300',
      dot: 'bg-indigo-400',
      icon: Send,
    },
    FAILED: {
      label: 'Failed',
      bg: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
      dot: 'bg-rose-400',
      icon: AlertTriangle,
    },
  };

  const config = configs[normalized] || configs.DRAFT;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border shadow-sm ${config.bg}`}
    >
      <Icon className="w-3 h-3 flex-shrink-0" />
      <span>{config.label}</span>
    </span>
  );
};
