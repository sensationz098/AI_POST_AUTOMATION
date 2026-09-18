'use client';

import React from 'react';
import { 
  Users, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Layers, 
  Eye, 
  BarChart2, 
  Percent, 
  CalendarDays,
  Zap
} from 'lucide-react';
import { 
  OverviewReportResponse, 
  GrowthMetrics, 
  formatMetricNumber, 
  formatPercentage, 
  formatGrowth 
} from '@/lib/analyticsApi';

interface EvolutionKpiCardsProps {
  overview?: OverviewReportResponse | null;
  growth?: GrowthMetrics | null;
  startDate?: string;
  endDate?: string;
}

export const EvolutionKpiCards: React.FC<EvolutionKpiCardsProps> = ({
  overview,
  growth,
  startDate,
  endDate,
}) => {
  const followerGrowth = formatGrowth(growth?.follower_change);
  const followerGrowthRate = formatGrowth(growth?.follower_growth_rate, true);

  // Derive publishing cadence based on selected period and total posts
  const cadence = React.useMemo(() => {
    if (!overview || overview.total_posts == null || !startDate || !endDate) {
      return { dailyPosts: null, weeklyPosts: null, periodDays: null };
    }
    try {
      const start = new Date(startDate);
      const end = new Date(endDate);
      const diffMs = Math.abs(end.getTime() - start.getTime());
      const diffDays = Math.max(1, Math.round(diffMs / (1000 * 60 * 60 * 24)) + 1);

      const daily = overview.total_posts / diffDays;
      const weekly = daily * 7;

      return {
        dailyPosts: daily >= 1 ? daily.toFixed(1) : daily.toFixed(2),
        weeklyPosts: weekly.toFixed(1),
        periodDays: diffDays,
      };
    } catch {
      return { dailyPosts: null, weeklyPosts: null, periodDays: null };
    }
  }, [overview, startDate, endDate]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 pt-1">
      {/* 1. Followers */}
      <div className="bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl p-3.5 space-y-1.5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Followers
          </span>
          <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <Users className="w-3 h-3" />
          </div>
        </div>
        <div>
          <p className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(overview?.total_followers)}
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
            Sum across active accounts
          </p>
        </div>
      </div>

      {/* 2. Follower Growth */}
      <div className="bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl p-3.5 space-y-1.5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Follower Growth
          </span>
          <div
            className={`w-6 h-6 rounded-md flex items-center justify-center ${
              followerGrowth.direction === 'positive'
                ? 'bg-emerald-50 dark:bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                : followerGrowth.direction === 'negative'
                ? 'bg-rose-50 dark:bg-rose-500/15 text-rose-600 dark:text-rose-400'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
            }`}
          >
            {followerGrowth.direction === 'positive' && <TrendingUp className="w-3 h-3" />}
            {followerGrowth.direction === 'negative' && <TrendingDown className="w-3 h-3" />}
            {followerGrowth.direction === 'zero' && <Minus className="w-3 h-3" />}
            {followerGrowth.direction === 'unavailable' && <Minus className="w-3 h-3" />}
          </div>
        </div>
        <div>
          <p
            className={`text-xl font-bold tracking-tight ${
              followerGrowth.direction === 'positive'
                ? 'text-emerald-600 dark:text-emerald-400'
                : followerGrowth.direction === 'negative'
                ? 'text-rose-600 dark:text-rose-400'
                : 'text-slate-900 dark:text-slate-100'
            }`}
          >
            {followerGrowth.text}
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
            {followerGrowthRate.direction !== 'unavailable' ? `${followerGrowthRate.text} rate` : 'In selected window'}
          </p>
        </div>
      </div>

      {/* 3. Publishing Cadence */}
      <div className="bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl p-3.5 space-y-1.5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Publish Cadence
          </span>
          <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-500/15 flex items-center justify-center text-blue-600 dark:text-blue-400">
            <CalendarDays className="w-3 h-3" />
          </div>
        </div>
        <div>
          <p className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {cadence.weeklyPosts ? `${cadence.weeklyPosts}/wk` : `${overview?.total_posts ?? 0} posts`}
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
            {cadence.dailyPosts ? `~${cadence.dailyPosts} posts/day` : 'Logical posts published'}
          </p>
        </div>
      </div>

      {/* 4. Total Reach */}
      <div className="bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl p-3.5 space-y-1.5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Reach
          </span>
          <div className="w-6 h-6 rounded-md bg-emerald-50 dark:bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <Eye className="w-3 h-3" />
          </div>
        </div>
        <div>
          <p className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(overview?.total_reach)}
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
            Sum of reported reach
          </p>
        </div>
      </div>

      {/* 5. Total Impressions */}
      <div className="bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl p-3.5 space-y-1.5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Impressions
          </span>
          <div className="w-6 h-6 rounded-md bg-sky-50 dark:bg-sky-500/15 flex items-center justify-center text-sky-600 dark:text-sky-400">
            <BarChart2 className="w-3 h-3" />
          </div>
        </div>
        <div>
          <p className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(overview?.total_impressions)}
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
            Content displays / views
          </p>
        </div>
      </div>

      {/* 6. Aggregate Engagement Rate */}
      <div className="bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/80 dark:border-slate-800/80 rounded-xl p-3.5 space-y-1.5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Engagement Rate
          </span>
          <div className="w-6 h-6 rounded-md bg-violet-50 dark:bg-violet-500/15 flex items-center justify-center text-violet-600 dark:text-violet-400">
            <Percent className="w-3 h-3" />
          </div>
        </div>
        <div>
          <p className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatPercentage(overview?.aggregate_engagement_rate)}
          </p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
            Interactions / Reach
          </p>
        </div>
      </div>
    </div>
  );
};
