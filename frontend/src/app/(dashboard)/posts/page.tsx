'use client';

import React, { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  Send, 
  RefreshCw, 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  FileEdit,
  Plus,
  Filter,
  Trash2,
  Loader2,
  X
} from 'lucide-react';
import { PostStatusBadge } from '@/components/PostStatusBadge';
import { SocialPost } from '@/lib/types';
import { apiClient } from '@/lib/api';
import Link from 'next/link';


export default function PostSchedulerPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Deletion UI State
  const [deletingPostId, setDeletingPostId] = useState<number | null>(null);
  const [confirmDeletePost, setConfirmDeletePost] = useState<SocialPost | null>(null);
  const [deleteStatusMessage, setDeleteStatusMessage] = useState<{
    type: 'success' | 'error';
    text: string;
    details?: any[];
  } | null>(null);

  const fetchPosts = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      // Clear legacy local storage queue if present
      try {
        localStorage.removeItem('local_posts_queue');
      } catch {}

      const res = await apiClient.get('/posts/');
      const apiPosts = Array.isArray(res.data) ? res.data : [];
      setPosts(apiPosts);
    } catch (e: any) {
      setPosts([]);
      setFetchError(e.response?.data?.detail || e.message || 'Failed to load post queue.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  const filteredPosts = filterStatus === 'ALL'
    ? posts
    : posts.filter((p) => p.status === filterStatus);

  const handleRetry = async (postId: number) => {
    try {
      await apiClient.post(`/posts/${postId}/retry`);
      await fetchPosts();
    } catch (e) {
      // Refresh backend list
      await fetchPosts();
    }
  };

  const handleDeletePost = async (postId: number) => {
    setDeletingPostId(postId);
    setDeleteStatusMessage(null);
    try {
      const res = await apiClient.delete(`/posts/${postId}`);
      const data = res.data;

      if (data && data.success === true) {
        // Refresh posts from backend after successful deletion
        await fetchPosts();

        setDeleteStatusMessage({
          type: 'success',
          text: data.message || 'Post and external targets deleted successfully.',
        });
        setConfirmDeletePost(null);
      } else {
        // Partial or total failure - DO NOT remove local post from list
        setDeleteStatusMessage({
          type: 'error',
          text: data?.message || 'Deletion failed for one or more external targets.',
          details: data?.details || [],
        });
      }
    } catch (e: any) {
      const errorMsg = e.response?.data?.detail || e.message || 'Failed to delete post.';
      setDeleteStatusMessage({
        type: 'error',
        text: `Deletion request failed: ${errorMsg}`,
      });
    } finally {
      setDeletingPostId(null);
    }
  };

  const userTimeZone = typeof window !== 'undefined'
    ? Intl.DateTimeFormat().resolvedOptions().timeZone
    : 'Local Time';

  const formatToLocalDateTime = (dateStr?: string) => {
    if (!dateStr) return '—';
    const normalizedStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
    const date = new Date(normalizedStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="space-y-5 select-none font-sans text-xs">
      {/* Linear Style Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/60">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
              <CalendarIcon className="w-4 h-4 text-indigo-400" />
              <span>Social Post Queue & Publishing Workflow</span>
            </h1>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-slate-900/60 text-slate-400 border border-slate-800">
              Timezone: {userTimeZone}
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Track drafts, scheduled queue times, and automated Meta Graph API retries.
          </p>
        </div>

        <Link
          href="/studio"
          className="inline-flex items-center space-x-1.5 px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] transition shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ Create Post</span>
        </Link>
      </div>

      {/* Global Success / Deletion Message Banner */}
      {deleteStatusMessage && deleteStatusMessage.type === 'success' && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-200 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>{deleteStatusMessage.text}</span>
          </div>
          <button
            onClick={() => setDeleteStatusMessage(null)}
            className="text-emerald-400 hover:text-emerald-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
        <span className="text-[11px] font-bold text-slate-400 mr-1 flex items-center space-x-1 flex-shrink-0">
          <Filter className="w-3 h-3 text-indigo-400" />
          <span>Filter:</span>
        </span>
        {['ALL', 'DRAFT', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'FAILED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition flex-shrink-0 ${
              filterStatus === st
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Enterprise Single Surface Jira/Linear Queue Table */}
      <div className="linear-panel rounded-lg overflow-hidden border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-900/60 border-b border-slate-800/80 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-3">Post ID & Visual</th>
                <th className="p-3">Title & Summary</th>
                <th className="p-3">Platforms</th>
                <th className="p-3">Status</th>
                <th className="p-3">Scheduled / Published ({userTimeZone})</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                      <span className="text-xs font-semibold">Loading post queue...</span>
                    </div>
                  </td>
                </tr>
              ) : fetchError ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-rose-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <AlertTriangle className="w-5 h-5 text-rose-400" />
                      <span className="text-xs font-semibold">{fetchError}</span>
                    </div>
                  </td>
                </tr>
              ) : filteredPosts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-1.5">
                      <CalendarIcon className="w-6 h-6 text-slate-500" />
                      <span className="text-xs font-semibold text-slate-300">No posts in queue</span>
                      <p className="text-[11px] text-slate-500">
                        {filterStatus !== 'ALL'
                          ? `No posts currently match the "${filterStatus}" filter.`
                          : 'Your social post queue is empty. Click "+ Create Post" to create a new post.'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredPosts.map((post) => (
                  <tr key={post.id} className="hover:bg-slate-800/40 transition-colors duration-150">
                    <td className="p-3">
                      <div className="flex items-center space-x-2.5">
                        <div className="flex flex-col">
                          <span className="text-[10px] font-mono text-slate-400 font-bold">#{post.id}</span>
                        </div>
                        {post.image_url ? (
                          <img
                            src={post.image_url}
                            alt={post.title || 'Post thumbnail'}
                            className="w-9 h-9 rounded object-cover border border-slate-700 flex-shrink-0"
                          />
                        ) : (
                          <div className="w-9 h-9 rounded bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 text-xs flex-shrink-0">
                            📝
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-3 max-w-sm">
                      <h4 className="font-semibold text-slate-100 text-xs truncate">
                        {post.title && post.title.trim() ? post.title : (post.caption ? (post.caption.slice(0, 45) + (post.caption.length > 45 ? '...' : '')) : 'Untitled Post')}
                      </h4>
                      <p className="text-slate-400 text-[11px] truncate mt-0.5">{post.caption}</p>
                      {(post.fb_post_id || post.ig_media_id) && (
                        <div className="flex items-center space-x-2 mt-1 text-[9px] font-mono text-indigo-400/90">
                          {post.fb_post_id && <span>FB ID: {post.fb_post_id}</span>}
                          {post.ig_media_id && <span>IG ID: {post.ig_media_id}</span>}
                        </div>
                      )}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center space-x-1.5">
                        {post.platforms.includes('facebook') && (
                          <span className="px-1.5 py-0.5 rounded bg-blue-950/60 border border-blue-800/60 text-blue-300 text-[9px] font-mono font-medium">
                            FB Page
                          </span>
                        )}
                        {post.platforms.includes('instagram') && (
                          <span className="px-1.5 py-0.5 rounded bg-pink-950/60 border border-pink-800/60 text-pink-300 text-[9px] font-mono font-medium">
                            IG Biz
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <PostStatusBadge status={post.status} />
                    </td>
                    <td className="p-3 text-slate-300 font-mono text-[11px]">
                      {post.published_at ? (
                        <span className="text-indigo-300 flex items-center space-x-1">
                          <CheckCircle className="w-3 h-3 text-indigo-400 inline" />
                          <span>{formatToLocalDateTime(post.published_at)}</span>
                        </span>
                      ) : post.scheduled_at ? (
                        <span className="text-sky-300 flex items-center space-x-1">
                          <Clock className="w-3 h-3 text-sky-400 inline" />
                          <span>{formatToLocalDateTime(post.scheduled_at)}</span>
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        {post.status === 'FAILED' ? (
                          <button
                            onClick={() => handleRetry(post.id)}
                            className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
                          >
                            <RefreshCw className="w-3 h-3" />
                            <span>Retry</span>
                          </button>
                        ) : post.status === 'APPROVED' ? (
                          <button
                            onClick={() => handleRetry(post.id)}
                            className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
                          >
                            <Send className="w-3 h-3" />
                            <span>Publish Now</span>
                          </button>
                        ) : null}

                        <button
                          disabled={deletingPostId === post.id}
                          onClick={() => {
                            setDeleteStatusMessage(null);
                            setConfirmDeletePost(post);
                          }}
                          className="px-2 py-1 rounded bg-slate-900 hover:bg-rose-950/60 border border-slate-800 hover:border-rose-800/60 text-slate-400 hover:text-rose-300 font-semibold text-[10px] transition flex items-center space-x-1 disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Delete post"
                        >
                          {deletingPostId === post.id ? (
                            <Loader2 className="w-3 h-3 animate-spin text-rose-400" />
                          ) : (
                            <Trash2 className="w-3 h-3" />
                          )}
                          <span>Delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation & Deletion Dialog Modal */}
      {confirmDeletePost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2 text-rose-400">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <h3 className="text-sm font-bold text-slate-100">
                  Delete Post #{confirmDeletePost.id}
                </h3>
              </div>
              <button
                disabled={deletingPostId !== null}
                onClick={() => setConfirmDeletePost(null)}
                className="text-slate-500 hover:text-slate-300 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-300">
              <p className="font-medium text-slate-200">
                Are you sure you want to delete this post?
              </p>

              {confirmDeletePost.status === 'PUBLISHED' && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200 space-y-1 text-[11px]">
                  <p className="font-bold flex items-center space-x-1 text-rose-300">
                    <span>⚠️ External Platform Removal Warning</span>
                  </p>
                  <p>
                    This post has been published. Deleting it will attempt to remove the published media directly from connected social platforms (Facebook / Instagram), not merely from this database.
                  </p>
                  {confirmDeletePost.platforms && confirmDeletePost.platforms.length > 1 && (
                    <p className="font-semibold text-rose-300 mt-1">
                      Target platforms: {confirmDeletePost.platforms.join(', ')}. All applicable published targets will be attempted.
                    </p>
                  )}
                </div>
              )}

              {confirmDeletePost.status === 'SCHEDULED' && (
                <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-200 text-[11px]">
                  <span>🕒 Deleting this post will safely cancel its scheduled execution and remove it.</span>
                </div>
              )}
            </div>

            {/* Error / Status message inside modal */}
            {deleteStatusMessage && deleteStatusMessage.type === 'error' && (
              <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 text-rose-200 text-[11px] space-y-1">
                <p className="font-bold text-rose-300">{deleteStatusMessage.text}</p>
                {deleteStatusMessage.details && deleteStatusMessage.details.length > 0 && (
                  <ul className="list-disc pl-4 space-y-0.5 text-[10px]">
                    {deleteStatusMessage.details.map((d: any, idx: number) => (
                      <li key={idx}>
                        {d.platform} ({d.external_post_id}): {d.error || (d.success ? 'Deleted' : 'Failed')}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                disabled={deletingPostId !== null}
                onClick={() => setConfirmDeletePost(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletingPostId !== null}
                onClick={() => handleDeletePost(confirmDeletePost.id)}
                className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-rose-900/40 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deletingPostId === confirmDeletePost.id ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Deleting External & Local...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Confirm Delete</span>
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
