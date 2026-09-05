'use client';

import React from 'react';
import { Search, Filter, Sparkles, FileText, Target, MessageSquare, ArrowUpDown } from 'lucide-react';

interface FilterBarProps {
  activeTab: 'posts' | 'ads' | 'stream';
  onTabChange: (tab: 'posts' | 'ads' | 'stream') => void;
  replyStatusFilter: 'all' | 'unreplied' | 'replied';
  onReplyStatusChange: (status: 'all' | 'unreplied' | 'replied') => void;
  sortOrder?: 'desc' | 'asc';
  onSortOrderChange?: (sort: 'desc' | 'asc') => void;
  adStatusFilter?: 'all' | 'active' | 'paused';
  onAdStatusChange?: (status: 'all' | 'active' | 'paused') => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSearchSubmit: () => void;
  platformFilter?: string;
  onPlatformChange?: (platform: string) => void;
}

export default function EngagementFilterBar({
  activeTab,
  onTabChange,
  replyStatusFilter,
  onReplyStatusChange,
  sortOrder = 'desc',
  onSortOrderChange,
  adStatusFilter = 'all',
  onAdStatusChange,
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  platformFilter = 'ALL',
  onPlatformChange,
}: FilterBarProps) {
  return (
    <div className="space-y-3">
      {/* Top Row: Content Source Tabs & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/70 p-3 rounded-2xl border border-slate-800/90 shadow-sm">
        {/* Content Type Toggles */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 md:pb-0">
          <button
            onClick={() => onTabChange('posts')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'posts'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Organic Posts</span>
          </button>

          <button
            onClick={() => onTabChange('ads')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'ads'
                ? 'bg-purple-600 text-white shadow-sm'
                : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/60'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            <span>Meta Ads</span>
          </button>

          <button
            onClick={() => onTabChange('stream')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 whitespace-nowrap ${
              activeTab === 'stream'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/60'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>All Conversations Stream</span>
          </button>
        </div>

        {/* Search Input Box */}
        <div className="flex items-center space-x-2">
          <div className="relative flex-1 md:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit()}
              placeholder="Search content or caption..."
              className="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 text-xs rounded-xl pl-8 pr-3 py-2 text-slate-100 placeholder-slate-500 outline-none transition"
            />
          </div>

          {onPlatformChange && (
            <select
              value={platformFilter}
              onChange={(e) => onPlatformChange(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-2.5 py-2 font-semibold outline-none focus:border-indigo-500 transition cursor-pointer"
            >
              <option value="ALL">All Platforms</option>
              <option value="FACEBOOK">Facebook</option>
              <option value="INSTAGRAM">Instagram</option>
            </select>
          )}
        </div>
      </div>

      {/* Bottom Row: Filter Pills & Sorting */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 overflow-x-auto pb-1">
        <div className="flex flex-wrap items-center gap-3">
          {/* Dedicated Meta Ad Status Filter — Displayed ONLY on Meta Ads Tab */}
          {activeTab === 'ads' && onAdStatusChange && (
            <div className="flex items-center space-x-2 border-r border-slate-800/80 pr-3">
              <span className="text-[11px] font-bold text-purple-400 uppercase tracking-wider flex items-center space-x-1">
                <Target className="w-3 h-3 text-purple-400" />
                <span>Ad Status:</span>
              </span>

              <button
                onClick={() => onAdStatusChange('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  adStatusFilter === 'all'
                    ? 'bg-purple-950 text-purple-200 border border-purple-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                All Ads
              </button>

              <button
                onClick={() => onAdStatusChange('active')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                  adStatusFilter === 'active'
                    ? 'bg-emerald-950 text-emerald-200 border border-emerald-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>Active</span>
              </button>

              <button
                onClick={() => onAdStatusChange('paused')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                  adStatusFilter === 'paused'
                    ? 'bg-amber-950 text-amber-200 border border-amber-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>Paused</span>
              </button>
            </div>
          )}

          {/* Thread Status Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center space-x-1">
              <Filter className="w-3 h-3 text-slate-500" />
              <span>Thread Status:</span>
            </span>

            <button
              onClick={() => onReplyStatusChange('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                replyStatusFilter === 'all'
                  ? 'bg-indigo-950 text-indigo-200 border border-indigo-700/80 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
              }`}
            >
              All Threads
            </button>

            <button
              onClick={() => onReplyStatusChange('unreplied')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                replyStatusFilter === 'unreplied'
                  ? 'bg-amber-950 text-amber-200 border border-amber-700/80 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              <span>Unreplied</span>
            </button>

            <button
              onClick={() => onReplyStatusChange('replied')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
                replyStatusFilter === 'replied'
                  ? 'bg-emerald-950 text-emerald-200 border border-emerald-700/80 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>Replied</span>
            </button>
          </div>

          {/* Dedicated Sort Order Controls */}
          {onSortOrderChange && (
            <div className="flex items-center space-x-2 border-l border-slate-800/80 pl-3">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center space-x-1">
                <ArrowUpDown className="w-3 h-3 text-slate-500" />
                <span>Sort:</span>
              </span>

              <button
                onClick={() => onSortOrderChange('desc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sortOrder === 'desc'
                    ? 'bg-indigo-950 text-indigo-200 border border-indigo-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                Newest First
              </button>

              <button
                onClick={() => onSortOrderChange('asc')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sortOrder === 'asc'
                    ? 'bg-indigo-950 text-indigo-200 border border-indigo-700/80 shadow-sm'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                }`}
              >
                Oldest First
              </button>
            </div>
          )}
        </div>

        {/* Future AI Priority Filter Pill Placeholder */}
        <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-slate-500 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800/60 opacity-75 whitespace-nowrap self-start sm:self-auto">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Needs Attention (AI Priority Ready)</span>
        </div>
      </div>
    </div>
  );
}
