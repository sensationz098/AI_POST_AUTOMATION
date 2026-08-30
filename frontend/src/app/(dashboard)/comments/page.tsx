'use client';

import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  Facebook, 
  Instagram, 
  RefreshCw, 
  AlertCircle, 
  Loader2, 
  Clock, 
  User, 
  Hash,
  ShieldCheck,
  CheckCircle2,
  CornerDownRight,
  Send,
  X
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialComment } from '@/lib/types';

export default function CommentsPage() {
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [platformFilter, setPlatformFilter] = useState<'all' | 'facebook' | 'instagram'>('all');

  // Reply Form States
  const [activeReplyCommentId, setActiveReplyCommentId] = useState<number | null>(null);
  const [replyTextMap, setReplyTextMap] = useState<Record<number, string>>({});
  const [isSubmittingMap, setIsSubmittingMap] = useState<Record<number, boolean>>({});
  const [feedbackMap, setFeedbackMap] = useState<Record<number, { type: 'success' | 'error'; message: string } | null>>({});

  const fetchComments = async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const res = await apiClient.get('/social-comments/');
      if (Array.isArray(res.data)) {
        setComments(res.data);
      } else {
        setComments([]);
      }
    } catch (e: any) {
      console.error('Failed to load social comments:', e);
      setError('Unable to load comments. Please try again.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchComments();
  }, []);

  const handleRefresh = () => {
    fetchComments(true);
  };

  const handleOpenReplyForm = (commentId: number) => {
    setActiveReplyCommentId(commentId);
    setFeedbackMap((prev) => ({ ...prev, [commentId]: null }));
  };

  const handleCloseReplyForm = (commentId: number) => {
    setActiveReplyCommentId(null);
    setReplyTextMap((prev) => ({ ...prev, [commentId]: '' }));
    setFeedbackMap((prev) => ({ ...prev, [commentId]: null }));
  };

  const handleReplyTextChange = (commentId: number, text: string) => {
    setReplyTextMap((prev) => ({ ...prev, [commentId]: text }));
    if (feedbackMap[commentId]) {
      setFeedbackMap((prev) => ({ ...prev, [commentId]: null }));
    }
  };

  const handleSendReply = async (comment: SocialComment) => {
    const message = (replyTextMap[comment.id] || '').trim();
    if (!message) return;

    setIsSubmittingMap((prev) => ({ ...prev, [comment.id]: true }));
    setFeedbackMap((prev) => ({ ...prev, [comment.id]: null }));

    try {
      const res = await apiClient.post(`/social-comments/${comment.id}/reply`, {
        message: message
      });

      if (res.data?.status === 'success') {
        setFeedbackMap((prev) => ({
          ...prev,
          [comment.id]: { type: 'success', message: res.data.message || 'Reply published successfully!' }
        }));

        // Clear typed message and close form after brief delay
        setTimeout(() => {
          setReplyTextMap((prev) => ({ ...prev, [comment.id]: '' }));
          setActiveReplyCommentId(null);
          fetchComments(true); // Refetch to show persistent reply history
        }, 1200);
      } else {
        setFeedbackMap((prev) => ({
          ...prev,
          [comment.id]: { type: 'error', message: res.data?.message || 'Unable to publish reply. Please try again.' }
        }));
      }
    } catch (e: any) {
      console.error('Failed to submit comment reply:', e);
      const errDetail = e?.response?.data?.detail || 'Unable to publish reply. Please try again.';
      setFeedbackMap((prev) => ({
        ...prev,
        [comment.id]: { type: 'error', message: errDetail }
      }));
    } finally {
      setIsSubmittingMap((prev) => ({ ...prev, [comment.id]: false }));
    }
  };

  const filteredComments = comments.filter((comment) => {
    if (platformFilter === 'all') return true;
    return comment.platform === platformFilter;
  });

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Just now';
    try {
      const date = new Date(isoString);
      return date.toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6 max-w-5xl select-none font-sans text-xs">
      {/* Page Header Banner */}
      <div className="linear-panel p-6 rounded-2xl space-y-4 border border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-11 h-11 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400 shadow-sm flex-shrink-0">
              <MessageSquare className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
                <span>Social Comments & Replies</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                  Manual Comment Replies Active
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                View incoming Facebook & Instagram comments and manually reply directly from your dashboard.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 flex-shrink-0">
            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              disabled={isLoading || isRefreshing}
              className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-200 hover:text-white font-semibold text-xs transition flex items-center space-x-2 shadow-md disabled:opacity-50"
              title="Refetch Comments"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>

        {/* Security & Verification Banner */}
        <div className="flex items-center space-x-2 text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
          <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>
            Strict User Isolation: Page access tokens are decrypted server-side only. AI automation is strictly disabled.
          </span>
        </div>
      </div>

      {/* Filter Tabs & Counter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setPlatformFilter('all')}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition ${
              platformFilter === 'all'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Platforms ({comments.length})
          </button>
          <button
            onClick={() => setPlatformFilter('facebook')}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition flex items-center space-x-1.5 ${
              platformFilter === 'facebook'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Facebook className="w-3 h-3 fill-current" />
            <span>Facebook ({comments.filter((c) => c.platform === 'facebook').length})</span>
          </button>
          <button
            onClick={() => setPlatformFilter('instagram')}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition flex items-center space-x-1.5 ${
              platformFilter === 'instagram'
                ? 'bg-pink-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Instagram className="w-3 h-3" />
            <span>Instagram ({comments.filter((c) => c.platform === 'instagram').length})</span>
          </button>
        </div>

        <div className="text-[11px] text-slate-400 font-mono">
          Showing {filteredComments.length} comment{filteredComments.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Main Content Area: Loading / Error / Empty / Data Cards */}
      {isLoading ? (
        <div className="linear-panel p-12 rounded-2xl text-center space-y-3 border border-slate-800 shadow-lg">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mx-auto" />
          <p className="text-xs text-slate-300 font-medium">Loading incoming social comments...</p>
        </div>
      ) : error ? (
        <div className="linear-panel p-8 rounded-2xl border border-rose-900/50 bg-rose-950/20 text-center space-y-4">
          <div className="w-10 h-10 rounded-full bg-rose-950/80 border border-rose-800 flex items-center justify-center text-rose-400 mx-auto">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-rose-200">{error}</h3>
            <p className="text-xs text-slate-400 mt-1">
              Please check your network connection or try refreshing.
            </p>
          </div>
          <button
            onClick={() => fetchComments()}
            className="px-4 py-2 rounded-lg bg-rose-900/80 hover:bg-rose-800 text-rose-100 font-bold text-xs transition inline-flex items-center space-x-2"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Loading</span>
          </button>
        </div>
      ) : filteredComments.length === 0 ? (
        /* Friendly Empty State */
        <div className="linear-panel p-12 rounded-2xl text-center space-y-4 border border-slate-800 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400 mx-auto shadow-inner">
            <MessageSquare className="w-7 h-7 text-indigo-400/80" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="text-sm font-bold text-slate-200">No comments received yet</h3>
            <p className="text-xs text-slate-400">
              Comments from your connected Facebook Pages and Instagram Professional accounts will appear here.
            </p>
          </div>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-semibold text-xs transition inline-flex items-center space-x-2"
          >
            <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
            <span>Check for New Comments</span>
          </button>
        </div>
      ) : (
        /* Comments List */
        <div className="space-y-4">
          {filteredComments.map((comment) => {
            const isReplying = activeReplyCommentId === comment.id;
            const replyText = replyTextMap[comment.id] || '';
            const isSubmitting = isSubmittingMap[comment.id] || false;
            const feedback = feedbackMap[comment.id];
            const hasReplies = comment.replies && comment.replies.length > 0;

            return (
              <div
                key={comment.id}
                className="linear-panel p-4 rounded-xl border border-slate-800/80 hover:border-slate-700 transition space-y-3.5 bg-slate-900/40 shadow-lg"
              >
                {/* Comment Header Row */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/60 pb-2.5">
                  <div className="flex items-center space-x-2">
                    {/* Platform Badge */}
                    {comment.platform === 'facebook' ? (
                      <span className="px-2.5 py-1 rounded-md bg-blue-950/80 text-blue-300 border border-blue-800/80 font-bold text-[10px] flex items-center space-x-1.5">
                        <Facebook className="w-3 h-3 fill-current text-blue-400" />
                        <span>Facebook</span>
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-md bg-pink-950/80 text-pink-300 border border-pink-800/80 font-bold text-[10px] flex items-center space-x-1.5">
                        <Instagram className="w-3 h-3 text-pink-400" />
                        <span>Instagram</span>
                      </span>
                    )}

                    {/* Commenter Info */}
                    <div className="flex items-center space-x-1.5 text-slate-200 font-semibold text-xs">
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      <span>{comment.commenter_name || comment.commenter_id || 'Anonymous User'}</span>
                    </div>
                  </div>

                  {/* Right Metadata: Processing Status & Timestamp */}
                  <div className="flex items-center space-x-3 text-[11px]">
                    {/* Processing Status Badge */}
                    <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 font-mono text-[9px] font-bold flex items-center space-x-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span>{comment.processing_status || 'RECEIVED'}</span>
                    </span>

                    {/* Timestamp */}
                    <span className="text-slate-400 flex items-center space-x-1 font-mono text-[10px]">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{formatDate(comment.event_timestamp || comment.created_at)}</span>
                    </span>
                  </div>
                </div>

                {/* Comment Body */}
                <div className="text-slate-100 text-xs font-normal leading-relaxed pl-1">
                  {comment.comment_text ? (
                    <p className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/70 font-sans text-slate-200">
                      "{comment.comment_text}"
                    </p>
                  ) : (
                    <p className="text-slate-500 italic text-[11px]">
                      (Comment payload received without text content)
                    </p>
                  )}
                </div>

                {/* Existing Reply History List */}
                {hasReplies && (
                  <div className="space-y-2 pt-1 pl-4 border-l-2 border-indigo-500/40">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 flex items-center space-x-1">
                      <CornerDownRight className="w-3 h-3 text-indigo-400" />
                      <span>Your Replies ({comment.replies!.length})</span>
                    </div>
                    {comment.replies!.map((reply) => (
                      <div
                        key={reply.id}
                        className="bg-slate-950/90 p-2.5 rounded-lg border border-indigo-900/30 text-xs space-y-1 shadow-inner"
                      >
                        <div className="flex items-center justify-between text-[10px] text-slate-400">
                          <span className="font-semibold text-indigo-300 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span>Page Owner</span>
                          </span>
                          <span className="font-mono text-slate-400">{formatDate(reply.created_at)}</span>
                        </div>
                        <p className="text-slate-200 font-sans">{reply.message}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* External IDs & Reply Action Button Footer */}
                <div className="flex flex-wrap items-center justify-between gap-3 text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/40">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="flex items-center space-x-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      <Hash className="w-3 h-3 text-slate-400" />
                      <span>Comment ID: {comment.external_comment_id}</span>
                    </span>

                    {comment.external_post_id && (
                      <span className="flex items-center space-x-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        <Hash className="w-3 h-3 text-indigo-400" />
                        <span>Post ID: {comment.external_post_id}</span>
                      </span>
                    )}
                  </div>

                  {/* Manual Reply Toggle Button */}
                  {!isReplying && (
                    <button
                      onClick={() => handleOpenReplyForm(comment.id)}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 hover:text-white border border-indigo-500/30 font-semibold text-xs transition flex items-center space-x-1.5 shadow-sm"
                    >
                      <CornerDownRight className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Reply</span>
                    </button>
                  )}
                </div>

                {/* Inline Reply Composer Form */}
                {isReplying && (
                  <div className="mt-3 bg-slate-950/90 p-3.5 rounded-xl border border-indigo-500/40 space-y-3 shadow-xl animate-in fade-in slide-in-from-top-1 duration-200">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-200 border-b border-slate-800 pb-2">
                      <span className="flex items-center space-x-1.5 text-indigo-400">
                        <CornerDownRight className="w-4 h-4 text-indigo-400" />
                        <span>Write Manual Reply</span>
                      </span>
                      <button
                        onClick={() => handleCloseReplyForm(comment.id)}
                        disabled={isSubmitting}
                        className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>

                    <textarea
                      value={replyText}
                      onChange={(e) => handleReplyTextChange(comment.id, e.target.value)}
                      disabled={isSubmitting}
                      maxLength={2000}
                      rows={3}
                      placeholder={`Type your manual reply to ${comment.commenter_name || 'this commenter'}...`}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none disabled:opacity-50"
                    />

                    {/* Feedback Alert Message */}
                    {feedback && (
                      <div
                        className={`p-2.5 rounded-lg border text-xs flex items-center space-x-2 ${
                          feedback.type === 'success'
                            ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
                            : 'bg-rose-950/40 border-rose-800 text-rose-300'
                        }`}
                      >
                        {feedback.type === 'success' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                        )}
                        <span>{feedback.message}</span>
                      </div>
                    )}

                    {/* Actions Row & Character Count */}
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] font-mono text-slate-500">
                        {replyText.length} / 2000 characters
                      </span>

                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={() => handleCloseReplyForm(comment.id)}
                          disabled={isSubmitting}
                          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 text-xs font-semibold transition disabled:opacity-50"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSendReply(comment)}
                          disabled={isSubmitting || !replyText.trim()}
                          className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white font-bold text-xs transition flex items-center space-x-1.5 shadow-md disabled:text-slate-500 disabled:cursor-not-allowed"
                        >
                          {isSubmitting ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                              <span>Sending Reply...</span>
                            </>
                          ) : (
                            <>
                              <Send className="w-3.5 h-3.5" />
                              <span>Send Reply</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
