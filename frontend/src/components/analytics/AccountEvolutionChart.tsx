'use client';

import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { 
  Users, 
  Layers, 
  Eye, 
  TrendingUp, 
  Info, 
  Calendar,
  Sparkles,
  Instagram,
  Facebook,
  Youtube
} from 'lucide-react';
import { 
  AccountSnapshotPoint, 
  GrowthMetrics, 
  OverviewReportResponse, 
  formatMetricNumber 
} from '@/lib/analyticsApi';
import { EvolutionKpiCards } from './EvolutionKpiCards';

export type EvolutionMetricTab = 'community' | 'account';

interface AccountEvolutionChartProps {
  snapshots: AccountSnapshotPoint[];
  growth?: GrowthMetrics | null;
  overview?: OverviewReportResponse | null;
  startDate?: string;
  endDate?: string;
  isLoading?: boolean;
}

interface EvolutionDataPoint {
  date: string;
  displayDate: string;
  // Total aggregations for chart rendering (numeric for Recharts domain)
  followers: number;
  reach: number;
  impressions: number;
  // Raw metrics preserving strict null vs zero semantics
  rawFollowers: number | null;
  rawReach: number | null;
  rawImpressions: number | null;
  // Platform-specific breakdowns (only present if reported)
  instagramFollowers?: number | null;
  facebookFollowers?: number | null;
  youtubeFollowers?: number | null;
  instagramReach?: number | null;
  facebookReach?: number | null;
  youtubeViews?: number | null;
  accountsCount: number;
}

export const AccountEvolutionChart: React.FC<AccountEvolutionChartProps> = ({
  snapshots,
  growth,
  overview,
  startDate,
  endDate,
  isLoading,
}) => {
  const [activeTab, setActiveTab] = useState<EvolutionMetricTab>('community');

  // Aggregate and align snapshot data by date with platform breakdowns
  const chartData: EvolutionDataPoint[] = useMemo(() => {
    if (!snapshots || snapshots.length === 0) return [];

    const dateMap = new Map<
      string,
      {
        followers: number | null;
        reach: number | null;
        impressions: number | null;
        instagramFollowers?: number | null;
        facebookFollowers?: number | null;
        youtubeFollowers?: number | null;
        instagramReach?: number | null;
        facebookReach?: number | null;
        youtubeViews?: number | null;
        accountsCount: number;
      }
    >();

    snapshots.forEach((snap) => {
      const d = snap.snapshot_date;
      const current = dateMap.get(d) || {
        followers: null,
        reach: null,
        impressions: null,
        accountsCount: 0,
      };

      const plat = snap.platform.toLowerCase();

      if (snap.followers_count != null) {
        current.followers = (current.followers ?? 0) + snap.followers_count;
        if (plat === 'instagram') {
          current.instagramFollowers = (current.instagramFollowers ?? 0) + snap.followers_count;
        } else if (plat === 'facebook') {
          current.facebookFollowers = (current.facebookFollowers ?? 0) + snap.followers_count;
        } else if (plat === 'youtube') {
          current.youtubeFollowers = (current.youtubeFollowers ?? 0) + snap.followers_count;
        }
      }

      if (snap.reach != null) {
        current.reach = (current.reach ?? 0) + snap.reach;
        if (plat === 'instagram') {
          current.instagramReach = (current.instagramReach ?? 0) + snap.reach;
        } else if (plat === 'facebook') {
          current.facebookReach = (current.facebookReach ?? 0) + snap.reach;
        }
      }

      if (snap.impressions != null) {
        current.impressions = (current.impressions ?? 0) + snap.impressions;
      }

      if (snap.views_count != null && plat === 'youtube') {
        current.youtubeViews = (current.youtubeViews ?? 0) + snap.views_count;
      }

      current.accountsCount += 1;
      dateMap.set(d, current);
    });

    const sortedDates = Array.from(dateMap.keys()).sort();

    return sortedDates.map((d) => {
      const entry = dateMap.get(d)!;
      let displayDate = d;
      try {
        const parsed = new Date(d + 'T00:00:00');
        displayDate = parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      } catch {
        displayDate = d;
      }

      return {
        date: d,
        displayDate,
        followers: entry.followers ?? 0,
        reach: entry.reach ?? 0,
        impressions: entry.impressions ?? 0,
        rawFollowers: entry.followers,
        rawReach: entry.reach,
        rawImpressions: entry.impressions,
        instagramFollowers: entry.instagramFollowers,
        facebookFollowers: entry.facebookFollowers,
        youtubeFollowers: entry.youtubeFollowers,
        instagramReach: entry.instagramReach,
        facebookReach: entry.facebookReach,
        youtubeViews: entry.youtubeViews,
        accountsCount: entry.accountsCount,
      };
    });
  }, [snapshots]);

  // Tab configurations
  const tabConfig = {
    community: {
      label: 'Community',
      sublabel: 'Followers over time',
      primaryKey: 'followers',
      color: '#6366f1',
      gradientId: 'colorEvolutionFollowers',
      legend: 'Total Followers',
      icon: Users,
    },
    account: {
      label: 'Account',
      sublabel: 'Reach & Impressions trajectory',
      primaryKey: 'reach',
      color: '#10b981',
      gradientId: 'colorEvolutionReach',
      legend: 'Reach',
      icon: Eye,
    },
  };

  const currentTabInfo = tabConfig[activeTab];

  // Calculate dynamic domain
  const yValues = useMemo(() => {
    if (chartData.length === 0) return [0, 100];
    if (activeTab === 'community') return chartData.map((d) => d.followers);
    return chartData.map((d) => Math.max(d.reach, d.impressions));
  }, [chartData, activeTab]);

  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const yDomainMin = Math.max(0, Math.floor(minY * 0.95));
  const yDomainMax = maxY > 0 ? Math.ceil(maxY * 1.05) : 10;

  // Custom Interactive Tooltip
  const renderCustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    const point: EvolutionDataPoint = payload[0].payload;

    return (
      <div className="bg-[#111827] text-white p-3 rounded-xl shadow-xl border border-slate-700 text-xs space-y-2 min-w-[180px]">
        <div className="flex items-center justify-between border-b border-slate-700/80 pb-1.5">
          <span className="font-semibold text-slate-300">{point.date}</span>
          <span className="text-[10px] font-mono text-slate-400">
            {point.accountsCount} {point.accountsCount === 1 ? 'account' : 'accounts'}
          </span>
        </div>

        {/* Selected metric summary */}
        {activeTab === 'community' && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-indigo-400 font-bold">
              <span>Followers:</span>
              <span>{formatMetricNumber(point.rawFollowers)}</span>
            </div>

            {/* Platform breakdown */}
            {(point.instagramFollowers != null || point.facebookFollowers != null || point.youtubeFollowers != null) && (
              <div className="pt-1.5 border-t border-slate-700/50 space-y-1 text-[11px] text-slate-300">
                {point.instagramFollowers != null && (
                  <div className="flex items-center justify-between">
                    <span className="flex items-center space-x-1">
                      <span className="w-2 h-2 rounded-full bg-pink-500 inline-block" />
                      <span>Instagram</span>
                    </span>
                    <span className="font-medium text-slate-200">{formatMetricNumber(point.instagramFollowers)}</span>
                  </div>
                )}
                {point.facebookFollowers != null && (
                  <div className="flex items-center justify-between">
                    <span className="flex items-center space-x-1">
                      <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                      <span>Facebook</span>
                    </span>
                    <span className="font-medium text-slate-200">{formatMetricNumber(point.facebookFollowers)}</span>
                  </div>
                )}
                {point.youtubeFollowers != null && (
                  <div className="flex items-center justify-between">
                    <span className="flex items-center space-x-1">
                      <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                      <span>YouTube</span>
                    </span>
                    <span className="font-medium text-slate-200">{formatMetricNumber(point.youtubeFollowers)}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'account' && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-emerald-400 font-bold">
              <span>Reach:</span>
              <span>{formatMetricNumber(point.rawReach)}</span>
            </div>
            <div className="flex items-center justify-between text-sky-400 font-semibold">
              <span>Impressions:</span>
              <span>{formatMetricNumber(point.rawImpressions)}</span>
            </div>
            {point.youtubeViews != null && (
              <div className="flex items-center justify-between text-red-400 font-semibold">
                <span>YouTube Views:</span>
                <span>{formatMetricNumber(point.youtubeViews)}</span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-5 shadow-xs space-y-5">
      {/* ── Section Header with Navigation Tabs ────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/60 pb-3.5">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              Account Evolution
            </h3>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              {chartData.length} {chartData.length === 1 ? 'day' : 'days'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {currentTabInfo.sublabel}
          </p>
        </div>

        {/* Metric Tabs Switcher */}
        <div className="flex items-center space-x-1.5 self-start md:self-auto bg-slate-100 dark:bg-slate-900/80 p-1 rounded-lg border border-slate-200/80 dark:border-slate-800">
          {(
            [
              { id: 'community', label: 'Community', icon: Users },
              { id: 'account', label: 'Account', icon: Eye },
            ] as const
          ).map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center space-x-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-white dark:bg-[#111827] text-indigo-600 dark:text-indigo-400 font-semibold shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Main Time-Series Chart ────────────────────────────────────── */}
      {chartData.length === 0 ? (
        <div className="py-12 px-6 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 text-center space-y-3">
          <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 mx-auto">
            <Users className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              No historical follower data available for this period
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Daily snapshots are captured automatically by the Celery analytics worker.
            </p>
          </div>
        </div>
      ) : (
        <div className="h-80 w-full pt-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEvolutionFollowers" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorEvolutionReach" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-800/80" vertical={false} />
              <XAxis
                dataKey="displayDate"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[yDomainMin, yDomainMax]}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => formatMetricNumber(v, true)}
              />
              <Tooltip content={renderCustomTooltip} />

              {activeTab === 'community' && (
                <Area
                  type="monotone"
                  dataKey="followers"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorEvolutionFollowers)"
                />
              )}

              {activeTab === 'account' && (
                <>
                  <Area
                    type="monotone"
                    dataKey="reach"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorEvolutionReach)"
                  />
                  <Area
                    type="monotone"
                    dataKey="impressions"
                    stroke="#38bdf8"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    fill="transparent"
                  />
                </>
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── KPI Row Beneath Chart ─────────────────────────────────────── */}
      <EvolutionKpiCards
        overview={overview}
        growth={growth}
        startDate={startDate}
        endDate={endDate}
      />

      {/* ── Non-Deduplicated Arithmetic Sum Disclaimer ────────────────── */}
      <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800/40">
        <Info className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
        <span>
          Followers, reach, and impressions across platforms are arithmetic sums and are not deduplicated unique users.
        </span>
      </div>
    </div>
  );
};
