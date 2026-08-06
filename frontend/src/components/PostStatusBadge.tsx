'use client';

import React from 'react';
import { PostStatus } from '@/lib/types';
import { FileEdit, CheckCircle, Clock, Send, AlertTriangle } from 'lucide-react';

interface Props {
  status: PostStatus;
}

export const PostStatusBadge: React.FC<Props> = ({ status }) => {
  const configs = {
    DRAFT: {
      label: 'Draft',
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
      icon: FileEdit,
    },
    APPROVED: {
      label: 'Approved',
      bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
      icon: CheckCircle,
    },
    SCHEDULED: {
      label: 'Scheduled',
      bg: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
      icon: Clock,
    },
    PUBLISHED: {
      label: 'Published',
      bg: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400',
      icon: Send,
    },
    FAILED: {
      label: 'Failed',
      bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
      icon: AlertTriangle,
    },
  };

  const config = configs[status] || configs.DRAFT;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${config.bg}`}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{config.label}</span>
    </span>
  );
};
