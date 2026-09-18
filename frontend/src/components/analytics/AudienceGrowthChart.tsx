'use client';

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Users, Info, TrendingUp } from 'lucide-react';
import { AccountSnapshotPoint, formatMetricNumber } from '@/lib/analyticsApi';

interface AudienceGrowthChartProps {
  snapshots: AccountSnapshotPoint[];
  isLoading?: boolean;
}

interface AggregatedChartPoint {
  date: string;
  displayDate: string;
  followers: number;
  reach?: number | null;
  views?: number | null;
  accounts: number;
}

export const AudienceGrowthChart: React.FC<AudienceGrowthChartProps> = ({ snapshots }) => {
  // Aggregate snapshots by date if multiple accounts exist for each day
  const chartData: AggregatedChartPoint[] = React.useMemo(() => {
    if (!snapshots || snapshots.length === 0) return [];

    const dateMap = new Map<string, { followers: number; reach: number; views: number; count: number }>();

    snapshots.forEach((snap) => {
      const dateKey = snap.snapshot_date;
      const current = dateMap.get(dateKey) || { followers: 0, reach: 0, views: 0, count: 0 };

      if (snap.followers_count != null) {
        current.followers += snap.followers_count;
      }
      if (snap.reach != null) {
        current.reach += snap.reach;
      }
      if (snap.views_count != null) {
        current.views += snap.views_count;
      }
      current.count += 1;
      dateMap.set(dateKey, current);
    });

    const sortedDates = Array.from(dateMap.keys()).sort();

    return sortedDates.map((d) => {
      const entry = dateMap.get(d)!;
      // Format display date (e.g. "Sep 18")
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
        followers: entry.followers,
        reach: entry.reach > 0 ? entry.reach : null,
        views: entry.views > 0 ? entry.views : null,
        accounts: entry.count,
      };
    });
  }, [snapshots]);

  if (chartData.length === 0) {
    return (
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-6 shadow-xs space-y-3 text-center">
        <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 mx-auto">
          <Users className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            No audience snapshot history for this period
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
            Historical snapshots are captured daily by the background sync worker.
          </p>
        </div>
      </div>
    );
  }

  // Calculate min and max for clean YAxis domain
  const followerValues = chartData.map((d) => d.followers);
  const minFollowers = Math.min(...followerValues);
  const maxFollowers = Math.max(...followerValues);
  const yDomainMin = Math.max(0, Math.floor(minFollowers * 0.95));
  const yDomainMax = Math.ceil(maxFollowers * 1.05);

  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-5 shadow-xs space-y-4">
      {/* Chart Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800/60 pb-3">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Audience Growth Trend
            </h3>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              {chartData.length} {chartData.length === 1 ? 'day' : 'days'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Daily historical follower trajectory across active channels.
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs font-medium">
          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-600" />
            <span className="text-slate-700 dark:text-slate-300 font-medium">Followers</span>
          </span>
        </div>
      </div>

      {/* Chart Render */}
      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorFollowers" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
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
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                borderColor: '#374151',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#f9fafb',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
              labelStyle={{ color: '#9ca3af', fontWeight: 600, marginBottom: '4px' }}
              formatter={(value: any) => [
                Number(value).toLocaleString(),
                'Followers',
              ]}
              labelFormatter={(label: any, payload: any) => {
                if (payload && payload[0] && payload[0].payload) {
                  return `Date: ${payload[0].payload.date}`;
                }
                return label;
              }}
            />
            <Area
              type="monotone"
              dataKey="followers"
              stroke="#6366f1"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorFollowers)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Cross-Platform Sum Disclaimer */}
      <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-100 dark:border-slate-800/40">
        <Info className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
        <span>
          Follower totals across platforms are summed and are not deduplicated unique users.
        </span>
      </div>
    </div>
  );
};
