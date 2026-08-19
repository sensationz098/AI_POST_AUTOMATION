'use client';

import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  Users, 
  Eye, 
  Layers,
  Facebook,
  Instagram,
  RefreshCw,
  Plus,
  Filter,
  Share2
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
import Link from 'next/link';

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
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const accRes = await apiClient.get('/social-accounts/');
      if (Array.isArray(accRes.data)) {
        const fakeIds = new Set(['109823471029', '17841400928371', '17841400928372', '17841400928373', '109823471030', 'sandbox']);
        const realAccs = accRes.data.filter(a => !fakeIds.has(a.account_id));
        setSocialAccounts(realAccs);
      }

      const res = await apiClient.get('/analytics/overview');
      setData(res.data);
    } catch (e) {
      console.warn('Backend analytics query error:', e);
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
          avg_engagement_rate: 0,
        },
        daily_trends: [],
        accounts_list: [],
        is_live_meta: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const filteredAccounts = selectedAccountId === 'all'
    ? (data?.accounts_list || socialAccounts.map(a => ({
        id: a.id,
        account_id: a.account_id,
        account_name: a.account_name,
        platform: a.platform,
        logo_url: a.logo_url,
        followers_count: 0,
        status: a.status,
      })))
    : (data?.accounts_list || []).filter(a => String(a.id) === selectedAccountId || a.account_id === selectedAccountId);

  const overview = data?.overview;
  const totalFollowersAll = filteredAccounts.reduce((acc, curr) => acc + (curr.followers_count || 0), 0);

  return (
    <div className="space-y-6 font-sans text-xs">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Performance metrics, audience growth & publishing analytics across Meta channels.
          </p>
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          <div className="flex items-center space-x-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] px-3 py-2 rounded-md">
            <Filter className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="bg-transparent text-xs text-[var(--text-primary)] font-medium focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-[var(--bg-secondary)] text-[var(--text-primary)]">
                All Social Accounts ({socialAccounts.length})
              </option>
              {socialAccounts.map((acc) => (
                <option key={acc.id} value={acc.id} className="bg-[var(--bg-secondary)] text-[var(--text-primary)]">
                  {acc.account_name} ({acc.platform})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={fetchAnalytics}
            className="p-2.5 rounded-md bg-[var(--bg-secondary)] border border-[var(--border-color)] hover:border-[var(--text-tertiary)] text-[var(--text-secondary)] transition"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-[var(--accent-color)]' : ''}`} />
          </button>

          <Link
            href="/studio"
            className="btn-primary text-xs py-2 px-3.5 space-x-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Post</span>
          </Link>
        </div>
      </div>

      {/* Hero Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Total Reach */}
        <div className="pub-card p-5 space-y-2">
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span className="text-xs font-medium">Total Reach</span>
            <Eye className="w-4 h-4 text-[var(--accent-color)]" />
          </div>
          <h2 className="text-3xl font-bold text-[var(--text-primary)] tracking-tight">
            {(overview?.total_reach || 0).toLocaleString()}
          </h2>
          <p className="text-xs text-[var(--text-tertiary)]">Live Meta Graph reach</p>
        </div>

        {/* Metric 2: Engagement Rate */}
        <div className="pub-card p-5 space-y-2">
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span className="text-xs font-medium">Engagement Rate</span>
            <TrendingUp className="w-4 h-4 text-[var(--success-color)]" />
          </div>
          <h2 className="text-3xl font-bold text-[var(--text-primary)] tracking-tight">
            {overview?.avg_engagement_rate || 0}%
          </h2>
          <p className="text-xs text-[var(--text-tertiary)]">Calculated from post interactions</p>
        </div>

        {/* Metric 3: Total Audience */}
        <div className="pub-card p-5 space-y-2">
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span className="text-xs font-medium">Total Followers</span>
            <Users className="w-4 h-4 text-[var(--accent-color)]" />
          </div>
          <h2 className="text-3xl font-bold text-[var(--text-primary)] tracking-tight">
            {totalFollowersAll.toLocaleString()}
          </h2>
          <p className="text-xs text-[var(--text-tertiary)]">FB Fans + IG Followers</p>
        </div>

        {/* Metric 4: Published Content */}
        <div className="pub-card p-5 space-y-2">
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span className="text-xs font-medium">Published Posts</span>
            <Layers className="w-4 h-4 text-[var(--accent-color)]" />
          </div>
          <h2 className="text-3xl font-bold text-[var(--text-primary)] tracking-tight">
            {overview?.published_posts || 0}
          </h2>
          <p className="text-xs text-[var(--text-tertiary)]">{overview?.scheduled_posts || 0} scheduled in queue</p>
        </div>
      </div>

      {/* Chart Area */}
      <div className="pub-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-[var(--text-primary)]">Reach & Impression Trends</h3>
            <p className="text-xs text-[var(--text-secondary)]">Daily audience performance breakdown across connected channels</p>
          </div>
          <div className="flex items-center space-x-4 text-xs font-mono text-[var(--text-secondary)]">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-color)]" />
              <span>Reach</span>
            </span>
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--info-color)]" />
              <span>Impressions</span>
            </span>
          </div>
        </div>

        {isMounted && data?.daily_trends && data.daily_trends.length > 0 ? (
          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily_trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-tertiary)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-tertiary)" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '6px',
                    color: 'var(--text-primary)',
                    fontSize: '12px'
                  }}
                />
                <Area type="monotone" dataKey="reach" stroke="var(--accent-color)" strokeWidth={2} fill="transparent" />
                <Area type="monotone" dataKey="impressions" stroke="var(--info-color)" strokeWidth={2} fill="transparent" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-48 w-full border border-dashed border-[var(--border-color)] rounded-lg flex flex-col items-center justify-center p-6 text-center text-[var(--text-secondary)]">
            <TrendingUp className="w-8 h-8 text-[var(--text-tertiary)] mb-2" />
            <p className="font-semibold text-xs text-[var(--text-primary)]">No trend data available yet</p>
            <p className="text-[11px] text-[var(--text-tertiary)] mt-1">Publish content via the Studio to start recording audience reach & impressions.</p>
          </div>
        )}
      </div>

      {/* Connected Accounts Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center space-x-2">
            <Share2 className="w-4 h-4 text-[var(--accent-color)]" />
            <span>Connected Social Channels ({filteredAccounts.length})</span>
          </h3>
          <Link href="/meta-connect" className="btn-tertiary text-xs">
            Manage Channels →
          </Link>
        </div>

        {filteredAccounts.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredAccounts.map((acc: any) => (
              <div key={acc.id || acc.account_id} className="pub-card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 min-w-0">
                    <img
                      src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                      alt={acc.account_name}
                      className="w-8 h-8 rounded object-cover border border-[var(--border-color)] flex-shrink-0"
                    />
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-[var(--text-primary)] truncate flex items-center space-x-1">
                        <span>{acc.account_name}</span>
                        {acc.platform === 'facebook' ? (
                          <Facebook className="w-3.5 h-3.5 text-[#1877F2] flex-shrink-0" />
                        ) : (
                          <Instagram className="w-3.5 h-3.5 text-[#E4405F] flex-shrink-0" />
                        )}
                      </h4>
                      <span className="text-[11px] font-mono text-[var(--text-tertiary)]">ID: {acc.account_id}</span>
                    </div>
                  </div>

                  <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--success-color)] text-[10px] font-mono font-medium border border-[var(--border-color)]">
                    Active
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="pub-card p-6 text-center space-y-3">
            <Share2 className="w-8 h-8 text-[var(--text-tertiary)] mx-auto" />
            <div>
              <p className="font-semibold text-xs text-[var(--text-primary)]">No Meta Channels Connected</p>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                Connect your Facebook Page or Instagram Business account to sync live audience metrics.
              </p>
            </div>
            <Link href="/meta-connect" className="btn-primary text-xs py-2 px-4 inline-flex">
              Connect Meta Channel
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
