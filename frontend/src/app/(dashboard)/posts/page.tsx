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
  List,
  CalendarDays,
  CalendarRange,
  Clock3,
  Facebook,
  Instagram,
  Youtube
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
                <Facebook className="w-3.5 h-3.5 text-blue-600 mr-2 flex-shrink-0" />
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
                <Instagram className="w-3.5 h-3.5 text-pink-600 mr-2 flex-shrink-0" />
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
  const platformIcon = hasFb ? (
    <Facebook className="w-3 h-3 text-blue-600 dark:text-blue-400" />
  ) : (
    <Instagram className="w-3 h-3 text-pink-600 dark:text-pink-400" />
  );

  return (
    <a
      href={singleUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700/80 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-[11px] transition flex items-center space-x-1.5 focus-ring shadow-xs"
      title={`Open live post on ${platformName}`}
    >
      {platformIcon}
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
  
  // Top-Level Mode: 'calendar' vs 'list'
  const [mode, setMode] = useState<'calendar' | 'list'>('calendar');

  // Calendar Sub-View: 'week' (primary) | 'month' | 'day'
  const [calendarView, setCalendarView] = useState<'week' | 'month' | 'day'>('week');

  // Calendar anchor date
  const [currentDate, setCurrentDate] = useState<Date>(() => new Date());

  // Filters
  const [filterType, setFilterType] = useState<'ALL' | 'POST' | 'STORY'>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Modals & Selected details
  const [previewStory, setPreviewStory] = useState<SchedulerItem | null>(null);
  const [selectedPostItem, setSelectedPostItem] = useState<SchedulerItem | null>(null);
  const [viewDayModal, setViewDayModal] = useState<{ dateStr: string; items: SchedulerItem[] } | null>(null);

  // Timeline scroll container ref
  const timelineScrollRef = useRef<HTMLDivElement>(null);

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

  // Auto-scroll timeline to 08:00 AM on initial week/day load
  useEffect(() => {
    if (timelineScrollRef.current && (calendarView === 'week' || calendarView === 'day')) {
      timelineScrollRef.current.scrollTop = 8 * 64; // 8:00 AM position
    }
  }, [calendarView, mode]);

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

  const getItemMinutesFromMidnight = (dateStr?: string) => {
    if (!dateStr) return 0;
    const normalized = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return 0;
    return d.getHours() * 60 + d.getMinutes();
  };

  // Date Navigation handlers
  const handlePrev = () => {
    setCurrentDate((prev) => {
      const d = new Date(prev);
      if (calendarView === 'week') d.setDate(d.getDate() - 7);
      else if (calendarView === 'day') d.setDate(d.getDate() - 1);
      else d.setMonth(d.getMonth() - 1);
      return d;
    });
  };

  const handleNext = () => {
    setCurrentDate((prev) => {
      const d = new Date(prev);
      if (calendarView === 'week') d.setDate(d.getDate() + 7);
      else if (calendarView === 'day') d.setDate(d.getDate() + 1);
      else d.setMonth(d.getMonth() + 1);
      return d;
    });
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  // Week View Calculations (Monday–Sunday)
  const { weekDays, weekLabel } = useMemo(() => {
    const startOfWeek = new Date(currentDate);
    const dayOfWeek = (currentDate.getDay() + 6) % 7; // Monday = 0
    startOfWeek.setDate(currentDate.getDate() - dayOfWeek);
    startOfWeek.setHours(0, 0, 0, 0);

    const days: { date: Date; dateKey: string; dayName: string; dayNumber: number; isToday: boolean }[] = [];
    const todayStr = getDateKey(new Date());

    for (let i = 0; i < 7; i++) {
      const d = new Date(startOfWeek);
      d.setDate(startOfWeek.getDate() + i);
      const key = getDateKey(d);
      days.push({
        date: d,
        dateKey: key,
        dayName: d.toLocaleDateString(undefined, { weekday: 'short' }),
        dayNumber: d.getDate(),
        isToday: key === todayStr,
      });
    }

    const endOfWeek = days[6].date;
    const sameMonth = startOfWeek.getMonth() === endOfWeek.getMonth();
    const sameYear = startOfWeek.getFullYear() === endOfWeek.getFullYear();

    let label = '';
    if (sameMonth && sameYear) {
      label = `${startOfWeek.toLocaleDateString(undefined, { month: 'short' })} ${startOfWeek.getDate()} – ${endOfWeek.getDate()}, ${startOfWeek.getFullYear()}`;
    } else if (sameYear) {
      label = `${startOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${endOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}, ${startOfWeek.getFullYear()}`;
    } else {
      label = `${startOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })} – ${endOfWeek.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
    }

    return { weekDays: days, weekLabel: label };
  }, [currentDate]);

  // Month View Calculations
  const { monthGrid, monthLabel } = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const todayStr = getDateKey(new Date());

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const totalDays = lastDay.getDate();
    const startDayIndex = (firstDay.getDay() + 6) % 7;
    const prevMonthLastDay = new Date(year, month, 0).getDate();

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

    // Leading days
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

    // Trailing days
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

    const formattedMonth = currentDate.toLocaleDateString(undefined, {
      month: 'long',
      year: 'numeric',
    });

    return { monthGrid: grid, monthLabel: formattedMonth };
  }, [currentDate, filteredItems]);

  // Day View Label
  const dayLabel = useMemo(() => {
    return currentDate.toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  }, [currentDate]);

  // Active toolbar date label
  const activeDateLabel = calendarView === 'week' ? weekLabel : calendarView === 'day' ? dayLabel : monthLabel;

  // 24 Hours array for timeline grids
  const hoursArray = useMemo(() => {
    return Array.from({ length: 24 }).map((_, i) => {
      const hour12 = i === 0 ? 12 : i > 12 ? i - 12 : i;
      const ampm = i < 12 ? 'AM' : 'PM';
      return {
        hour24: i,
        label: `${hour12}:00 ${ampm}`,
        shortLabel: `${hour12} ${ampm}`,
      };
    });
  }, []);

  const postCount = items.filter(i => i.item_type === 'post').length;
  const storyCount = items.filter(i => i.item_type === 'story').length;

  return (
    <div className="space-y-4 select-none font-sans text-xs">
      {/* ── Page Header & Top Level Switcher ─────────────────────────── */}
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
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
            Plan, schedule and manage your social content across time and platforms.
          </p>
        </div>

        <div className="flex items-center space-x-2.5 flex-shrink-0">
          {/* Top-Level Mode Switcher: Calendar vs List */}
          <div className="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-xs">
            <button
              onClick={() => setMode('calendar')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                mode === 'calendar'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <CalendarDays className="w-3.5 h-3.5" />
              <span>Calendar</span>
            </button>
            <button
              onClick={() => setMode('list')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                mode === 'list'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span>List</span>
            </button>
          </div>

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
            <span>+ New Post</span>
          </Link>
        </div>
      </div>

      {/* ── Status Message Alert Banner ───────────────────────────────── */}
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

      {/* ── Calendar Toolbar (Always visible in Calendar & List) ───────── */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        
        {/* Left: Prev / Today / Next + Active Date Range Title + Refresh */}
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800/60 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700/60">
            <button
              onClick={handlePrev}
              className="p-1.5 rounded-md text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
              title="Previous period"
              aria-label="Previous period"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleToday}
              className="px-2.5 py-1 text-xs font-semibold rounded-md text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
            >
              Today
            </button>
            <button
              onClick={handleNext}
              className="p-1.5 rounded-md text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 transition"
              title="Next period"
              aria-label="Next period"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 min-w-[180px]">
            {activeDateLabel}
          </h2>

          <button
            onClick={fetchQueue}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition shadow-xs"
            title="Refresh schedule feed"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
        </div>

        {/* Center/Right: Calendar View Switcher (Week / Month / Day) + Filters */}
        <div className="flex items-center space-x-2.5 flex-wrap gap-y-2">
          {/* Calendar Views: Week (Default) | Month | Day (active in calendar mode) */}
          {mode === 'calendar' && (
            <div className="flex items-center space-x-1 bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setCalendarView('week')}
                className={`px-3 py-1 rounded-md text-xs font-bold transition flex items-center space-x-1 ${
                  calendarView === 'week'
                    ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                <CalendarRange className="w-3 h-3" />
                <span>Week</span>
              </button>
              <button
                onClick={() => setCalendarView('month')}
                className={`px-3 py-1 rounded-md text-xs font-bold transition flex items-center space-x-1 ${
                  calendarView === 'month'
                    ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                <CalendarDays className="w-3 h-3" />
                <span>Month</span>
              </button>
              <button
                onClick={() => setCalendarView('day')}
                className={`px-3 py-1 rounded-md text-xs font-bold transition flex items-center space-x-1 ${
                  calendarView === 'day'
                    ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                <Clock3 className="w-3 h-3" />
                <span>Day</span>
              </button>
            </div>
          )}

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

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* ── MODE 1: CALENDAR WORKSPACE (NO QUEUE UNDERNEATH) ─────────────── */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {mode === 'calendar' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          
          {/* ── CALENDAR SUB-VIEW: 1. WEEK VIEW (UNIFIED MATRIX TIME-GRID) ── */}
          {calendarView === 'week' && (
            <div className="overflow-x-auto">
              <div className="min-w-[920px]">
                {/* Unified Day Header Row */}
                <div className="grid grid-cols-[76px_repeat(7,minmax(0,1fr))] border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 sticky top-0 z-20">
                  {/* Fixed time column header */}
                  <div className="p-2.5 text-center border-r border-slate-200 dark:border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center justify-center">
                    Time
                  </div>
                  {/* 7 Day Headers with continuous vertical borders */}
                  {weekDays.map((d) => (
                    <div
                      key={d.dateKey}
                      className={`p-2.5 text-center border-r border-slate-200 dark:border-slate-800 last:border-r-0 ${
                        d.isToday ? 'bg-indigo-50/60 dark:bg-indigo-950/40' : ''
                      }`}
                    >
                      <span className="text-[11px] font-bold uppercase text-slate-500 dark:text-slate-400 block">
                        {d.dayName}
                      </span>
                      <span
                        className={`text-sm font-bold inline-flex items-center justify-center w-6 h-6 rounded-full mt-0.5 ${
                          d.isToday
                            ? 'bg-indigo-600 text-white shadow-xs'
                            : 'text-slate-900 dark:text-slate-100'
                        }`}
                      >
                        {d.dayNumber}
                      </span>
                    </div>
                  ))}
                </div>

                {/* 24-Hour Scrollable Time Grid Body */}
                <div
                  ref={timelineScrollRef}
                  className="h-[620px] overflow-y-auto"
                >
                  <div className="grid grid-cols-[76px_repeat(7,minmax(0,1fr))] relative h-[1536px]">
                    {/* Left Column: 24 Hour Labels */}
                    <div className="border-r border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/30 divide-y divide-slate-200/80 dark:divide-slate-800/80">
                      {hoursArray.map((h) => (
                        <div
                          key={h.hour24}
                          className="h-[64px] px-2 pt-1 text-right text-[10px] font-mono text-slate-500 dark:text-slate-400"
                        >
                          {h.label}
                        </div>
                      ))}
                    </div>

                    {/* 7 Day Columns with identical vertical boundaries */}
                    {weekDays.map((d) => {
                      const dayItems = filteredItems.filter((item) => {
                        const itemKey = getItemDateKey(item.scheduled_at || item.published_at || item.created_at);
                        return itemKey === d.dateKey;
                      });

                      return (
                        <div
                          key={d.dateKey}
                          className={`relative border-r border-slate-200 dark:border-slate-800 last:border-r-0 ${
                            d.isToday ? 'bg-indigo-50/20 dark:bg-indigo-950/15' : 'bg-white dark:bg-slate-900'
                          }`}
                        >
                          {/* Continuous Horizontal Hour Guideline Grid */}
                          <div className="absolute inset-0 pointer-events-none divide-y divide-slate-200/80 dark:divide-slate-800/80">
                            {hoursArray.map((h) => (
                              <div key={h.hour24} className="h-[64px]" />
                            ))}
                          </div>

                          {/* Positioned Content Items (Strictly inside day column) */}
                          {dayItems.map((item) => {
                            const mins = getItemMinutesFromMidnight(item.scheduled_at || item.published_at || item.created_at);
                            const topPx = (mins / 60) * 64;
                            const isStory = item.item_type === 'story';
                            const isFb = item.platforms.includes('facebook');
                            const isIg = item.platforms.includes('instagram');
                            const isYt = (item.platforms as string[]).includes('youtube');
                            const timeStr = formatShortTime(item.scheduled_at || item.published_at || item.created_at);

                            return (
                              <div
                                key={`${item.item_type}-${item.id}`}
                                onClick={() => {
                                  if (isStory) setPreviewStory(item);
                                  else setSelectedPostItem(item);
                                }}
                                style={{ top: `${topPx}px` }}
                                className={`absolute left-1 right-1 z-10 p-1.5 rounded-lg border text-[11px] cursor-pointer transition-all hover:scale-[1.02] hover:z-20 shadow-xs flex flex-col space-y-1 ${
                                  isStory
                                    ? 'bg-fuchsia-50/95 dark:bg-fuchsia-950/85 border-fuchsia-300 dark:border-fuchsia-800 text-fuchsia-950 dark:text-fuchsia-100'
                                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100'
                                }`}
                                title={`${item.title || item.caption || 'Scheduled content'} (${timeStr})`}
                              >
                                {/* Header: Platform icon & Time */}
                                <div className="flex items-center justify-between text-[10px]">
                                  <div className="flex items-center space-x-1">
                                    {isFb && <Facebook className="w-3 h-3 text-blue-600 flex-shrink-0" />}
                                    {isIg && <Instagram className="w-3 h-3 text-pink-600 flex-shrink-0" />}
                                    {isYt && <Youtube className="w-3 h-3 text-red-600 flex-shrink-0" />}
                                    <span className="font-bold">{timeStr}</span>
                                  </div>
                                  <span className={`w-1.5 h-1.5 rounded-full ${
                                    item.status === 'PUBLISHED' ? 'bg-emerald-500' :
                                    item.status === 'FAILED' ? 'bg-rose-500' :
                                    item.status === 'DRAFT' ? 'bg-slate-400' : 'bg-sky-500'
                                  }`} />
                                </div>

                                {/* Body: Thumbnail & Snippet */}
                                <div className="flex items-center space-x-1.5 min-w-0">
                                  {item.thumbnail_url ? (
                                    <img
                                      src={item.thumbnail_url}
                                      alt=""
                                      className="w-5 h-5 rounded object-cover border border-slate-200 dark:border-slate-700 flex-shrink-0"
                                    />
                                  ) : isStory ? (
                                    <Sparkles className="w-3.5 h-3.5 text-fuchsia-500 flex-shrink-0" />
                                  ) : (
                                    <ImageIcon className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                                  )}
                                  <span className="truncate font-semibold text-[11px] leading-tight flex-1">
                                    {item.title || item.caption || (isStory ? 'Story Asset' : 'Feed Post')}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── CALENDAR SUB-VIEW: 2. MONTH VIEW ───────────────────────────── */}
          {calendarView === 'month' && (
            <div>
              {/* Weekday Row */}
              <div className="grid grid-cols-7 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-center text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider py-2.5">
                <div>Mon</div>
                <div>Tue</div>
                <div>Wed</div>
                <div>Thu</div>
                <div>Fri</div>
                <div>Sat</div>
                <div>Sun</div>
              </div>

              {/* Month Day Grid with continuous visible slate boundaries */}
              <div className="grid grid-cols-7 divide-x divide-y divide-slate-200 dark:divide-slate-800 border-b border-slate-200 dark:border-slate-800">
                {monthGrid.map((cell) => (
                  <div
                    key={cell.dateKey}
                    className={`min-h-[135px] sm:min-h-[145px] p-2 flex flex-col justify-between transition-colors ${
                      cell.isCurrentMonth
                        ? 'bg-white dark:bg-slate-900'
                        : 'bg-slate-50/60 dark:bg-slate-950/40 text-slate-400 dark:text-slate-600'
                    } ${cell.isToday ? 'ring-2 ring-inset ring-indigo-500/50' : ''}`}
                  >
                    {/* Top: Day Number + Count */}
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
                          {cell.items.length} {cell.items.length === 1 ? 'post' : 'posts'}
                        </span>
                      )}
                    </div>

                    {/* Middle: Content Cards in this Day */}
                    <div className="space-y-1.5 mt-1.5 flex-1">
                      {cell.items.slice(0, 3).map((item) => {
                        const isStory = item.item_type === 'story';
                        const timeStr = formatShortTime(item.scheduled_at || item.published_at || item.created_at);
                        const isFb = item.platforms.includes('facebook');
                        const isIg = item.platforms.includes('instagram');
                        const isYt = (item.platforms as string[]).includes('youtube');

                        return (
                          <div
                            key={`${item.item_type}-${item.id}`}
                            onClick={() => {
                              if (isStory) setPreviewStory(item);
                              else setSelectedPostItem(item);
                            }}
                            className={`p-1.5 rounded-lg border text-[11px] cursor-pointer transition-all hover:border-indigo-400 dark:hover:border-indigo-600 hover:shadow-xs flex flex-col space-y-1 ${
                              isStory
                                ? 'bg-fuchsia-50/70 dark:bg-fuchsia-950/30 border-fuchsia-200 dark:border-fuchsia-800/60 text-fuchsia-950 dark:text-fuchsia-200'
                                : 'bg-slate-50/90 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100'
                            }`}
                            title={`${item.title || item.caption || 'Scheduled content'} — Click for details`}
                          >
                            <div className="flex items-center justify-between text-[10px]">
                              <div className="flex items-center space-x-1">
                                {isFb && <Facebook className="w-3 h-3 text-blue-600 flex-shrink-0" />}
                                {isIg && <Instagram className="w-3 h-3 text-pink-600 flex-shrink-0" />}
                                {isYt && <Youtube className="w-3 h-3 text-red-600 flex-shrink-0" />}
                                <span className="font-semibold text-slate-700 dark:text-slate-300">
                                  {isFb ? 'FB' : isIg ? 'IG' : 'Post'}
                                </span>
                              </div>
                              <span className={`w-1.5 h-1.5 rounded-full ${
                                item.status === 'PUBLISHED' ? 'bg-emerald-500' :
                                item.status === 'FAILED' ? 'bg-rose-500' :
                                item.status === 'DRAFT' ? 'bg-slate-400' : 'bg-sky-500'
                              }`} />
                            </div>
                            <div className="flex items-center space-x-1.5">
                              {item.thumbnail_url ? (
                                <img src={item.thumbnail_url} alt="" className="w-5 h-5 rounded object-cover border border-slate-200 dark:border-slate-700 flex-shrink-0" />
                              ) : isStory ? (
                                <Sparkles className="w-3.5 h-3.5 text-fuchsia-500 flex-shrink-0" />
                              ) : (
                                <ImageIcon className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                              )}
                              <span className="truncate font-medium text-[11px] leading-tight flex-1">
                                {item.title || (item.caption && item.caption.trim() ? item.caption.slice(0, 30) : isStory ? 'Story Asset' : 'Untitled Post')}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 dark:text-slate-400 pt-0.5">
                              <span>{timeStr || '—'}</span>
                              <span className="capitalize">{item.status.toLowerCase()}</span>
                            </div>
                          </div>
                        );
                      })}

                      {cell.items.length > 3 && (
                        <button
                          onClick={() => setViewDayModal({ dateStr: cell.dateKey, items: cell.items })}
                          className="w-full text-center text-[10px] font-bold text-indigo-600 dark:text-indigo-400 hover:underline py-0.5 bg-indigo-50/50 dark:bg-indigo-950/30 rounded"
                        >
                          +{cell.items.length - 3} more
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── CALENDAR SUB-VIEW: 3. DAY VIEW (UNIFIED MATRIX TIMELINE) ────── */}
          {calendarView === 'day' && (
            <div className="flex flex-col">
              {/* Single Day Header matching time column */}
              <div className="grid grid-cols-[76px_minmax(0,1fr)] border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 sticky top-0 z-20">
                <div className="p-2.5 text-center border-r border-slate-200 dark:border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center justify-center">
                  Time
                </div>
                <div className="p-2.5 px-4 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Clock3 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {dayLabel} Timeline
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-500">
                    {filteredItems.filter(i => getItemDateKey(i.scheduled_at || i.published_at || i.created_at) === getDateKey(currentDate)).length} scheduled
                  </span>
                </div>
              </div>

              {/* Day 24-Hour Timeline */}
              <div
                ref={timelineScrollRef}
                className="h-[620px] overflow-y-auto"
              >
                <div className="grid grid-cols-[76px_minmax(0,1fr)] relative h-[1536px]">
                  {/* Left Column: Hours */}
                  <div className="border-r border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/30 divide-y divide-slate-200/80 dark:divide-slate-800/80">
                    {hoursArray.map((h) => (
                      <div
                        key={h.hour24}
                        className="h-[64px] px-2 pt-1 text-right text-[10px] font-mono text-slate-500 dark:text-slate-400"
                      >
                        {h.label}
                      </div>
                    ))}
                  </div>

                  {/* Right Column: Time Grid Workspace */}
                  <div className="relative bg-white dark:bg-slate-900">
                    {/* Continuous Guidelines */}
                    <div className="absolute inset-0 pointer-events-none divide-y divide-slate-200/80 dark:divide-slate-800/80">
                      {hoursArray.map((h) => (
                        <div key={h.hour24} className="h-[64px]" />
                      ))}
                    </div>

                    {/* Content Items on this specific day */}
                    {filteredItems
                      .filter(i => getItemDateKey(i.scheduled_at || i.published_at || i.created_at) === getDateKey(currentDate))
                      .map((item) => {
                        const mins = getItemMinutesFromMidnight(item.scheduled_at || item.published_at || item.created_at);
                        const topPx = (mins / 60) * 64;
                        const isStory = item.item_type === 'story';
                        const isFb = item.platforms.includes('facebook');
                        const isIg = item.platforms.includes('instagram');
                        const timeStr = formatShortTime(item.scheduled_at || item.published_at || item.created_at);

                        return (
                          <div
                            key={`${item.item_type}-${item.id}`}
                            onClick={() => {
                              if (isStory) setPreviewStory(item);
                              else setSelectedPostItem(item);
                            }}
                            style={{ top: `${topPx}px` }}
                            className={`absolute left-4 right-4 sm:right-16 z-10 p-3 rounded-xl border cursor-pointer transition-all hover:scale-[1.01] hover:z-20 shadow-xs flex items-center justify-between space-x-3 ${
                              isStory
                                ? 'bg-fuchsia-50/95 dark:bg-fuchsia-950/85 border-fuchsia-300 dark:border-fuchsia-800'
                                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700'
                            }`}
                          >
                            <div className="flex items-center space-x-3 min-w-0">
                              {item.thumbnail_url ? (
                                <img src={item.thumbnail_url} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0" />
                              ) : (
                                <div className="w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center text-indigo-600 flex-shrink-0">
                                  {isStory ? <Sparkles className="w-5 h-5" /> : <ImageIcon className="w-5 h-5" />}
                                </div>
                              )}
                              <div className="min-w-0 space-y-0.5">
                                <div className="flex items-center space-x-2">
                                  <span className="font-bold text-slate-900 dark:text-slate-100 text-xs truncate">
                                    {item.title || item.caption || (isStory ? 'Story Asset' : 'Feed Post')}
                                  </span>
                                  {isFb && <Facebook className="w-3 h-3 text-blue-600" />}
                                  {isIg && <Instagram className="w-3 h-3 text-pink-600" />}
                                </div>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                                  {item.caption || 'No caption text.'}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center space-x-3 flex-shrink-0">
                              <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                                {timeStr}
                              </span>
                              <PostStatusBadge status={item.status} />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Empty Calendar State across Week/Month/Day */}
          {!isLoading && filteredItems.length === 0 && (
            <div className="py-14 px-6 text-center space-y-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20">
              <div className="w-11 h-11 rounded-xl bg-slate-200/70 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 mx-auto">
                <CalendarIcon className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  No scheduled content
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
                  Your calendar is clear. Create your first post or story to start planning your social content schedule.
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

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* ── MODE 2: LIST VIEW (DEDICATED QUEUE TABLE ONLY) ───────────────── */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {mode === 'list' && (
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
      )}

      {/* ── Day Items Modal (for +N more on calendar) ─────────────────── */}
      {viewDayModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <CalendarDays className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Scheduled on {viewDayModal.dateStr} ({viewDayModal.items.length})
                </h3>
              </div>
              <button
                onClick={() => setViewDayModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {viewDayModal.items.map((item) => {
                const isStory = item.item_type === 'story';
                return (
                  <div
                    key={`${item.item_type}-${item.id}`}
                    onClick={() => {
                      setViewDayModal(null);
                      if (isStory) setPreviewStory(item);
                      else setSelectedPostItem(item);
                    }}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 hover:border-indigo-400 dark:hover:border-indigo-600 cursor-pointer transition flex items-center justify-between space-x-3"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      {item.thumbnail_url ? (
                        <img src={item.thumbnail_url} alt="" className="w-8 h-8 rounded-lg object-cover flex-shrink-0" />
                      ) : (
                        <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center text-indigo-600 flex-shrink-0">
                          {isStory ? <Sparkles className="w-4 h-4" /> : <ImageIcon className="w-4 h-4" />}
                        </div>
                      )}
                      <div className="min-w-0">
                        <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                          {item.title || item.caption || (isStory ? 'Story Asset' : 'Feed Post')}
                        </h4>
                        <p className="text-[10px] font-mono text-slate-500">
                          {formatShortTime(item.scheduled_at || item.published_at || item.created_at)} • {item.platforms.join(', ')}
                        </p>
                      </div>
                    </div>
                    <PostStatusBadge status={item.status} />
                  </div>
                );
              })}
            </div>

            <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setViewDayModal(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

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
