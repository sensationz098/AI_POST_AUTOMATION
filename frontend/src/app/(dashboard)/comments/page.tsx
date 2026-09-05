'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  MessageSquare, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Sparkles,
  Layers,
  ChevronDown,
  Loader2
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialAccount, SocialComment, SocialCommentReply } from '@/lib/types';

// Import New Social Conversation Feed Components
import AccountSelector from './components/AccountSelector';
import EngagementMetricsBar from './components/EngagementMetricsBar';
import EngagementFilterBar from './components/EngagementFilterBar';
import PostCardComponent from './components/PostCardComponent';
import AdCardComponent from './components/AdCardComponent';
import ConversationThread from './components/ConversationThread';
import ContextualEmptyState from './components/ContextualEmptyState';
import { FeedLoadingView, PostSkeleton, MetricsSkeleton } from './components/LoadingSkeletons';

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
  ads_metrics?: {
    top_level_comment_count: number;
    reply_count: number;
    total_interaction_count: number;
  };
  all_metrics?: {
    top_level_comment_count: number;
    reply_count: number;
    total_interaction_count: number;
  };
  recent_ads: Array<{
    id: number;
    name: string;
    campaign_name?: string;
    comment_count: number;
    effective_status?: string;
  }>;
  recent_posts: Array<{
    id: number | string;
    external_post_id: string;
    title: string;
    comment_count: number;
    platform: string;
  }>;
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

interface PostItem {
  id: number | string;
  external_post_id: string;
  title: string;
  caption?: string;
  image_url?: string;
  media_type?: string;
  platform: string;
  published_at?: string;
  comment_count: number;
  top_level_comment_count?: number;
  permalink?: string;
}

export default function EngagementDashboardPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const tabParam = (searchParams.get('tab') as 'posts' | 'ads' | 'stream') || 'posts';

  // Social account selection state
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('ALL');

  // Overview metrics state
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(false);

  // Content Feed state
  const [activeTab, setActiveTab] = useState<'posts' | 'ads' | 'stream'>(tabParam);
  const [replyStatusFilter, setReplyStatusFilter] = useState<'all' | 'unreplied' | 'replied'>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [adStatusFilter, setAdStatusFilter] = useState<'all' | 'active' | 'paused'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState('ALL');

  // Ads state
  const [ads, setAds] = useState<AdItem[]>([]);
  const [loadingAds, setLoadingAds] = useState(false);

  // Organic Posts state
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);

  // Unified Stream state
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [streamSkip, setStreamSkip] = useState(0);
  const [hasMoreComments, setHasMoreComments] = useState(false);
  const [loadingComments, setLoadingComments] = useState(false);
  const [loadingMoreComments, setLoadingMoreComments] = useState(false);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [globalNotice, setGlobalNotice] = useState<string | null>(null);

  // Synchronize Tab with URL query param
  useEffect(() => {
    if (tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  const handleTabChange = (newTab: 'posts' | 'ads' | 'stream') => {
    setActiveTab(newTab);
    router.push(`/comments?tab=${newTab}`);
  };

  // 1. Fetch connected social accounts
  const fetchSocialAccounts = async () => {
    try {
      const res = await apiClient.get('/social-accounts/');
      setSocialAccounts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch social accounts:', e);
    }
  };

  // 2. Fetch authoritative engagement overview
  const fetchOverview = async () => {
    setLoadingOverview(true);
    try {
      const params = new URLSearchParams();
      if (selectedAccountId !== 'ALL') params.append('social_account_id', selectedAccountId);
      const res = await apiClient.get(`/social-comments/overview?${params.toString()}`);
      setOverview(res.data);
    } catch (e) {
      console.error('Failed to fetch overview metrics:', e);
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
      console.error('Failed to fetch posts:', e);
    } finally {
      setLoadingPosts(false);
    }
  };

  // 4. Fetch Meta Ads index with ad status filtering
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

  // 5. Fetch Unified Comments Feed Stream
  const fetchCommentsFeed = async (skip = 0, append = false) => {
    if (append) {
      setLoadingMoreComments(true);
    } else {
      setLoadingComments(true);
    }
    setCommentsError(null);
    try {
      const params = new URLSearchParams();
      params.append('skip', String(skip));
      params.append('limit', '50');
      params.append('sort_order', sortOrder);
      if (replyStatusFilter !== 'all') {
        params.append('reply_status', replyStatusFilter);
      }
      if (selectedAccountId !== 'ALL') {
        params.append('social_account_id', selectedAccountId);
      }
      if (platformFilter && platformFilter !== 'ALL') {
        params.append('platform', platformFilter.toLowerCase());
      }

      const res = await apiClient.get(`/social-comments/?${params.toString()}`);
      const newComments = res.data || [];
      setHasMoreComments(newComments.length === 50);
      setStreamSkip(skip);

      if (append) {
        setComments((prev) => [...prev, ...newComments]);
      } else {
        setComments(newComments);
      }
    } catch (e: any) {
      console.error('Failed to fetch comments feed:', e);
      setCommentsError(e?.response?.data?.detail || 'Failed to load comments feed.');
    } finally {
      setLoadingComments(false);
      setLoadingMoreComments(false);
    }
  };

  const handleLoadMoreStream = () => {
    if (loadingMoreComments || !hasMoreComments) return;
    const nextSkip = streamSkip + 50;
    fetchCommentsFeed(nextSkip, true);
  };

  // Initial Load
  useEffect(() => {
    fetchSocialAccounts();
  }, []);

  // Handle Account Selection Change -> Clear Stale State & Fetch New Account Data Immediately
  const handleSelectAccount = (accountId: string) => {
    setSelectedAccountId(accountId);
    setStreamSkip(0);
    // Clear feed states to prevent displaying stale data from previous account
    setPosts([]);
    setAds([]);
    setComments([]);
    setOverview(null);
  };

  // Trigger Data Fetch on Tab, Account ID, Platform, Reply Status, Sort Order, or Ad Status Change
  useEffect(() => {
    fetchOverview();
    if (activeTab === 'posts') fetchPosts();
    if (activeTab === 'ads') fetchAds();
    if (activeTab === 'stream') fetchCommentsFeed(0, false);
  }, [activeTab, selectedAccountId, platformFilter, adStatusFilter, replyStatusFilter, sortOrder]);

  // Reply Addition Handler (Updates Thread local state & metrics)
  const handleReplyAdded = (commentId: number, newReply: SocialCommentReply) => {
    setComments((prevComments) =>
      prevComments.map((c) => {
        if (c.id === commentId) {
          const updatedReplies = [...(c.replies || []), newReply];
          return { ...c, replies: updatedReplies };
        }
        return c;
      })
    );

    setGlobalNotice('Reply posted successfully!');
    setTimeout(() => setGlobalNotice(null), 4000);
  };

  // Comment Deletion Handler
  const handleCommentDeleted = async (commentId: number) => {
    try {
      await apiClient.delete(`/social-comments/${commentId}`);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      setGlobalNotice('Comment deleted successfully.');
      setTimeout(() => setGlobalNotice(null), 3000);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to delete comment.');
    }
  };

  // Client-side filtering for thread status ('all' | 'unreplied' | 'replied')
  const filteredComments = comments.filter((c) => {
    const hasReplies = c.replies && c.replies.length > 0;
    if (replyStatusFilter === 'unreplied') return !hasReplies;
    if (replyStatusFilter === 'replied') return hasReplies;
    return true;
  });

  // Combined filtering for Meta Ads (Ad Status + Thread Status)
  const filteredAds = ads.filter((ad) => {
    if (replyStatusFilter === 'unreplied') {
      const unrepliedCount = ad.unreplied_comment_count ?? (ad.top_level_comment_count ?? ad.comment_count);
      return unrepliedCount > 0;
    }
    if (replyStatusFilter === 'replied') {
      const repliedCount = ad.replied_comment_count ?? ((ad.top_level_comment_count ?? ad.comment_count) - (ad.unreplied_comment_count ?? 0));
      return repliedCount > 0;
    }
    return true;
  });

  const selectedAccountObj = socialAccounts.find((a) => String(a.id) === String(selectedAccountId));

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
            <MessageSquare className="w-6 h-6 text-indigo-400" />
            <span>Social Engagement Hub</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Social-media-native conversation stream and moderation co-pilot.
          </p>
        </div>

        <button
          onClick={() => {
            fetchOverview();
            if (activeTab === 'posts') fetchPosts();
            if (activeTab === 'ads') fetchAds();
            if (activeTab === 'stream') fetchCommentsFeed(0, false);
          }}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-bold transition flex items-center space-x-2 self-start md:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
          <span>Refresh Feed</span>
        </button>
      </div>

      {/* 1. Account Selector Bar */}
      <AccountSelector
        accounts={socialAccounts}
        selectedAccountId={selectedAccountId}
        onSelectAccount={handleSelectAccount}
      />

      {/* Global Toast Notice */}
      {globalNotice && (
        <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs flex items-center space-x-2 shadow-sm animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{globalNotice}</span>
        </div>
      )}

      {/* 2. Contextual Engagement Metrics Bar */}
      {(() => {
        const activeMetrics = activeTab === 'posts'
          ? (overview?.posts_metrics ?? {
              top_level_comment_count: overview?.total_post_comments ?? 0,
              reply_count: overview?.post_reply_count ?? 0,
              total_interaction_count: (overview?.total_post_comments ?? 0) + (overview?.post_reply_count ?? 0)
            })
          : activeTab === 'ads'
          ? (overview?.ads_metrics ?? {
              top_level_comment_count: overview?.total_ad_comments ?? 0,
              reply_count: overview?.ad_reply_count ?? 0,
              total_interaction_count: (overview?.total_ad_comments ?? 0) + (overview?.ad_reply_count ?? 0)
            })
          : (overview?.all_metrics ?? {
              top_level_comment_count: overview?.top_level_comment_count ?? 0,
              reply_count: overview?.reply_count ?? 0,
              total_interaction_count: overview?.total_interaction_count ?? 0
            });

        const metricsTitle = activeTab === 'posts'
          ? 'POST CONVERSATION METRICS'
          : activeTab === 'ads'
          ? 'AD CONVERSATION METRICS'
          : 'ACCOUNT-LEVEL ENGAGEMENT METRICS';

        const metricsSubtitle = activeTab === 'posts'
          ? 'Scoped to Organic Posts'
          : activeTab === 'ads'
          ? 'Scoped to Meta Ads'
          : 'Scoped by Account Selector';

        return (
          <EngagementMetricsBar
            title={metricsTitle}
            subtitle={metricsSubtitle}
            topLevelCount={activeMetrics.top_level_comment_count}
            replyCount={activeMetrics.reply_count}
            totalInteractions={activeMetrics.total_interaction_count}
            loading={loadingOverview}
          />
        );
      })()}

      {/* 3. Engagement Filter & Navigation Bar */}
      <EngagementFilterBar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        replyStatusFilter={replyStatusFilter}
        onReplyStatusChange={setReplyStatusFilter}
        sortOrder={sortOrder}
        onSortOrderChange={setSortOrder}
        adStatusFilter={adStatusFilter}
        onAdStatusChange={setAdStatusFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearchSubmit={() => {
          if (activeTab === 'posts') fetchPosts();
          if (activeTab === 'ads') fetchAds();
        }}
        platformFilter={platformFilter}
        onPlatformChange={setPlatformFilter}
      />

      {/* 4. MAIN SOCIAL CONVERSATION FEED CONTENT VIEWS */}
      <div className="pt-2">
        {/* VIEW 1: ORGANIC POSTS FEED */}
        {activeTab === 'posts' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1 pb-1 border-b border-slate-800/60">
              <span className="flex items-center space-x-2 text-indigo-300 font-bold">
                <span>Organic Posts ({posts.length})</span>
                <span className="text-slate-600">•</span>
                <span className="text-slate-400 font-normal">{overview?.total_post_comments ?? 0} Organic Conversations</span>
              </span>
              <span className="text-[11px] text-slate-500 font-mono">Strictly Non-Ad Organic Content</span>
            </div>

            {loadingPosts ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <PostSkeleton />
                <PostSkeleton />
              </div>
            ) : posts.length === 0 ? (
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
                  fetchPosts();
                }}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {posts.map((post) => (
                  <PostCardComponent
                    key={post.id}
                    post={post}
                    selectedAccountId={selectedAccountId}
                    accountName={selectedAccountObj?.account_name}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: META ADS FEED */}
        {activeTab === 'ads' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1 pb-1 border-b border-slate-800/60">
              <span className="flex items-center space-x-2 text-purple-300 font-bold">
                <span>Meta Ads ({filteredAds.length})</span>
                <span className="text-slate-600">•</span>
                <span className="text-slate-400 font-normal">{overview?.total_ad_comments ?? 0} Meta Ad Conversations</span>
              </span>
              <span className="text-[11px] text-slate-500 font-mono">Meta Campaign Ad Content</span>
            </div>

            {loadingAds ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <PostSkeleton />
                <PostSkeleton />
              </div>
            ) : filteredAds.length === 0 ? (
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
                {filteredAds.map((ad) => (
                  <AdCardComponent
                    key={ad.id}
                    ad={ad}
                    selectedAccountId={selectedAccountId}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* VIEW 3: UNIFIED CONVERSATION STREAM */}
        {activeTab === 'stream' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1 pb-1 border-b border-slate-800/60">
              <span className="flex items-center space-x-2 text-emerald-300 font-bold">
                <span>All Conversations Stream ({comments.length})</span>
                <span className="text-slate-600">•</span>
                <span className="text-slate-400 font-normal">
                  {sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}
                </span>
              </span>
              <span className="text-[11px] text-slate-500 font-mono">Parent Context Enabled</span>
            </div>

            {commentsError && (
              <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-sm flex items-center space-x-3">
                <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
                <span>{commentsError}</span>
              </div>
            )}

            {loadingComments ? (
              <FeedLoadingView label="Loading conversation threads..." />
            ) : comments.length === 0 ? (
              <ContextualEmptyState
                type={replyStatusFilter === 'unreplied' ? 'unreplied' : 'general'}
                description={
                  replyStatusFilter === 'unreplied'
                    ? `You're all caught up! No unreplied conversations for ${selectedAccountObj?.account_name || 'this view'}.`
                    : `No comments found for ${selectedAccountObj?.account_name || 'the selected account filter'}.`
                }
                onResetFilters={() => {
                  setReplyStatusFilter('all');
                  setSortOrder('desc');
                  fetchCommentsFeed(0, false);
                }}
              />
            ) : (
              <div className="space-y-4 max-w-4xl mx-auto">
                {comments.map((comment) => (
                  <ConversationThread
                    key={comment.id}
                    comment={comment}
                    onReplyAdded={handleReplyAdded}
                    onCommentDeleted={handleCommentDeleted}
                  />
                ))}

                {hasMoreComments && (
                  <div className="pt-4 text-center">
                    <button
                      onClick={handleLoadMoreStream}
                      disabled={loadingMoreComments}
                      className="px-4 py-2 rounded-xl bg-emerald-950/80 hover:bg-emerald-900 text-emerald-200 border border-emerald-800 text-xs font-semibold transition flex items-center space-x-2 mx-auto disabled:opacity-50"
                    >
                      {loadingMoreComments ? (
                        <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-emerald-400" />
                      )}
                      <span>{loadingMoreComments ? 'Loading older comments...' : 'Load More Comments'}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
