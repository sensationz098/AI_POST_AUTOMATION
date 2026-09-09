'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Calendar as CalendarIcon,
  Send,
  RefreshCw,
  CheckCircle,
  Clock,
  AlertTriangle,
  Plus,
  Filter,
  Trash2,
  Loader2,
  X,
  ExternalLink,
  ChevronDown,
  Sparkles,
  Film,
  Image as ImageIcon,
  Eye,
  Layers,
  ShieldCheck
} from 'lucide-react';
import { PostStatusBadge } from '@/components/PostStatusBadge';
import { SchedulerItem, SchedulerItemType } from '@/lib/types';
import { apiClient } from '@/lib/api';
import Link from 'next/link';
import { StoryPreviewModal } from '@/components/StoryPreviewModal';
import { getValidStoryUrls } from '@/lib/storyUrlHelper';
import toast from 'react-hot-toast';

function ViewPostButton({ item }: { item: SchedulerItem }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fbUrl = item.fb_url || (item.fb_id ? `https://www.facebook.com/${item.fb_id}` : null);
  const igUrl = item.ig_url && (item.ig_url.startsWith('http://') || item.ig_url.startsWith('https://'))
    ? item.ig_url
    : null;

  const hasFb = Boolean(fbUrl && item.fb_id);
  const hasIg = Boolean(igUrl);

  if (!hasFb && !hasIg) {
    return null;
  }

  if (hasFb && hasIg) {
    return (
      <div className="relative inline-block text-left" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="px-2.5 py-1 rounded bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-800/80 text-indigo-200 font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
          title="View published post options"
        >
          <ExternalLink className="w-3 h-3 text-indigo-400" />
          <span>View Post</span>
          <ChevronDown className="w-3 h-3 text-indigo-400" />
        </button>

        {isOpen && (
          <div className="origin-top-right absolute right-0 mt-1 w-36 rounded-md shadow-2xl bg-slate-900 border border-slate-800 ring-1 ring-black ring-opacity-5 z-30">
            <div className="py-1" role="menu">
              <a
                href={fbUrl!}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setIsOpen(false)}
                className="flex items-center px-3 py-1.5 text-[11px] text-slate-200 hover:bg-slate-800 hover:text-blue-300 transition-colors"
                role="menuitem"
              >
                <span className="w-2 h-2 rounded-full bg-blue-500 mr-2 flex-shrink-0"></span>
                View on Facebook
              </a>
              <a
                href={igUrl!}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setIsOpen(false)}
                className="flex items-center px-3 py-1.5 text-[11px] text-slate-200 hover:bg-slate-800 hover:text-pink-300 transition-colors"
                role="menuitem"
              >
                <span className="w-2 h-2 rounded-full bg-pink-500 mr-2 flex-shrink-0"></span>
                View on Instagram
              </a>
            </div>
          </div>
        )}
      </div>
    );
  }

  const singleUrl = hasFb ? fbUrl! : igUrl!;
  const platformName = hasFb ? 'Facebook' : 'Instagram';
  const platformColor = hasFb ? 'text-blue-400' : 'text-pink-400';

  return (
    <a
      href={singleUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700/80 border border-slate-700 text-slate-200 font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
      title={`Open live post on ${platformName}`}
    >
      <ExternalLink className={`w-3 h-3 ${platformColor}`} />
      <span>View Post</span>
    </a>
  );
}

function StoryActionButtons({
  item,
  onOpenPreview
}: {
  item: SchedulerItem;
  onOpenPreview: () => void;
}) {
  const { fbUrl, igUrl, hasFb, hasIg } = getValidStoryUrls(item);

  return (
    <>
      <button
        type="button"
        onClick={onOpenPreview}
        className="px-2.5 py-1 rounded bg-fuchsia-950/60 hover:bg-fuchsia-900 border border-fuchsia-800/60 text-fuchsia-200 font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
        title="View internal 9:16 story preview"
      >
        <Eye className="w-3 h-3 text-fuchsia-400" />
        <span>Preview</span>
      </button>

      {hasFb && fbUrl && (
        <a
          href={fbUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-2.5 py-1 rounded bg-blue-950/80 hover:bg-blue-900 border border-blue-800/80 text-blue-300 font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
          title="Open live story on Facebook"
        >
          <ExternalLink className="w-3 h-3 text-blue-400" />
          <span>View on Facebook</span>
        </a>
      )}

      {hasIg && igUrl && (
        <a
          href={igUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-2.5 py-1 rounded bg-pink-950/80 hover:bg-pink-900 border border-pink-800/80 text-pink-300 font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
          title="Open live story on Instagram"
        >
          <ExternalLink className="w-3 h-3 text-pink-400" />
          <span>View on Instagram</span>
        </a>
      )}
    </>
  );
}

export default function PostSchedulerPage() {
  const [items, setItems] = useState<SchedulerItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  
  // Filters
  const [filterType, setFilterType] = useState<'ALL' | 'POST' | 'STORY'>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Story Preview Modal
  const [previewStory, setPreviewStory] = useState<SchedulerItem | null>(null);

  // Deletion UI State
  const [deletingItemId, setDeletingItemId] = useState<number | null>(null);
  const [deletingItemType, setDeletingItemType] = useState<SchedulerItemType | null>(null);
  const [confirmDeleteItem, setConfirmDeleteItem] = useState<SchedulerItem | null>(null);
  const [deleteStatusMessage, setDeleteStatusMessage] = useState<{
    type: 'success' | 'error';
    text: string;
    details?: any[];
  } | null>(null);

  const fetchQueue = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      // Clear legacy local storage queue if present
      try {
        localStorage.removeItem('local_posts_queue');
      } catch { }

      // Try the unified scheduler-feed endpoint first
      try {
        const res = await apiClient.get('/posts/scheduler-feed');
        if (Array.isArray(res.data)) {
          setItems(res.data);
          setIsLoading(false);
          return;
        }
      } catch (feedErr) {
        console.warn('Fallback to multi-endpoint queue fetch:', feedErr);
      }

      // Resilient fallback: Query /posts/ and /stories in parallel
      const [postsRes, storiesRes, accRes] = await Promise.all([
        apiClient.get('/posts/').catch(() => ({ data: [] })),
        apiClient.get('/stories').catch(() => ({ data: [] })),
        apiClient.get('/social-accounts/').catch(() => ({ data: [] }))
      ]);

      const userAccs = Array.isArray(accRes.data) ? accRes.data : [];
      const accMap = new Map(userAccs.map((a: any) => [a.id, a]));

      const rawPosts = Array.isArray(postsRes.data) ? postsRes.data : [];
      const rawStories = Array.isArray(storiesRes.data) ? storiesRes.data : [];

      const postItems: SchedulerItem[] = rawPosts.map((p: any) => {
        const matched = userAccs.filter((a: any) => (p.platforms || []).includes(a.platform));
        return {
          id: p.id,
          item_type: 'post',
          brand_id: p.brand_id,
          user_id: p.user_id,
          title: p.title,
          caption: p.caption,
          media_url: p.image_url,
          media_type: p.media_type || (p.image_url && p.image_url.match(/\.(mp4|mov|webm)$/i) ? 'video' : 'image'),
          thumbnail_url: p.thumbnail_url || p.image_url,
          platforms: p.platforms || [],
          target_account_ids: matched.map((a: any) => a.id),
          target_accounts: matched,
          status: p.status,
          scheduled_at: p.scheduled_at,
          published_at: p.published_at,
          retry_count: p.retry_count || 0,
          max_retries: p.max_retries || 3,
          last_error: p.last_error,
          fb_id: p.fb_post_id,
          ig_id: p.ig_media_id,
          fb_url: p.fb_post_url,
          ig_url: p.ig_media_url,
          created_at: p.created_at,
          updated_at: p.updated_at
        };
      });

      const storyItems: SchedulerItem[] = rawStories.map((s: any) => {
        const targets = s.target_account_ids || [];
        const matched = targets.map((id: number) => accMap.get(id)).filter(Boolean);
        return {
          id: s.id,
          item_type: 'story',
          brand_id: s.brand_id,
          user_id: s.user_id,
          title: s.title,
          caption: s.caption,
          media_url: s.media_url,
          media_type: s.media_type,
          thumbnail_url: s.thumbnail_url || s.media_url,
          platforms: s.platforms || [],
          target_account_ids: targets,
          target_accounts: matched,
          status: s.status,
          scheduled_at: s.scheduled_at,
          published_at: s.published_at,
          retry_count: s.retry_count || 0,
          max_retries: s.max_retries || 3,
          last_error: s.last_error,
          fb_id: s.fb_story_id,
          ig_id: s.ig_story_id,
          fb_url: s.fb_story_id ? `https://www.facebook.com/${s.fb_story_id}` : null,
          ig_url: s.ig_story_id ? 'https://www.instagram.com/stories/' : null,
          created_at: s.created_at,
          updated_at: s.updated_at
        };
      });

      const combined = [...postItems, ...storyItems];
      combined.sort((a, b) => {
        const dateA = new Date(a.scheduled_at || a.published_at || a.created_at).getTime();
        const dateB = new Date(b.scheduled_at || b.published_at || b.created_at).getTime();
        return dateB - dateA;
      });

      setItems(combined);
    } catch (e: any) {
      setItems([]);
      setFetchError(e.response?.data?.detail || e.message || 'Failed to load scheduler feed.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  // Filter items
  const filteredItems = items.filter((item) => {
    // Type filter
    if (filterType === 'POST' && item.item_type !== 'post') return false;
    if (filterType === 'STORY' && item.item_type !== 'story') return false;

    // Status filter
    if (filterStatus !== 'ALL' && item.status !== filterStatus) return false;

    return true;
  });

  // Action handlers
  const handleRetryItem = async (itemId: number, itemType: SchedulerItemType) => {
    try {
      if (itemType === 'story') {
        await apiClient.post(`/stories/${itemId}/retry`);
        toast.success(`Retrying Story #${itemId}...`);
      } else {
        await apiClient.post(`/posts/${itemId}/retry`);
        toast.success(`Retrying Post #${itemId}...`);
      }
      await fetchQueue();
    } catch (e: any) {
      const err = e.response?.data?.detail || e.message || 'Retry failed';
      toast.error(err);
      await fetchQueue();
    }
  };

  const handlePublishNowItem = async (itemId: number, itemType: SchedulerItemType) => {
    try {
      if (itemType === 'story') {
        await apiClient.post(`/stories/${itemId}/publish-now`);
        toast.success(`Publishing Story #${itemId}...`);
      } else {
        await apiClient.post(`/posts/${itemId}/publish-now`);
        toast.success(`Publishing Post #${itemId}...`);
      }
      await fetchQueue();
    } catch (e: any) {
      const err = e.response?.data?.detail || e.message || 'Publishing failed';
      toast.error(err);
      await fetchQueue();
    }
  };

  const handleDeleteItem = async (item: SchedulerItem) => {
    setDeletingItemId(item.id);
    setDeletingItemType(item.item_type);
    setDeleteStatusMessage(null);
    try {
      if (item.item_type === 'story') {
        const res = await apiClient.delete(`/stories/${item.id}`);
        const data = res.data;
        if (data && data.success === true) {
          await fetchQueue();
          setDeleteStatusMessage({
            type: 'success',
            text: data.message || `Story #${item.id} deleted successfully.`,
          });
          setConfirmDeleteItem(null);
          toast.success(`Story #${item.id} deleted successfully.`);
        } else {
          setDeleteStatusMessage({
            type: 'error',
            text: data?.message || 'Story deletion failed.',
            details: data?.details || [],
          });
        }
      } else {
        const res = await apiClient.delete(`/posts/${item.id}`);
        const data = res.data;
        if (data && data.success === true) {
          await fetchQueue();
          setDeleteStatusMessage({
            type: 'success',
            text: data.message || `Post #${item.id} and external targets deleted successfully.`,
          });
          setConfirmDeleteItem(null);
          toast.success(`Post #${item.id} deleted successfully.`);
        } else {
          setDeleteStatusMessage({
            type: 'error',
            text: data?.message || 'Deletion failed for one or more external targets.',
            details: data?.details || [],
          });
        }
      }
    } catch (e: any) {
      const errorMsg = e.response?.data?.detail || e.message || 'Failed to delete item.';
      setDeleteStatusMessage({
        type: 'error',
        text: `Deletion request failed: ${errorMsg}`,
      });
      toast.error(errorMsg);
    } finally {
      setDeletingItemId(null);
      setDeletingItemType(null);
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

  const postCount = items.filter(i => i.item_type === 'post').length;
  const storyCount = items.filter(i => i.item_type === 'story').length;

  return (
    <div className="space-y-5 select-none font-sans text-xs">
      {/* Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/60">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
              <CalendarIcon className="w-5 h-5 text-indigo-400" />
              <span>Unified Content Scheduler</span>
            </h1>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-slate-900/60 text-slate-400 border border-slate-800">
              Timezone: {userTimeZone}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Manage, preview, and schedule feed Posts and 24-hour Stories across Facebook & Instagram with isolated account targeting.
          </p>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <Link
            href="/studio?tab=stories"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 text-white font-bold text-[11px] transition shadow-md shadow-fuchsia-900/20"
          >
            <Sparkles className="w-3.5 h-3.5 text-fuchsia-300" />
            <span>+ Create Story</span>
          </Link>
          <Link
            href="/studio"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>+ Create Post</span>
          </Link>
        </div>
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

      {/* Unified Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
        
        {/* Type Filter: ALL vs POST vs STORY */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1 flex items-center space-x-1">
            <Layers className="w-3 h-3 text-indigo-400" />
            <span>Type:</span>
          </span>
          <button
            onClick={() => setFilterType('ALL')}
            className={`px-3 py-1 rounded-lg text-[11px] font-bold transition ${
              filterType === 'ALL'
                ? 'bg-slate-800 text-white border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Content ({items.length})
          </button>
          <button
            onClick={() => setFilterType('POST')}
            className={`px-3 py-1 rounded-lg text-[11px] font-bold transition flex items-center space-x-1 ${
              filterType === 'POST'
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 shadow-sm'
                : 'text-slate-400 hover:text-indigo-300'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mr-1" />
            <span>Posts ({postCount})</span>
          </button>
          <button
            onClick={() => setFilterType('STORY')}
            className={`px-3 py-1 rounded-lg text-[11px] font-bold transition flex items-center space-x-1.5 ${
              filterType === 'STORY'
                ? 'bg-fuchsia-600/30 text-fuchsia-300 border border-fuchsia-500/40 shadow-sm'
                : 'text-slate-400 hover:text-fuchsia-300'
            }`}
          >
            <Sparkles className="w-3 h-3 text-fuchsia-400" />
            <span>Stories ({storyCount})</span>
          </button>
        </div>

        {/* Status Filter */}
        <div className="flex items-center space-x-1.5 overflow-x-auto">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1 flex items-center space-x-1 flex-shrink-0">
            <Filter className="w-3 h-3 text-slate-400" />
            <span>Status:</span>
          </span>
          {['ALL', 'SCHEDULED', 'PUBLISHED', 'FAILED', 'DRAFT'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-semibold transition flex-shrink-0 ${
                filterStatus === st
                  ? 'bg-slate-800 text-slate-100 border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Enterprise Single Surface Queue Table */}
      <div className="linear-panel rounded-xl overflow-hidden border border-slate-800/80 shadow-xl bg-slate-950/40">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-3 w-44">Type & Media Preview</th>
                <th className="p-3">Title & Content Summary</th>
                <th className="p-3">Target Accounts & Platforms</th>
                <th className="p-3">Status</th>
                <th className="p-3">Scheduled / Published ({userTimeZone})</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                      <span className="text-xs font-semibold">Loading content scheduler queue...</span>
                    </div>
                  </td>
                </tr>
              ) : fetchError ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-rose-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <AlertTriangle className="w-6 h-6 text-rose-400" />
                      <span className="text-xs font-semibold">{fetchError}</span>
                    </div>
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <CalendarIcon className="w-8 h-8 text-slate-600" />
                      <span className="text-sm font-semibold text-slate-300">No items in scheduler queue</span>
                      <p className="text-xs text-slate-500 max-w-sm">
                        {filterType !== 'ALL' || filterStatus !== 'ALL'
                          ? `No items match the active filters (${filterType} • ${filterStatus}).`
                          : 'Your content scheduler queue is empty. Click "+ Create Post" or "+ Create Story" to start.'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const isStory = item.item_type === 'story';
                  const isVideo = item.media_type === 'video' || (item.media_url && Boolean(item.media_url.match(/\.(mp4|mov|webm)$/i)));

                  return (
                    <tr key={`${item.item_type}-${item.id}`} className="hover:bg-slate-800/30 transition-colors duration-150">
                      
                      {/* Column 1: Type & Visual (9:16 for Story, 1:1 for Post) */}
                      <td className="p-3">
                        <div className="flex items-center space-x-3">
                          {/* Distinct Visual Thumbnail */}
                          {isStory ? (
                            <div
                              onClick={() => setPreviewStory(item)}
                              className="relative w-10 h-[70px] rounded-lg overflow-hidden border border-fuchsia-500/40 bg-black flex-shrink-0 cursor-pointer group shadow-sm hover:border-fuchsia-400 transition"
                              title="Click to view 9:16 Story Preview"
                            >
                              {item.media_url ? (
                                isVideo ? (
                                  <div className="w-full h-full relative flex items-center justify-center bg-slate-900">
                                    <video src={item.media_url} className="w-full h-full object-cover" />
                                    <div className="absolute inset-0 bg-black/30 flex items-center justify-center group-hover:bg-black/10 transition">
                                      <Film className="w-3.5 h-3.5 text-fuchsia-300 drop-shadow" />
                                    </div>
                                  </div>
                                ) : (
                                  <img
                                    src={item.media_url}
                                    alt={item.title || 'Story Visual'}
                                    className="w-full h-full object-cover group-hover:scale-105 transition duration-200"
                                  />
                                )
                              ) : (
                                <div className="w-full h-full bg-slate-900 flex items-center justify-center text-fuchsia-400">
                                  <Sparkles className="w-4 h-4" />
                                </div>
                              )}
                              <div className="absolute top-0.5 right-0.5 bg-black/70 rounded p-0.5 text-[8px] text-fuchsia-300 font-mono">
                                9:16
                              </div>
                            </div>
                          ) : (
                            <div className="relative w-11 h-11 rounded-lg overflow-hidden border border-slate-700 bg-slate-900 flex items-center justify-center flex-shrink-0">
                              {item.media_url ? (
                                <img
                                  src={item.media_url}
                                  alt={item.title || 'Post thumbnail'}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="text-slate-400 text-xs">📝</div>
                              )}
                            </div>
                          )}

                          {/* Explicit Type Badge */}
                          <div className="flex flex-col space-y-1">
                            {isStory ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-gradient-to-r from-fuchsia-600/30 to-violet-600/30 border border-fuchsia-500/40 text-fuchsia-300 text-[10px] font-extrabold uppercase tracking-wider w-fit">
                                <Sparkles className="w-2.5 h-2.5 text-fuchsia-400" />
                                <span>STORY</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 text-[10px] font-extrabold uppercase tracking-wider w-fit">
                                <span>POST</span>
                              </span>
                            )}
                            <span className="text-[10px] font-mono text-slate-400 font-bold">#{item.id}</span>
                          </div>
                        </div>
                      </td>

                      {/* Column 2: Title & Summary */}
                      <td className="p-3 max-w-xs sm:max-w-sm">
                        <h4 className="font-semibold text-slate-100 text-xs truncate flex items-center space-x-1.5">
                          <span>{item.title || (item.caption && item.caption.trim() ? item.caption.slice(0, 40) + '...' : isStory ? '24-Hour Story' : 'Untitled Post')}</span>
                        </h4>
                        <p className="text-slate-400 text-[11px] truncate mt-0.5">
                          {item.caption || (isStory ? `Story Media Asset (${item.media_type || 'image'})` : 'No caption')}
                        </p>
                        {(item.fb_id || item.ig_id) && (
                          <div className="flex items-center space-x-2 mt-1 text-[9px] font-mono text-indigo-400/90">
                            {item.fb_id && <span>FB: {item.fb_id}</span>}
                            {item.ig_id && <span>IG: {item.ig_id}</span>}
                          </div>
                        )}
                      </td>

                      {/* Column 3: Targets & Platforms */}
                      <td className="p-3">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-1.5 flex-wrap gap-1">
                            {item.platforms.includes('facebook') && (
                              <span className="px-1.5 py-0.5 rounded bg-blue-950/60 border border-blue-800/60 text-blue-300 text-[9px] font-mono font-medium">
                                FB Page
                              </span>
                            )}
                            {item.platforms.includes('instagram') && (
                              <span className="px-1.5 py-0.5 rounded bg-pink-950/60 border border-pink-800/60 text-pink-300 text-[9px] font-mono font-medium">
                                IG Biz
                              </span>
                            )}
                          </div>
                          {isStory && item.target_account_ids && item.target_account_ids.length > 0 && (
                            <p className="text-[9px] text-slate-500 font-mono flex items-center space-x-1">
                              <ShieldCheck className="w-2.5 h-2.5 text-emerald-400" />
                              <span>{item.target_account_ids.length} targeted {item.target_account_ids.length === 1 ? 'account' : 'accounts'}</span>
                            </p>
                          )}
                        </div>
                      </td>

                      {/* Column 4: Status */}
                      <td className="p-3">
                        <PostStatusBadge status={item.status} />
                      </td>

                      {/* Column 5: Scheduled / Published */}
                      <td className="p-3 text-slate-300 font-mono text-[11px]">
                        {item.published_at ? (
                          <span className="text-indigo-300 flex items-center space-x-1">
                            <CheckCircle className="w-3 h-3 text-indigo-400 inline" />
                            <span>{formatToLocalDateTime(item.published_at)}</span>
                          </span>
                        ) : item.scheduled_at ? (
                          <span className="text-sky-300 flex items-center space-x-1">
                            <Clock className="w-3 h-3 text-sky-400 inline" />
                            <span>{formatToLocalDateTime(item.scheduled_at)}</span>
                          </span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>

                      {/* Column 6: Actions */}
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          {isStory ? (
                            <StoryActionButtons
                              item={item}
                              onOpenPreview={() => setPreviewStory(item)}
                            />
                          ) : (
                            <ViewPostButton item={item} />
                          )}

                          {item.status === 'FAILED' ? (
                            <button
                              onClick={() => handleRetryItem(item.id, item.item_type)}
                              className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
                            >
                              <RefreshCw className="w-3 h-3" />
                              <span>Retry</span>
                            </button>
                          ) : item.status === 'APPROVED' || item.status === 'DRAFT' ? (
                            <button
                              onClick={() => handlePublishNowItem(item.id, item.item_type)}
                              className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[10px] transition flex items-center space-x-1 focus-ring"
                            >
                              <Send className="w-3 h-3" />
                              <span>Publish</span>
                            </button>
                          ) : null}

                          <button
                            disabled={deletingItemId === item.id && deletingItemType === item.item_type}
                            onClick={() => {
                              setDeleteStatusMessage(null);
                              setConfirmDeleteItem(item);
                            }}
                            className="px-2 py-1 rounded bg-slate-900 hover:bg-rose-950/60 border border-slate-800 hover:border-rose-800/60 text-slate-400 hover:text-rose-300 font-semibold text-[10px] transition flex items-center space-x-1 disabled:opacity-50 disabled:cursor-not-allowed"
                            title={isStory ? 'Delete / cancel story' : 'Delete post'}
                          >
                            {deletingItemId === item.id && deletingItemType === item.item_type ? (
                              <Loader2 className="w-3 h-3 animate-spin text-rose-400" />
                            ) : (
                              <Trash2 className="w-3 h-3" />
                            )}
                            <span>{item.status === 'SCHEDULED' ? 'Cancel' : 'Delete'}</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Story 9:16 Interactive Preview Modal */}
      <StoryPreviewModal
        item={previewStory}
        isOpen={Boolean(previewStory)}
        onClose={() => setPreviewStory(null)}
        userTimeZone={userTimeZone}
        onRetry={async (id) => handleRetryItem(id, 'story')}
        onPublishNow={async (id) => handlePublishNowItem(id, 'story')}
        onDelete={(item) => setConfirmDeleteItem(item)}
      />

      {/* Confirmation & Deletion Dialog Modal */}
      {confirmDeleteItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2 text-rose-400">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <h3 className="text-sm font-bold text-slate-100">
                  {confirmDeleteItem.status === 'SCHEDULED' ? 'Cancel Scheduled' : 'Delete'} {confirmDeleteItem.item_type === 'story' ? 'Story' : 'Post'} #{confirmDeleteItem.id}
                </h3>
              </div>
              <button
                disabled={deletingItemId !== null}
                onClick={() => setConfirmDeleteItem(null)}
                className="text-slate-500 hover:text-slate-300 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-300">
              <p className="font-medium text-slate-200">
                Are you sure you want to {confirmDeleteItem.status === 'SCHEDULED' ? 'cancel and delete' : 'delete'} this {confirmDeleteItem.item_type === 'story' ? 'Story' : 'Post'}?
              </p>

              {confirmDeleteItem.item_type === 'story' ? (
                confirmDeleteItem.status === 'SCHEDULED' ? (
                  <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-200 text-[11px] space-y-1">
                    <p className="font-bold">🕒 Scheduled Story Cancellation</p>
                    <p>Deleting this record will safely cancel scheduled publication and prevent any Meta API calls.</p>
                  </div>
                ) : confirmDeleteItem.status === 'PUBLISHED' || Boolean(confirmDeleteItem.fb_id || confirmDeleteItem.ig_id) ? (
                  <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200 space-y-2 text-[11px]">
                    <p className="font-bold flex items-center space-x-1 text-rose-300">
                      <span>⚠️ External Platform Story Removal</span>
                    </p>
                    <p>This will attempt to remove the Story from the connected platforms:</p>
                    
                    <div className="space-y-1 pl-1 font-mono text-[11px]">
                      {confirmDeleteItem.fb_id ? (
                        <div className="text-emerald-400 flex items-center space-x-1.5">
                          <span>✓</span>
                          <span className="text-slate-200">Facebook Page</span>
                          <span className="text-[10px] text-slate-400">({confirmDeleteItem.fb_id})</span>
                        </div>
                      ) : (confirmDeleteItem.platforms || []).includes('facebook') ? (
                        <div className="text-rose-400 flex items-center space-x-1.5">
                          <span>✕</span>
                          <span className="text-slate-400">Facebook Page (not published)</span>
                        </div>
                      ) : null}

                      {confirmDeleteItem.ig_id ? (
                        <div className="text-emerald-400 flex items-center space-x-1.5">
                          <span>✓</span>
                          <span className="text-slate-200">Instagram Business</span>
                          <span className="text-[10px] text-slate-400">({confirmDeleteItem.ig_id})</span>
                        </div>
                      ) : (confirmDeleteItem.platforms || []).includes('instagram') ? (
                        <div className="text-rose-400 flex items-center space-x-1.5">
                          <span>✕</span>
                          <span className="text-slate-400">Instagram Business (not published)</span>
                        </div>
                      ) : null}
                    </div>

                    {((!confirmDeleteItem.fb_id && (confirmDeleteItem.platforms || []).includes('facebook')) ||
                      (!confirmDeleteItem.ig_id && (confirmDeleteItem.platforms || []).includes('instagram'))) && (
                      <p className="text-[10px] text-amber-300">
                        Only successfully published platforms will be affected by deletion.
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-300 text-[11px] space-y-1">
                    <p className="font-bold text-slate-200">ℹ️ Story Record Removal</p>
                    <p>Deleting this record will remove it from your scheduler queue.</p>
                  </div>
                )
              ) : (
                confirmDeleteItem.status === 'PUBLISHED' ? (
                  <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200 space-y-1 text-[11px]">
                    <p className="font-bold flex items-center space-x-1 text-rose-300">
                      <span>⚠️ External Platform Removal Warning</span>
                    </p>
                    <p>
                      This post has been published. Deleting it will attempt to remove the published media directly from connected social platforms (Facebook / Instagram).
                    </p>
                  </div>
                ) : confirmDeleteItem.status === 'SCHEDULED' ? (
                  <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-200 text-[11px]">
                    <span>🕒 Deleting this post will safely cancel its scheduled execution and remove it.</span>
                  </div>
                ) : null
              )}
            </div>

            {/* Error message inside modal */}
            {deleteStatusMessage && deleteStatusMessage.type === 'error' && (
              <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 text-rose-200 text-[11px] space-y-1">
                <p className="font-bold text-rose-300">{deleteStatusMessage.text}</p>
                {deleteStatusMessage.details && deleteStatusMessage.details.length > 0 && (
                  <ul className="list-disc pl-4 space-y-0.5 text-[10px]">
                    {deleteStatusMessage.details.map((d: any, idx: number) => (
                      <li key={idx}>
                        {d.platform} ({d.external_story_id || d.external_post_id}): {d.error || (d.success ? 'Deleted' : 'Failed')}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                disabled={deletingItemId !== null}
                onClick={() => setConfirmDeleteItem(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletingItemId !== null}
                onClick={() => handleDeleteItem(confirmDeleteItem)}
                className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-rose-900/40 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deletingItemId === confirmDeleteItem.id && deletingItemType === confirmDeleteItem.item_type ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Confirm {confirmDeleteItem.status === 'SCHEDULED' ? 'Cancel' : 'Delete'}</span>
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
