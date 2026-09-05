'use client';

import React, { useState } from 'react';
import { Send, Loader2, AlertCircle, CheckCircle2, CornerDownRight } from 'lucide-react';
import { apiClient } from '@/lib/api';

import { SocialCommentAccountContext } from '@/lib/types';

interface ReplyComposerProps {
  commentId: number;
  authoritativeAccount?: SocialCommentAccountContext | null;
  platform?: 'facebook' | 'instagram' | string;
  onSuccess: (newReply: any) => void;
  onCancel: () => void;
}

export default function ReplyComposer({ 
  commentId, 
  authoritativeAccount, 
  platform = 'facebook', 
  onSuccess, 
  onCancel 
}: ReplyComposerProps) {
  const [replyText, setReplyText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isInstagram = (platform || '').toLowerCase() === 'instagram';
  const displayName = authoritativeAccount?.account_name || 
    authoritativeAccount?.display_name || 
    (isInstagram ? '@business_account' : 'Facebook Page');

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!replyText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const res = await apiClient.post(`/social-comments/${commentId}/reply`, {
        message: replyText.trim(),
      });
      onSuccess(res.data.reply);
      setReplyText('');
    } catch (err: any) {
      console.error('Failed to post reply:', err);
      setError(err?.response?.data?.detail || 'Failed to send reply. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2 pt-2 border-t border-slate-800/80">
      {/* Authoritative Sender Indicator */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 pb-0.5 px-1">
        <div className="flex items-center space-x-1.5 min-w-0">
          <span className="text-slate-500 font-medium flex-shrink-0">Replying as:</span>
          <div className="flex items-center space-x-1.5 font-semibold text-slate-200 truncate">
            {isInstagram ? (
              <span className="text-pink-400 truncate">
                @{displayName.replace(/^@/, '')}
              </span>
            ) : (
              <span className="text-blue-400 truncate">
                {displayName}
              </span>
            )}
            <span className="text-slate-500 font-normal">·</span>
            <span className={`text-[10px] font-bold uppercase tracking-wider ${isInstagram ? 'text-pink-400' : 'text-blue-400'}`}>
              {isInstagram ? 'Instagram' : 'Facebook'}
            </span>
          </div>
        </div>
        <span className="text-[10px] text-slate-500 hidden sm:inline-block font-mono">
          Authoritative Owner
        </span>
      </div>
      {error && (
        <div className="p-2 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center space-x-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="relative">
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          placeholder="Write an official brand reply..."
          rows={2}
          disabled={isSubmitting}
          className="w-full bg-slate-950 border border-indigo-800/80 focus:border-indigo-500 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 outline-none transition resize-none disabled:opacity-50 shadow-inner"
        />
      </div>

      <div className="flex items-center justify-end space-x-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
        >
          Cancel
        </button>

        <button
          type="submit"
          disabled={isSubmitting || !replyText.trim()}
          className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
              <span>Sending...</span>
            </>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>Post Reply</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
}
