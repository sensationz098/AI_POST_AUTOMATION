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
  ShieldCheck,
  CheckCircle2,
  CornerDownRight,
  Send,
  X,
  ExternalLink,
  Image as ImageIcon,
  Video,
  FileText,
  Trash2,
  Filter,
  Share2
} from 'lucide-react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { SocialComment, SocialCommentPostContext, SocialCommentAccountContext, SocialCommentReply, SocialAccount } from '@/lib/types';

// 1. Post Context Preview Component
function PostContextCard({
  post,
  account,
  externalPostId,
  platform,
}: {
  post?: SocialCommentPostContext | null;
  account?: SocialCommentAccountContext | null;
  externalPostId?: string;
  platform: 'facebook' | 'instagram';
}) {
  const isFb = platform === 'facebook';
  const accountDisplayName = account?.account_name || account?.display_name || (isFb ? 'Facebook Page' : 'Instagram Account');

  return (
    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/90 flex flex-col space-y-2 mb-3.5 shadow-sm">
      {/* Receiving Social Account Header Badge */}
      <div className="flex items-center justify-between text-[11px] pb-2 border-b border-slate-900/80">
        <div className="flex items-center space-x-2 min-w-0">
          {isFb ? (
            <span className="px-2 py-0.5 rounded bg-blue-950/90 text-blue-300 border border-blue-800/70 font-bold text-[10px] flex items-center space-x-1 flex-shrink-0">
              <Facebook className="w-3 h-3 fill-current" />
              <span>Facebook Page</span>
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-pink-950/90 text-pink-300 border border-pink-800/70 font-bold text-[10px] flex items-center space-x-1 flex-shrink-0">
              <Instagram className="w-3 h-3" />
              <span>Instagram</span>
            </span>
          )}
          <span className="font-semibold text-slate-200 truncate">
            {isFb ? accountDisplayName : `@${accountDisplayName.replace(/^@/, '')}`}
          </span>
        </div>

        {post?.permalink ? (
          <a
            href={post.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/70 text-indigo-300 hover:text-white text-[10px] font-semibold transition flex items-center space-x-1 flex-shrink-0"
          >
            <span>View Post</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        ) : post?.source === 'local' ? (
          <Link
            href="/posts"
            className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/70 text-indigo-300 hover:text-white text-[10px] font-semibold transition flex items-center space-x-1 flex-shrink-0"
          >
            <span>View Post</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        ) : null}
      </div>

      {/* Post Context Body */}
      {post ? (
        <div className="flex items-start space-x-3 min-w-0 pt-0.5">
          {post.thumbnail_url || post.image_url ? (
            <img
              src={post.thumbnail_url || post.image_url}
              alt={post.title || 'Social post'}
              className="w-11 h-11 rounded-lg object-cover border border-slate-800 flex-shrink-0 bg-slate-900"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          ) : post.media_type === 'video' ? (
            <div className="w-11 h-11 rounded-lg bg-indigo-950/40 border border-indigo-800/50 flex items-center justify-center text-indigo-400 flex-shrink-0">
              <Video className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-11 h-11 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 flex-shrink-0">
              <ImageIcon className="w-5 h-5" />
            </div>
          )}

          <div className="min-w-0 space-y-0.5">
            <span className="font-bold text-slate-100 text-xs line-clamp-1">
              {post.title || 'Social Post'}
            </span>
            {post.caption && (
              <p className="text-[11px] text-slate-300 line-clamp-2 leading-snug font-sans">
                {post.caption}
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center space-x-2.5 min-w-0 py-1">
          <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 flex-shrink-0">
            <FileText className="w-4 h-4 text-slate-400" />
          </div>
          <div className="min-w-0">
            <span className="font-semibold text-slate-300 text-xs">Post details could not be loaded</span>
            {externalPostId && (
              <p className="text-[10px] font-mono text-slate-500 truncate mt-0.5">
                External Post ID: {externalPostId}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// 2. Original Customer Comment Component
function OriginalComment({
  comment,
  formatDate,
}: {
  comment: SocialComment;
  formatDate: (iso?: string) => string;
}) {
  return (
    <div className="space-y-2">
      {/* Comment Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold text-xs flex-shrink-0">
            {comment.commenter_name ? comment.commenter_name.charAt(0).toUpperCase() : <User className="w-3.5 h-3.5" />}
          </div>
          <div>
            <span className="text-slate-100 font-bold text-xs">
              {comment.commenter_name || comment.commenter_id || 'Anonymous User'}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 text-[10px]">
          <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 font-mono font-bold flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>{comment.processing_status || 'RECEIVED'}</span>
          </span>

          <span className="text-slate-400 flex items-center space-x-1 font-mono">
            <Clock className="w-3 h-3 text-slate-500" />
            <span>{formatDate(comment.event_timestamp || comment.created_at)}</span>
          </span>
        </div>
      </div>

      {/* Comment Text */}
      <div className="text-slate-200 text-xs leading-relaxed bg-slate-900/90 p-3 rounded-xl border border-slate-800/80 font-sans shadow-inner">
        {comment.comment_text ? (
          <p className="whitespace-pre-wrap">"{comment.comment_text}"</p>
        ) : (
          <p className="text-slate-500 italic text-[11px]">
            (Comment payload received without text content)
          </p>
        )}
      </div>
    </div>
  );
}

// 3. Nested Owner Reply Thread Component
function ReplyThread({
  replies,
  formatDate,
}: {
  replies?: SocialCommentReply[];
  formatDate: (iso?: string) => string;
}) {
  if (!replies || replies.length === 0) return null;

  return (
    <div className="pl-3 sm:pl-5 border-l-2 border-indigo-500/30 space-y-2 my-2.5">
      <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 flex items-center space-x-1 mb-1.5">
        <CornerDownRight className="w-3 h-3 text-indigo-400" />
        <span>Owner Reply Thread ({replies.length})</span>
      </div>

      {replies.map((reply) => {
        const isFailed = reply.status === 'FAILED';

        return (
          <div
            key={reply.id}
            className={`p-2.5 rounded-xl border text-xs space-y-1 shadow-sm transition ${
              isFailed
                ? 'bg-rose-950/30 border-rose-800/60 text-rose-200'
                : 'bg-slate-950/90 border-slate-800/90 text-slate-200'
            }`}
          >
            <div className="flex items-center justify-between text-[10px] text-slate-400">
              <div className="flex items-center space-x-1.5">
                <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold text-[9px] flex items-center space-x-1">
                  {isFailed ? (
                    <AlertCircle className="w-2.5 h-2.5 text-rose-400" />
                  ) : (
                    <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                  )}
                  <span>You (Owner)</span>
                </span>

                {isFailed ? (
                  <span className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 font-mono text-[9px] font-bold">
                    FAILED
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono text-[9px] font-bold">
                    SUCCESS
                  </span>
                )}
              </div>

              <span className="font-mono text-slate-400">{formatDate(reply.created_at)}</span>
            </div>

            <p className="text-slate-100 font-sans pl-1 whitespace-pre-wrap">{reply.message}</p>

            {isFailed && reply.error_message && (
              <p className="text-[10px] text-rose-400 font-mono italic pt-0.5 pl-1">
                Error details: {reply.error_message}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// 4. Reply Composer Form Component
function ReplyComposer({
  comment,
  isReplying,
  replyText,
  isSubmitting,
  feedback,
  onOpen,
  onClose,
  onTextChange,
  onSubmit,
  onDelete,
}: {
  comment: SocialComment;
  isReplying: boolean;
  replyText: string;
  isSubmitting: boolean;
  feedback: { type: 'success' | 'error'; message: string } | null;
  onOpen: () => void;
  onClose: () => void;
  onTextChange: (text: string) => void;
  onSubmit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="pt-1">
      {!isReplying ? (
        <div className="flex items-center justify-between">
          <button
            onClick={onOpen}
            className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 hover:text-white border border-indigo-500/30 font-semibold text-xs transition flex items-center space-x-1.5 shadow-sm"
          >
            <CornerDownRight className="w-3.5 h-3.5 text-indigo-400" />
            <span>Reply</span>
          </button>

          <button
            onClick={onDelete}
            className="px-3 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 hover:text-white border border-rose-800/50 font-semibold text-xs transition flex items-center space-x-1.5 shadow-sm"
            title="Delete comment permanently from social media platform"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-400" />
            <span>Delete</span>
          </button>
        </div>
      ) : (
        <div className="bg-slate-950/90 p-3.5 rounded-xl border border-indigo-500/40 space-y-3 shadow-xl animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="flex items-center justify-between text-xs font-bold text-slate-200 border-b border-slate-800 pb-2">
            <span className="flex items-center space-x-1.5 text-indigo-400">
              <CornerDownRight className="w-4 h-4 text-indigo-400" />
              <span>Reply to {comment.commenter_name || 'commenter'} as Page Owner</span>
            </span>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <textarea
            value={replyText}
            onChange={(e) => onTextChange(e.target.value)}
            disabled={isSubmitting}
            maxLength={2000}
            rows={3}
            placeholder={`Type your response to ${comment.commenter_name || 'this commenter'}...`}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none disabled:opacity-50"
          />

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

          <div className="flex items-center justify-between pt-1">
            <span className="text-[10px] font-mono text-slate-500">
              {replyText.length} / 2000 characters
            </span>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 text-xs font-semibold transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onSubmit}
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
}

// 5. Delete Confirmation Modal Component
function DeleteConfirmationModal({
  comment,
  isDeleting,
  error,
  onConfirm,
  onCancel,
}: {
  comment: SocialComment | null;
  isDeleting: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!comment) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 font-sans text-xs">
        <div className="flex items-start space-x-3">
          <div className="w-10 h-10 rounded-xl bg-rose-950/80 border border-rose-800/80 flex items-center justify-center text-rose-400 flex-shrink-0">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-100">Delete this comment?</h3>
            <p className="text-slate-300 leading-relaxed text-xs">
              This will permanently remove the comment from <strong className="text-slate-100 capitalize">{comment.platform}</strong>. This action cannot be undone.
            </p>
          </div>
        </div>

        {/* Comment Preview Box */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-bold text-slate-200">{comment.commenter_name || comment.commenter_id || 'Commenter'}</span>
            <span className="text-slate-400 font-mono capitalize">{comment.platform}</span>
          </div>
          <p className="text-slate-300 text-xs italic line-clamp-3">"{comment.comment_text || 'No comment text'}"</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center justify-end space-x-2.5 pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:bg-slate-800 text-white font-bold text-xs transition flex items-center space-x-2 shadow-lg disabled:text-slate-500 disabled:cursor-not-allowed"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                <span>Delete Comment</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// 6. Main Conversation Container Component
function CommentConversation({
  comment,
  formatDate,
  activeReplyCommentId,
  replyTextMap,
  isSubmittingMap,
  feedbackMap,
  handleOpenReplyForm,
  handleCloseReplyForm,
  handleReplyTextChange,
  handleSendReply,
  onRequestDelete,
}: {
  comment: SocialComment;
  formatDate: (iso?: string) => string;
  activeReplyCommentId: number | null;
  replyTextMap: Record<number, string>;
  isSubmittingMap: Record<number, boolean>;
  feedbackMap: Record<number, { type: 'success' | 'error'; message: string } | null>;
  handleOpenReplyForm: (id: number) => void;
  handleCloseReplyForm: (id: number) => void;
  handleReplyTextChange: (id: number, text: string) => void;
  handleSendReply: (comment: SocialComment) => void;
  onRequestDelete: (comment: SocialComment) => void;
}) {
  const isReplying = activeReplyCommentId === comment.id;
  const replyText = replyTextMap[comment.id] || '';
  const isSubmitting = isSubmittingMap[comment.id] || false;
  const feedback = feedbackMap[comment.id] || null;

  return (
    <div className="linear-panel p-4 sm:p-5 rounded-2xl border border-slate-800/80 hover:border-slate-700 transition space-y-3 bg-slate-900/40 shadow-lg">
      {/* POST CONTEXT HEADER */}
      <PostContextCard post={comment.post} account={comment.account} externalPostId={comment.external_post_id} platform={comment.platform} />

      {/* ORIGINAL CUSTOMER COMMENT */}
      <OriginalComment comment={comment} formatDate={formatDate} />

      {/* NESTED REPLIES THREAD */}
      <ReplyThread replies={comment.replies} formatDate={formatDate} />

      {/* REPLY COMPOSER & ACTIONS */}
      <ReplyComposer
        comment={comment}
        isReplying={isReplying}
        replyText={replyText}
        isSubmitting={isSubmitting}
        feedback={feedback}
        onOpen={() => handleOpenReplyForm(comment.id)}
        onClose={() => handleCloseReplyForm(comment.id)}
        onTextChange={(text) => handleReplyTextChange(comment.id, text)}
        onSubmit={() => handleSendReply(comment)}
        onDelete={() => onRequestDelete(comment)}
      />
    </div>
  );
}

export default function CommentsPage() {
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [platformFilter, setPlatformFilter] = useState<'all' | 'facebook' | 'instagram'>('all');

  // Reply Form States
  const [activeReplyCommentId, setActiveReplyCommentId] = useState<number | null>(null);
  const [replyTextMap, setReplyTextMap] = useState<Record<number, string>>({});
  const [isSubmittingMap, setIsSubmittingMap] = useState<Record<number, boolean>>({});
  const [feedbackMap, setFeedbackMap] = useState<Record<number, { type: 'success' | 'error'; message: string } | null>>({});

  // 1. Fetch multi-account destinations
  const fetchSocialAccounts = async () => {
    try {
      const res = await apiClient.get('/social-accounts/');
      if (Array.isArray(res.data)) {
        const fakeIds = new Set(['109823471029', '17841400928371', '17841400928372', '17841400928373', '109823471030', 'sandbox']);
        const realAccs = res.data.filter((a: SocialAccount) => !fakeIds.has(a.account_id));
        setSocialAccounts(realAccs);
      }
    } catch (e) {
      console.warn('Failed to load connected social accounts:', e);
    }
  };

  // 2. Fetch comments with optional account filtering
  const fetchComments = async (isManualRefresh = false, overrideAccountId?: string) => {
    const targetAccountId = overrideAccountId !== undefined ? overrideAccountId : selectedAccountId;
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const params: Record<string, any> = {};
      if (targetAccountId !== 'all') {
        params.social_account_id = Number(targetAccountId);
      }
      const res = await apiClient.get('/social-comments/', { params });
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
    fetchSocialAccounts();
    fetchComments();
  }, []);

  const handleAccountChange = (newAccountId: string) => {
    setSelectedAccountId(newAccountId);

    // Intelligently reset or adjust platform filter if selected account platform conflicts
    if (newAccountId !== 'all') {
      const acc = socialAccounts.find((a) => String(a.id) === newAccountId);
      if (acc && platformFilter !== 'all' && acc.platform !== platformFilter) {
        setPlatformFilter('all');
      }
    }

    fetchComments(false, newAccountId);
  };

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

        setTimeout(() => {
          setReplyTextMap((prev) => ({ ...prev, [comment.id]: '' }));
          setActiveReplyCommentId(null);
          fetchComments(true);
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

  // Delete Comment Modal States & Handlers
  const [deletingComment, setDeletingComment] = useState<SocialComment | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleRequestDelete = (comment: SocialComment) => {
    setDeletingComment(comment);
    setDeleteError(null);
  };

  const handleCancelDelete = () => {
    if (isDeleting) return;
    setDeletingComment(null);
    setDeleteError(null);
  };

  const handleConfirmDelete = async () => {
    if (!deletingComment) return;
    setIsDeleting(true);
    setDeleteError(null);

    try {
      const res = await apiClient.delete(`/social-comments/${deletingComment.id}`);
      if (res.data?.status === 'success') {
        // Immediately remove comment from local state and update counts
        setComments((prev) => prev.filter((c) => c.id !== deletingComment.id));
        setDeletingComment(null);
      } else {
        setDeleteError(res.data?.message || 'Unable to delete comment.');
      }
    } catch (e: any) {
      console.error('Failed to delete social comment:', e);
      const errDetail = e?.response?.data?.detail || 'Unable to delete this comment from the social media platform.';
      setDeleteError(errDetail);
    } finally {
      setIsDeleting(false);
    }
  };

  const selectedAccount = selectedAccountId === 'all'
    ? null
    : socialAccounts.find((a) => String(a.id) === selectedAccountId);

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
      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        comment={deletingComment}
        isDeleting={isDeleting}
        error={deleteError}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />

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
                View incoming Facebook & Instagram comments, see post context, and reply directly from your dashboard.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 flex-shrink-0 flex-wrap gap-y-2">
            {/* Account Switcher Dropdown (Reusing Dashboard Styling & Icon Conventions) */}
            <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-2 rounded-xl shadow-sm">
              <Filter className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <select
                value={selectedAccountId}
                onChange={(e) => handleAccountChange(e.target.value)}
                className="bg-transparent text-xs text-indigo-300 font-semibold focus:outline-none cursor-pointer pr-1"
                title="Select Connected Social Account"
              >
                <option value="all" className="bg-slate-900 text-slate-100 font-medium">
                  🌐 All Connected Accounts ({socialAccounts.length})
                </option>
                {socialAccounts.map((acc) => (
                  <option key={acc.id} value={String(acc.id)} className="bg-slate-900 text-slate-100 font-medium">
                    {acc.platform === 'facebook' ? `📘 Facebook: ${acc.account_name}` : `📸 Instagram: @${acc.account_name.replace(/^@/, '')}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              disabled={isLoading || isRefreshing}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-200 hover:text-white font-semibold text-xs transition flex items-center space-x-2 shadow-md disabled:opacity-50"
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

          {/* Show Facebook tab if all accounts or Facebook account is selected */}
          {(!selectedAccount || selectedAccount.platform === 'facebook') && (
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
          )}

          {/* Show Instagram tab if all accounts or Instagram account is selected */}
          {(!selectedAccount || selectedAccount.platform === 'instagram') && (
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
          )}
        </div>

        <div className="text-[11px] text-slate-400 font-mono">
          Showing {filteredComments.length} comment{filteredComments.length !== 1 ? 's' : ''}
          {selectedAccount ? ` for ${selectedAccount.account_name}` : ''}
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
      ) : socialAccounts.length === 0 ? (
        /* Empty State: No connected social accounts */
        <div className="linear-panel p-12 rounded-2xl text-center space-y-4 border border-slate-800 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400 mx-auto shadow-inner">
            <Share2 className="w-7 h-7 text-indigo-400/80" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="text-sm font-bold text-slate-200">No social accounts connected yet</h3>
            <p className="text-xs text-slate-400">
              Connect your Facebook Pages and Instagram Professional accounts to start viewing and replying to incoming comments.
            </p>
          </div>
          <Link
            href="/meta-connect"
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition inline-flex items-center space-x-2 shadow"
          >
            <span>Connect Social Accounts</span>
          </Link>
        </div>
      ) : filteredComments.length === 0 ? (
        /* Empty State: No comments for selected account / platform filter */
        <div className="linear-panel p-12 rounded-2xl text-center space-y-4 border border-slate-800 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400 mx-auto shadow-inner">
            <MessageSquare className="w-7 h-7 text-indigo-400/80" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="text-sm font-bold text-slate-200">
              {platformFilter !== 'all'
                ? `No ${platformFilter === 'facebook' ? 'Facebook' : 'Instagram'} comments for ${selectedAccount ? selectedAccount.account_name : 'this account'} yet`
                : selectedAccount
                ? `No comments for ${selectedAccount.account_name} yet`
                : 'No comments received yet'}
            </h3>
            <p className="text-xs text-slate-400">
              {selectedAccount
                ? `Comments received for ${selectedAccount.account_name} will appear here.`
                : 'Comments from your connected Facebook Pages and Instagram Professional accounts will appear here.'}
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
        /* Comments List rendered via CommentConversation */
        <div className="space-y-4">
          {filteredComments.map((comment) => (
            <CommentConversation
              key={comment.id}
              comment={comment}
              formatDate={formatDate}
              activeReplyCommentId={activeReplyCommentId}
              replyTextMap={replyTextMap}
              isSubmittingMap={isSubmittingMap}
              feedbackMap={feedbackMap}
              handleOpenReplyForm={handleOpenReplyForm}
              handleCloseReplyForm={handleCloseReplyForm}
              handleReplyTextChange={handleReplyTextChange}
              handleSendReply={handleSendReply}
              onRequestDelete={handleRequestDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
