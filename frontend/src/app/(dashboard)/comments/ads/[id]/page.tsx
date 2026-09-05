'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Target, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  ChevronDown
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialComment, SocialCommentReply, MetaAdCommentsResponse } from '@/lib/types';

import ConversationThread from '../../components/ConversationThread';
import AdCardComponent from '../../components/AdCardComponent';
import ContextualEmptyState from '../../components/ContextualEmptyState';
import EngagementMetricsBar from '../../components/EngagementMetricsBar';

interface AdDetails {
  id: number | string;
  meta_ad_id: string;
  name: string;
  campaign_name?: string;
  adset_name?: string;
  effective_status?: string;
  facebook_page_id?: string;
  facebook_post_id?: string;
  meta_ad_account_id?: string;
  permalink?: string;
  platform?: string;
}

export default function AdCommentsPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const adId = params?.id as string;
  const socialAccountId = searchParams?.get('social_account_id');

  const [ad, setAd] = useState<AdDetails | null>(null);
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [topLevelCount, setTopLevelCount] = useState(0);
  const [replyCount, setReplyCount] = useState(0);
  const [totalInteractions, setTotalInteractions] = useState(0);
  const [replyStatusFilter, setReplyStatusFilter] = useState<'all' | 'unreplied' | 'replied'>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchAdComments = async (pageNum = 1, append = false, currentFilter = replyStatusFilter, currentSort = sortOrder) => {
    if (!adId) return;
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const requestUrl = `/social-comments/ads/${adId}`;
      const queryParams: any = { page: pageNum, limit: 50, reply_status: currentFilter, sort_order: currentSort };
      if (socialAccountId) queryParams.social_account_id = socialAccountId;

      const res = await apiClient.get<MetaAdCommentsResponse>(requestUrl, {
        params: queryParams
      });

      const payload = res?.data;
      const adObj = payload?.ad || null;
      const commentsList = Array.isArray(payload?.comments) ? payload.comments : [];
      
      const tTop = typeof payload?.top_level_comment_count === 'number' ? payload.top_level_comment_count : (payload?.total_comments || 0);
      const tReply = typeof payload?.reply_count === 'number' ? payload.reply_count : 0;
      const tTotal = typeof payload?.total_interaction_count === 'number' ? payload.total_interaction_count : (tTop + tReply);
      const hasNextPage = Boolean(payload?.has_next);
      const currentPage = typeof payload?.page === 'number' ? payload.page : pageNum;

      setAd(adObj);
      setTopLevelCount(tTop);
      setReplyCount(tReply);
      setTotalInteractions(tTotal);
      setHasNext(hasNextPage);
      setPage(currentPage);

      if (append) {
        setComments((prev) => [...prev, ...commentsList]);
      } else {
        setComments(commentsList);
      }
    } catch (e: any) {
      console.error('Failed to fetch ad comments:', e);
      setError(e?.response?.data?.detail || 'Failed to load comments for this Meta ad.');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchAdComments(1, false, replyStatusFilter, sortOrder);
  }, [adId, replyStatusFilter, sortOrder, socialAccountId]);

  const handleLoadMore = () => {
    if (!hasNext || loadingMore) return;
    const nextPage = page + 1;
    fetchAdComments(nextPage, true, replyStatusFilter, sortOrder);
  };

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
    setReplyCount((prev) => prev + 1);
    setTotalInteractions((prev) => prev + 1);
    setNotice('Reply posted successfully!');
    setTimeout(() => setNotice(null), 4000);
  };

  const handleCommentDeleted = async (commentId: number) => {
    await apiClient.delete(`/social-comments/${commentId}`);
    setComments((prev) => prev.filter((c) => c.id !== commentId));
    setTopLevelCount((prev) => Math.max(0, prev - 1));
    setTotalInteractions((prev) => Math.max(0, prev - 1));
    setNotice('Comment deleted successfully.');
    setTimeout(() => setNotice(null), 3000);
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Top Header & Breadcrumb */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link
            href={`/comments?tab=ads${socialAccountId ? `&social_account_id=${socialAccountId}` : ''}`}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Back to Meta Ads Index"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
              <Target className="w-5 h-5 text-purple-400" />
              <span>Meta Ad Conversations</span>
            </h1>
            <p className="text-xs text-slate-400">
              Inspect conversation threads and brand responses for this Meta Ad.
            </p>
          </div>
        </div>

        <button
          onClick={() => fetchAdComments(1, false, replyStatusFilter, sortOrder)}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-semibold transition flex items-center space-x-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5 text-purple-400" />
          <span>Refresh</span>
        </button>
      </div>

      {notice && (
        <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-800/80 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-sm flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-3">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading Meta Ad content & conversation threads...</p>
        </div>
      ) : !ad ? (
        <ContextualEmptyState type="ads" title="Ad Not Found" description="The requested Meta Ad could not be loaded." />
      ) : (
        <div className="space-y-6">
          {/* Meta Ad Card Banner */}
          <AdCardComponent
            ad={{
              ...ad,
              comment_count: topLevelCount,
            }}
            selectedAccountId={socialAccountId || 'ALL'}
          />

          {/* Scoped Metrics Bar */}
          <EngagementMetricsBar
            title="AD CONVERSATION METRICS"
            subtitle="Scoped to this Meta Ad"
            topLevelCount={topLevelCount}
            replyCount={replyCount}
            totalInteractions={totalInteractions}
          />

          {/* Filter & Sort Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-2xl border border-slate-800/90">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-slate-400 uppercase">Filter:</span>
              <button
                onClick={() => setReplyStatusFilter('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  replyStatusFilter === 'all'
                    ? 'bg-purple-950 text-purple-200 border border-purple-800'
                    : 'bg-slate-950 text-slate-400 border border-slate-800'
                }`}
              >
                All Threads
              </button>
              <button
                onClick={() => setReplyStatusFilter('unreplied')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  replyStatusFilter === 'unreplied'
                    ? 'bg-amber-950 text-amber-200 border border-amber-800'
                    : 'bg-slate-950 text-slate-400 border border-slate-800'
                }`}
              >
                Unreplied
              </button>
              <button
                onClick={() => setReplyStatusFilter('replied')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  replyStatusFilter === 'replied'
                    ? 'bg-emerald-950 text-emerald-200 border border-emerald-800'
                    : 'bg-slate-950 text-slate-400 border border-slate-800'
                }`}
              >
                Replied
              </button>
            </div>

            <div className="flex items-center space-x-2 border-t sm:border-t-0 sm:border-l border-slate-800/80 pt-2 sm:pt-0 sm:pl-3">
              <span className="text-xs font-bold text-slate-400 uppercase">Sort:</span>
              <button
                onClick={() => setSortOrder('desc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  sortOrder === 'desc'
                    ? 'bg-purple-950 text-purple-200 border border-purple-800 shadow-sm'
                    : 'bg-slate-950 text-slate-400 border border-slate-800'
                }`}
              >
                Newest First
              </button>
              <button
                onClick={() => setSortOrder('asc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  sortOrder === 'asc'
                    ? 'bg-purple-950 text-purple-200 border border-purple-800 shadow-sm'
                    : 'bg-slate-950 text-slate-400 border border-slate-800'
                }`}
              >
                Oldest First
              </button>
            </div>
          </div>

          {/* Conversation Threads List */}
          {comments.length === 0 ? (
            <ContextualEmptyState
              type={replyStatusFilter === 'unreplied' ? 'unreplied' : 'general'}
              description={
                replyStatusFilter === 'unreplied'
                  ? 'No unreplied threads exist for this Meta ad.'
                  : 'No comments recorded for this Meta ad yet.'
              }
            />
          ) : (
            <div className="space-y-4">
              {comments.map((comment) => (
                <ConversationThread
                  key={comment.id}
                  comment={comment}
                  onReplyAdded={handleReplyAdded}
                  onCommentDeleted={handleCommentDeleted}
                />
              ))}

              {hasNext && (
                <div className="pt-4 text-center">
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="px-4 py-2 rounded-xl bg-purple-950/80 hover:bg-purple-900 text-purple-200 border border-purple-800 text-xs font-semibold transition flex items-center space-x-2 mx-auto disabled:opacity-50"
                  >
                    {loadingMore ? (
                      <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-purple-400" />
                    )}
                    <span>{loadingMore ? 'Loading older comments...' : 'Load More Comments'}</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
