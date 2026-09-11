'use client';

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Link from 'next/link';
import {
  Youtube,
  Search,
  RefreshCw,
  Sliders,
  ExternalLink,
  Loader2,
  AlertCircle,
  Film,
  Lock,
  Globe,
  EyeOff,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Check,
  UploadCloud,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import {
  YouTubeVideoItem,
  YouTubeVideoListResponse,
  YouTubeVideoDetailResponse,
  SocialAccount,
} from '@/lib/types';
import { YouTubeVideoEditModal } from '@/components/YouTubeVideoEditModal';
import toast, { Toaster } from 'react-hot-toast';

export default function YouTubeVideosPage() {
  // Data State
  const [videos, setVideos] = useState<YouTubeVideoItem[]>([]);
  const [channelTitle, setChannelTitle] = useState<string | null>(null);
  const [channelId, setChannelId] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState<number | null>(null);

  // Loading & Error States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isAccountsLoading, setIsAccountsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Pagination State
  const [currentPageToken, setCurrentPageToken] = useState<string | null>(null);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [tokenStack, setTokenStack] = useState<(string | null)[]>([]); // for backward navigation

  // Search Query
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Channel Accounts
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [isAccountDropdownOpen, setIsAccountDropdownOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Edit Modal State
  const [editingVideoId, setEditingVideoId] = useState<string | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);

  // Close account dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsAccountDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Load connected YouTube channels on mount
  useEffect(() => {
    setIsAccountsLoading(true);
    apiClient
      .get<SocialAccount[]>('/social-accounts/')
      .then((res) => {
        const ytAccounts = res.data.filter((acc) => acc.platform === 'youtube');
        setAccounts(ytAccounts);
        if (ytAccounts.length > 0) {
          setSelectedAccountId((prev) => (prev !== null ? prev : ytAccounts[0].id));
        } else {
          setIsLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load social accounts:', err);
        setErrorMsg('Failed to load connected YouTube accounts.');
        setIsLoading(false);
      })
      .finally(() => {
        setIsAccountsLoading(false);
      });
  }, []);

  // Fetch videos for current page and channel
  const fetchVideos = useCallback(
    async (pageToken: string | null = null, isRefresh: boolean = false) => {
      if (isRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setErrorMsg(null);

      const params: Record<string, any> = { limit: 20 };
      if (pageToken) params.page_token = pageToken;
      if (selectedAccountId) params.social_account_id = selectedAccountId;

      try {
        const res = await apiClient.get<YouTubeVideoListResponse>('/youtube/videos', { params });
        const data = res.data;
        setVideos(data.videos || []);
        setNextPageToken(data.next_page_token || null);
        setChannelTitle(data.channel_title || null);
        setChannelId(data.channel_id || null);
        setTotalResults(data.total_results ?? null);
        setCurrentPageToken(pageToken);
      } catch (err: any) {
        const msg =
          err.response?.data?.detail ||
          err.message ||
          'Failed to load channel videos from YouTube.';
        setErrorMsg(msg);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [selectedAccountId]
  );

  useEffect(() => {
    if (selectedAccountId !== null) {
      setTokenStack([]);
      setCurrentPageToken(null);
      fetchVideos(null);
    }
  }, [selectedAccountId, fetchVideos]);

  // Handle account switching
  const handleAccountChange = (newAccountId: number) => {
    if (newAccountId === selectedAccountId) {
      setIsAccountDropdownOpen(false);
      return;
    }
    setIsAccountDropdownOpen(false);
    setVideos([]); // Immediately clear previous account's videos while loading
    setSearchQuery(''); // Reset search
    setTokenStack([]); // Clear pagination stack
    setCurrentPageToken(null); // Reset page token
    setSelectedAccountId(newAccountId);
  };

  // Find currently active account object
  const selectedAccount = useMemo(() => {
    return accounts.find((a) => a.id === selectedAccountId) || accounts[0] || null;
  }, [accounts, selectedAccountId]);

  // Handlers for pagination
  const handleNextPage = () => {
    if (!nextPageToken) return;
    setTokenStack((prev) => [...prev, currentPageToken]);
    fetchVideos(nextPageToken);
  };

  const handlePrevPage = () => {
    if (tokenStack.length === 0) return;
    const prevToken = tokenStack[tokenStack.length - 1];
    setTokenStack((prev) => prev.slice(0, -1));
    fetchVideos(prevToken);
  };

  const handleRefresh = () => {
    fetchVideos(currentPageToken, true);
  };

  // Open Edit Modal
  const handleOpenEdit = (videoId: string) => {
    setEditingVideoId(videoId);
    setIsEditModalOpen(true);
  };

  // Update video in local list when editing succeeds
  const handleVideoUpdated = (updated: YouTubeVideoDetailResponse) => {
    setVideos((prev) =>
      prev.map((v) =>
        v.video_id === updated.video_id
          ? {
              ...v,
              title: updated.title,
              description: updated.description,
              privacy_status: updated.privacy_status,
              thumbnail_url: updated.thumbnail_url || v.thumbnail_url,
            }
          : v
      )
    );
    toast.success('Video updated in your library!');
  };

  // Client-side search filtering on current page
  const filteredVideos = useMemo(() => {
    if (!searchQuery.trim()) return videos;
    const q = searchQuery.toLowerCase().trim();
    return videos.filter(
      (v) =>
        v.title.toLowerCase().includes(q) ||
        (v.description && v.description.toLowerCase().includes(q))
    );
  }, [videos, searchQuery]);

  // Privacy Status helper
  const renderPrivacyBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'public') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-950/80 border border-emerald-800/80 text-emerald-300 text-[10px] font-bold uppercase tracking-wider">
          <Globe className="w-2.5 h-2.5" />
          <span>Public</span>
        </span>
      );
    }
    if (s === 'unlisted') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-amber-950/80 border border-amber-800/80 text-amber-300 text-[10px] font-bold uppercase tracking-wider">
          <EyeOff className="w-2.5 h-2.5" />
          <span>Unlisted</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-800/80 text-indigo-300 text-[10px] font-bold uppercase tracking-wider">
        <Lock className="w-2.5 h-2.5" />
        <span>Private</span>
      </span>
    );
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'Unknown date';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <Toaster position="top-right" />

      {/* Top Header Card */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 shadow-sm backdrop-blur-sm">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-red-600/10 text-red-400 border border-red-500/20 flex items-center justify-center shadow-inner">
            <Youtube className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold text-white tracking-tight">YouTube Videos</h1>
            </div>
            <p className="text-xs text-slate-400">
              Browse, manage, and edit videos from your connected YouTube channels.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 flex-wrap">
          {/* Multi-Account Selector / Account Display */}
          {accounts.length > 1 ? (
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setIsAccountDropdownOpen((prev) => !prev)}
                className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-950 hover:bg-slate-800/80 border border-slate-700/80 hover:border-slate-600 text-xs text-slate-200 font-medium transition shadow-sm"
                title="Switch YouTube Account"
                aria-haspopup="true"
                aria-expanded={isAccountDropdownOpen}
              >
                <div className="w-5 h-5 rounded-full bg-red-600/20 text-red-400 flex items-center justify-center overflow-hidden flex-shrink-0">
                  {selectedAccount?.logo_url ? (
                    <img src={selectedAccount.logo_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <Youtube className="w-3 h-3" />
                  )}
                </div>
                <span className="text-slate-400 font-normal">YouTube Account:</span>
                <span className="font-semibold text-white max-w-[140px] sm:max-w-[200px] truncate">
                  {selectedAccount?.account_name || channelTitle || 'Select Account'}
                </span>
                <ChevronDown
                  className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                    isAccountDropdownOpen ? 'rotate-180 text-red-400' : ''
                  }`}
                />
              </button>

              {isAccountDropdownOpen && (
                <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl shadow-black/80 py-2 z-50 animate-in fade-in zoom-in-95 duration-100 backdrop-blur-md">
                  <div className="px-3.5 py-1.5 border-b border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Connected Channels</span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                      {accounts.length}
                    </span>
                  </div>
                  <div className="max-h-64 overflow-y-auto py-1">
                    {accounts.map((acc) => {
                      const isSelected = acc.id === selectedAccountId;
                      return (
                        <button
                          key={acc.id}
                          type="button"
                          onClick={() => handleAccountChange(acc.id)}
                          className={`w-full flex items-center justify-between px-3.5 py-2.5 text-left text-xs transition ${
                            isSelected
                              ? 'bg-red-950/40 text-white font-semibold border-l-2 border-red-500'
                              : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                          }`}
                        >
                          <div className="flex items-center space-x-3 min-w-0 pr-2">
                            <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center overflow-hidden flex-shrink-0">
                              {acc.logo_url ? (
                                <img src={acc.logo_url} alt="" className="w-full h-full object-cover" />
                              ) : (
                                <Youtube className="w-4 h-4 text-red-400" />
                              )}
                            </div>
                            <div className="min-w-0">
                              <div className="truncate text-xs font-semibold">{acc.account_name || 'YouTube Channel'}</div>
                              {acc.account_id && (
                                <div className="text-[10px] text-slate-500 font-mono truncate">{acc.account_id}</div>
                              )}
                            </div>
                          </div>
                          {isSelected && <Check className="w-4 h-4 text-red-400 flex-shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : accounts.length === 1 ? (
            <div className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 shadow-sm">
              <div className="w-5 h-5 rounded-full bg-red-600/20 text-red-400 flex items-center justify-center overflow-hidden flex-shrink-0">
                {selectedAccount?.logo_url ? (
                  <img src={selectedAccount.logo_url} alt="" className="w-full h-full object-cover" />
                ) : (
                  <Youtube className="w-3 h-3" />
                )}
              </div>
              <span className="text-slate-400 font-normal">YouTube Account:</span>
              <span className="font-semibold text-white max-w-[180px] truncate">
                {selectedAccount?.account_name || channelTitle || 'Connected Channel'}
              </span>
            </div>
          ) : null}

          <button
            type="button"
            onClick={handleRefresh}
            disabled={isLoading || isRefreshing || accounts.length === 0}
            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center space-x-1.5 border border-slate-700 disabled:opacity-50"
            title="Refresh videos from YouTube"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-red-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <Link
            href="/studio"
            className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-red-600/20"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload New Video</span>
          </Link>
        </div>
      </div>

      {/* Search & Stats Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 transform -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search videos by title..."
            className="w-full bg-slate-900/80 border border-slate-800 rounded-xl pl-9 pr-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
          />
        </div>

        <div className="flex items-center space-x-3 text-xs text-slate-400">
          {totalResults !== null && (
            <span className="flex items-center space-x-1 font-mono">
              <Film className="w-3.5 h-3.5 text-slate-500" />
              <span>
                {totalResults} {totalResults === 1 ? 'total video' : 'total videos'}
              </span>
            </span>
          )}
          {searchQuery && (
            <span className="text-slate-400 text-[11px]">
              Showing {filteredVideos.length} of {videos.length} on this page
            </span>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1.5 flex-1">
            <p className="font-bold">Error loading YouTube videos</p>
            <p className="text-slate-300">{errorMsg}</p>
            <button
              type="button"
              onClick={handleRefresh}
              className="mt-1 px-3 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-200 rounded-lg text-xs font-semibold flex items-center space-x-1 w-fit"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        /* Loading Skeleton Grid */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden animate-pulse flex flex-col"
            >
              <div className="aspect-video bg-slate-800/70" />
              <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="h-4 bg-slate-800 rounded w-5/6" />
                  <div className="h-3 bg-slate-800/60 rounded w-2/3" />
                </div>
                <div className="flex items-center justify-between pt-2">
                  <div className="h-6 bg-slate-800/80 rounded w-16" />
                  <div className="h-6 bg-slate-800/80 rounded w-20" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : accounts.length === 0 && !isAccountsLoading ? (
        /* Zero Connected Accounts Empty State */
        <div className="py-16 text-center rounded-2xl bg-slate-900/40 border border-slate-800/60 p-8 space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-red-600/10 text-red-400 border border-red-500/20 flex items-center justify-center mx-auto shadow-inner">
            <Youtube className="w-7 h-7" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="text-sm font-bold text-white">No YouTube Account Connected</h3>
            <p className="text-xs text-slate-400">
              Connect your YouTube channel in Meta & Social Connections to view, manage, and edit your videos.
            </p>
          </div>
          <Link
            href="/meta-connect"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold transition shadow-md shadow-red-600/20"
          >
            <Youtube className="w-4 h-4" />
            <span>Connect YouTube Account</span>
          </Link>
        </div>
      ) : !errorMsg && filteredVideos.length === 0 ? (
        /* Empty State */
        <div className="py-16 text-center rounded-2xl bg-slate-900/40 border border-slate-800/60 p-8 space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-red-600/10 text-red-400 border border-red-500/20 flex items-center justify-center mx-auto shadow-inner">
            <Film className="w-7 h-7" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="text-sm font-bold text-white">
              {searchQuery ? 'No matching videos found' : 'No videos found on channel'}
            </h3>
            <p className="text-xs text-slate-400">
              {searchQuery
                ? `No videos on this page matched "${searchQuery}". Try clearing your search.`
                : 'Upload your first YouTube video using the Studio composer to manage it here.'}
            </p>
          </div>
          {searchQuery ? (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
            >
              Clear Search
            </button>
          ) : (
            <Link
              href="/studio"
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold transition shadow-md shadow-red-600/20"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Go to Studio</span>
            </Link>
          )}
        </div>
      ) : (
        /* Video Cards Grid */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredVideos.map((video) => (
            <div
              key={video.video_id}
              className="bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-2xl overflow-hidden transition duration-200 flex flex-col group shadow-sm hover:shadow-lg hover:shadow-red-950/20"
            >
              {/* Thumbnail Container */}
              <div className="relative aspect-video bg-black overflow-hidden flex items-center justify-center">
                {video.thumbnail_url ? (
                  <img
                    src={video.thumbnail_url}
                    alt={video.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-slate-600 space-y-1">
                    <Film className="w-8 h-8" />
                    <span className="text-[10px]">No Thumbnail</span>
                  </div>
                )}

                {/* Privacy Badge on Thumbnail */}
                <div className="absolute top-2.5 left-2.5">
                  {renderPrivacyBadge(video.privacy_status)}
                </div>

                {/* Video ID Tag */}
                <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/80 backdrop-blur-sm text-[9px] font-mono text-slate-300 border border-white/10">
                  {video.video_id}
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                <div className="space-y-1.5">
                  <h3
                    className="text-xs font-bold text-white line-clamp-2 leading-snug group-hover:text-red-300 transition"
                    title={video.title}
                  >
                    {video.title || 'Untitled Video'}
                  </h3>

                  <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    <span>{formatDate(video.published_at)}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => handleOpenEdit(video.video_id)}
                    className="flex-1 py-1.5 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center justify-center space-x-1 border border-slate-700 hover:border-slate-600"
                  >
                    <Sliders className="w-3 h-3 text-red-400" />
                    <span>Edit</span>
                  </button>

                  <a
                    href={video.video_url || `https://www.youtube.com/watch?v=${video.video_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="py-1.5 px-2.5 rounded-lg bg-slate-800/60 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition flex items-center justify-center space-x-1 border border-slate-700/60"
                    title="Watch on YouTube"
                  >
                    <ExternalLink className="w-3 h-3 text-slate-400" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Footer */}
      {(tokenStack.length > 0 || nextPageToken) && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-800/80">
          <button
            type="button"
            onClick={handlePrevPage}
            disabled={tokenStack.length === 0 || isLoading}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center space-x-1.5 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous Page</span>
          </button>

          <span className="text-xs text-slate-400 font-mono">
            Page {tokenStack.length + 1}
          </span>

          <button
            type="button"
            onClick={handleNextPage}
            disabled={!nextPageToken || isLoading}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center space-x-1.5 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Next Page</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Edit Video Modal */}
      {editingVideoId && isEditModalOpen && (
        <YouTubeVideoEditModal
          isOpen={isEditModalOpen}
          onClose={() => {
            setIsEditModalOpen(false);
            setEditingVideoId(null);
          }}
          videoId={editingVideoId}
          channelTitle={channelTitle}
          onVideoUpdated={handleVideoUpdated}
        />
      )}
    </div>
  );
}
