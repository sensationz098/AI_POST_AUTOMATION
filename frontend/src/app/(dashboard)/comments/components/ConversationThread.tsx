'use client';

import React, { useState } from 'react';
import { SocialComment, SocialCommentReply } from '@/lib/types';
import { User, Clock, CornerDownRight, CheckCircle2, Trash2, Loader2, MessageSquare, ExternalLink, Megaphone, FileText } from 'lucide-react';

import ReplyComposer from './ReplyComposer';
import AIAssistanceCard from './AIAssistanceCard';

interface ConversationThreadProps {
  comment: SocialComment;
  onReplyAdded?: (commentId: number, newReply: SocialCommentReply) => void;
  onCommentDeleted?: (commentId: number) => void;
  showPostContext?: boolean;
}

export default function ConversationThread({
  comment,
  onReplyAdded,
  onCommentDeleted,
  showPostContext = true,
}: ConversationThreadProps) {
  const [isReplying, setIsReplying] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const commenterName = comment.commenter_name || comment.commenter_id || 'Anonymous Customer';
  const initial = commenterName.charAt(0).toUpperCase();

  const repliesList = comment.replies || [];
  const isReplied = repliesList.length > 0;

  const postCtx = comment.post;
  const adCtx = comment.meta_ad;

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this comment?')) return;
    setDeleting(true);
    try {
      if (onCommentDeleted) {
        await onCommentDeleted(comment.id);
      }
    } finally {
      setDeleting(false);
    }
  };

  const handleUseSuggestedReply = (suggestedText: string) => {
    setIsReplying(true);
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
      {/* Context Banner: Parent Meta Ad or Organic Post Source */}
      {showPostContext && (adCtx || postCtx) && (
        <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/70 text-xs flex items-center justify-between gap-3 text-slate-300">
          <div className="flex items-center space-x-2.5 min-w-0">
            {adCtx ? (
              <span className="px-2 py-0.5 rounded bg-purple-950/90 text-purple-300 border border-purple-800/80 text-[10px] font-extrabold flex items-center space-x-1 flex-shrink-0">
                <Megaphone className="w-3 h-3 text-purple-400" />
                <span>Meta Ad</span>
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded bg-indigo-950/90 text-indigo-300 border border-indigo-800/80 text-[10px] font-extrabold flex items-center space-x-1 flex-shrink-0">
                <FileText className="w-3 h-3 text-indigo-400" />
                <span>Organic Post</span>
              </span>
            )}

            <div className="min-w-0 flex-1">
              <p className="font-semibold text-slate-200 truncate">
                {adCtx?.name || postCtx?.title || (postCtx?.caption ? postCtx.caption.slice(0, 60) : 'Social Content')}
              </p>
              {adCtx?.campaign_name && (
                <p className="text-[10px] text-slate-400 truncate">
                  Campaign: <span className="text-slate-300 font-medium">{adCtx.campaign_name}</span>
                </p>
              )}
            </div>
          </div>

          {(adCtx?.permalink || postCtx?.permalink) && (
            <a
              href={adCtx?.permalink || postCtx?.permalink}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white text-[11px] font-medium transition flex items-center space-x-1 flex-shrink-0"
            >
              <span>View Source</span>
              <ExternalLink className="w-3 h-3 text-indigo-400" />
            </a>
          )}
        </div>
      )}
      {/* Thread Header: Customer Identity & Reply Status Badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-white font-extrabold text-xs flex-shrink-0 shadow-sm">
            {initial}
          </div>

          <div className="min-w-0 space-y-0.5">
            <div className="flex items-center space-x-2 flex-wrap">
              <span className="font-bold text-sm text-slate-100 truncate">
                {commenterName}
              </span>

              {/* Reply Status Badge */}
              {isReplied ? (
                <span className="px-2 py-0.5 rounded-full bg-emerald-950/90 text-emerald-300 border border-emerald-800/80 text-[10px] font-bold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Replied</span>
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full bg-amber-950/90 text-amber-300 border border-amber-800/80 text-[10px] font-bold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                  <span>Unreplied</span>
                </span>
              )}
            </div>

            <div className="flex items-center space-x-2 text-[11px] text-slate-400">
              <Clock className="w-3 h-3 text-slate-500" />
              <span>
                {comment.created_at ? new Date(comment.created_at).toLocaleString() : 'Recent'}
              </span>
              <span className="text-slate-600">•</span>
              <span className="font-mono text-slate-500 text-[10px]">ID: {comment.external_comment_id}</span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 border border-transparent hover:border-rose-800/50 transition flex-shrink-0"
          title="Delete Comment"
        >
          {deleting ? (
            <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Main Comment Text */}
      <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800/70 text-xs text-slate-100 leading-relaxed font-sans whitespace-pre-wrap shadow-inner">
        {comment.comment_text || <em className="text-slate-500">No comment text</em>}
      </div>

      {/* AI Co-Pilot Card */}
      <AIAssistanceCard
        intent="Customer Inquiry"
        sentiment="Positive"
        priority="Medium"
        onUseSuggestedReply={handleUseSuggestedReply}
      />

      {/* Nested Replies Branch */}
      {repliesList.length > 0 && (
        <div className="pl-4 border-l-2 border-indigo-500/40 space-y-2 mt-3 pt-1">
          <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">
            Replies ({repliesList.length})
          </span>

          {repliesList.map((reply: SocialCommentReply) => {
            const isOwnerReply = reply.source === 'owner';
            const customerName = reply.commenter_name || (reply.source === 'meta' ? 'Customer Reply' : null);

            return (
              <div
                key={reply.id}
                className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60 text-xs text-slate-200 flex items-start space-x-2.5 shadow-sm"
              >
                <CornerDownRight className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="text-slate-100 font-sans leading-relaxed">{reply.message}</p>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                    {isOwnerReply ? (
                      <span className="flex items-center space-x-1 font-semibold text-indigo-300">
                        <span>Official Brand Reply</span>
                      </span>
                    ) : (
                      <span className="flex items-center space-x-1 font-semibold text-slate-300">
                        <span>{customerName || 'Customer Reply'}</span>
                      </span>
                    )}
                    <span className="flex items-center space-x-1.5">
                      {isOwnerReply && (
                        <span className="text-emerald-400 font-bold flex items-center space-x-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>Sent</span>
                        </span>
                      )}
                      {isOwnerReply && <span className="text-slate-600">•</span>}
                      <span>{reply.created_at ? new Date(reply.created_at).toLocaleString() : ''}</span>
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Reply Composer Form / Trigger Button */}
      {isReplying ? (
        <ReplyComposer
          commentId={comment.id}
          onSuccess={(newReply) => {
            setIsReplying(false);
            if (onReplyAdded) onReplyAdded(comment.id, newReply);
          }}
          onCancel={() => setIsReplying(false)}
        />
      ) : (
        <div className="flex justify-end pt-1">
          <button
            onClick={() => setIsReplying(true)}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-indigo-300 hover:text-white border border-slate-700/60 text-xs font-semibold transition flex items-center space-x-1.5 shadow-sm"
          >
            <CornerDownRight className="w-3.5 h-3.5 text-indigo-400" />
            <span>Reply to Conversation</span>
          </button>
        </div>
      )}
    </div>
  );
}
