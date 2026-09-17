'use client';

import React from 'react';
import Link from 'next/link';
import { Target, ExternalLink, ChevronRight, Megaphone, MessageSquare } from 'lucide-react';

interface AdCardProps {
  ad: {
    id: number | string;
    meta_ad_id: string;
    name: string;
    campaign_name?: string;
    adset_name?: string;
    effective_status?: string;
    facebook_page_id?: string;
    facebook_post_id?: string;
    created_at?: string;
    comment_count: number;
    top_level_comment_count?: number;
    permalink?: string;
    platform?: string;
  };
  selectedAccountId?: string;
  onViewComments?: (adId: string) => void;
  children?: React.ReactNode;
}

export default function AdCardComponent({
  ad,
  selectedAccountId = 'ALL',
  onViewComments,
  children,
}: AdCardProps) {
  const isActive = ad.effective_status === 'ACTIVE';
  const commentCountToDisplay = ad.top_level_comment_count !== undefined
    ? ad.top_level_comment_count
    : ad.comment_count;

  const drilldownHref = `/comments/ads/${ad.id}${
    selectedAccountId !== 'ALL' ? `?social_account_id=${selectedAccountId}` : ''
  }`;

  return (
    <div className="bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800/90 rounded-2xl overflow-hidden shadow-sm transition hover:border-purple-300 dark:hover:border-purple-800/60 flex flex-col justify-between space-y-3">
      {/* 1. Header: Ad Identity & Effective Status */}
      <div className="p-4 pb-0 flex items-start justify-between gap-3">
        <div className="flex items-start space-x-3 min-w-0">
          <div className="w-9 h-9 rounded-full bg-purple-50 dark:bg-purple-950/90 border border-purple-200 dark:border-purple-800/80 flex items-center justify-center text-purple-600 dark:text-purple-400 flex-shrink-0 shadow-sm mt-0.5">
            <Target className="w-4 h-4" />
          </div>

          <div className="min-w-0 space-y-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100 truncate">{ad.name}</h3>
              <span
                className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold flex-shrink-0 border ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800'
                    : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800'
                }`}
              >
                ● {ad.effective_status || 'UNKNOWN'}
              </span>
            </div>

            <div className="text-[11px] text-slate-600 dark:text-slate-400 space-y-0.5 font-sans">
              {ad.campaign_name && (
                <p className="truncate">
                  <span className="text-slate-500 font-semibold">Campaign:</span> {ad.campaign_name}
                </p>
              )}
              {ad.adset_name && (
                <p className="truncate">
                  <span className="text-slate-500 font-semibold">Ad Set:</span> {ad.adset_name}
                </p>
              )}
              <p className="font-mono text-[10px] text-slate-500">ID: {ad.meta_ad_id}</p>
            </div>
          </div>
        </div>

        {/* External Link Button */}
        {ad.permalink && (ad.permalink.startsWith('http://') || ad.permalink.startsWith('https://')) && (
          <a
            href={ad.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 dark:bg-blue-950/70 dark:hover:bg-blue-900/80 border border-slate-200 dark:border-blue-700/70 text-slate-700 dark:text-blue-200 text-[11px] font-semibold transition flex items-center space-x-1 flex-shrink-0"
          >
            <span>View Ad</span>
            <ExternalLink className="w-3 h-3 text-slate-500 dark:text-blue-300" />
          </a>
        )}
      </div>

      {/* 2. Embedded Conversations Container */}
      {children && <div className="px-4 pt-1">{children}</div>}

      {/* 3. Footer: Engagement Bar & Action Button */}
      <div className="p-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
        <div className="flex items-center space-x-2 text-xs text-slate-700 dark:text-purple-300 font-semibold">
          <MessageSquare className="w-4 h-4 text-purple-600 dark:text-purple-400" />
          <span>{commentCountToDisplay} Comments</span>
        </div>

        <div className="flex items-center space-x-2">
          {onViewComments ? (
            <button
              onClick={() => onViewComments(String(ad.id))}
              className="px-3.5 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-950/80 dark:hover:bg-purple-900 dark:text-purple-200 dark:border-purple-800/80 font-bold text-xs transition flex items-center space-x-1"
            >
              <span>Inspect Ad Conversations</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <Link
              href={drilldownHref}
              className="px-3.5 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-950/80 dark:hover:bg-purple-900 dark:text-purple-200 dark:border-purple-800/80 font-bold text-xs transition flex items-center space-x-1"
            >
              <span>Inspect Ad Conversations</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
