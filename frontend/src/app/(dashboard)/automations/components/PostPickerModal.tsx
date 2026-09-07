'use client';

import React, { useState, useEffect } from 'react';
import { Search, Image as ImageIcon, Calendar, Check, X, Loader2, ExternalLink, AlertCircle } from 'lucide-react';
import { SocialPost, AutomationPlatform } from '@/lib/types';
import { apiClient } from '@/lib/api';

interface PostPickerModalProps {
  isOpen: boolean;
  platform: AutomationPlatform;
  selectedPostId: number | null;
  onSelectPost: (post: SocialPost) => void;
  onClose: () => void;
}

export default function PostPickerModal({
  isOpen,
  platform,
  selectedPostId,
  onSelectPost,
  onClose,
}: PostPickerModalProps) {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const fetchPosts = async () => {
      setIsLoading(true);
      setFetchError(null);
      try {
        const res = await apiClient.get<SocialPost[]>('/posts', {
          params: { status: 'PUBLISHED' },
        });
        // Filter by platform
        const filtered = (res.data || []).filter((p) =>
          Array.isArray(p.platforms) ? p.platforms.includes(platform) : true
        );
        setPosts(filtered);
      } catch (err: any) {
        console.error('Failed to load published posts:', err);
        setFetchError(err.response?.data?.detail || 'Failed to load published posts. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPosts();
  }, [isOpen, platform]);

  if (!isOpen) return null;

  const filteredPosts = posts.filter((p) => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      (p.title && p.title.toLowerCase().includes(query)) ||
      (p.caption && p.caption.toLowerCase().includes(query)) ||
      (p.fb_post_id && p.fb_post_id.includes(query)) ||
      (p.ig_media_id && p.ig_media_id.includes(query))
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden relative">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center space-x-2">
              <span>Select Target Post</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {platform}
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Choose the published post to attach this comment automation to.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b border-slate-800/60 bg-slate-950/40">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by caption, title, or post ID..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
        </div>

        {/* Posts List Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              <p className="text-xs font-semibold">Loading published posts...</p>
            </div>
          ) : fetchError ? (
            <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{fetchError}</span>
            </div>
          ) : filteredPosts.length === 0 ? (
            <div className="py-16 text-center text-slate-400 space-y-2">
              <ImageIcon className="w-10 h-10 mx-auto text-slate-600" />
              <p className="text-xs font-semibold text-slate-300">No published posts found</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                Make sure you have published posts for {platform === 'facebook' ? 'Facebook' : 'Instagram'}.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredPosts.map((post) => {
                const isSelected = selectedPostId === post.id;
                const mediaUrl = post.image_url || post.thumbnail_url;
                const dateStr = post.published_at
                  ? new Date(post.published_at).toLocaleDateString(undefined, {
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
                          alt={post.title || 'Post thumbnail'}
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
                        <span className="text-xs font-bold text-slate-200 truncate">
                          {post.title || `Post #${post.id}`}
                        </span>
                        {dateStr && (
                          <span className="text-[10px] text-slate-500 flex items-center space-x-1 flex-shrink-0">
                            <Calendar className="w-2.5 h-2.5" />
                            <span>{dateStr}</span>
                          </span>
                        )}
                      </div>

                      <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                        {post.caption || 'No caption text'}
                      </p>

                      <div className="pt-1 flex items-center justify-between text-[10px] text-slate-500">
                        <span className="font-mono truncate">
                          ID: {post.ig_media_id || post.fb_post_id || `#${post.id}`}
                        </span>
                        <span className="text-indigo-400 font-semibold group-hover:underline">
                          Select →
                        </span>
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
            This automation will only run on the selected post.
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
