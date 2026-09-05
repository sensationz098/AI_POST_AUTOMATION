'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  MessageSquare, 
  RefreshCw, 
  Search,
  Filter,
  ArrowUpDown,
  Sparkles
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialAccount } from '@/lib/types';

import AccountSelector from '../components/AccountSelector';
import AccountCommentBreakdownBar, { AccountMetric } from '../components/AccountCommentBreakdownBar';
import EngagementMetricsBar from '../components/EngagementMetricsBar';
import PostCardComponent from '../components/PostCardComponent';
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
  posts_metrics?: {
    top_level_comment_count: number;
    reply_count: number;
    total_interaction_count: number;
  };
  account_metrics?: AccountMetric[];
}

interface PostItem {
  id: number | string;
  external_post_id: string;
  social_account_id?: number;
  account_name?: string;
  title: string;
  caption?: string;
  image_url?: string;
  media_type?: string;
  platform: string;
  published_at?: string;
  comment_count: number;
  top_level_comment_count?: number;
  unreplied_comment_count?: number;
  replied_comment_count?: number;
  permalink?: string;
}

export default function OrganicCommentsPage() {
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
  const [platformFilter, setPlatformFilter] = useState('ALL');
  const [replyStatusFilter, setReplyStatusFilter] = useState<'all' | 'unreplied' | 'replied'>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // Organic Posts state
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);

  // 1. Fetch connected social accounts
  const fetchSocialAccounts = async () => {
    try {
      const res = await apiClient.get('/social-accounts/');
      setSocialAccounts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch social accounts:', e);
    }
  };

  // 2. Fetch authoritative organic engagement overview
  const fetchOverview = async () => {
    setLoadingOverview(true);
    try {
      const params = new URLSearchParams();
      params.append('scope', 'posts');
      if (selectedAccountId !== 'ALL') params.append('social_account_id', selectedAccountId);
      const res = await apiClient.get(`/social-comments/overview?${params.toString()}`);
      setOverview(res.data);
    } catch (e) {
      console.error('Failed to fetch organic overview metrics:', e);
    } finally {
      setLoadingOverview(false);
    }
  };

  // 3. Fetch Organic Posts index
  const fetchPosts = async () => {
    setLoadingPosts(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('q', searchQuery.trim());
      if (platformFilter && platformFilter !== 'ALL') params.append('platform', platformFilter.toLowerCase());
      if (selectedAccountId !== 'ALL') params.append('social_account_id', selectedAccountId);

      const res = await apiClient.get(`/social-comments/posts?${params.toString()}`);
      setPosts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch organic posts:', e);
    } finally {
      setLoadingPosts(false);
    }
  };

  // Initial Load
  useEffect(() => {
    fetchSocialAccounts();
  }, []);

  // Account Selection Handler
  const handleSelectAccount = (accountId: string) => {
    setSelectedAccountId(accountId);
    setPosts([]);
    setOverview(null);
  };

  // Refetch when account, platform, or search changes
  useEffect(() => {
    fetchOverview();
    fetchPosts();
  }, [selectedAccountId, platformFilter]);

  const selectedAccountObj = socialAccounts.find((a) => String(a.id) === String(selectedAccountId));

  // Client-side thread status filtering
  const filteredPosts = posts.filter((post) => {
    if (replyStatusFilter === 'unreplied') {
      const unreplied = post.unreplied_comment_count ?? post.top_level_comment_count ?? post.comment_count;
      return unreplied > 0;
    }
    if (replyStatusFilter === 'replied') {
      const replied = post.replied_comment_count ?? ((post.top_level_comment_count ?? post.comment_count) - (post.unreplied_comment_count ?? 0));
      return replied > 0;
    }
    return true;
  });

  // Sort filtered posts
  const sortedPosts = [...filteredPosts].sort((a, b) => {
    const timeA = a.published_at ? new Date(a.published_at).getTime() : 0;
    const timeB = b.published_at ? new Date(b.published_at).getTime() : 0;
    return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
  });

  // Defensive Filter: When an individual account is selected, strictly enforce account & platform isolation
  const accountScopedPosts = sortedPosts.filter((post) => {
    if (selectedAccountId !== 'ALL' && selectedAccountObj) {
      if (post.platform && selectedAccountObj.platform && post.platform.toLowerCase() !== selectedAccountObj.platform.toLowerCase()) {
        return false;
      }
      if (post.social_account_id && String(post.social_account_id) !== String(selectedAccountId)) {
        return false;
      }
    }
    return true;
  });

  const organicMetrics = overview?.posts_metrics ?? {
    top_level_comment_count: overview?.total_post_comments ?? 0,
    reply_count: overview?.post_reply_count ?? 0,
    total_interaction_count: (overview?.total_post_comments ?? 0) + (overview?.post_reply_count ?? 0),
  };

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Top Bar Header & Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight flex items-center space-x-2.5">
            <MessageSquare className="w-6 h-6 text-blue-400" />
            <span>Organic Post Comments</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage and respond to conversations on your published Facebook and Instagram posts.
          </p>
        </div>

        <button
          onClick={() => {
            fetchOverview();
            fetchPosts();
          }}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-bold transition flex items-center space-x-2 self-start md:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
          <span>Refresh Feed</span>
        </button>
      </div>

      {/* 1. Account Selector Bar */}
      <AccountSelector
        accounts={socialAccounts}
        selectedAccountId={selectedAccountId}
        onSelectAccount={handleSelectAccount}
      />

      {/* 2. Comments by Account Breakdown Bar */}
      {socialAccounts.length > 0 && (
        <AccountCommentBreakdownBar
          accounts={
            overview?.account_metrics && overview.account_metrics.length > 0
              ? overview.account_metrics
              : socialAccounts.map((a) => ({
                  social_account_id: a.id,
                  account_name: a.account_name,
                  username: a.username || (a.platform === 'instagram' ? a.account_name : undefined),
                  platform: a.platform,
                  logo_url: a.logo_url,
                  top_level_comment_count: 0,
                  reply_count: 0,
                  total_interaction_count: 0,
                }))
          }
          selectedAccountId={selectedAccountId}
          onSelectAccount={handleSelectAccount}
          totalOrganicConversations={overview?.total_post_comments ?? 0}
          totalOrganicReplies={overview?.post_reply_count ?? 0}
          loading={loadingOverview}
        />
      )}

      {/* 3. Contextual Engagement Metrics Bar */}
      <EngagementMetricsBar
        title="POST CONVERSATION METRICS"
        subtitle="Scoped to Organic Posts"
        topLevelCount={organicMetrics.top_level_comment_count}
        replyCount={organicMetrics.reply_count}
        totalInteractions={organicMetrics.total_interaction_count}
        loading={loadingOverview}
      />

      {/* 3. Dedicated Organic Filter Bar */}
      <div className="space-y-3">
        {/* Search & Platform Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/70 p-3 rounded-2xl border border-slate-800/90 shadow-sm">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchPosts()}
              placeholder="Search post caption or content..."
              className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 text-xs rounded-xl pl-8 pr-3 py-2 text-slate-100 placeholder-slate-500 outline-none transition"
            />
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 font-semibold outline-none focus:border-blue-500 transition cursor-pointer"
            >
              <option value="ALL">All Platforms</option>
              <option value="FACEBOOK">Facebook</option>
              <option value="INSTAGRAM">Instagram</option>
            </select>

            <button
              onClick={fetchPosts}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition"
            >
              Search
            </button>
          </div>
        </div>

        {/* Thread Status & Sorting Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 overflow-x-auto pb-1">
          <div className="flex flex-wrap items-center gap-3">
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
                    ? 'bg-blue-950 text-blue-200 border border-blue-700/80 shadow-sm'
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
                    ? 'bg-blue-950 text-blue-200 border border-blue-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                Newest First
              </button>

              <button
                onClick={() => setSortOrder('asc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sortOrder === 'asc'
                    ? 'bg-blue-950 text-blue-200 border border-blue-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                Oldest First
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-slate-500 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800/60 opacity-75 whitespace-nowrap self-start sm:self-auto">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>AI Moderation Ready</span>
          </div>
        </div>
      </div>

      {/* 4. Organic Posts Grid */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1 pb-1 border-b border-slate-800/60">
          <span className="flex items-center space-x-2 text-blue-300 font-bold">
            <span>Organic Posts ({accountScopedPosts.length})</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400 font-normal">
              {organicMetrics.top_level_comment_count} Organic Conversations
            </span>
          </span>
          <span className="text-[11px] text-slate-500 font-mono">Strictly Non-Ad Organic Content</span>
        </div>

        {loadingPosts ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <PostSkeleton />
            <PostSkeleton />
          </div>
        ) : accountScopedPosts.length === 0 ? (
          <ContextualEmptyState
            type="posts"
            description={
              selectedAccountId !== 'ALL'
                ? `No organic posts found for ${selectedAccountObj?.account_name || 'selected account'}.`
                : 'No organic posts match your current search or platform filter.'
            }
            onResetFilters={() => {
              setSearchQuery('');
              setPlatformFilter('ALL');
              setReplyStatusFilter('all');
              fetchPosts();
            }}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {accountScopedPosts.map((post) => (
              <PostCardComponent
                key={`${post.platform}_${post.external_post_id || post.id}`}
                post={post}
                selectedAccountId={selectedAccountId}
                accountName={selectedAccountObj?.account_name || post.account_name}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
