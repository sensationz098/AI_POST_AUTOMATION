'use client';

import React, { useState, useEffect } from 'react';
import { Search, Image as ImageIcon, Calendar, Check, X, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { PlatformPost, PlatformPostsResponse, AutomationPlatform } from '@/lib/types';
import { apiClient } from '@/lib/api';

interface PostPickerModalProps {
  isOpen: boolean;
  socialAccountId: number | null;
  platform: AutomationPlatform;
  selectedPostId: string | null;
  onSelectPost: (post: PlatformPost) => void;
  onClose: () => void;
}

export default function PostPickerModal({
  isOpen,
  socialAccountId,
  platform,
  selectedPostId,
  onSelectPost,
  onClose,
}: PostPickerModalProps) {
  const [posts, setPosts] = useState<PlatformPost[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchPlatformPosts = async () => {
    if (!socialAccountId) {
      setFetchError('No connected social account selected.');
      return;
    }

    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await apiClient.get<PlatformPostsResponse>(
        `/social-accounts/${socialAccountId}/platform-posts`,
        {
          params: { limit: 50 },
        }
      );
      setPosts(res.data?.items || []);
    } catch (err: any) {
      console.error('Failed to load platform posts from Meta:', err);
      const detail = err.response?.data?.detail;
      setFetchError(
        typeof detail === 'string'
          ? detail
          : 'Failed to load posts from Meta account. Please verify account connection.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    fetchPlatformPosts();
  }, [isOpen, socialAccountId, platform]);

  if (!isOpen) return null;

  const filteredPosts = posts.filter((p) => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      (p.caption && p.caption.toLowerCase().includes(query)) ||
      (p.id && p.id.toLowerCase().includes(query))
    );
  });

  const isInstagram = platform === 'instagram';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden relative">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center space-x-2">
              <span>Select Real Platform Post</span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                  isInstagram
                    ? 'bg-pink-500/10 text-pink-400 border-pink-500/20'
                    : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                }`}
              >
                {platform}
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Fetched directly from your connected {isInstagram ? 'Instagram Business Account' : 'Facebook Page'}.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={fetchPlatformPosts}
              disabled={isLoading}
              title="Refresh posts from Meta"
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-xl hover:bg-slate-800 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-xl hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b border-slate-800/60 bg-slate-950/40">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by caption or real Meta Post ID..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
        </div>

        {/* Posts List Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              <p className="text-xs font-semibold">Fetching posts from Meta...</p>
            </div>
          ) : fetchError ? (
            <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-semibold">{fetchError}</p>
                <button
                  type="button"
                  onClick={fetchPlatformPosts}
                  className="mt-2 inline-flex items-center space-x-1 text-xs text-rose-200 underline font-medium"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Retry</span>
                </button>
              </div>
            </div>
          ) : filteredPosts.length === 0 ? (
            <div className="py-16 text-center text-slate-400 space-y-2">
              <ImageIcon className="w-10 h-10 mx-auto text-slate-600" />
              <p className="text-xs font-semibold text-slate-300">No posts found on this account</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                No published posts were returned from Meta for this {platform} account.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredPosts.map((post) => {
                const isSelected = selectedPostId === post.id;
                const mediaUrl = post.thumbnail_url || post.media_url;
                const dateStr = post.created_time
                  ? new Date(post.created_time).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })
                  : null;

                return (
                  <div
                    key={post.id}
                    onClick={() => {
                      onSelectPost(post);
                      onClose();
                    }}
                    className={`group relative p-3.5 rounded-2xl border transition-all cursor-pointer flex gap-3 select-none ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                    }`}
                  >
                    {/* Media Thumbnail */}
                    <div className="w-16 h-16 rounded-xl bg-slate-900 border border-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center relative">
                      {mediaUrl ? (
                        <img
                          src={mediaUrl}
                          alt="Post thumbnail"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <ImageIcon className="w-6 h-6 text-slate-600" />
                      )}
                      {isSelected && (
                        <div className="absolute inset-0 bg-indigo-600/60 flex items-center justify-center">
                          <Check className="w-6 h-6 text-white stroke-[3]" />
                        </div>
                      )}
                    </div>

                    {/* Post Content */}
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                          {isInstagram ? 'Instagram Media' : 'Facebook Post'}
                        </span>
                        {dateStr && (
                          <span className="text-[10px] text-slate-500 flex items-center space-x-1 flex-shrink-0">
                            <Calendar className="w-2.5 h-2.5" />
                            <span>{dateStr}</span>
                          </span>
                        )}
                      </div>

                      <p className="text-[11px] text-slate-300 line-clamp-2 leading-relaxed font-normal">
                        {post.caption || 'No caption text'}
                      </p>

                      <div className="pt-1 flex flex-col space-y-0.5 text-[10px]">
                        <span className="font-mono text-slate-400 truncate">
                          {isInstagram ? 'Instagram Media ID: ' : 'Facebook Post ID: '}
                          <span className="text-slate-200 font-semibold">{post.id}</span>
                        </span>
                        {post.internal_post_id ? (
                          <span className="text-[9px] text-emerald-400 font-mono">
                            Local Post: #{post.internal_post_id}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between text-xs">
          <p className="text-[11px] text-slate-400">
            Selected target will use the real Meta Platform ID for 100% accurate webhook comment matching.
          </p>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
