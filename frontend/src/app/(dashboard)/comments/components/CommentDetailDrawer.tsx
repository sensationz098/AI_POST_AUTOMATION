'use client';

import React, { useState } from 'react';
import { 
  X, 
  MessageSquare, 
  Clock, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  Bot, 
  ChevronDown, 
  ChevronUp, 
  Copy, 
  Check, 
  Sparkles,
  Send,
  Loader2,
  PlusCircle,
  FileText
} from 'lucide-react';
import { SocialComment, SocialCommentReply } from '@/lib/types';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';

interface CommentDetailDrawerProps {
  isOpen: boolean;
  comment: SocialComment | null;
  onClose: () => void;
  onReplyAdded: (commentId: number, newReply: SocialCommentReply) => void;
  onCreateAutomationClick?: (comment: SocialComment) => void;
}

export default function CommentDetailDrawer({
  isOpen,
  comment,
  onClose,
  onReplyAdded,
  onCreateAutomationClick,
}: CommentDetailDrawerProps) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Reply Composer state
  const [replyMessage, setReplyMessage] = useState('');
  const [isSendingReply, setIsSendingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);

  if (!isOpen || !comment) return null;

  const commenterDisplayName = comment.commenter_name || comment.commenter_id || 'Anonymous';
  const commenterHandle = comment.commenter_name ? `@${comment.commenter_name.toLowerCase().replace(/\s+/g, '')}` : null;
  const initial = (commenterDisplayName.charAt(0) || 'U').toUpperCase();

  const isInstagram = (comment.platform || '').toLowerCase() === 'instagram';
  const isFacebook = (comment.platform || '').toLowerCase() === 'facebook';

  const formatAbsoluteTime = (dateStr?: string) => {
    if (!dateStr) return 'Unknown';
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return dateStr;
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyMessage.trim() || isSendingReply) return;

    setIsSendingReply(true);
    setReplyError(null);

    try {
      const res = await apiClient.post(`/social-comments/${comment.id}/reply`, {
        message: replyMessage.trim(),
        social_account_id: comment.social_account_id,
      });

      const newReply: SocialCommentReply = {
        id: res.data.id || Date.now(),
        message: replyMessage.trim(),
        status: 'SUCCESS',
        external_reply_id: res.data.external_reply_id,
        created_at: new Date().toISOString(),
        source: 'owner',
      };

      onReplyAdded(comment.id, newReply);
      setReplyMessage('');
      toast.success('Reply sent successfully!');
    } catch (err: any) {
      console.error('Error replying to comment:', err);
      const errMsg = err?.response?.data?.detail || 'Failed to send reply. Please try again.';
      setReplyError(errMsg);
      toast.error(errMsg);
    } finally {
      setIsSendingReply(false);
    }
  };

  // Build authentic activity timeline strictly grounded in real persisted data
  const timelineEvents: Array<{ title: string; time?: string; detail?: string; isDone: boolean }> = [];

  if (comment.event_timestamp) {
    timelineEvents.push({
      title: `Comment posted on ${comment.platform === 'instagram' ? 'Instagram' : 'Facebook'}`,
      time: formatAbsoluteTime(comment.event_timestamp),
      detail: `By ${commenterDisplayName}`,
      isDone: true,
    });
  }

  if (comment.created_at) {
    timelineEvents.push({
      title: 'Comment received & saved',
      time: formatAbsoluteTime(comment.created_at),
      detail: `Webhook payload processed`,
      isDone: true,
    });
  }

  if (comment.automation_execution) {
    const auto = comment.automation_execution;
    timelineEvents.push({
      title: `Automation '${auto.automation_name || 'Rule'}' evaluated`,
      time: auto.created_at ? formatAbsoluteTime(auto.created_at) : undefined,
      detail: auto.matched_keyword ? `Matched keyword: "${auto.matched_keyword}"` : `Status: ${auto.status}`,
      isDone: auto.status === 'COMPLETED' || auto.status === 'PENDING',
    });
  } else if (comment.lifecycle_status === 'NEEDS_REPLY') {
    timelineEvents.push({
      title: 'Automation rules checked',
      detail: 'No automation matched this comment',
      isDone: false,
    });
  }

  const existingReplies = comment.replies || [];
  existingReplies.forEach((r, idx) => {
    timelineEvents.push({
      title: r.source === 'owner' ? 'Manual reply sent' : 'Reply posted',
      time: r.created_at ? formatAbsoluteTime(r.created_at) : undefined,
      detail: `"${r.message}"`,
      isDone: r.status === 'SUCCESS',
    });
  });

  const postCtx = comment.post;
  const adCtx = comment.meta_ad;
  const postPermalink = postCtx?.permalink || adCtx?.permalink;
  const postTitle = postCtx?.title || adCtx?.name || (postCtx?.caption ? postCtx.caption.slice(0, 60) : 'Social Post');
  const postThumbnail = postCtx?.thumbnail_url || postCtx?.image_url;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div 
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/40 dark:bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in"
      />

      {/* Slide-over Drawer Panel */}
      <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col h-full z-10 animate-in slide-in-from-right duration-200 text-slate-800 dark:text-slate-100">
        {/* Top Header */}
        <div className="p-4 sm:px-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Comment Details
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {isInstagram ? 'Instagram' : 'Facebook'} conversation thread
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {/* Commenter Profile & Main Comment */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="w-11 h-11 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center font-bold text-slate-700 dark:text-slate-200 text-base">
                  {initial}
                </div>
                <div>
                  <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                    {commenterDisplayName}
                  </h3>
                  <div className="flex items-center space-x-2 text-xs text-slate-500 dark:text-slate-400">
                    {commenterHandle && <span>{commenterHandle}</span>}
                    <span>•</span>
                    <span>{formatAbsoluteTime(comment.event_timestamp || comment.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Platform Badge */}
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                isInstagram 
                  ? 'bg-pink-50 text-pink-700 border border-pink-200 dark:bg-pink-950/60 dark:text-pink-300 dark:border-pink-800/80' 
                  : 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/80'
              }`}>
                {isInstagram ? 'Instagram' : 'Facebook'}
              </span>
            </div>

            {/* Comment Body */}
            <div className="text-sm text-slate-800 dark:text-slate-100 leading-relaxed pt-1">
              <p className="whitespace-pre-line font-normal">{comment.comment_text || '[No text]'}</p>
            </div>
          </div>

          {/* Post / Reel Context */}
          {(postTitle || postPermalink) && (
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Post Context
              </div>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center space-x-3 min-w-0">
                  {postThumbnail ? (
                    <img 
                      src={postThumbnail} 
                      alt="Thumbnail" 
                      className="w-10 h-10 rounded-lg object-cover border border-slate-200 dark:border-slate-700 flex-shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-400 flex-shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="font-semibold text-xs text-slate-800 dark:text-slate-200 truncate">
                      {postTitle}
                    </p>
                    {comment.account?.account_name && (
                      <p className="text-[11px] text-slate-400 truncate">
                        Account: {comment.account.account_name}
                      </p>
                    )}
                  </div>
                </div>

                {postPermalink && (
                  <a
                    href={postPermalink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium transition flex items-center space-x-1 flex-shrink-0"
                  >
                    <span>View Post</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          )}

          {/* System Status & Automation Explanation */}
          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 space-y-2.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              System Action
            </div>
            <div className="flex items-start space-x-2.5 text-xs text-slate-700 dark:text-slate-200">
              {comment.lifecycle_status === 'AUTOMATED' ? (
                <Bot className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0 mt-0.5" />
              ) : comment.lifecycle_status === 'REPLIED' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
              ) : comment.lifecycle_status === 'FAILED' ? (
                <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
              ) : (
                <Clock className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p className="font-semibold">{comment.status_reason || 'No automation matched this comment.'}</p>
                {comment.automation_execution?.matched_keyword && (
                  <p className="text-slate-500 dark:text-slate-400 mt-0.5">
                    Triggered by keyword match: <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">"{comment.automation_execution.matched_keyword}"</span>
                  </p>
                )}
              </div>
            </div>

            {/* If Needs Reply, offer Create Automation shortcut */}
            {comment.lifecycle_status === 'NEEDS_REPLY' && onCreateAutomationClick && (
              <div className="pt-2 border-t border-slate-200/80 dark:border-slate-700/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">Want to automate similar comments?</span>
                <button
                  type="button"
                  onClick={() => {
                    onCreateAutomationClick(comment);
                  }}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition flex items-center space-x-1"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Create Automation</span>
                </button>
              </div>
            )}
          </div>

          {/* Activity Timeline (Derived strictly from real persisted timestamps) */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Activity Timeline
            </h4>
            <div className="relative pl-5 space-y-4 border-l-2 border-slate-200 dark:border-slate-800">
              {timelineEvents.map((evt, idx) => (
                <div key={idx} className="relative">
                  <div className={`absolute -left-[27px] top-0.5 w-3.5 h-3.5 rounded-full border-2 ${
                    evt.isDone 
                      ? 'bg-emerald-500 border-white dark:border-slate-900' 
                      : 'bg-slate-300 dark:bg-slate-700 border-white dark:border-slate-900'
                  }`} />
                  <div className="text-xs">
                    <p className="font-semibold text-slate-800 dark:text-slate-200">{evt.title}</p>
                    {evt.detail && (
                      <p className="text-slate-500 dark:text-slate-400 mt-0.5">{evt.detail}</p>
                    )}
                    {evt.time && (
                      <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">{evt.time}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Conversation Thread (Existing Replies) */}
          {existingReplies.length > 0 && (
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Replies ({existingReplies.length})
              </h4>
              <div className="space-y-2.5">
                {existingReplies.map((r) => (
                  <div 
                    key={r.id} 
                    className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                      <span className="font-bold text-slate-700 dark:text-slate-300">
                        {r.source === 'owner' ? 'Your Reply' : (r.commenter_name || 'Reply')}
                      </span>
                      <span>{formatAbsoluteTime(r.created_at)}</span>
                    </div>
                    <p className="text-slate-800 dark:text-slate-100 font-normal leading-relaxed whitespace-pre-line">
                      {r.message}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Technical Details (Collapsible for developer debugging) */}
          <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-400 transition"
            >
              <span>Technical details</span>
              {showTechnicalDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showTechnicalDetails && (
              <div className="p-4 bg-white dark:bg-slate-900 text-xs space-y-2.5 font-mono text-slate-600 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <span>Internal Comment ID:</span>
                  <div className="flex items-center space-x-1.5">
                    <span className="font-bold text-slate-800 dark:text-slate-200">{comment.id}</span>
                    <button 
                      onClick={() => handleCopy(String(comment.id), 'id')}
                      className="p-1 hover:text-indigo-600"
                    >
                      {copiedKey === 'id' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span>External Comment ID:</span>
                  <div className="flex items-center space-x-1.5">
                    <span className="font-bold text-slate-800 dark:text-slate-200 truncate max-w-[180px]">{comment.external_comment_id}</span>
                    <button 
                      onClick={() => handleCopy(comment.external_comment_id, 'ext_cid')}
                      className="p-1 hover:text-indigo-600"
                    >
                      {copiedKey === 'ext_cid' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>

                {comment.external_post_id && (
                  <div className="flex items-center justify-between">
                    <span>External Post ID:</span>
                    <div className="flex items-center space-x-1.5">
                      <span className="font-bold text-slate-800 dark:text-slate-200 truncate max-w-[180px]">{comment.external_post_id}</span>
                      <button 
                        onClick={() => handleCopy(comment.external_post_id || '', 'ext_pid')}
                        className="p-1 hover:text-indigo-600"
                      >
                        {copiedKey === 'ext_pid' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span>Social Account ID:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">{comment.social_account_id}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span>Webhook Object:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">{comment.webhook_object}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span>Processing Status:</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">{comment.processing_status}</span>
                </div>

                {comment.created_at && (
                  <div className="flex items-center justify-between">
                    <span>DB Ingestion Timestamp:</span>
                    <span className="font-bold text-slate-800 dark:text-slate-200 text-[10px]">{comment.created_at}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Bottom Reply Composer */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <form onSubmit={handleSendReply} className="space-y-2.5">
            {replyError && (
              <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{replyError}</span>
              </div>
            )}

            <div className="relative">
              <textarea
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder={`Reply to ${commenterDisplayName}...`}
                rows={2}
                maxLength={2000}
                className="w-full text-xs rounded-xl p-3 pr-20 border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/70 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none"
              />

              <div className="absolute right-2.5 bottom-2.5">
                <button
                  type="submit"
                  disabled={!replyMessage.trim() || isSendingReply}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center space-x-1 shadow-sm"
                >
                  {isSendingReply ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <>
                      <span>Send</span>
                      <Send className="w-3 h-3" />
                    </>
                  )}
                </button>
              </div>
            </div>
            <div className="flex justify-between text-[11px] text-slate-400 px-1">
              <span>Press Send to publish reply to Meta</span>
              <span>{replyMessage.length}/2000</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
