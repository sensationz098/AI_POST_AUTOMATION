'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
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
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Film,
  Image as ImageIcon,
  Eye,
  Layers,
  ShieldCheck,
  List,
  LayoutGrid,
  CalendarDays,
  ArrowRight,
  Globe
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
          className="px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/80 dark:hover:bg-indigo-900 border border-indigo-200 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-200 font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
          title="View published post options"
        >
          <ExternalLink className="w-3 h-3 text-indigo-500 dark:text-indigo-400" />
          <span>View Post</span>
          <ChevronDown className="w-3 h-3 text-indigo-500 dark:text-indigo-400" />
        </button>

        {isOpen && (
          <div className="origin-top-right absolute right-0 mt-1 w-40 rounded-xl shadow-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 ring-1 ring-black/5 z-30 p-1">
            <div className="space-y-0.5" role="menu">
              <a
                href={fbUrl!}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setIsOpen(false)}
                className="flex items-center px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-blue-600 dark:hover:text-blue-300 rounded-lg transition-colors"
                role="menuitem"
              >
                <span className="w-2 h-2 rounded-full bg-blue-500 mr-2 flex-shrink-0" />
                <span>Facebook Page</span>
              </a>
              <a
                href={igUrl!}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setIsOpen(false)}
                className="flex items-center px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-pink-600 dark:hover:text-pink-300 rounded-lg transition-colors"
                role="menuitem"
              >
                <span className="w-2 h-2 rounded-full bg-pink-500 mr-2 flex-shrink-0" />
                <span>Instagram Feed</span>
              </a>
            </div>
          </div>
        )}
      </div>
    );
  }

  const singleUrl = hasFb ? fbUrl! : igUrl!;
  const platformName = hasFb ? 'Facebook' : 'Instagram';
  const platformColor = hasFb ? 'text-blue-500 dark:text-blue-400' : 'text-pink-500 dark:text-pink-400';

  return (
    <a
      href={singleUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700/80 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
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
        className="px-2.5 py-1 rounded-lg bg-fuchsia-50 hover:bg-fuchsia-100 dark:bg-fuchsia-950/60 dark:hover:bg-fuchsia-900 border border-fuchsia-200 dark:border-fuchsia-800/60 text-fuchsia-700 dark:text-fuchsia-200 font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
        title="View internal 9:16 story preview"
      >
        <Eye className="w-3 h-3 text-fuchsia-500 dark:text-fuchsia-400" />
        <span>Preview</span>
      </button>

      {hasFb && fbUrl && (
        <a
          href={fbUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/80 dark:hover:bg-blue-900 border border-blue-200 dark:border-blue-800/80 text-blue-700 dark:text-blue-300 font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
          title="Open live story on Facebook"
        >
          <ExternalLink className="w-3 h-3 text-blue-500 dark:text-blue-400" />
          <span>Facebook</span>
        </a>
      )}

      {hasIg && igUrl && (
        <a
          href={igUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-2.5 py-1 rounded-lg bg-pink-50 hover:bg-pink-100 dark:bg-pink-950/80 dark:hover:bg-pink-900 border border-pink-200 dark:border-pink-800/80 text-pink-700 dark:text-pink-300 font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
          title="Open live story on Instagram"
        >
          <ExternalLink className="w-3 h-3 text-pink-500 dark:text-pink-400" />
          <span>Instagram</span>
        </a>
      )}
    </>
  );
}

export default function PostSchedulerPage() {
  const [items, setItems] = useState<SchedulerItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  
  // View mode: Month Calendar vs Detailed Queue List
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');

  // Calendar period state
  const [currentMonthDate, setCurrentMonthDate] = useState<Date>(() => new Date());

  // Filters
  const [filterType, setFilterType] = useState<'ALL' | 'POST' | 'STORY'>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Modals & Selected details
  const [previewStory, setPreviewStory] = useState<SchedulerItem | null>(null);
  const [selectedPostItem, setSelectedPostItem] = useState<SchedulerItem | null>(null);

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
      try {
        localStorage.removeItem('local_posts_queue');
      } catch { }

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
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (filterType === 'POST' && item.item_type !== 'post') return false;
      if (filterType === 'STORY' && item.item_type !== 'story') return false;
      if (filterStatus !== 'ALL' && item.status !== filterStatus) return false;
      return true;
    });
  }, [items, filterType, filterStatus]);

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
          if (selectedPostItem?.id === item.id) setSelectedPostItem(null);
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
          if (selectedPostItem?.id === item.id) setSelectedPostItem(null);
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

  const formatShortTime = (dateStr?: string) => {
    if (!dateStr) return '';
    const normalizedStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
    const date = new Date(normalizedStr);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  const getDateKey = (date: Date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  const getItemDateKey = (dateStr?: string) => {
    if (!dateStr) return null;
    const normalized = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return null;
    return getDateKey(d);
  };

  // Calendar navigation
  const handlePrevMonth = () => {
    setCurrentMonthDate((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonthDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const handleToday = () => {
    setCurrentMonthDate(new Date());
  };

  // Calendar Grid Generation
  const { calendarGrid, monthLabel, todayKey } = useMemo(() => {
    const year = currentMonthDate.getFullYear();
    const month = currentMonthDate.getMonth();
    const todayStr = getDateKey(new Date());

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const totalDays = lastDay.getDate();

    // Monday as 0: (firstDay.getDay() + 6) % 7
    const startDayIndex = (firstDay.getDay() + 6) % 7;

    const prevMonthLastDay = new Date(year, month, 0).getDate();

    // Build day items map from filtered items
    const itemsByDate: Record<string, SchedulerItem[]> = {};
    for (const item of filteredItems) {
      const dateKey = getItemDateKey(item.scheduled_at || item.published_at || item.created_at);
      if (dateKey) {
        if (!itemsByDate[dateKey]) itemsByDate[dateKey] = [];
        itemsByDate[dateKey].push(item);
      }
    }

    interface CalendarDayCell {
      date: Date;
      dateKey: string;
      dayNumber: number;
      isCurrentMonth: boolean;
      isToday: boolean;
      items: SchedulerItem[];
    }

    const grid: CalendarDayCell[] = [];

    // Leading days from prev month
    for (let i = startDayIndex - 1; i >= 0; i--) {
      const prevDate = new Date(year, month - 1, prevMonthLastDay - i);
      const key = getDateKey(prevDate);
      grid.push({
        date: prevDate,
        dateKey: key,
        dayNumber: prevMonthLastDay - i,
        isCurrentMonth: false,
        isToday: key === todayStr,
        items: itemsByDate[key] || [],
      });
    }

    // Current month days
    for (let d = 1; d <= totalDays; d++) {
      const curDate = new Date(year, month, d);
      const key = getDateKey(curDate);
      grid.push({
        date: curDate,
        dateKey: key,
        dayNumber: d,
        isCurrentMonth: true,
        isToday: key === todayStr,
        items: itemsByDate[key] || [],
      });
    }

    // Trailing days from next month to complete 35 or 42 slots
    const totalSlots = grid.length > 35 ? 42 : 35;
    const remaining = totalSlots - grid.length;
    for (let d = 1; d <= remaining; d++) {
      const nextDate = new Date(year, month + 1, d);
      const key = getDateKey(nextDate);
      grid.push({
        date: nextDate,
        dateKey: key,
        dayNumber: d,
        isCurrentMonth: false,
        isToday: key === todayStr,
        items: itemsByDate[key] || [],
      });
    }

    const formattedMonth = currentMonthDate.toLocaleDateString(undefined, {
      month: 'long',
      year: 'numeric',
    });

    return {
      calendarGrid: grid,
      monthLabel: formattedMonth,
      todayKey: todayStr,
    };
  }, [currentMonthDate, filteredItems]);

  const postCount = items.filter(i => i.item_type === 'post').length;
  const storyCount = items.filter(i => i.item_type === 'story').length;

  return (
    <div className="space-y-5 select-none font-sans text-xs">
      {/* ── Page Header ────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              Content Calendar
            </h1>
            <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700/80">
              {userTimeZone}
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Plan, schedule, and review social media feed posts and 24-hour stories.
          </p>
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          <button
            onClick={handleToday}
            className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-semibold text-xs transition shadow-xs"
          >
            Today
          </button>
          <Link
            href="/studio?tab=stories"
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-fuchsia-600 hover:bg-fuchsia-700 text-white font-semibold text-xs transition shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-fuchsia-200" />
            <span>+ Create Story</span>
          </Link>
          <Link
            href="/studio"
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>+ Create Post</span>
          </Link>
        </div>
      </div>

      {/* ── Status Message Alert ──────────────────────────────────────── */}
      {deleteStatusMessage && deleteStatusMessage.type === 'success' && (
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-200 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            <span className="font-medium">{deleteStatusMessage.text}</span>
          </div>
          <button
            onClick={() => setDeleteStatusMessage(null)}
            className="text-emerald-600 hover:text-emerald-800 dark:text-emerald-400 dark:hover:text-emerald-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── Calendar Toolbar & Unified Filters ────────────────────────── */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Left: Navigation (Prev, Month Title, Next) */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800/60 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700/60">
            <button
              onClick={handlePrevMonth}
              className="p-1.5 rounded-md text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
              title="Previous Month"
              aria-label="Previous Month"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleNextMonth}
              className="p-1.5 rounded-md text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
              title="Next Month"
              aria-label="Next Month"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 min-w-[160px]">
            {monthLabel}
          </h2>

          <button
            onClick={fetchQueue}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 transition"
            title="Refresh schedule feed"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
        </div>

        {/* Center: Type & Status Filters */}
        <div className="flex items-center space-x-2 flex-wrap gap-y-2">
          {/* Type Filter */}
          <div className="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800/60 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700/60">
            <button
              onClick={() => setFilterType('ALL')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                filterType === 'ALL'
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              All ({items.length})
            </button>
            <button
              onClick={() => setFilterType('POST')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition flex items-center space-x-1 ${
                filterType === 'POST'
                  ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-indigo-600'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              <span>Posts ({postCount})</span>
            </button>
            <button
              onClick={() => setFilterType('STORY')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition flex items-center space-x-1 ${
                filterType === 'STORY'
                  ? 'bg-white dark:bg-slate-700 text-fuchsia-600 dark:text-fuchsia-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-fuchsia-600'
              }`}
            >
              <Sparkles className="w-3 h-3 text-fuchsia-500" />
              <span>Stories ({storyCount})</span>
            </button>
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-1">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-lg px-2.5 py-1 text-[11px] font-medium focus:outline-none cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="PUBLISHED">Published</option>
              <option value="DRAFT">Draft</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>

        {/* Right: View Switcher (Month Calendar vs List) */}
        <div className="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800/60 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700/60 self-start md:self-auto">
          <button
            onClick={() => setViewMode('calendar')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition flex items-center space-x-1.5 ${
              viewMode === 'calendar'
                ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            <CalendarDays className="w-3.5 h-3.5" />
            <span>Calendar</span>
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition flex items-center space-x-1.5 ${
              viewMode === 'list'
                ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            <List className="w-3.5 h-3.5" />
            <span>List View</span>
          </button>
        </div>
      </div>

      {/* ── Error Banner ──────────────────────────────────────────────── */}
      {fetchError && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 flex items-center justify-between shadow-xs">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span className="text-xs font-semibold">{fetchError}</span>
          </div>
          <button
            onClick={fetchQueue}
            className="px-3 py-1 rounded-lg bg-rose-600 text-white font-semibold text-xs hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── View 1: Month Calendar View ───────────────────────────────── */}
      {viewMode === 'calendar' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          {/* Weekday Row */}
          <div className="grid grid-cols-7 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/90 text-center text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider py-2.5">
            <div>Mon</div>
            <div>Tue</div>
            <div>Wed</div>
            <div>Thu</div>
            <div>Fri</div>
            <div>Sat</div>
            <div>Sun</div>
          </div>

          {/* Calendar Day Grid */}
          {isLoading ? (
            <div className="grid grid-cols-7 divide-x divide-y divide-slate-100 dark:divide-slate-800/60">
              {Array.from({ length: 35 }).map((_, i) => (
                <div key={i} className="min-h-[105px] p-2 space-y-1.5 animate-pulse">
                  <div className="w-5 h-5 rounded-full bg-slate-200 dark:bg-slate-800" />
                  <div className="h-6 rounded bg-slate-100 dark:bg-slate-800/60 w-full" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-7 divide-x divide-y divide-slate-200/70 dark:divide-slate-800/80">
              {calendarGrid.map((cell) => {
                return (
                  <div
                    key={cell.dateKey}
                    className={`min-h-[110px] p-1.5 sm:p-2 flex flex-col justify-between transition-colors ${
                      cell.isCurrentMonth
                        ? 'bg-white dark:bg-slate-900/90'
                        : 'bg-slate-50/70 dark:bg-slate-950/40 text-slate-400 dark:text-slate-600'
                    } ${cell.isToday ? 'ring-1 ring-inset ring-indigo-500/40' : ''}`}
                  >
                    {/* Top: Day Number & Today indicator */}
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-xs font-semibold inline-flex items-center justify-center w-6 h-6 rounded-full ${
                          cell.isToday
                            ? 'bg-indigo-600 text-white font-bold shadow-xs'
                            : cell.isCurrentMonth
                            ? 'text-slate-800 dark:text-slate-200'
                            : 'text-slate-400 dark:text-slate-600'
                        }`}
                      >
                        {cell.dayNumber}
                      </span>

                      {cell.items.length > 0 && (
                        <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 font-medium">
                          {cell.items.length} {cell.items.length === 1 ? 'item' : 'items'}
                        </span>
                      )}
                    </div>

                    {/* Middle: Content items in this day */}
                    <div className="space-y-1 mt-1 flex-1">
                      {cell.items.slice(0, 2).map((item) => {
                        const isStory = item.item_type === 'story';
                        const timeStr = formatShortTime(item.scheduled_at || item.published_at || item.created_at);
                        const isFb = item.platforms.includes('facebook');
                        const isIg = item.platforms.includes('instagram');

                        return (
                          <div
                            key={`${item.item_type}-${item.id}`}
                            onClick={() => {
                              if (isStory) setPreviewStory(item);
                              else setSelectedPostItem(item);
                            }}
                            className={`p-1.5 rounded-lg border text-[11px] cursor-pointer transition-all hover:scale-[1.02] shadow-xs flex items-center space-x-1.5 ${
                              isStory
                                ? 'bg-fuchsia-50/80 dark:bg-fuchsia-950/40 border-fuchsia-200 dark:border-fuchsia-800/60 text-fuchsia-900 dark:text-fuchsia-200'
                                : 'bg-slate-50 dark:bg-slate-800/70 border-slate-200 dark:border-slate-700/80 text-slate-900 dark:text-slate-100'
                            }`}
                            title={`${item.title || item.caption || 'Scheduled item'} — Click to view details`}
                          >
                            {/* Platform dot / indicator */}
                            <div className="flex items-center -space-x-1 flex-shrink-0">
                              {isFb && <span className="w-2 h-2 rounded-full bg-blue-500 border border-white dark:border-slate-900" />}
                              {isIg && <span className="w-2 h-2 rounded-full bg-pink-500 border border-white dark:border-slate-900" />}
                              {!isFb && !isIg && <span className="w-2 h-2 rounded-full bg-indigo-500" />}
                            </div>

                            {/* Title / Caption truncated */}
                            <span className="truncate font-medium flex-1">
                              {item.title || item.caption || (isStory ? 'Story Asset' : 'Feed Post')}
                            </span>

                            {/* Time badge */}
                            {timeStr && (
                              <span className="text-[9px] font-mono text-slate-500 dark:text-slate-400 flex-shrink-0">
                                {timeStr}
                              </span>
                            )}
                          </div>
                        );
                      })}

                      {/* "+N more" items indicator */}
                      {cell.items.length > 2 && (
                        <button
                          onClick={() => setViewMode('list')}
                          className="w-full text-center text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline pt-0.5 block"
                        >
                          +{cell.items.length - 2} more
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty Calendar State */}
          {!isLoading && filteredItems.length === 0 && (
            <div className="py-12 px-6 text-center space-y-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20">
              <div className="w-10 h-10 rounded-xl bg-slate-200/70 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 mx-auto">
                <CalendarIcon className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Your calendar is clear
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
                  {filterType !== 'ALL' || filterStatus !== 'ALL'
                    ? `No scheduled content matches active filters (${filterType} • ${filterStatus}).`
                    : 'Schedule your first feed post or story in Creator Studio to start planning your social media schedule.'}
                </p>
              </div>
              <div className="pt-1">
                <Link
                  href="/studio"
                  className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition shadow-xs"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>+ Create Post</span>
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── View 2: Schedule Queue List View ──────────────────────────── */}
      <div className="bg-white dark:bg-slate-900 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="p-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Content Schedule Queue ({filteredItems.length})
            </h3>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {userTimeZone}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                <th className="p-3 w-40">Type & Preview</th>
                <th className="p-3">Title & Summary</th>
                <th className="p-3">Platforms</th>
                <th className="p-3">Status</th>
                <th className="p-3">Scheduled / Published</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-slate-500 dark:text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                      <span className="text-xs font-semibold">Loading content schedule queue...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-10 text-center text-slate-500 dark:text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-1.5">
                      <CalendarIcon className="w-7 h-7 text-slate-400 dark:text-slate-600" />
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">No scheduled content in queue</span>
                      <p className="text-xs text-slate-500 max-w-sm">
                        Click "+ Create Post" or "+ Create Story" to start scheduling content.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const isStory = item.item_type === 'story';
                  const isVideo = item.media_type === 'video' || (item.media_url && Boolean(item.media_url.match(/\.(mp4|mov|webm)$/i)));

                  return (
                    <tr key={`${item.item_type}-${item.id}`} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                      {/* Column 1: Type & Visual */}
                      <td className="p-3">
                        <div className="flex items-center space-x-3">
                          {isStory ? (
                            <div
                              onClick={() => setPreviewStory(item)}
                              className="relative w-10 h-[64px] rounded-lg overflow-hidden border border-fuchsia-300 dark:border-fuchsia-700/60 bg-black flex-shrink-0 cursor-pointer group shadow-xs hover:border-fuchsia-500 transition"
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
                                <div className="w-full h-full bg-slate-100 dark:bg-slate-900 flex items-center justify-center text-fuchsia-600 dark:text-fuchsia-400">
                                  <Sparkles className="w-4 h-4" />
                                </div>
                              )}
                              <div className="absolute top-0.5 right-0.5 bg-black/70 rounded p-0.5 text-[8px] text-fuchsia-300 font-mono">
                                9:16
                              </div>
                            </div>
                          ) : (
                            <div className="relative w-11 h-11 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 flex items-center justify-center flex-shrink-0">
                              {item.media_url ? (
                                <img
                                  src={item.media_url}
                                  alt={item.title || 'Post thumbnail'}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <ImageIcon className="w-4 h-4 text-slate-400" />
                              )}
                            </div>
                          )}

                          <div className="flex flex-col space-y-1">
                            {isStory ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/60 border border-fuchsia-200 dark:border-fuchsia-800/60 text-fuchsia-700 dark:text-fuchsia-300 text-[10px] font-bold uppercase tracking-wider w-fit">
                                <Sparkles className="w-2.5 h-2.5 text-fuchsia-600 dark:text-fuchsia-400" />
                                <span>Story</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/60 text-indigo-700 dark:text-indigo-300 text-[10px] font-bold uppercase tracking-wider w-fit">
                                <span>Post</span>
                              </span>
                            )}
                            <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">#{item.id}</span>
                          </div>
                        </div>
                      </td>

                      {/* Column 2: Title & Summary */}
                      <td className="p-3 max-w-xs sm:max-w-sm">
                        <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-xs truncate">
                          {item.title || (item.caption && item.caption.trim() ? item.caption.slice(0, 45) + '...' : isStory ? '24-Hour Story' : 'Untitled Post')}
                        </h4>
                        <p className="text-slate-500 dark:text-slate-400 text-[11px] truncate mt-0.5">
                          {item.caption || (isStory ? `Story Media (${item.media_type || 'image'})` : 'No caption')}
                        </p>
                        {(item.fb_id || item.ig_id) && (
                          <div className="flex items-center space-x-2 mt-1 text-[10px] font-mono text-indigo-600 dark:text-indigo-400">
                            {item.fb_id && <span>FB: {item.fb_id}</span>}
                            {item.ig_id && <span>IG: {item.ig_id}</span>}
                          </div>
                        )}
                      </td>

                      {/* Column 3: Targets & Platforms */}
                      <td className="p-3">
                        <div className="flex items-center space-x-1.5 flex-wrap gap-1">
                          {item.platforms.includes('facebook') && (
                            <span className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800/60 text-blue-700 dark:text-blue-300 text-[10px] font-semibold">
                              Facebook
                            </span>
                          )}
                          {item.platforms.includes('instagram') && (
                            <span className="px-2 py-0.5 rounded bg-pink-50 dark:bg-pink-950/60 border border-pink-200 dark:border-pink-800/60 text-pink-700 dark:text-pink-300 text-[10px] font-semibold">
                              Instagram
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Column 4: Status */}
                      <td className="p-3">
                        <PostStatusBadge status={item.status} />
                      </td>

                      {/* Column 5: Scheduled / Published */}
                      <td className="p-3 text-slate-700 dark:text-slate-300 font-mono text-[11px]">
                        {item.published_at ? (
                          <span className="text-indigo-700 dark:text-indigo-300 flex items-center space-x-1">
                            <CheckCircle className="w-3 h-3 text-indigo-600 dark:text-indigo-400 inline flex-shrink-0" />
                            <span>{formatToLocalDateTime(item.published_at)}</span>
                          </span>
                        ) : item.scheduled_at ? (
                          <span className="text-sky-700 dark:text-sky-300 flex items-center space-x-1">
                            <Clock className="w-3 h-3 text-sky-600 dark:text-sky-400 inline flex-shrink-0" />
                            <span>{formatToLocalDateTime(item.scheduled_at)}</span>
                          </span>
                        ) : (
                          <span className="text-slate-400 dark:text-slate-500">—</span>
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
                              className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
                            >
                              <RefreshCw className="w-3 h-3" />
                              <span>Retry</span>
                            </button>
                          ) : item.status === 'APPROVED' || item.status === 'DRAFT' ? (
                            <button
                              onClick={() => handlePublishNowItem(item.id, item.item_type)}
                              className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[11px] transition flex items-center space-x-1 focus-ring shadow-xs"
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
                            className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-rose-50 dark:bg-slate-800 dark:hover:bg-rose-950/60 border border-slate-200 hover:border-rose-200 dark:border-slate-700 dark:hover:border-rose-800/60 text-slate-600 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-300 font-semibold text-[11px] transition flex items-center space-x-1 shadow-xs disabled:opacity-50"
                            title={isStory ? 'Delete / cancel story' : 'Delete post'}
                          >
                            {deletingItemId === item.id && deletingItemType === item.item_type ? (
                              <Loader2 className="w-3 h-3 animate-spin text-rose-500 dark:text-rose-400" />
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

      {/* ── Post Detail Modal ─────────────────────────────────────────── */}
      {selectedPostItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/60 text-indigo-700 dark:text-indigo-300 text-xs font-bold uppercase tracking-wider">
                  Post #{selectedPostItem.id}
                </span>
                <PostStatusBadge status={selectedPostItem.status} />
              </div>
              <button
                onClick={() => setSelectedPostItem(null)}
                className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Media preview */}
            {selectedPostItem.media_url && (
              <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 max-h-56 bg-slate-950 flex items-center justify-center">
                {selectedPostItem.media_type === 'video' ? (
                  <video src={selectedPostItem.media_url} controls className="max-h-56 w-full object-contain" />
                ) : (
                  <img src={selectedPostItem.media_url} alt="Post media" className="max-h-56 w-full object-contain" />
                )}
              </div>
            )}

            <div className="space-y-2">
              <h4 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                {selectedPostItem.title || 'Untitled Post'}
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400 whitespace-pre-line leading-relaxed max-h-36 overflow-y-auto">
                {selectedPostItem.caption || 'No caption text provided.'}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
              <div className="space-y-0.5 font-mono text-[11px]">
                {selectedPostItem.scheduled_at && (
                  <p>Scheduled: {formatToLocalDateTime(selectedPostItem.scheduled_at)}</p>
                )}
                {selectedPostItem.published_at && (
                  <p className="text-indigo-600 dark:text-indigo-400 font-semibold">Published: {formatToLocalDateTime(selectedPostItem.published_at)}</p>
                )}
              </div>

              <div className="flex items-center space-x-2">
                <ViewPostButton item={selectedPostItem} />
                <button
                  onClick={() => {
                    setConfirmDeleteItem(selectedPostItem);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/50 dark:hover:bg-rose-900 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold transition"
                >
                  {selectedPostItem.status === 'SCHEDULED' ? 'Cancel' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Story 9:16 Interactive Preview Modal ──────────────────────── */}
      <StoryPreviewModal
        item={previewStory}
        isOpen={Boolean(previewStory)}
        onClose={() => setPreviewStory(null)}
        userTimeZone={userTimeZone}
        onRetry={async (id) => handleRetryItem(id, 'story')}
        onPublishNow={async (id) => handlePublishNowItem(id, 'story')}
        onDelete={(item) => setConfirmDeleteItem(item)}
      />

      {/* ── Confirmation & Deletion Dialog Modal ──────────────────────── */}
      {confirmDeleteItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2 text-rose-600 dark:text-rose-400">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {confirmDeleteItem.status === 'SCHEDULED' ? 'Cancel Scheduled' : 'Delete'} {confirmDeleteItem.item_type === 'story' ? 'Story' : 'Post'} #{confirmDeleteItem.id}
                </h3>
              </div>
              <button
                disabled={deletingItemId !== null}
                onClick={() => setConfirmDeleteItem(null)}
                className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
              <p className="font-medium text-slate-900 dark:text-slate-200">
                Are you sure you want to {confirmDeleteItem.status === 'SCHEDULED' ? 'cancel and delete' : 'delete'} this {confirmDeleteItem.item_type === 'story' ? 'Story' : 'Post'}?
              </p>

              {confirmDeleteItem.item_type === 'story' ? (
                confirmDeleteItem.status === 'SCHEDULED' ? (
                  <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/50 text-amber-800 dark:text-amber-200 text-[11px] space-y-1">
                    <p className="font-bold">🕒 Scheduled Story Cancellation</p>
                    <p>Deleting this record will safely cancel scheduled publication and prevent any Meta API calls.</p>
                  </div>
                ) : confirmDeleteItem.status === 'PUBLISHED' || Boolean(confirmDeleteItem.fb_id || confirmDeleteItem.ig_id) ? (
                  <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/50 text-rose-800 dark:text-rose-200 space-y-2 text-[11px]">
                    <p className="font-bold flex items-center space-x-1 text-rose-700 dark:text-rose-300">
                      <span>⚠️ External Platform Story Removal</span>
                    </p>
                    <p>This will attempt to remove the Story from the connected platforms:</p>
                    
                    <div className="space-y-1 pl-1 font-mono text-[11px]">
                      {confirmDeleteItem.fb_id ? (
                        <div className="text-emerald-600 dark:text-emerald-400 flex items-center space-x-1.5">
                          <span>✓</span>
                          <span className="text-slate-700 dark:text-slate-200">Facebook Page</span>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400">({confirmDeleteItem.fb_id})</span>
                        </div>
                      ) : (confirmDeleteItem.platforms || []).includes('facebook') ? (
                        <div className="text-rose-600 dark:text-rose-400 flex items-center space-x-1.5">
                          <span>✕</span>
                          <span className="text-slate-500 dark:text-slate-400">Facebook Page (not published)</span>
                        </div>
                      ) : null}

                      {confirmDeleteItem.ig_id ? (
                        <div className="text-emerald-600 dark:text-emerald-400 flex items-center space-x-1.5">
                          <span>✓</span>
                          <span className="text-slate-700 dark:text-slate-200">Instagram Business</span>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400">({confirmDeleteItem.ig_id})</span>
                        </div>
                      ) : (confirmDeleteItem.platforms || []).includes('instagram') ? (
                        <div className="text-rose-600 dark:text-rose-400 flex items-center space-x-1.5">
                          <span>✕</span>
                          <span className="text-slate-500 dark:text-slate-400">Instagram Business (not published)</span>
                        </div>
                      ) : null}
                    </div>

                    {((!confirmDeleteItem.fb_id && (confirmDeleteItem.platforms || []).includes('facebook')) ||
                      (!confirmDeleteItem.ig_id && (confirmDeleteItem.platforms || []).includes('instagram'))) && (
                      <p className="text-[10px] text-amber-700 dark:text-amber-300">
                        Only successfully published platforms will be affected by deletion.
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-[11px] space-y-1">
                    <p className="font-bold text-slate-800 dark:text-slate-200">ℹ️ Story Record Removal</p>
                    <p>Deleting this record will remove it from your scheduler queue.</p>
                  </div>
                )
              ) : (
                confirmDeleteItem.status === 'PUBLISHED' ? (
                  <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/50 text-rose-800 dark:text-rose-200 space-y-1 text-[11px]">
                    <p className="font-bold flex items-center space-x-1 text-rose-700 dark:text-rose-300">
                      <span>⚠️ External Platform Removal Warning</span>
                    </p>
                    <p>
                      This post has been published. Deleting it will attempt to remove the published media directly from connected social platforms (Facebook / Instagram).
                    </p>
                  </div>
                ) : confirmDeleteItem.status === 'SCHEDULED' ? (
                  <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/50 text-amber-800 dark:text-amber-200 text-[11px]">
                    <span>🕒 Deleting this post will safely cancel its scheduled execution and remove it.</span>
                  </div>
                ) : null
              )}
            </div>

            {deleteStatusMessage && deleteStatusMessage.type === 'error' && (
              <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800/80 text-rose-800 dark:text-rose-200 text-[11px] space-y-1">
                <p className="font-bold text-rose-700 dark:text-rose-300">{deleteStatusMessage.text}</p>
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

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                disabled={deletingItemId !== null}
                onClick={() => setConfirmDeleteItem(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold transition"
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
