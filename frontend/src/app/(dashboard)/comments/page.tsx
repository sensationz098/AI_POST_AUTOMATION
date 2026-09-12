'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  MessageSquare, 
  RefreshCw, 
  Search, 
  Filter, 
  ArrowUpDown, 
  CheckCircle2, 
  Bot, 
  Clock, 
  AlertCircle, 
  PlusCircle, 
  Sparkles,
  Layers,
  Megaphone,
  Share2
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { 
  SocialComment, 
  SocialAccount, 
  SocialCommentReply, 
  InboxStatusCounts, 
  InboxHealthMetrics,
  AutomationPlatform
} from '@/lib/types';
import CommentCard from './components/CommentCard';
import CommentDetailDrawer from './components/CommentDetailDrawer';
import AutomationWizardModal, { AutomationPrefillData } from '../automations/components/AutomationWizardModal';

type StatusFilterKey = 'all' | 'needs_reply' | 'automated' | 'replied' | 'ignored' | 'failed';

export default function CommentInboxPage() {
  const searchParams = useSearchParams();
  const initialAccountId = searchParams.get('social_account_id') || 'ALL';

  // Data states
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [statusCounts, setStatusCounts] = useState<InboxStatusCounts>({
    all: 0,
    needs_reply: 0,
    automated: 0,
    replied: 0,
    ignored: 0,
    failed: 0,
  });
  const [healthMetrics, setHealthMetrics] = useState<InboxHealthMetrics | null>(null);

  // Filter states
  const [activeTab, setActiveTab] = useState<StatusFilterKey>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState<'ALL' | 'instagram' | 'facebook'>('ALL');
  const [selectedAccountId, setSelectedAccountId] = useState<string>(initialAccountId);
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // UI interaction states
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedComment, setSelectedComment] = useState<SocialComment | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Create automation modal state
  const [isAutomationModalOpen, setIsAutomationModalOpen] = useState(false);
  const [automationPrefill, setAutomationPrefill] = useState<AutomationPrefillData | null>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch connected social accounts
  const fetchSocialAccounts = async () => {
    try {
      const res = await apiClient.get('/social-accounts/');
      setSocialAccounts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch social accounts:', e);
    }
  };

  // Fetch summary metrics (counts + health)
  const fetchInboxSummary = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (platformFilter !== 'ALL') params.append('platform', platformFilter);
      if (selectedAccountId !== 'ALL') params.append('social_account_id', selectedAccountId);

      const res = await apiClient.get(`/social-comments/inbox-summary?${params.toString()}`);
      if (res.data?.status_counts) {
        setStatusCounts(res.data.status_counts);
      }
      if (res.data?.health) {
        setHealthMetrics(res.data.health);
      }
    } catch (e) {
      console.error('Failed to fetch inbox summary:', e);
    }
  }, [platformFilter, selectedAccountId]);

  // Fetch comments with filters
  const fetchComments = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('skip', '0');
      params.append('limit', '50');
      params.append('sort_order', sortOrder);

      if (activeTab !== 'all') {
        params.append('status', activeTab);
      }

      if (platformFilter !== 'ALL') {
        params.append('platform', platformFilter);
      }

      if (selectedAccountId !== 'ALL') {
        params.append('social_account_id', selectedAccountId);
      }

      if (debouncedSearch) {
        params.append('search', debouncedSearch);
      }

      const res = await apiClient.get(`/social-comments/?${params.toString()}`);
      setComments(res.data || []);
    } catch (e: any) {
      console.error('Failed to fetch inbox comments:', e);
      setError(e?.response?.data?.detail || 'Failed to load comments. Please check your connection.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [activeTab, platformFilter, selectedAccountId, debouncedSearch, sortOrder]);

  // Initial load
  useEffect(() => {
    fetchSocialAccounts();
  }, []);

  // Refetch when filters change
  useEffect(() => {
    fetchInboxSummary();
    fetchComments();
  }, [fetchInboxSummary, fetchComments]);

  // Handle comment selection
  const handleSelectComment = (comment: SocialComment) => {
    setSelectedComment(comment);
    setIsDrawerOpen(true);
  };

  // Handle direct reply click
  const handleReplyClick = (comment: SocialComment) => {
    setSelectedComment(comment);
    setIsDrawerOpen(true);
  };

  // Handle reply added in drawer
  const handleReplyAdded = (commentId: number, newReply: SocialCommentReply) => {
    setComments((prev) =>
      prev.map((c) => {
        if (c.id === commentId) {
          const updatedReplies = [...(c.replies || []), newReply];
          return {
            ...c,
            lifecycle_status: 'REPLIED',
            status_reason: 'Reply sent successfully.',
            replies: updatedReplies,
          };
        }
        return c;
      })
    );
    if (selectedComment && selectedComment.id === commentId) {
      setSelectedComment((prev) =>
        prev
          ? {
              ...prev,
              lifecycle_status: 'REPLIED',
              status_reason: 'Reply sent successfully.',
              replies: [...(prev.replies || []), newReply],
            }
          : null
      );
    }
    // Update summary counts
    fetchInboxSummary();
  };

  // Handle Create Automation click from comment card
  const handleCreateAutomationClick = (comment: SocialComment) => {
    // Extract candidate keywords from comment text (simple stopwords filter)
    const rawWords = (comment.comment_text || '')
      .toLowerCase()
      .replace(/[^\w\s]/g, '')
      .split(/\s+/)
      .filter((w) => w.length > 2 && !['the', 'and', 'for', 'this', 'that', 'with', 'you', 'how', 'can'].includes(w));
    const suggestedKeywords = Array.from(new Set(rawWords)).slice(0, 4);

    const prefill: AutomationPrefillData = {
      platform: (comment.platform as AutomationPlatform) || 'instagram',
      social_account_id: comment.social_account_id,
      external_post_id: comment.external_post_id || null,
      post_title: comment.post?.title || null,
      post_thumbnail: comment.post?.thumbnail_url || comment.post?.image_url || null,
      name: comment.comment_text ? `Auto-Reply: "${comment.comment_text.slice(0, 20)}..."` : 'Comment Auto-Reply',
      keywords: suggestedKeywords.length > 0 ? suggestedKeywords : ['price', 'info'],
      sample_comment: comment.comment_text || undefined,
    };

    setAutomationPrefill(prefill);
    setIsAutomationModalOpen(true);
  };

  // Tabs configuration
  const tabs: Array<{ key: StatusFilterKey; label: string; count: number }> = [
    { key: 'all', label: 'All', count: statusCounts.all },
    { key: 'needs_reply', label: 'Needs Reply', count: statusCounts.needs_reply },
    { key: 'automated', label: 'Automated', count: statusCounts.automated },
    { key: 'replied', label: 'Replied', count: statusCounts.replied },
    { key: 'ignored', label: 'Ignored', count: statusCounts.ignored },
    { key: 'failed', label: 'Failed', count: statusCounts.failed },
  ];

  return (
    <div className="min-h-screen bg-[#F7F8FA] dark:bg-slate-950 text-slate-800 dark:text-slate-100 font-sans p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-xs">
          <div>
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
                  Comments
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Monitor and respond to comments across your connected accounts.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3 flex-wrap gap-y-2">
            {/* Health indicators */}
            {healthMetrics && (
              <div className="flex items-center space-x-2 text-xs">
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium ${
                  healthMetrics.instagram_connected 
                    ? 'bg-pink-50 text-pink-700 border border-pink-200 dark:bg-pink-950/40 dark:text-pink-300 dark:border-pink-800' 
                    : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${healthMetrics.instagram_connected ? 'bg-pink-500' : 'bg-slate-400'}`} />
                  Instagram
                </span>

                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium ${
                  healthMetrics.facebook_connected 
                    ? 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800' 
                    : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${healthMetrics.facebook_connected ? 'bg-blue-500' : 'bg-slate-400'}`} />
                  Facebook
                </span>
              </div>
            )}

            {/* Refresh Button */}
            <button
              onClick={() => {
                fetchInboxSummary();
                fetchComments(true);
              }}
              disabled={refreshing || loading}
              className="px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition flex items-center space-x-1.5 shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-indigo-600' : ''}`} />
              <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>

        {/* Status Tabs Bar */}
        <div className="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none border-b border-slate-200/80 dark:border-slate-800">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3.5 py-2 rounded-t-xl text-xs font-semibold transition whitespace-nowrap flex items-center space-x-2 border-b-2 ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-white dark:bg-slate-900 shadow-xs'
                    : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100/60 dark:hover:bg-slate-800/40'
                }`}
              >
                <span>{tab.label}</span>
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                  isActive
                    ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}>
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Filter Controls Row */}
        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/90 dark:border-slate-800 shadow-xs flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Search Bar */}
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by comment text, commenter name..."
              className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center space-x-2.5 flex-wrap gap-y-2">
            {/* Platform Filter */}
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value as any)}
              className="text-xs px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
            >
              <option value="ALL">All Platforms</option>
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
            </select>

            {/* Account Filter */}
            {socialAccounts.length > 0 && (
              <select
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                className="text-xs px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 max-w-[180px] truncate"
              >
                <option value="ALL">All Accounts</option>
                {socialAccounts.map((acc) => (
                  <option key={acc.id} value={String(acc.id)}>
                    {acc.platform === 'instagram' ? '📷 ' : '📘 '}
                    {acc.account_name}
                  </option>
                ))}
              </select>
            )}

            {/* Sort Order */}
            <button
              onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
              className="px-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition flex items-center space-x-1.5"
            >
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <span>{sortOrder === 'desc' ? 'Newest first' : 'Oldest first'}</span>
            </button>
          </div>
        </div>

        {/* Error State Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => fetchComments()}
              className="px-3 py-1 rounded-lg bg-rose-600 text-white font-semibold hover:bg-rose-700 transition"
            >
              Retry
            </button>
          </div>
        )}

        {/* Comments List or Skeleton or Empty States */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-3 animate-pulse"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-800" />
                    <div className="space-y-1.5">
                      <div className="w-32 h-3.5 bg-slate-200 dark:bg-slate-800 rounded" />
                      <div className="w-20 h-2.5 bg-slate-200 dark:bg-slate-800 rounded" />
                    </div>
                  </div>
                  <div className="w-20 h-6 bg-slate-200 dark:bg-slate-800 rounded-full" />
                </div>
                <div className="w-full h-4 bg-slate-200 dark:bg-slate-800 rounded" />
                <div className="w-3/4 h-3 bg-slate-200 dark:bg-slate-800 rounded" />
              </div>
            ))}
          </div>
        ) : comments.length === 0 ? (
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-10 sm:p-14 text-center space-y-3">
            {activeTab === 'needs_reply' ? (
              <>
                <div className="w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                  You're all caught up!
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  No comments currently require manual attention. All comments have been automated, replied to, or handled.
                </p>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-400 mx-auto flex items-center justify-center">
                  <MessageSquare className="w-6 h-6" />
                </div>
                <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                  No comments yet
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  Comments from your connected Instagram and Facebook accounts will appear here automatically when received.
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {comments.map((comment) => (
              <CommentCard
                key={comment.id}
                comment={comment}
                isSelected={selectedComment?.id === comment.id && isDrawerOpen}
                onSelect={handleSelectComment}
                onReplyClick={handleReplyClick}
                onCreateAutomationClick={handleCreateAutomationClick}
              />
            ))}
          </div>
        )}

      </div>

      {/* Slide-over Detail Drawer */}
      <CommentDetailDrawer
        isOpen={isDrawerOpen}
        comment={selectedComment}
        onClose={() => setIsDrawerOpen(false)}
        onReplyAdded={handleReplyAdded}
        onCreateAutomationClick={handleCreateAutomationClick}
      />

      {/* Create Automation Wizard Modal (Prefilled from comment) */}
      <AutomationWizardModal
        isOpen={isAutomationModalOpen}
        editingAutomation={null}
        initialValues={automationPrefill}
        socialAccounts={socialAccounts}
        onClose={() => {
          setIsAutomationModalOpen(false);
          setAutomationPrefill(null);
        }}
        onSuccess={() => {
          setIsAutomationModalOpen(false);
          setAutomationPrefill(null);
          fetchInboxSummary();
          fetchComments();
        }}
      />
    </div>
  );
}
