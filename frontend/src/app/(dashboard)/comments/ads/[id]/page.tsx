'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Target, 
  MessageSquare, 
  RefreshCw, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  User, 
  Clock, 
  CornerDownRight, 
  Send, 
  Trash2, 
  ExternalLink,
  Facebook,
  Instagram,
  FileText
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialComment, SocialCommentReply, MetaAdCommentsResponse } from '@/lib/types';

interface AdDetails {
  id: number;
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
  const adId = params?.id as string;

  const [ad, setAd] = useState<AdDetails | null>(null);
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [totalComments, setTotalComments] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  // Reply state
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState('');
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);
  const [replySuccess, setReplySuccess] = useState<string | null>(null);

  // Deletion state
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchAdComments = async (pageNum = 1, append = false) => {
    if (!adId) return;
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError(null);
    try {
      const requestUrl = `/social-comments/ads/${adId}`;
      const res = await apiClient.get<MetaAdCommentsResponse>(requestUrl, {
        params: { page: pageNum, limit: 50 }
      });

      const payload = res?.data;
      const adObj = payload?.ad || null;
      const commentsList = Array.isArray(payload?.comments) ? payload.comments : [];
      const totalCnt = typeof payload?.total_comments === 'number' ? payload.total_comments : commentsList.length;
      const hasNextPage = Boolean(payload?.has_next);
      const currentPage = typeof payload?.page === 'number' ? payload.page : pageNum;

      console.log('[AD_COMMENTS_FRONTEND_RESPONSE]', {
        routeAdId: adId,
        requestUrl,
        httpStatus: res.status,
        responseObjectKeys: Object.keys(res || {}),
        responseDataKeys: Object.keys(payload || {}),
        commentsArrayDetected: Array.isArray(payload?.comments),
        commentsLength: commentsList.length,
        totalComments: totalCnt,
        page: currentPage,
        hasNext: hasNextPage
      });

      setAd(adObj);
      setTotalComments(totalCnt);
      setHasNext(hasNextPage);
      setPage(currentPage);

      if (append) {
        setComments((prev) => [...prev, ...commentsList]);
      } else {
        setComments(commentsList);
      }
    } catch (e: any) {
      const requestUrl = `/social-comments/ads/${adId}`;
      const httpStatus = e?.response?.status;
      const backendDetail = e?.response?.data?.detail;
      const errorMsg = backendDetail || e?.message || 'Unable to display comments for this Meta Ad.';

      console.error('[AD_COMMENTS_FRONTEND_ERROR]', {
        routeAdId: adId,
        requestUrl,
        errorName: e?.name || 'Error',
        errorMessage: e?.message || String(e),
        httpStatus: httpStatus || 'N/A',
        backendDetail: backendDetail || 'N/A'
      });

      setError(errorMsg);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchAdComments(1, false);
  }, [adId]);

  const handleLoadMore = () => {
    if (hasNext && !loadingMore) {
      fetchAdComments(page + 1, true);
    }
  };

  const handleSendReply = async (commentId: number) => {
    if (!replyText.trim()) return;
    setIsSubmittingReply(true);
    setReplyError(null);
    setReplySuccess(null);
    try {
      const res = await apiClient.post(`/social-comments/${commentId}/reply`, {
        message: replyText.trim(),
      });

      setComments((prevComments) =>
        prevComments.map((c) => {
          if (c.id === commentId) {
            const updatedReplies = [...(c.replies || []), res.data.reply];
            return { ...c, replies: updatedReplies };
          }
          return c;
        })
      );

      setReplySuccess('Reply posted successfully!');
      setReplyText('');
      setReplyingToId(null);
      setTimeout(() => setReplySuccess(null), 4000);
    } catch (e: any) {
      console.error('Failed to post reply:', e);
      setReplyError(e?.response?.data?.detail || 'Failed to post reply to Meta.');
    } finally {
      setIsSubmittingReply(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!confirm('Are you sure you want to delete this comment? This will delete it on Facebook.')) return;
    setDeletingId(commentId);
    setDeleteError(null);
    try {
      await apiClient.delete(`/social-comments/${commentId}`);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      setTotalComments((prev) => Math.max(0, prev - 1));
    } catch (e: any) {
      console.error('Failed to delete comment:', e);
      setDeleteError(e?.response?.data?.detail || 'Failed to delete comment.');
    } finally {
      setDeletingId(null);
    }
  };

  const isInstagram = ad?.platform?.toLowerCase() === 'instagram';
  const hasValidPermalink = ad?.permalink && (ad.permalink.startsWith('http://') || ad.permalink.startsWith('https://'));

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Top Header & Breadcrumbs */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link
            href="/comments?tab=ads"
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Back to Ads Index"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded bg-purple-950/90 text-purple-300 border border-purple-800/80 font-bold text-[10px] uppercase flex items-center space-x-1">
                <Target className="w-3 h-3 text-purple-400" />
                <span>Meta Ad Drill-down</span>
              </span>
              {ad?.effective_status && (
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                    ad.effective_status === 'ACTIVE'
                      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80'
                      : 'bg-amber-950/80 text-amber-300 border-amber-800/80'
                  }`}
                >
                  ● {ad.effective_status}
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-100 mt-1 truncate">
              {ad ? ad.name : `Ad #${adId}`}
            </h1>
          </div>
        </div>

        <button
          onClick={() => fetchAdComments(1, false)}
          disabled={loading}
          className="px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white font-medium text-xs transition flex items-center space-x-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Comments</span>
        </button>
      </div>

      {/* Ad Context Banner */}
      {ad && (
        <div className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-xs text-slate-400">
              <span className="font-semibold text-slate-300">Campaign:</span>
              <span className="text-slate-200">{ad.campaign_name || 'N/A'}</span>
              <span className="text-slate-600">•</span>
              <span className="font-semibold text-slate-300">Ad Set:</span>
              <span className="text-slate-200">{ad.adset_name || 'N/A'}</span>
            </div>
            <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-400">
              <span>Meta Ad ID: {ad.meta_ad_id}</span>
              {ad.facebook_post_id && (
                <span>Backing Post ID: {ad.facebook_post_id}</span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {hasValidPermalink && (
              <a
                href={ad.permalink!}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg bg-blue-950/70 hover:bg-blue-900/80 border border-blue-700/70 text-blue-200 text-xs font-semibold transition flex items-center space-x-1.5 shadow-sm"
              >
                {isInstagram ? <Instagram className="w-3.5 h-3.5 text-pink-400" /> : <Facebook className="w-3.5 h-3.5 text-blue-400" />}
                <span>View on {isInstagram ? 'Instagram' : 'Facebook'}</span>
                <ExternalLink className="w-3 h-3 ml-0.5 text-blue-300" />
              </a>
            )}
            <div className="px-3 py-1.5 rounded-lg bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 text-xs font-semibold flex items-center space-x-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
              <span>{totalComments} Comments</span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-sm flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Notifications */}
      {replySuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/50 border border-emerald-800/80 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{replySuccess}</span>
        </div>
      )}

      {deleteError && (
        <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{deleteError}</span>
        </div>
      )}

      {/* Comments List */}
      {loading ? (
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm text-slate-400">Loading comments for this Meta Ad...</p>
        </div>
      ) : error ? null : comments.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-400">
            <MessageSquare className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-200">No Comments Found</h3>
          <p className="text-xs text-slate-400 max-w-md">
            There are no synced comments for this specific ad yet. You can click &quot;Sync Active Comments&quot; in Meta Accounts to fetch fresh engagement.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => {
            const commenterName = comment.commenter_name || comment.commenter_id || 'Anonymous User';
            const initial = commenterName.charAt(0).toUpperCase();

            return (
              <div
                key={comment.id}
                className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-4 transition-colors hover:border-slate-700/80 space-y-3 shadow-sm"
              >
                {/* Header: Commenter Identity & Timestamp */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center space-x-3 min-w-0">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-sm">
                      {initial}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span className="font-bold text-sm text-slate-100 truncate">
                          {commenterName}
                        </span>
                        {comment.commenter_name ? (
                          <span className="px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 text-[9px] font-semibold">
                            Verified User
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700/60 text-[9px] font-semibold">
                            Privacy Protected
                          </span>
                        )}
                        {comment.parent_comment_id && (
                          <span className="px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800/60 text-[9px] font-semibold flex items-center space-x-1">
                            <CornerDownRight className="w-2.5 h-2.5 inline" />
                            <span>Reply</span>
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>
                          {comment.created_at ? new Date(comment.created_at).toLocaleString() : 'Recent'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteComment(comment.id)}
                    disabled={deletingId === comment.id}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 border border-transparent hover:border-rose-800/50 transition"
                    title="Delete Comment on Facebook"
                  >
                    {deletingId === comment.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {/* Comment Message Body */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800/60 text-sm text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
                  {comment.comment_text}
                </div>

                {/* Existing Reply History */}
                {comment.replies && comment.replies.length > 0 && (
                  <div className="pl-4 border-l-2 border-indigo-500/40 space-y-2 mt-2">
                    <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider">
                      Replies ({comment.replies.length})
                    </span>
                    {comment.replies.map((reply: SocialCommentReply) => (
                      <div key={reply.id} className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/50 text-xs text-slate-300 flex items-start space-x-2">
                        <CornerDownRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="text-slate-200">{reply.message}</p>
                          <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1">
                            <span>{reply.created_at ? new Date(reply.created_at).toLocaleString() : 'Sent'}</span>
                            <span className="text-emerald-400 font-semibold">● Sent to Meta</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Reply Composer Controls */}
                {replyingToId === comment.id ? (
                  <div className="space-y-2 pt-2 border-t border-slate-800/60">
                    {replyError && (
                      <div className="text-xs text-rose-400 flex items-center space-x-1">
                        <AlertCircle className="w-3 h-3" />
                        <span>{replyError}</span>
                      </div>
                    )}
                    <textarea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder="Write an official response to this ad comment..."
                      rows={2}
                      className="w-full bg-slate-950 border border-indigo-800/80 focus:border-indigo-500 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 outline-none transition"
                    />
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => {
                          setReplyingToId(null);
                          setReplyText('');
                          setReplyError(null);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSendReply(comment.id)}
                        disabled={isSubmittingReply || !replyText.trim()}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center space-x-1.5 disabled:opacity-50"
                      >
                        {isSubmittingReply ? (
                          <Loader2 className="w-3 h-3 animate-spin text-white" />
                        ) : (
                          <Send className="w-3 h-3" />
                        )}
                        <span>{isSubmittingReply ? 'Sending...' : 'Post Reply'}</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-end pt-1">
                    <button
                      onClick={() => {
                        setReplyingToId(comment.id);
                        setReplyText('');
                        setReplyError(null);
                      }}
                      className="px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-indigo-300 hover:text-white border border-slate-700/60 text-xs font-medium transition flex items-center space-x-1.5"
                    >
                      <CornerDownRight className="w-3 h-3 text-indigo-400" />
                      <span>Reply</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {/* Load More Pagination */}
          {hasNext && (
            <div className="pt-4 text-center">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-indigo-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center space-x-2 mx-auto disabled:opacity-50"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                    <span>Loading More Comments...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 text-indigo-400" />
                    <span>Load More Comments ({comments.length} of {totalComments})</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
