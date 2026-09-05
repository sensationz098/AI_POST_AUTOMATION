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
  FileText
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialComment, SocialCommentReply } from '@/lib/types';

import ConversationThread from '../../components/ConversationThread';
import PostCardComponent from '../../components/PostCardComponent';
import ContextualEmptyState from '../../components/ContextualEmptyState';
import EngagementMetricsBar from '../../components/EngagementMetricsBar';

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
  const [replyCount, setReplyCount] = useState(0);
  const [totalInteractions, setTotalInteractions] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replyStatusFilter, setReplyStatusFilter] = useState<'all' | 'unreplied' | 'replied'>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [notice, setNotice] = useState<string | null>(null);

  const fetchPostComments = async () => {
    if (!postId) return;
    setLoading(true);
    setError(null);
    try {
      const queryParams: any = { reply_status: replyStatusFilter, sort_order: sortOrder };
      if (socialAccountId) queryParams.social_account_id = socialAccountId;

      const res = await apiClient.get(`/social-comments/posts/${postId}`, {
        params: queryParams
      });

      setPost(res.data.post);
      setComments(res.data.comments || []);
      setTopLevelCount(res.data.top_level_comment_count ?? res.data.total_comments ?? 0);
      setReplyCount(res.data.reply_count ?? 0);
      setTotalInteractions(res.data.total_interaction_count ?? (res.data.top_level_comment_count + res.data.reply_count));
    } catch (e: any) {
      console.error('Failed to fetch post comments:', e);
      setError(e?.response?.data?.detail || 'Failed to load comments for this organic post.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPostComments();
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
              Inspect conversation threads and brand responses for this specific post.
            </p>
          </div>
        </div>

        <button
          onClick={fetchPostComments}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-semibold transition flex items-center space-x-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
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
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading post content & conversation threads...</p>
        </div>
      ) : !post ? (
        <ContextualEmptyState type="posts" title="Post Not Found" description="The requested organic post could not be loaded." />
      ) : (
        <div className="space-y-6">
          {/* Post Card Banner */}
          <PostCardComponent
            post={{
              ...post,
              platform: post.platform || 'facebook',
              comment_count: topLevelCount,
            }}
            selectedAccountId={socialAccountId || 'ALL'}
          />

          {/* Scoped Metrics Bar */}
          <EngagementMetricsBar
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
                    ? 'bg-blue-950 text-blue-200 border border-blue-800'
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
                    ? 'bg-blue-950 text-blue-200 border border-blue-800 shadow-sm'
                    : 'bg-slate-950 text-slate-400 border border-slate-800'
                }`}
              >
                Newest First
              </button>
              <button
                onClick={() => setSortOrder('asc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  sortOrder === 'asc'
                    ? 'bg-blue-950 text-blue-200 border border-blue-800 shadow-sm'
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
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
