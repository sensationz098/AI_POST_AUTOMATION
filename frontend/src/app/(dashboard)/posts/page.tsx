'use client';

import React, { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  Send, 
  RefreshCw, 
  CheckCircle, 
  Clock, 
  Plus,
  Filter,
  FileText
} from 'lucide-react';
import { PostStatusBadge } from '@/components/PostStatusBadge';
import { SocialPost } from '@/lib/types';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

export default function PostSchedulerPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchPosts() {
      setIsLoading(true);
      let localQueue: SocialPost[] = [];
      try {
        const stored = localStorage.getItem('local_posts_queue');
        if (stored) localQueue = JSON.parse(stored);
      } catch {}

      try {
        const res = await apiClient.get('/posts/');
        if (res.data && Array.isArray(res.data)) {
          const combined = [...localQueue, ...res.data];
          const uniquePosts = Array.from(new Map(combined.map(p => [p.id, p])).values());
          setPosts(uniquePosts);
        } else {
          setPosts(localQueue);
        }
      } catch (e) {
        setPosts(localQueue);
      } finally {
        setIsLoading(false);
      }
    }
    fetchPosts();
  }, []);

  const filteredPosts = filterStatus === 'ALL'
    ? posts
    : posts.filter((p) => p.status === filterStatus);

  const handleRetry = async (postId: number) => {
    try {
      await apiClient.post(`/posts/${postId}/retry`);
    } catch (e) {
      // Local state update if backend offline
    }
    setPosts((prev) =>
      prev.map((p) =>
        p.id === postId ? { ...p, status: 'PUBLISHED', published_at: new Date().toISOString() } : p
      )
    );
  };

  const userTimeZone = typeof window !== 'undefined'
    ? Intl.DateTimeFormat().resolvedOptions().timeZone
    : 'UTC';

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
    <div className="space-y-6 font-sans text-xs select-none">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight flex items-center space-x-2">
              <CalendarIcon className="w-5 h-5 text-[var(--accent-color)]" />
              <span>Post Queue & Scheduling</span>
            </h1>
            <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-color)]">
              Timezone: {userTimeZone}
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Track draft states, queue times, and automated publishing retry tasks.
          </p>
        </div>

        <Link
          href="/studio"
          className="btn-primary text-xs py-2 px-3.5 space-x-1.5 self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ Create Post</span>
        </Link>
      </div>

      {/* Filter Tabs Bar */}
      <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
        <span className="text-xs font-semibold text-[var(--text-secondary)] mr-2 flex items-center space-x-1 flex-shrink-0">
          <Filter className="w-3.5 h-3.5 text-[var(--accent-color)]" />
          <span>Filter Status:</span>
        </span>
        {['ALL', 'DRAFT', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'FAILED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-medium transition flex-shrink-0 ${
              filterStatus === st
                ? 'bg-[var(--accent-color)] text-white'
                : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)]'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Publishing Queue Table */}
      <div className="pub-card overflow-hidden">
        {filteredPosts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="pub-table">
              <thead>
                <tr>
                  <th className="p-3">ID & Visual</th>
                  <th className="p-3">Title & Caption</th>
                  <th className="p-3">Destinations</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Scheduled / Published ({userTimeZone})</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPosts.map((post) => (
                  <tr key={post.id}>
                    <td className="p-3">
                      <div className="flex items-center space-x-2.5">
                        <span className="text-[11px] font-mono text-[var(--text-tertiary)] font-semibold">#{post.id}</span>
                        {post.image_url ? (
                          <img
                            src={post.image_url}
                            alt={post.title}
                            className="w-9 h-9 rounded object-cover border border-[var(--border-color)] flex-shrink-0"
                          />
                        ) : (
                          <div className="w-9 h-9 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center text-[var(--text-tertiary)] text-xs flex-shrink-0">
                            📝
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-3 max-w-xs">
                      <h4 className="font-semibold text-[var(--text-primary)] text-xs truncate">{post.title || 'Untitled Post'}</h4>
                      <p className="text-[var(--text-secondary)] text-[11px] truncate mt-0.5">{post.caption}</p>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center space-x-1.5">
                        {(post.platforms || []).includes('facebook') && (
                          <span className="px-2 py-0.5 rounded bg-[#1877F2]/10 border border-[#1877F2]/30 text-[#1877F2] text-[10px] font-mono font-medium">
                            FB Page
                          </span>
                        )}
                        {(post.platforms || []).includes('instagram') && (
                          <span className="px-2 py-0.5 rounded bg-[#E4405F]/10 border border-[#E4405F]/30 text-[#E4405F] text-[10px] font-mono font-medium">
                            IG Biz
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <PostStatusBadge status={post.status} />
                    </td>
                    <td className="p-3 text-[var(--text-primary)] font-mono text-[11px]">
                      {post.published_at ? (
                        <span className="text-[var(--success-color)] flex items-center space-x-1">
                          <CheckCircle className="w-3.5 h-3.5 text-[var(--success-color)] inline mr-1" />
                          <span>{formatToLocalDateTime(post.published_at)}</span>
                        </span>
                      ) : post.scheduled_at ? (
                        <span className="text-[var(--accent-color)] flex items-center space-x-1">
                          <Clock className="w-3.5 h-3.5 text-[var(--accent-color)] inline mr-1" />
                          <span>{formatToLocalDateTime(post.scheduled_at)}</span>
                        </span>
                      ) : (
                        <span className="text-[var(--text-tertiary)]">—</span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      {post.status === 'FAILED' ? (
                        <button
                          onClick={() => handleRetry(post.id)}
                          className="btn-danger py-1 px-2.5 text-[11px] flex items-center space-x-1 ml-auto"
                        >
                          <RefreshCw className="w-3 h-3" />
                          <span>Retry</span>
                        </button>
                      ) : post.status === 'APPROVED' ? (
                        <button
                          onClick={() => handleRetry(post.id)}
                          className="btn-primary py-1 px-2.5 text-[11px] flex items-center space-x-1 ml-auto"
                        >
                          <Send className="w-3 h-3" />
                          <span>Publish Now</span>
                        </button>
                      ) : (
                        <span className="text-[var(--text-tertiary)] text-[11px] font-mono">Ready</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center space-y-3">
            <FileText className="w-10 h-10 text-[var(--text-tertiary)] mx-auto" />
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">No Posts Found in Queue</h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {filterStatus !== 'ALL'
                  ? `No posts matching status "${filterStatus}".`
                  : 'You have not created or scheduled any social posts yet.'}
              </p>
            </div>
            <Link href="/studio" className="btn-primary text-xs py-2 px-4 inline-flex items-center space-x-1.5">
              <Plus className="w-3.5 h-3.5" />
              <span>Create Your First Post</span>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
