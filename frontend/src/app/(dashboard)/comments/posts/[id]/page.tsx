'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  FileText,
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialComment, SocialCommentReply } from '@/lib/types';

import ConversationThread from '../../components/ConversationThread';
import ContextualEmptyState from '../../components/ContextualEmptyState';
import EngagementMetricsBar from '../../components/EngagementMetricsBar';
import SocialPostPreview from '@/components/SocialPostPreview';

interface PostDetails {
  id: number | string;
  external_post_id: string;
  title: string;
  caption?: string;
  image_url?: string;
  media_type?: string;
  platform?: string;
  published_at?: string;
  permalink?: string;
  account_name?: string;
  account_avatar?: string;
}

export default function PostCommentsPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const postId = params?.id as string;
  const socialAccountId = searchParams?.get('social_account_id');

  const [post, setPost] = useState<PostDetails | null>(null);
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [topLevelCount, setTopLevelCount] = useState(0);
  const [filteredTopLevelCount, setFilteredTopLevelCount] = useState(0);
  const [replyCount, setReplyCount] = useState(0);
  const [totalInteractions, setTotalInteractions] = useState(0);

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [replyStatusFilter, setReplyStatusFilter] = useState<'all' | 'unreplied' | 'replied'>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [notice, setNotice] = useState<string | null>(null);

  const fetchPostComments = async (isManualSync = false) => {
    if (!postId) return;
    if (isManualSync) {
      setSyncing(true);
      try {
        await apiClient.post(`/social-comments/posts/${postId}/sync`, null, {
          params: socialAccountId ? { social_account_id: socialAccountId } : {}
        });
      } catch (syncErr) {
        console.warn('Sync attempt completed or skipped:', syncErr);
      } finally {
        setSyncing(false);
      }
    }

    setLoading(true);
    setError(null);
    try {
      const queryParams: any = { 
        skip: 0, 
        limit: 50, 
        reply_status: replyStatusFilter, 
        sort_order: sortOrder 
      };
      if (socialAccountId) queryParams.social_account_id = socialAccountId;

      const res = await apiClient.get(`/social-comments/posts/${postId}`, {
        params: queryParams
      });

      setPost(res.data.post);
      setComments(res.data.comments || []);
      setTopLevelCount(res.data.top_level_comment_count ?? res.data.total_comments ?? 0);
      setFilteredTopLevelCount(res.data.filtered_top_level_count ?? res.data.top_level_comment_count ?? 0);
      setReplyCount(res.data.reply_count ?? 0);
      setTotalInteractions(res.data.total_interaction_count ?? (res.data.top_level_comment_count + res.data.reply_count));
    } catch (e: any) {
      console.error('Failed to fetch post comments:', e);
      setError(e?.response?.data?.detail || 'Failed to load comments for this organic post.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = async () => {
    if (loadingMore || !postId) return;
    setLoadingMore(true);
    try {
      const queryParams: any = {
        skip: comments.length,
        limit: 50,
        reply_status: replyStatusFilter,
        sort_order: sortOrder
      };
      if (socialAccountId) queryParams.social_account_id = socialAccountId;

      const res = await apiClient.get(`/social-comments/posts/${postId}`, {
        params: queryParams
      });

      const newItems: SocialComment[] = res.data.comments || [];
      setComments((prev) => {
        const existingIds = new Set(prev.map((c) => c.id));
        const uniqueNew = newItems.filter((c) => !existingIds.has(c.id));
        return [...prev, ...uniqueNew];
      });
    } catch (e: any) {
      console.error('Failed to load more comments:', e);
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchPostComments(false);
  }, [postId, replyStatusFilter, sortOrder, socialAccountId]);

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
    setFilteredTopLevelCount((prev) => Math.max(0, prev - 1));
    setTotalInteractions((prev) => Math.max(0, prev - 1));
    setNotice('Comment deleted successfully.');
    setTimeout(() => setNotice(null), 3000);
  };

  const effectiveTotalCount = replyStatusFilter === 'all' ? topLevelCount : filteredTopLevelCount;
  const hasMoreComments = comments.length < effectiveTotalCount;
  const isIg = post?.platform?.toLowerCase().includes('instagram');

  // Resolve real connected account identity from post metadata or comments account context
  const accountFromComment = comments.find((c) => c.account && (c.account.account_name || c.account.username || c.account.display_name))?.account;
  const resolvedAccountName = post?.account_name || accountFromComment?.account_name || accountFromComment?.username || accountFromComment?.display_name;
  const resolvedAccountAvatar = post?.account_avatar || accountFromComment?.logo_url;

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Top Header & Breadcrumb Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link
            href={`/comments?tab=posts${socialAccountId ? `&social_account_id=${socialAccountId}` : ''}`}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Back to Organic Posts"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-400" />
              <span>Organic Post Conversations</span>
            </h1>
            <p className="text-xs text-slate-400">
              Inspect live platform preview and native conversation threads for this post.
            </p>
          </div>
        </div>

        <button
          onClick={() => fetchPostComments(true)}
          disabled={loading || syncing}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-semibold transition flex items-center space-x-1.5 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${syncing || loading ? 'animate-spin' : ''}`} />
          <span>{syncing ? 'Syncing...' : 'Sync & Refresh'}</span>
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
        <div className="py-20 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-3">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading published post preview & conversation threads...</p>
        </div>
      ) : !post ? (
        <ContextualEmptyState type="posts" title="Post Not Found" description="The requested organic post could not be loaded." />
      ) : (
        <div className="lg:grid lg:grid-cols-12 lg:gap-8 items-start">
          {/* Left Column: Social Post Preview (Sticky on Desktop) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="lg:sticky lg:top-6 space-y-4">
              {/* Platform & Source Card Header */}
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center space-x-2 min-w-0">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex-shrink-0">
                    Published Post
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase flex-shrink-0 ${
                      isIg
                        ? 'bg-pink-950/90 text-pink-300 border border-pink-800/80'
                        : 'bg-blue-950/90 text-blue-300 border border-blue-800/80'
                    }`}
                  >
                    {post.platform || 'Facebook'}
                  </span>
                </div>
                {post.permalink && (
                  <a
                    href={post.permalink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center space-x-1 flex-shrink-0"
                  >
                    <span>Open on {isIg ? 'Instagram' : 'Facebook'}</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>

              {/* Native Social Post Preview Component */}
              <SocialPostPreview
                platform={post.platform || 'facebook'}
                accountName={resolvedAccountName}
                accountAvatar={resolvedAccountAvatar}
                caption={post.caption || post.title}
                imageUrl={post.image_url}
                mediaType={post.media_type}
                publishedAt={post.published_at}
                permalink={post.permalink}
                externalPostId={post.external_post_id}
                commentCount={topLevelCount}
                isPublished={true}
              />

              {/* Post Metadata Summary */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 space-y-2 shadow-sm">
                {resolvedAccountName && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Account:</span>
                    <span className="font-semibold text-slate-200 text-[11px] truncate max-w-[200px]">
                      {resolvedAccountName}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Post ID:</span>
                  <span className="font-mono text-slate-300 text-[11px] truncate max-w-[200px]">
                    {post.external_post_id}
                  </span>
                </div>
                {post.published_at && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Published:</span>
                    <span className="text-slate-300">{new Date(post.published_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Comments & Conversations Feed */}
          <div className="lg:col-span-7 space-y-5 mt-6 lg:mt-0">
            {/* Scoped Metrics Bar */}
            <EngagementMetricsBar
              topLevelCount={topLevelCount}
              replyCount={replyCount}
              totalInteractions={totalInteractions}
            />

            {/* Filter & Sort Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800/90 shadow-sm">
              <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                <span className="text-xs font-bold text-slate-400 uppercase mr-1">Filter:</span>
                <button
                  onClick={() => setReplyStatusFilter('all')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                    replyStatusFilter === 'all'
                      ? 'bg-blue-950 text-blue-200 border border-blue-800 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  All Threads ({topLevelCount})
                </button>
                <button
                  onClick={() => setReplyStatusFilter('unreplied')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                    replyStatusFilter === 'unreplied'
                      ? 'bg-amber-950 text-amber-200 border border-amber-800 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  Unreplied
                </button>
                <button
                  onClick={() => setReplyStatusFilter('replied')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                    replyStatusFilter === 'replied'
                      ? 'bg-emerald-950 text-emerald-200 border border-emerald-800 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  Replied
                </button>
              </div>

              <div className="flex items-center space-x-2 border-t sm:border-t-0 sm:border-l border-slate-800/80 pt-2 sm:pt-0 sm:pl-3">
                <span className="text-xs font-bold text-slate-400 uppercase mr-1">Sort:</span>
                <button
                  onClick={() => setSortOrder('desc')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                    sortOrder === 'desc'
                      ? 'bg-blue-950 text-blue-200 border border-blue-800 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  Newest First
                </button>
                <button
                  onClick={() => setSortOrder('asc')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                    sortOrder === 'asc'
                      ? 'bg-blue-950 text-blue-200 border border-blue-800 shadow-sm'
                      : 'bg-slate-950/80 text-slate-400 border border-slate-800 hover:text-slate-200'
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
                    ? 'No unreplied threads exist for this post.'
                    : 'No comments recorded for this post yet.'
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
                    showPostContext={false}
                  />
                ))}

                {/* Load More Pagination Button */}
                {hasMoreComments && (
                  <div className="pt-2 text-center">
                    <button
                      onClick={handleLoadMore}
                      disabled={loadingMore}
                      className="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-blue-300 hover:text-blue-200 text-xs font-bold transition flex items-center justify-center space-x-2 mx-auto disabled:opacity-50 shadow-md"
                    >
                      {loadingMore ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Loading more conversations...</span>
                        </>
                      ) : (
                        <span>Load More Comments ({comments.length} of {effectiveTotalCount})</span>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

