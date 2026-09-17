'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  TrendingUp, 
  Users, 
  Eye, 
  Calendar,
  Facebook,
  Instagram,
  RefreshCw,
  Sparkles,
  Layers,
  Share2,
  Filter,
  BarChart3,
  ArrowRight,
  MessageSquare,
  Radio
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { apiClient } from '@/lib/api';
import { SocialAccount } from '@/lib/types';

interface MetricOverview {
  total_posts: number;
  published_posts: number;
  scheduled_posts: number;
  failed_posts: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_reach: number;
  total_impressions: number;
  avg_engagement_rate: number;
}

interface DailyMetricPoint {
  date: string;
  reach: number;
  impressions: number;
  engagement: number;
}

interface AccountInsight {
  id: number;
  account_id: string;
  account_name: string;
  platform: 'facebook' | 'instagram' | 'youtube' | string;
  logo_url?: string;
  followers_count: number;
  fan_count?: number;
  media_count?: number;
  category?: string;
  status: string;
  link?: string;
}

interface AnalyticsData {
  overview: MetricOverview;
  daily_trends: DailyMetricPoint[];
  accounts_list?: AccountInsight[];
  is_live_meta?: boolean;
}

export default function AnalyticsDashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch multi-account social destinations
      const accRes = await apiClient.get('/social-accounts/');
      if (Array.isArray(accRes.data)) {
        const fakeIds = new Set(['109823471029', '17841400928371', '17841400928372', '17841400928373', '109823471030', 'sandbox']);
        const realAccs = accRes.data.filter(a => !fakeIds.has(a.account_id));
        setSocialAccounts(realAccs);
      }

      // 2. Fetch multi-account aggregated overview analytics
      const res = await apiClient.get('/analytics/overview');
      setData(res.data);
    } catch (e) {
      console.warn('Backend analytics query:', e);
      setData({
        overview: {
          total_posts: 0,
          published_posts: 0,
          scheduled_posts: 0,
          failed_posts: 0,
          total_likes: 0,
          total_comments: 0,
          total_shares: 0,
          total_reach: 0,
          total_impressions: 0,
          avg_engagement_rate: 0.0,
        },
        daily_trends: [],
        is_live_meta: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  // Filter analytics by selected profile dropdown
  const filteredAccounts = selectedAccountId === 'all'
    ? (data?.accounts_list || socialAccounts.map(a => ({
        id: a.id,
        account_id: a.account_id,
        account_name: a.account_name,
        platform: a.platform,
        logo_url: a.logo_url,
        followers_count: 0,
        status: a.status,
        link: a.platform === 'facebook' ? `https://facebook.com/${a.account_id}` : `https://instagram.com/${a.account_name.replace('@', '')}`
      })))
    : (data?.accounts_list || []).filter(a => String(a.id) === selectedAccountId || a.account_id === selectedAccountId);

  const overview = data?.overview;
  const totalFollowersAll = filteredAccounts.reduce((acc, curr) => acc + (curr.followers_count || 0), 0);

  return (
    <div className="space-y-6 select-none font-sans text-sm">
      {/* ── Page Header ────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              Social Analytics
            </h1>
            <span className="inline-flex items-center space-x-1.5 text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>{socialAccounts.length} Connected</span>
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Understand how your connected social profiles, reach, impressions, and published content are performing.
          </p>
        </div>

        <div className="flex items-center space-x-2.5 flex-shrink-0">
          {/* Account Filter Dropdown */}
          <div className="flex items-center space-x-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-lg shadow-xs">
            <Filter className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="bg-transparent text-sm font-semibold text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
                All Profiles ({socialAccounts.length})
              </option>
              {socialAccounts.map((acc) => (
                <option key={acc.id} value={acc.id} className="bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
                  {acc.platform === 'facebook' ? 'Facebook' : 'Instagram'}: {acc.account_name}
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchAnalytics}
            className="p-2 rounded-lg bg-white hover:bg-slate-50 dark:bg-slate-900 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 transition-colors shadow-xs"
            title="Refresh Live Metrics"
            aria-label="Refresh live analytics"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-600 dark:text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── Connected Profile Summary ─────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Share2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Connected Profiles ({filteredAccounts.length})
            </h2>
          </div>
          <Link 
            href="/meta-connect" 
            className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 font-semibold hover:underline flex items-center space-x-1"
          >
            <span>Manage Connections</span>
            <span>→</span>
          </Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs animate-pulse space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800 flex-shrink-0" />
                  <div className="space-y-1.5 flex-1">
                    <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-3/4" />
                    <div className="h-2.5 bg-slate-100 dark:bg-slate-800/60 rounded w-1/2" />
                  </div>
                </div>
                <div className="flex items-center justify-between pt-2.5 border-t border-slate-100 dark:border-slate-800">
                  <div className="h-4 bg-slate-100 dark:bg-slate-800/50 rounded w-1/3" />
                  <div className="h-4 bg-slate-100 dark:bg-slate-800/50 rounded w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredAccounts.length === 0 ? (
          <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-6 text-center space-y-3 shadow-xs max-w-lg mx-auto">
            <div className="w-11 h-11 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/60 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mx-auto shadow-xs">
              <Share2 className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                No social profiles connected
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
                Connect your Facebook Pages and Instagram accounts to start tracking live reach, impressions, and publishing metrics.
              </p>
            </div>
            <div className="pt-1">
              <Link 
                href="/meta-connect" 
                className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors shadow-xs"
              >
                <span>Connect Meta Accounts</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {filteredAccounts.map((acc: any) => {
              const isFb = acc.platform === 'facebook';
              return (
                <div 
                  key={acc.id || acc.account_id} 
                  className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center space-x-3 min-w-0">
                      <img
                        src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                        alt={acc.account_name}
                        className="w-10 h-10 rounded-xl object-cover border border-slate-200 dark:border-slate-700 flex-shrink-0"
                      />
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center space-x-1.5">
                          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                            {acc.account_name}
                          </h3>
                          {isFb ? (
                            <Facebook className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                          ) : (
                            <Instagram className="w-3.5 h-3.5 text-pink-600 dark:text-pink-400 flex-shrink-0" />
                          )}
                        </div>
                        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate">
                          ID: {acc.account_id}
                        </p>
                      </div>
                    </div>

                    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 text-xs font-semibold flex-shrink-0">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span>Active</span>
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-2.5 border-t border-slate-100 dark:border-slate-800/60 text-xs">
                    <div className="flex items-baseline space-x-1.5">
                      <span className="text-slate-500 dark:text-slate-400 font-medium">Followers</span>
                      <span className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                        {(acc.followers_count || 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-baseline space-x-1.5">
                      <span className="text-slate-500 dark:text-slate-400 font-medium">Posts</span>
                      <span className="font-bold font-mono text-indigo-600 dark:text-indigo-400 text-sm">
                        {acc.media_count != null ? acc.media_count.toLocaleString() : 'Unavailable'}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Primary KPI Metrics Grid ──────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Total Followers / Audience */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-2.5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Total Audience
            </span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="space-y-0.5">
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              {totalFollowersAll.toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              FB Page Fans + IG Followers
            </p>
          </div>
        </div>

        {/* KPI 2: Posts Published via SocialAI */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-2.5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Published Posts
            </span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-500/15 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="space-y-0.5">
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              {(overview?.published_posts || overview?.total_posts || 0).toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Content published via SocialAI
            </p>
          </div>
        </div>

        {/* KPI 3: Total Reach */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-2.5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Total Reach
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Eye className="w-4 h-4" />
            </div>
          </div>
          <div className="space-y-0.5">
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              {(overview?.total_reach || 0).toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Unique accounts reached across feeds
            </p>
          </div>
        </div>

        {/* KPI 4: Total Impressions */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-2.5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Total Impressions
            </span>
            <div className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-500/15 flex items-center justify-center text-sky-600 dark:text-sky-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="space-y-0.5">
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              {(overview?.total_impressions || 0).toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Total content displays across feeds
            </p>
          </div>
        </div>
      </div>

      {/* ── Performance & Reach Trend Chart ───────────────────────────── */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/80 pb-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Performance & Reach Trend
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Daily breakdown of reach vs impressions across connected destinations
            </p>
          </div>
          <div className="flex items-center space-x-4 text-xs font-medium">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
              <span className="text-slate-700 dark:text-slate-300 font-semibold">Reach</span>
            </span>
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
              <span className="text-slate-700 dark:text-slate-300 font-semibold">Impressions</span>
            </span>
          </div>
        </div>

        {data?.daily_trends && data.daily_trends.length > 0 ? (
          <div className="h-68 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily_trends} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorReach" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorImpressions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800" vertical={false} />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: 'var(--bg-surface, #ffffff)', 
                    borderColor: 'var(--border-subtle, #e2e8f0)', 
                    borderRadius: '12px', 
                    fontSize: '12px', 
                    color: 'var(--text-primary, #0f172a)',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                  }}
                  itemStyle={{ color: 'var(--text-primary, #0f172a)' }}
                />
                <Area type="monotone" dataKey="reach" stroke="#6366f1" strokeWidth={2.5} fillOpacity={1} fill="url(#colorReach)" />
                <Area type="monotone" dataKey="impressions" stroke="#38bdf8" strokeWidth={2.5} fillOpacity={1} fill="url(#colorImpressions)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="py-12 px-6 rounded-xl bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 text-center space-y-3">
            <div className="w-10 h-10 rounded-xl bg-slate-200/80 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 mx-auto">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                No performance trend data yet
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
                Publish content in the Studio to start recording live reach, impressions, and engagement metrics.
              </p>
            </div>
            <div className="pt-1">
              <Link 
                href="/studio" 
                className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors shadow-xs"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>+ Create First Post</span>
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* ── Workspace Quick Action Launchpad ──────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
        <Link
          href="/studio"
          className="group bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs hover:border-indigo-300 dark:hover:border-indigo-800/80 transition-colors flex flex-col justify-between space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
              →
            </span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
              Creator Studio
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Draft, compose, and publish multi-platform graphics, reels & stories.
            </p>
          </div>
        </Link>

        <Link
          href="/posts"
          className="group bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs hover:border-blue-300 dark:hover:border-blue-800/80 transition-colors flex flex-col justify-between space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-500/15 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <Calendar className="w-4 h-4" />
            </div>
            <span className="text-slate-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              →
            </span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              Post Scheduler
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Manage scheduled publication queue and automated publishing calendar.
            </p>
          </div>
        </Link>

        <Link
          href="/comments"
          className="group bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs hover:border-emerald-300 dark:hover:border-emerald-800/80 transition-colors flex flex-col justify-between space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <MessageSquare className="w-4 h-4" />
            </div>
            <span className="text-slate-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
              →
            </span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
              Comment Inbox
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Engage with audience responses and configure automated comment replies.
            </p>
          </div>
        </Link>
      </div>
    </div>
  );
}
