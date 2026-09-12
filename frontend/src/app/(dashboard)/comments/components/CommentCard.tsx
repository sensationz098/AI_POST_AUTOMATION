'use client';

import React from 'react';
import { 
  MessageSquare, 
  Bot, 
  Sparkles, 
  Clock, 
  CornerDownRight, 
  ExternalLink, 
  AlertCircle, 
  CheckCircle2, 
  ShieldAlert,
  HelpCircle,
  PlusCircle,
  ArrowRight
} from 'lucide-react';
import { SocialComment } from '@/lib/types';

interface CommentCardProps {
  comment: SocialComment;
  isSelected?: boolean;
  onSelect: (comment: SocialComment) => void;
  onReplyClick: (comment: SocialComment) => void;
  onCreateAutomationClick?: (comment: SocialComment) => void;
}

export default function CommentCard({
  comment,
  isSelected = false,
  onSelect,
  onReplyClick,
  onCreateAutomationClick,
}: CommentCardProps) {
  const commenterDisplayName = comment.commenter_name || comment.commenter_id || 'Anonymous';
  const commenterHandle = comment.commenter_name ? `@${comment.commenter_name.toLowerCase().replace(/\s+/g, '')}` : null;
  const initial = (commenterDisplayName.charAt(0) || 'U').toUpperCase();

  const isInstagram = (comment.platform || '').toLowerCase() === 'instagram';
  const isFacebook = (comment.platform || '').toLowerCase() === 'facebook';

  // Format relative/readable timestamp
  const getRelativeTime = (dateStr?: string) => {
    if (!dateStr) return 'Recently';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHr / 24);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  const timeDisplay = getRelativeTime(comment.event_timestamp || comment.created_at);

  // Status mapping
  const status = comment.lifecycle_status || 'NEEDS_REPLY';
  const replyCount = (comment.replies || []).length;

  const renderStatusBadge = () => {
    switch (status) {
      case 'NEEDS_REPLY':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/80">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            Needs Reply
          </span>
        );
      case 'AUTOMATED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800/80">
            <Bot className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
            Automated
          </span>
        );
      case 'REPLIED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/80">
            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            Replied ({replyCount})
          </span>
        );
      case 'OWNER_COMMENT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">
            Owner Comment
          </span>
        );
      case 'IGNORED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
            Ignored
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/80">
            <AlertCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
            Failed
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/80">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping"></span>
            Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const postTitle = comment.post?.title || (comment.post?.caption ? comment.post.caption.slice(0, 50) : null) || (comment.meta_ad?.name || null);
  const postThumbnail = comment.post?.thumbnail_url || comment.post?.image_url;

  return (
    <div
      onClick={() => onSelect(comment)}
      className={`group relative bg-white dark:bg-slate-900 border rounded-xl p-4 sm:p-5 transition-all duration-150 cursor-pointer shadow-sm hover:shadow-md ${
        isSelected
          ? 'border-indigo-600 ring-2 ring-indigo-500/20 bg-indigo-50/20 dark:bg-indigo-950/20'
          : 'border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
      }`}
    >
      {/* Top Header Row: Commenter Info, Platform Badge, Timestamp */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          {/* Avatar Initial */}
          <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center font-bold text-slate-700 dark:text-slate-200 text-sm flex-shrink-0">
            {initial}
          </div>

          <div className="min-w-0">
            <div className="flex items-center space-x-2 flex-wrap">
              <span className="font-semibold text-sm text-slate-900 dark:text-slate-100 truncate">
                {commenterDisplayName}
              </span>
              {commenterHandle && commenterHandle !== `@${commenterDisplayName.toLowerCase()}` && (
                <span className="text-xs text-slate-400 dark:text-slate-500 truncate">
                  {commenterHandle}
                </span>
              )}
            </div>

            {/* Platform and Connected Account */}
            <div className="flex items-center space-x-2 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {isInstagram && (
                <span className="inline-flex items-center gap-1 font-medium text-pink-600 dark:text-pink-400">
                  <span className="w-2 h-2 rounded-full bg-pink-500"></span>
                  Instagram
                </span>
              )}
              {isFacebook && (
                <span className="inline-flex items-center gap-1 font-medium text-blue-600 dark:text-blue-400">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  Facebook
                </span>
              )}
              {comment.account?.account_name && (
                <>
                  <span className="text-slate-300 dark:text-slate-700">•</span>
                  <span className="truncate max-w-[140px] sm:max-w-[200px]">
                    {comment.account.account_name}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Timestamp & Status Badge */}
        <div className="flex flex-col items-end space-y-1.5 flex-shrink-0">
          <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
            <Clock className="w-3 h-3 text-slate-400" />
            {timeDisplay}
          </span>
          {renderStatusBadge()}
        </div>
      </div>

      {/* Main Comment Text */}
      <div className="mt-3 text-sm text-slate-800 dark:text-slate-200 font-normal leading-relaxed break-words">
        {comment.comment_text ? (
          <p className="whitespace-pre-line">{comment.comment_text}</p>
        ) : (
          <p className="italic text-slate-400">[Media comment or empty text]</p>
        )}
      </div>

      {/* Context: Connected Post / Reel (if available) */}
      {postTitle && (
        <div className="mt-3 flex items-center space-x-2.5 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300">
          {postThumbnail ? (
            <img
              src={postThumbnail}
              alt="Post thumbnail"
              className="w-7 h-7 rounded object-cover flex-shrink-0 border border-slate-200 dark:border-slate-700"
            />
          ) : (
            <div className="w-7 h-7 rounded bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 text-slate-400">
              <MessageSquare className="w-3.5 h-3.5" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-slate-700 dark:text-slate-200">
              {postTitle}
            </p>
          </div>
        </div>
      )}

      {/* System Explanation & Action Row */}
      <div className="mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between gap-3 flex-wrap">
        {/* What our system did explanation */}
        <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 min-w-0 flex-1 truncate">
          {comment.status_reason || 'No automation matched this comment.'}
        </p>

        {/* Actions: Reply and Create Automation */}
        <div className="flex items-center space-x-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {status === 'NEEDS_REPLY' && onCreateAutomationClick && (
            <button
              type="button"
              onClick={() => onCreateAutomationClick(comment)}
              className="px-2.5 py-1 text-xs font-medium rounded-lg text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition flex items-center space-x-1"
            >
              <PlusCircle className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>Create Automation</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => onReplyClick(comment)}
            className="px-3 py-1 text-xs font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition flex items-center space-x-1 shadow-sm"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Reply</span>
          </button>
        </div>
      </div>
    </div>
  );
}
