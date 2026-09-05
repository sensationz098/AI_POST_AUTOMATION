'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  Megaphone, 
  Target,
  RefreshCw, 
  Search,
  Filter,
  ArrowUpDown,
  Sparkles
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialAccount } from '@/lib/types';

import AccountSelector from '../components/AccountSelector';
import EngagementMetricsBar from '../components/EngagementMetricsBar';
import AdCardComponent from '../components/AdCardComponent';
import ContextualEmptyState from '../components/ContextualEmptyState';
import { PostSkeleton } from '../components/LoadingSkeletons';

interface OverviewMetrics {
  scope?: string;
  top_level_comment_count: number;
  reply_count: number;
  total_interaction_count: number;
  total_comments: number;
  total_ad_comments: number;
  total_post_comments: number;
  post_reply_count?: number;
  ad_reply_count?: number;
  ads_metrics?: {
    top_level_comment_count: number;
    reply_count: number;
    total_interaction_count: number;
  };
}

interface AdItem {
  id: number;
  meta_ad_id: string;
  name: string;
  campaign_name?: string;
  adset_name?: string;
  effective_status?: string;
  created_at?: string;
  comment_count: number;
  top_level_comment_count?: number;
  unreplied_comment_count?: number;
  replied_comment_count?: number;
  permalink?: string;
  platform?: string;
}

export default function MetaAdsCommentsPage() {
  const searchParams = useSearchParams();
  const initialAccountId = searchParams.get('social_account_id') || 'ALL';

  // Social account selection state
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>(initialAccountId);

  // Overview metrics state
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(false);

  // Filter controls state
  const [searchQuery, setSearchQuery] = useState('');
  const [adStatusFilter, setAdStatusFilter] = useState<'all' | 'active' | 'paused'>('all');
  const [replyStatusFilter, setReplyStatusFilter] = useState<'all' | 'unreplied' | 'replied'>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // Meta Ads state
  const [ads, setAds] = useState<AdItem[]>([]);
  const [loadingAds, setLoadingAds] = useState(false);

  // 1. Fetch connected social accounts
  const fetchSocialAccounts = async () => {
    try {
      const res = await apiClient.get('/social-accounts/');
      setSocialAccounts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch social accounts:', e);
    }
  };

  // 2. Fetch authoritative ad engagement overview
  const fetchOverview = async () => {
    setLoadingOverview(true);
    try {
      const params = new URLSearchParams();
      params.append('scope', 'ads');
      if (selectedAccountId !== 'ALL') params.append('social_account_id', selectedAccountId);
      const res = await apiClient.get(`/social-comments/overview?${params.toString()}`);
      setOverview(res.data);
    } catch (e) {
      console.error('Failed to fetch ad overview metrics:', e);
    } finally {
      setLoadingOverview(false);
    }
  };

  // 3. Fetch Meta Ads index with ad status filtering
  const fetchAds = async () => {
    setLoadingAds(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('q', searchQuery.trim());
      if (selectedAccountId !== 'ALL') params.append('social_account_id', selectedAccountId);
      if (adStatusFilter !== 'all') params.append('status', adStatusFilter.toUpperCase());

      const res = await apiClient.get(`/social-comments/ads?${params.toString()}`);
      setAds(res.data || []);
    } catch (e) {
      console.error('Failed to fetch ads:', e);
    } finally {
      setLoadingAds(false);
    }
  };

  // Initial Load
  useEffect(() => {
    fetchSocialAccounts();
  }, []);

  // Account Selection Handler
  const handleSelectAccount = (accountId: string) => {
    setSelectedAccountId(accountId);
    setAds([]);
    setOverview(null);
  };

  // Refetch when account or ad status changes
  useEffect(() => {
    fetchOverview();
    fetchAds();
  }, [selectedAccountId, adStatusFilter]);

  const selectedAccountObj = socialAccounts.find((a) => String(a.id) === String(selectedAccountId));

  // Client-side thread status filtering
  const filteredAds = ads.filter((ad) => {
    if (replyStatusFilter === 'unreplied') {
      const unreplied = ad.unreplied_comment_count ?? ad.top_level_comment_count ?? ad.comment_count;
      return unreplied > 0;
    }
    if (replyStatusFilter === 'replied') {
      const replied = ad.replied_comment_count ?? ((ad.top_level_comment_count ?? ad.comment_count) - (ad.unreplied_comment_count ?? 0));
      return replied > 0;
    }
    return true;
  });

  // Sort filtered ads
  const sortedAds = [...filteredAds].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
  });

  const adMetrics = overview?.ads_metrics ?? {
    top_level_comment_count: overview?.total_ad_comments ?? 0,
    reply_count: overview?.ad_reply_count ?? 0,
    total_interaction_count: (overview?.total_ad_comments ?? 0) + (overview?.ad_reply_count ?? 0),
  };

  const getAdsEmptyDescription = () => {
    if (adStatusFilter === 'active' && replyStatusFilter === 'unreplied') {
      return `No unreplied conversations found for active ads${selectedAccountId !== 'ALL' ? ` on ${selectedAccountObj?.account_name || 'selected account'}` : ''}.`;
    }
    if (adStatusFilter === 'active' && replyStatusFilter === 'replied') {
      return `No replied conversations found for active ads${selectedAccountId !== 'ALL' ? ` on ${selectedAccountObj?.account_name || 'selected account'}` : ''}.`;
    }
    if (adStatusFilter === 'paused' && replyStatusFilter === 'unreplied') {
      return `No unreplied conversations found for paused ads${selectedAccountId !== 'ALL' ? ` on ${selectedAccountObj?.account_name || 'selected account'}` : ''}.`;
    }
    if (adStatusFilter === 'paused' && replyStatusFilter === 'replied') {
      return `No replied conversations found for paused ads${selectedAccountId !== 'ALL' ? ` on ${selectedAccountObj?.account_name || 'selected account'}` : ''}.`;
    }
    if (adStatusFilter === 'active') {
      return `No active Meta Ads found${selectedAccountId !== 'ALL' ? ` for ${selectedAccountObj?.account_name || 'selected account'}` : ''}.`;
    }
    if (adStatusFilter === 'paused') {
      return `No paused Meta Ads found${selectedAccountId !== 'ALL' ? ` for ${selectedAccountObj?.account_name || 'selected account'}` : ''}.`;
    }
    if (replyStatusFilter === 'unreplied') {
      return `No unreplied conversations found for Meta Ads.`;
    }
    if (replyStatusFilter === 'replied') {
      return `No replied conversations found for Meta Ads.`;
    }
    return selectedAccountId !== 'ALL'
      ? `No synced Meta Ads found for ${selectedAccountObj?.account_name || 'selected account'}.`
      : 'No synced Meta Ads match your current filter.';
  };

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Top Bar Header & Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight flex items-center space-x-2.5">
            <Megaphone className="w-6 h-6 text-purple-400" />
            <span>Meta Ads Comments</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage and respond to conversations generated by your Meta advertising campaigns.
          </p>
        </div>

        <button
          onClick={() => {
            fetchOverview();
            fetchAds();
          }}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-bold transition flex items-center space-x-2 self-start md:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5 text-purple-400" />
          <span>Refresh Ads</span>
        </button>
      </div>

      {/* 1. Account Selector Bar */}
      <AccountSelector
        accounts={socialAccounts}
        selectedAccountId={selectedAccountId}
        onSelectAccount={handleSelectAccount}
      />

      {/* 2. Contextual Engagement Metrics Bar */}
      <EngagementMetricsBar
        title="AD CONVERSATION METRICS"
        subtitle="Scoped to Meta Ads"
        topLevelCount={adMetrics.top_level_comment_count}
        replyCount={adMetrics.reply_count}
        totalInteractions={adMetrics.total_interaction_count}
        loading={loadingOverview}
      />

      {/* 3. Dedicated Meta Ads Filter Bar */}
      <div className="space-y-3">
        {/* Search Input Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/70 p-3 rounded-2xl border border-slate-800/90 shadow-sm">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchAds()}
              placeholder="Search by ad name, campaign, or ad set..."
              className="w-full bg-slate-950 border border-slate-800 focus:border-purple-500 text-xs rounded-xl pl-8 pr-3 py-2 text-slate-100 placeholder-slate-500 outline-none transition"
            />
          </div>

          <button
            onClick={fetchAds}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold transition self-end md:self-auto"
          >
            Search Ads
          </button>
        </div>

        {/* Ad Status, Thread Status & Sorting Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 overflow-x-auto pb-1">
          <div className="flex flex-wrap items-center gap-3">
            {/* Ad Status Filter */}
            <div className="flex items-center space-x-2 border-r border-slate-800/80 pr-3">
              <span className="text-[11px] font-bold text-purple-400 uppercase tracking-wider flex items-center space-x-1">
                <Target className="w-3 h-3 text-purple-400" />
                <span>Ad Status:</span>
              </span>

              <button
                onClick={() => setAdStatusFilter('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  adStatusFilter === 'all'
                    ? 'bg-purple-950 text-purple-200 border border-purple-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                All Ads
              </button>

              <button
                onClick={() => setAdStatusFilter('active')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                  adStatusFilter === 'active'
                    ? 'bg-emerald-950 text-emerald-200 border border-emerald-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>Active</span>
              </button>

              <button
                onClick={() => setAdStatusFilter('paused')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                  adStatusFilter === 'paused'
                    ? 'bg-amber-950 text-amber-200 border border-amber-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>Paused</span>
              </button>
            </div>

            {/* Thread Status Filter */}
            <div className="flex items-center space-x-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center space-x-1">
                <Filter className="w-3 h-3 text-slate-500" />
                <span>Thread Status:</span>
              </span>

              <button
                onClick={() => setReplyStatusFilter('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  replyStatusFilter === 'all'
                    ? 'bg-purple-950 text-purple-200 border border-purple-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                All Threads
              </button>

              <button
                onClick={() => setReplyStatusFilter('unreplied')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                  replyStatusFilter === 'unreplied'
                    ? 'bg-amber-950 text-amber-200 border border-amber-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>Unreplied</span>
              </button>

              <button
                onClick={() => setReplyStatusFilter('replied')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                  replyStatusFilter === 'replied'
                    ? 'bg-emerald-950 text-emerald-200 border border-emerald-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>Replied</span>
              </button>
            </div>

            {/* Sort Order Controls */}
            <div className="flex items-center space-x-2 border-l border-slate-800/80 pl-3">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center space-x-1">
                <ArrowUpDown className="w-3 h-3 text-slate-500" />
                <span>Sort:</span>
              </span>

              <button
                onClick={() => setSortOrder('desc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sortOrder === 'desc'
                    ? 'bg-purple-950 text-purple-200 border border-purple-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                Newest First
              </button>

              <button
                onClick={() => setSortOrder('asc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sortOrder === 'asc'
                    ? 'bg-purple-950 text-purple-200 border border-purple-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                Oldest First
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-slate-500 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800/60 opacity-75 whitespace-nowrap self-start sm:self-auto">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>AI Moderation Ready</span>
          </div>
        </div>
      </div>

      {/* 4. Meta Ads Grid */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1 pb-1 border-b border-slate-800/60">
          <span className="flex items-center space-x-2 text-purple-300 font-bold">
            <span>Meta Ads ({sortedAds.length})</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400 font-normal">
              {adMetrics.top_level_comment_count} Meta Ad Conversations
            </span>
          </span>
          <span className="text-[11px] text-slate-500 font-mono">Meta Campaign Ad Content</span>
        </div>

        {loadingAds ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <PostSkeleton />
            <PostSkeleton />
          </div>
        ) : sortedAds.length === 0 ? (
          <ContextualEmptyState
            type="ads"
            description={getAdsEmptyDescription()}
            onResetFilters={() => {
              setSearchQuery('');
              setAdStatusFilter('all');
              setReplyStatusFilter('all');
              fetchAds();
            }}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sortedAds.map((ad) => (
              <AdCardComponent
                key={ad.id}
                ad={ad}
                selectedAccountId={selectedAccountId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
