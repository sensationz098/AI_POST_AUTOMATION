'use client';

import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  Users, 
  Eye, 
  Heart, 
  MessageSquare, 
  Calendar,
  Facebook,
  Instagram,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Layers,
  Share2,
  Filter
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
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
  platform: 'facebook' | 'instagram';
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
    <div className="space-y-6 select-none font-sans text-xs">
      {/* SaaS Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/60">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <h1 className="text-lg font-bold text-slate-100 tracking-tight">
              Multi-Account Social Analytics
            </h1>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
              ● Active Meta API ({socialAccounts.length} Connected)
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Real-time performance, reach, impressions & engagement aggregated across all your connected Facebook Pages and Instagram accounts.
          </p>
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          {/* Account Switcher Dropdown */}
          <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
            <Filter className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="bg-transparent text-xs text-indigo-300 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900 text-slate-100">
                🌐 All Connected Profiles ({socialAccounts.length})
              </option>
              {socialAccounts.map((acc) => (
                <option key={acc.id} value={acc.id} className="bg-slate-900 text-slate-100">
                  {acc.platform === 'facebook' ? '📘' : '📸'} {acc.account_name} ({acc.platform})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={fetchAnalytics}
            className="p-2 rounded-lg bg-slate-900/60 hover:bg-slate-800 border border-slate-800 text-slate-300 transition"
            title="Refresh Live Metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>

          <a
            href="/studio"
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>+ Create Post</span>
          </a>
        </div>
      </div>

      {/* Connected Accounts Overview Cards Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-200 flex items-center space-x-2">
            <Share2 className="w-4 h-4 text-indigo-400" />
            <span>Connected Social Profiles ({filteredAccounts.length})</span>
          </h2>
          <a href="/meta-connect" className="text-[10px] text-indigo-400 hover:underline">
            Manage Connections →
          </a>
        </div>

        {filteredAccounts.length === 0 ? (
          <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 text-center space-y-2">
            <p className="text-xs text-slate-400">No social accounts connected yet.</p>
            <a href="/meta-connect" className="inline-block px-3 py-1.5 rounded bg-indigo-600 text-white font-bold text-xs">
              Connect Meta Accounts
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredAccounts.map((acc: any) => (
              <div key={acc.id || acc.account_id} className="linear-card p-3.5 rounded-xl space-y-3 border border-slate-800/80 hover:border-slate-700 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5 min-w-0">
                    <img
                      src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                      alt={acc.account_name}
                      className="w-8 h-8 rounded-lg object-cover border border-slate-700 flex-shrink-0"
                    />
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-slate-100 truncate flex items-center space-x-1">
                        <span>{acc.account_name}</span>
                        {acc.platform === 'facebook' ? (
                          <Facebook className="w-3 h-3 text-blue-400 fill-blue-400/20 flex-shrink-0" />
                        ) : (
                          <Instagram className="w-3 h-3 text-pink-400 flex-shrink-0" />
                        )}
                      </h4>
                      <span className="text-[10px] font-mono text-slate-400">ID: {acc.account_id}</span>
                    </div>
                  </div>

                  <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 text-[9px] font-mono flex-shrink-0">
                    ● Active
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/60">
                  <div className="bg-slate-900/50 p-2 rounded border border-slate-800/60">
                    <span className="text-[9px] text-slate-400">No. of Followers</span>
                    <p className="text-xs font-bold text-slate-100 mt-0.5">
                      {(acc.followers_count || 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded border border-slate-800/60">
                    <span className="text-[9px] text-slate-400">Platform Posts</span>
                    <p className="text-xs font-bold text-indigo-300 mt-0.5 font-mono">
                      {(acc.media_count ?? 0).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Primary KPI Grid Cards: Followers & Published Posts Focus */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* KPI 1: Total Followers */}
        <div className="linear-card p-4 rounded-xl space-y-2 border border-indigo-500/30">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold text-slate-200">Total Followers</span>
            <Users className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">
              {totalFollowersAll.toLocaleString()}
            </h2>
          </div>
          <p className="text-[10px] text-slate-400">FB Page Fans + IG Followers</p>
        </div>

        {/* KPI 2: Posts Published via SocialAI */}
        <div className="linear-card p-4 rounded-xl space-y-2 border border-blue-500/30">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold text-slate-200">Posts Published via SocialAI</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">
              {overview?.published_posts || overview?.total_posts || 0}
            </h2>
          </div>
          <p className="text-[10px] text-slate-400">Total posts published through SocialAI</p>
        </div>

        {/* KPI 3: Total Reach */}
        <div className="linear-card p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-medium">Total Reach</span>
            <Eye className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">
              {(overview?.total_reach || 0).toLocaleString()}
            </h2>
          </div>
          <p className="text-[10px] text-slate-400">Combined audience across pages</p>
        </div>

        {/* KPI 4: Total Impressions */}
        <div className="linear-card p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-medium">Total Impressions</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">
              {(overview?.total_impressions || 0).toLocaleString()}
            </h2>
          </div>
          <p className="text-[10px] text-slate-400">Total content displays on feed</p>
        </div>
      </div>

      {/* Interactive Recharts Analytics Chart */}
      <div className="linear-card p-5 rounded-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-100">Performance & Reach Trend</h3>
            <p className="text-[10px] text-slate-400">Daily breakdown of reach vs impressions across connected destinations</p>
          </div>
          <div className="flex items-center space-x-3 text-[10px] font-mono">
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              <span className="text-slate-300">Reach</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span className="text-slate-300">Impressions</span>
            </span>
          </div>
        </div>

        {data?.daily_trends && data.daily_trends.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily_trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorReach" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorImpressions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                  itemStyle={{ color: '#f8fafc' }}
                />
                <Area type="monotone" dataKey="reach" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorReach)" />
                <Area type="monotone" dataKey="impressions" stroke="#38bdf8" strokeWidth={2} fillOpacity={1} fill="url(#colorImpressions)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800 text-center space-y-2">
            <p className="text-xs text-slate-400 font-medium">No performance trend data recorded yet.</p>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              Create and publish posts in the Studio to start recording live reach, impressions, and engagement metrics.
            </p>
            <a href="/studio" className="inline-block px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition mt-1">
              + Create First Post
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
