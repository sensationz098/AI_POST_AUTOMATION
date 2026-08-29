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
  Filter
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialComment } from '@/lib/types';

export default function CommentsPage() {
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [platformFilter, setPlatformFilter] = useState<'all' | 'facebook' | 'instagram'>('all');

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
                <span>Social Comments</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                  Meta Webhooks Ingestion
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                View real-time comments ingested from connected Facebook Pages & Instagram Professional accounts.
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
            Webhook Storage Active: Comments are automatically ingested, isolated by account ownership, and deduplicated.
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

      {/* Main Content Area: Loading / Error / Empty / Data Table */}
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
        /* Comments Table / Cards List */
        <div className="space-y-3">
          {filteredComments.map((comment) => (
            <div
              key={comment.id}
              className="linear-panel p-4 rounded-xl border border-slate-800/80 hover:border-slate-700 transition space-y-3 bg-slate-900/40"
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
                  <p className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/60 font-sans">
                    "{comment.comment_text}"
                  </p>
                ) : (
                  <p className="text-slate-500 italic text-[11px]">
                    (Comment payload received without text content)
                  </p>
                )}
              </div>

              {/* External IDs Metadata Footer */}
              <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono text-slate-400 pt-1">
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
