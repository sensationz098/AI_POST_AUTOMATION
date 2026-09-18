'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AnalyticsHeader } from '@/components/analytics/AnalyticsHeader';
import { KpiSummaryGrid } from '@/components/analytics/KpiSummaryGrid';
import { AudienceGrowthChart } from '@/components/analytics/AudienceGrowthChart';
import { PlatformBreakdownSection } from '@/components/analytics/PlatformBreakdownSection';
import { PostPerformanceTable } from '@/components/analytics/PostPerformanceTable';
import {
  KpiGridSkeleton,
  ChartSkeleton,
  PlatformBreakdownSkeleton,
  TableSkeleton,
} from '@/components/analytics/AnalyticsSkeleton';
import { AnalyticsEmptyState } from '@/components/analytics/AnalyticsEmptyState';
import {
  AnalyticsFilterState,
  PostSortState,
  PostPaginationState,
  OverviewReportResponse,
  AccountAnalyticsResponse,
  PlatformBreakdownResponse,
  PostPerformanceListResponse,
  fetchOverviewReport,
  fetchAccountSnapshots,
  fetchPlatformBreakdown,
  fetchPostsPerformance,
} from '@/lib/analyticsApi';
import { SocialAccount } from '@/lib/types';
import { apiClient } from '@/lib/api';

export default function AnalyticsPage() {
  // ── Initial Date Calculations (Default: Last 30 Days) ────────────────────
  const getInitialDates = () => {
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - 30);
    const formatDate = (d: Date) => d.toISOString().split('T')[0];
    return {
      startDate: formatDate(start),
      endDate: formatDate(today),
    };
  };

  const initialDates = getInitialDates();

  // ── Centralized Filter State ─────────────────────────────────────────────
  const [filters, setFilters] = useState<AnalyticsFilterState>({
    preset: '30d',
    startDate: initialDates.startDate,
    endDate: initialDates.endDate,
    platform: 'all',
    socialAccountId: 'all',
  });

  const [sort, setSort] = useState<PostSortState>({
    orderBy: 'published_at',
    orderDir: 'desc',
  });

  const [pagination, setPagination] = useState<PostPaginationState>({
    limit: 20,
    offset: 0,
  });

  // ── Data State ───────────────────────────────────────────────────────────
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [overview, setOverview] = useState<OverviewReportResponse | null>(null);
  const [snapshots, setSnapshots] = useState<AccountAnalyticsResponse | null>(null);
  const [platforms, setPlatforms] = useState<PlatformBreakdownResponse | null>(null);
  const [posts, setPosts] = useState<PostPerformanceListResponse | null>(null);

  // ── Loading & Error States ───────────────────────────────────────────────
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPostsLoading, setIsPostsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // ── Fetch Connected Social Accounts (One-Time) ───────────────────────────
  useEffect(() => {
    async function loadAccounts() {
      try {
        const res = await apiClient.get('/social-accounts/');
        if (Array.isArray(res.data)) {
          const fakeIds = new Set(['109823471029', '17841400928371', '17841400928372', '17841400928373', '109823471030', 'sandbox']);
          const realAccs = res.data.filter((a: any) => !fakeIds.has(a.account_id));
          setSocialAccounts(realAccs);
        }
      } catch (err) {
        console.warn('Could not load social accounts selector:', err);
      }
    }
    loadAccounts();
  }, []);

  // ── Unified Data Fetching Function ───────────────────────────────────────
  const loadAllAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [overviewRes, snapshotsRes, platformsRes, postsRes] = await Promise.allSettled([
        fetchOverviewReport(filters),
        fetchAccountSnapshots(filters),
        fetchPlatformBreakdown(filters),
        fetchPostsPerformance(filters, sort, pagination),
      ]);

      // Process Overview
      if (overviewRes.status === 'fulfilled') {
        setOverview(overviewRes.value);
      } else {
        console.error('Overview report fetch failed:', overviewRes.reason);
      }

      // Process Snapshots
      if (snapshotsRes.status === 'fulfilled') {
        setSnapshots(snapshotsRes.value);
      } else {
        console.error('Account snapshots fetch failed:', snapshotsRes.reason);
      }

      // Process Platforms
      if (platformsRes.status === 'fulfilled') {
        setPlatforms(platformsRes.value);
      } else {
        console.error('Platform breakdown fetch failed:', platformsRes.reason);
      }

      // Process Posts
      if (postsRes.status === 'fulfilled') {
        setPosts(postsRes.value);
      } else {
        console.error('Post performance fetch failed:', postsRes.reason);
      }

      // Check if all failed
      if (
        overviewRes.status === 'rejected' &&
        snapshotsRes.status === 'rejected' &&
        platformsRes.status === 'rejected' &&
        postsRes.status === 'rejected'
      ) {
        setError('Failed to fetch analytics data. Please check your network and retry.');
      }
    } catch (err: any) {
      setError(err?.message || 'An unexpected error occurred while loading analytics.');
    } finally {
      setIsLoading(false);
    }
  }, [filters, sort, pagination]);

  // ── Trigger Load When Filters Change ─────────────────────────────────────
  useEffect(() => {
    loadAllAnalytics();
  }, [filters.preset, filters.startDate, filters.endDate, filters.platform, filters.socialAccountId]);

  // ── Specific Handler for Post Sorting & Pagination ──────────────────────
  const handleSortChange = async (newSort: PostSortState) => {
    setSort(newSort);
    setIsPostsLoading(true);
    try {
      const res = await fetchPostsPerformance(filters, newSort, { ...pagination, offset: 0 });
      setPosts(res);
      setPagination((prev) => ({ ...prev, offset: 0 }));
    } catch (err) {
      console.error('Failed to sort posts:', err);
    } finally {
      setIsPostsLoading(false);
    }
  };

  const handlePaginationChange = async (newPagination: PostPaginationState) => {
    setPagination(newPagination);
    setIsPostsLoading(true);
    try {
      const res = await fetchPostsPerformance(filters, sort, newPagination);
      setPosts(res);
    } catch (err) {
      console.error('Failed to paginate posts:', err);
    } finally {
      setIsPostsLoading(false);
    }
  };

  const handleFilterChange = (updater: Partial<AnalyticsFilterState>) => {
    // Reset pagination offset on filter change
    setPagination((prev) => ({ ...prev, offset: 0 }));
    setFilters((prev) => ({ ...prev, ...updater }));
  };

  return (
    <div className="space-y-6 select-none font-sans text-sm pb-10">
      {/* ── Header with Controls ────────────────────────────────────────── */}
      <AnalyticsHeader
        filters={filters}
        onFilterChange={handleFilterChange}
        onRefresh={loadAllAnalytics}
        isLoading={isLoading}
        socialAccounts={socialAccounts}
      />

      {/* ── Global Error Banner (if any) ────────────────────────────────── */}
      {error && !isLoading && (
        <AnalyticsEmptyState
          icon="error"
          title="Unable to load analytics"
          description={error}
          onRetry={loadAllAnalytics}
        />
      )}

      {/* ── KPI Summary Grid ────────────────────────────────────────────── */}
      {isLoading ? (
        <KpiGridSkeleton />
      ) : (
        <KpiSummaryGrid overview={overview} growth={snapshots?.growth} />
      )}

      {/* ── Audience Growth Chart ───────────────────────────────────────── */}
      {isLoading ? (
        <ChartSkeleton />
      ) : (
        <AudienceGrowthChart snapshots={snapshots?.snapshots || []} isLoading={isLoading} />
      )}

      {/* ── Platform Breakdown Section ─────────────────────────────────── */}
      {isLoading ? (
        <PlatformBreakdownSkeleton />
      ) : (
        <PlatformBreakdownSection platforms={platforms?.platforms || []} />
      )}

      {/* ── Post Performance Table ──────────────────────────────────────── */}
      {isLoading || isPostsLoading ? (
        <TableSkeleton />
      ) : (
        <PostPerformanceTable
          posts={posts?.items || []}
          total={posts?.total || 0}
          sort={sort}
          onSortChange={handleSortChange}
          pagination={pagination}
          onPaginationChange={handlePaginationChange}
          isLoading={isPostsLoading}
        />
      )}
    </div>
  );
}
