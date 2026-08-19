'use client';

import React from 'react';
import { PostStatus } from '@/lib/types';
import { FileEdit, CheckCircle, Clock, Send, AlertTriangle } from 'lucide-react';

interface Props {
  status: PostStatus | string;
}

export const PostStatusBadge: React.FC<Props> = ({ status }) => {
  const normalized = (status || 'DRAFT').toUpperCase() as PostStatus;

  const configs: Record<string, { label: string; styleClass: string; icon: any }> = {
    DRAFT: {
      label: 'DRAFT',
      styleClass: 'bg-[var(--bg-tertiary)] text-[var(--warning-color)] border-[var(--border-color)]',
      icon: FileEdit,
    },
    APPROVED: {
      label: 'APPROVED',
      styleClass: 'bg-[var(--bg-tertiary)] text-[var(--accent-color)] border-[var(--border-color)]',
      icon: CheckCircle,
    },
    SCHEDULED: {
      label: 'SCHEDULED',
      styleClass: 'bg-[var(--bg-tertiary)] text-[var(--accent-color)] border-[var(--border-color)]',
      icon: Clock,
    },
    PUBLISHED: {
      label: 'PUBLISHED',
      styleClass: 'bg-[var(--bg-tertiary)] text-[var(--success-color)] border-[var(--border-color)]',
      icon: Send,
    },
    FAILED: {
      label: 'FAILED',
      styleClass: 'bg-[var(--bg-tertiary)] text-[var(--danger-color)] border-[var(--border-color)]',
      icon: AlertTriangle,
    },
  };

  const config = configs[normalized] || configs.DRAFT;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${config.styleClass}`}
    >
      <Icon className="w-3 h-3 flex-shrink-0" />
      <span>{config.label}</span>
    </span>
  );
};
