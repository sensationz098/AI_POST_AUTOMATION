'use client';

import React, { useState } from 'react';
import { SocialComment, SocialCommentReply } from '@/lib/types';
import { 
  User, 
  Clock, 
  CornerDownRight, 
  CheckCircle2, 
  Trash2, 
  Loader2, 
  MessageSquare, 
  ExternalLink, 
  Megaphone, 
  FileText,
  ShieldCheck,
  Sparkles
} from 'lucide-react';

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
  showPostContext = false,
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

  const formattedDate = comment.event_timestamp || comment.created_at
    ? new Date(comment.event_timestamp || comment.created_at).toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : 'Recent';

  return (
    <div className="bg-slate-900/80 border border-slate-800/90 hover:border-slate-700/80 rounded-2xl p-4 sm:p-5 space-y-4 transition-all shadow-md">
      {/* Context Banner: Parent Meta Ad or Organic Post Source (if applicable) */}
      {showPostContext && (adCtx || postCtx) && (
        <div className="p-2.5 rounded-xl bg-slate-950/90 border border-slate-800/80 text-xs flex items-center justify-between gap-3 text-slate-300">
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

      {/* Parent Comment Header: Profile & Status */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-600 flex items-center justify-center text-white font-extrabold text-sm flex-shrink-0 shadow-md ring-2 ring-indigo-500/20">
            {initial}
          </div>

          <div className="min-w-0 space-y-0.5">
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <span className="font-bold text-sm text-slate-100 truncate">
                {commenterName}
              </span>

              {/* Status Pill */}
              {isReplied ? (
                <span className="px-2 py-0.5 rounded-full bg-emerald-950/90 text-emerald-300 border border-emerald-800/80 text-[10px] font-bold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Replied ({repliesList.length})</span>
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
              <span>{formattedDate}</span>
              {comment.external_comment_id && (
                <>
                  <span className="text-slate-600">•</span>
                  <span className="font-mono text-slate-500 text-[10px]">ID: {comment.external_comment_id}</span>
                </>
              )}
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
      <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 text-sm text-slate-100 leading-relaxed font-sans whitespace-pre-wrap shadow-inner">
        {comment.comment_text || <em className="text-slate-500">No comment text</em>}
      </div>

      {/* AI Assistance Co-Pilot (Visually Secondary) */}
      <AIAssistanceCard
        intent="Customer Engagement"
        sentiment="Positive"
        priority="Medium"
        onUseSuggestedReply={handleUseSuggestedReply}
      />

      {/* Nested Replies Branch */}
      {repliesList.length > 0 && (
        <div className="pl-4 sm:pl-6 border-l-2 border-indigo-500/30 space-y-3 mt-4 pt-1">
          <div className="flex items-center space-x-2 text-[11px] font-bold text-indigo-400 uppercase tracking-wider">
            <CornerDownRight className="w-3.5 h-3.5" />
            <span>Replies ({repliesList.length})</span>
          </div>

          {repliesList.map((reply: SocialCommentReply) => {
            const isOwnerReply = reply.source === 'owner';
            const customerName = reply.commenter_name || (reply.source === 'meta' ? 'Customer' : null);
            const replyInitial = (customerName || (isOwnerReply ? 'B' : 'U')).charAt(0).toUpperCase();
            const replyDate = reply.event_timestamp || reply.created_at
              ? new Date(reply.event_timestamp || reply.created_at).toLocaleString(undefined, {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })
              : '';

            return (
              <div
                key={reply.id}
                className={`p-3.5 rounded-xl border transition-all text-xs space-y-2 shadow-sm ${
                  isOwnerReply
                    ? 'bg-indigo-950/40 border-indigo-500/40 ring-1 ring-indigo-500/20'
                    : 'bg-slate-950/60 border-slate-800/80'
                }`}
              >
                {/* Reply Header */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-2.5 min-w-0">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-extrabold flex-shrink-0 text-white ${
                        isOwnerReply
                          ? 'bg-indigo-600 ring-1 ring-indigo-400'
                          : 'bg-slate-700'
                      }`}
                    >
                      {replyInitial}
                    </div>

                    <div className="min-w-0">
                      {isOwnerReply ? (
                        <div className="flex items-center space-x-1.5 font-bold text-indigo-300">
                          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Official Brand Reply</span>
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 fill-emerald-400/20" />
                        </div>
                      ) : (
                        <div className="flex items-center space-x-1 font-semibold text-slate-200">
                          <span>{customerName || 'Customer Reply'}</span>
                          <span className="text-[10px] text-slate-500 font-normal">via Meta</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5 text-[10px] text-slate-400 flex-shrink-0">
                    {isOwnerReply && (
                      <span className="px-1.5 py-0.2 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 font-semibold text-[9px]">
                        Sent
                      </span>
                    )}
                    <span>{replyDate}</span>
                  </div>
                </div>

                {/* Reply Body */}
                <p className="text-slate-100 font-sans leading-relaxed pl-8 whitespace-pre-wrap">
                  {reply.message}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Reply Composer Form / Action Button */}
      {isReplying ? (
        <div className="pt-2">
          <ReplyComposer
            commentId={comment.id}
            onSuccess={(newReply) => {
              setIsReplying(false);
              if (onReplyAdded) onReplyAdded(comment.id, newReply);
            }}
            onCancel={() => setIsReplying(false)}
          />
        </div>
      ) : (
        <div className="flex justify-end pt-1">
          <button
            onClick={() => setIsReplying(true)}
            className="px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-white border border-indigo-500/40 text-xs font-semibold transition flex items-center space-x-1.5 shadow-sm"
          >
            <CornerDownRight className="w-3.5 h-3.5 text-indigo-400" />
            <span>Reply to Thread</span>
          </button>
        </div>
      )}
    </div>
  );
}

