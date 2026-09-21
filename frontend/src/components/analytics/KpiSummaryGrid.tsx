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
  CheckCircle2,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { 
  OverviewReportResponse, 
  GrowthMetrics, 
  LiveAnalyticsResponse,
  formatMetricNumber, 
  formatPercentage, 
  formatGrowth 
} from '@/lib/analyticsApi';

interface KpiSummaryGridProps {
  overview?: OverviewReportResponse | null;
  growth?: GrowthMetrics | null;
  liveAnalytics?: LiveAnalyticsResponse | null;
}

export const KpiSummaryGrid: React.FC<KpiSummaryGridProps> = ({ overview, growth, liveAnalytics }) => {
  const followerGrowth = formatGrowth(growth?.follower_change);
  const followerGrowthRate = formatGrowth(growth?.follower_growth_rate, true);

  // Use historical overview if present, otherwise immediately use live platform analytics
  const totalFollowers = overview?.total_followers ?? liveAnalytics?.summary?.total_followers;
  const totalReach = overview?.total_reach ?? liveAnalytics?.summary?.total_reach;
  const totalImpressions = overview?.total_impressions ?? liveAnalytics?.summary?.total_impressions;
  const engagementRate = overview?.aggregate_engagement_rate ?? liveAnalytics?.summary?.aggregate_engagement_rate;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
      {/* 1. Total Followers */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-2 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Followers
          </span>
          <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <Users className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="space-y-0.5">
          <p className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(totalFollowers)}
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            Across active channels*
          </p>
        </div>
      </div>


      {/* 2. Follower Growth */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-2 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Follower Growth
          </span>
          <div
            className={`w-7 h-7 rounded-lg flex items-center justify-center ${
              followerGrowth.direction === 'positive'
                ? 'bg-emerald-50 dark:bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                : followerGrowth.direction === 'negative'
                ? 'bg-rose-50 dark:bg-rose-500/15 text-rose-600 dark:text-rose-400'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
            }`}
          >
            {followerGrowth.direction === 'positive' && <TrendingUp className="w-3.5 h-3.5" />}
            {followerGrowth.direction === 'negative' && <TrendingDown className="w-3.5 h-3.5" />}
            {followerGrowth.direction === 'zero' && <Minus className="w-3.5 h-3.5" />}
            {followerGrowth.direction === 'unavailable' && <Minus className="w-3.5 h-3.5" />}
          </div>
        </div>
        <div className="space-y-0.5">
          <p
            className={`text-xl sm:text-2xl font-bold tracking-tight ${
              followerGrowth.direction === 'positive'
                ? 'text-emerald-600 dark:text-emerald-400'
                : followerGrowth.direction === 'negative'
                ? 'text-rose-600 dark:text-rose-400'
                : 'text-slate-900 dark:text-slate-100'
            }`}
          >
            {followerGrowth.text}
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            {followerGrowthRate.direction !== 'unavailable' ? `${followerGrowthRate.text} change` : 'In selected period'}
          </p>
        </div>
      </div>

      {/* 3. Total Posts */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-2 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Posts
          </span>
          <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-500/15 flex items-center justify-center text-blue-600 dark:text-blue-400">
            <Layers className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="space-y-0.5">
          <p className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(overview?.total_posts ?? 0)}
          </p>
          <div className="flex items-center space-x-2 text-[10px] text-slate-500 dark:text-slate-400 pt-0.5">
            <span className="inline-flex items-center text-emerald-600 dark:text-emerald-400" title="Published">
              <CheckCircle2 className="w-2.5 h-2.5 mr-0.5" />
              {overview?.published_posts ?? 0}
            </span>
            <span className="inline-flex items-center text-blue-600 dark:text-blue-400" title="Scheduled">
              <Clock className="w-2.5 h-2.5 mr-0.5" />
              {overview?.scheduled_posts ?? 0}
            </span>
            {(overview?.failed_posts ?? 0) > 0 && (
              <span className="inline-flex items-center text-rose-600 dark:text-rose-400" title="Failed">
                <AlertTriangle className="w-2.5 h-2.5 mr-0.5" />
                {overview?.failed_posts}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 4. Total Reach */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-2 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Reach
          </span>
          <div className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <Eye className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="space-y-0.5">
          <p className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(totalReach)}
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            Sum of reported platform reach
          </p>
        </div>
      </div>

      {/* 5. Total Impressions */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-2 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Total Impressions
          </span>
          <div className="w-7 h-7 rounded-lg bg-sky-50 dark:bg-sky-500/15 flex items-center justify-center text-sky-600 dark:text-sky-400">
            <BarChart2 className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="space-y-0.5">
          <p className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatMetricNumber(totalImpressions)}
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            Total content views
          </p>
        </div>
      </div>

      {/* 6. Aggregate Engagement Rate */}
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-2 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Engagement Rate
          </span>
          <div className="w-7 h-7 rounded-lg bg-violet-50 dark:bg-violet-500/15 flex items-center justify-center text-violet-600 dark:text-violet-400">
            <Percent className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="space-y-0.5">
          <p className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            {formatPercentage(engagementRate)}
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            Interactions / Reach
          </p>
        </div>
      </div>

    </div>
  );
};
