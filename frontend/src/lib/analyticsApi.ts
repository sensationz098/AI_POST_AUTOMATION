import { apiClient } from './api';

export interface AccountSnapshotPoint {
  id: number;
  social_account_id: number;
  platform: string;
  account_name?: string | null;
  snapshot_date: string;
  followers_count?: number | null;
  following_count?: number | null;
  media_count?: number | null;
  views_count?: number | null;
  reach?: number | null;
  impressions?: number | null;
  engagement_rate?: number | null;
  metadata_json?: Record<string, any> | null;
}

export interface GrowthMetrics {
  initial_followers?: number | null;
  current_followers?: number | null;
  follower_change?: number | null;
  follower_growth_rate?: number | null;
  initial_media_count?: number | null;
  current_media_count?: number | null;
  media_count_change?: number | null;
  initial_views?: number | null;
  current_views?: number | null;
  views_change?: number | null;
}

export interface AccountAnalyticsResponse {
  snapshots: AccountSnapshotPoint[];
  growth: GrowthMetrics;
  total_records: number;
}

export interface OverviewReportResponse {
  total_followers?: number | null;
  total_posts: number;
  published_posts: number;
  scheduled_posts: number;
  failed_posts: number;
  total_likes?: number | null;
  total_comments?: number | null;
  total_shares?: number | null;
  total_saves?: number | null;
  total_reach?: number | null;
  total_impressions?: number | null;
  aggregate_engagement_rate?: number | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface PlatformBreakdownItem {
  platform: string;
  connected_accounts_count: number;
  total_followers?: number | null;
  total_posts: number;
  total_likes?: number | null;
  total_comments?: number | null;
  total_shares?: number | null;
  total_saves?: number | null;
  total_reach?: number | null;
  total_impressions?: number | null;
  total_views?: number | null;
  aggregate_engagement_rate?: number | null;
}

export interface PlatformBreakdownResponse {
  platforms: PlatformBreakdownItem[];
}

export interface PostPerformanceItem {
  post_id: number;
  title?: string | null;
  caption?: string | null;
  status: string;
  platforms: string[];
  media_type?: string | null;
  thumbnail_url?: string | null;
  image_url?: string | null;
  published_at?: string | null;
  created_at: string;
  likes?: number | null;
  comments?: number | null;
  shares?: number | null;
  saves?: number | null;
  reach?: number | null;
  impressions?: number | null;
  engagement_rate?: number | null;
  analytics_updated_at?: string | null;
}

export interface PostPerformanceListResponse {
  items: PostPerformanceItem[];
  total: number;
  limit: number;
  offset: number;
}

export type DatePreset = 'today' | '7d' | '30d' | '90d' | 'custom';
export type PlatformFilter = 'all' | 'instagram' | 'facebook' | 'youtube';

export interface AnalyticsFilterState {
  preset: DatePreset;
  startDate?: string;
  endDate?: string;
  platform: PlatformFilter;
  socialAccountId?: number | 'all';
  brandId?: number;
}

export interface PostSortState {
  orderBy: 'published_at' | 'created_at' | 'likes' | 'comments' | 'shares' | 'saves' | 'reach' | 'impressions' | 'engagement_rate';
  orderDir: 'asc' | 'desc';
}

export interface PostPaginationState {
  limit: number;
  offset: number;
}

// ── API Caller Functions ───────────────────────────────────────────────────

export async function fetchOverviewReport(filters: AnalyticsFilterState): Promise<OverviewReportResponse> {
  const params: Record<string, any> = {};
  if (filters.startDate) params.start_date = filters.startDate;
  if (filters.endDate) params.end_date = filters.endDate;
  if (filters.platform && filters.platform !== 'all') params.platform = filters.platform;
  if (filters.socialAccountId && filters.socialAccountId !== 'all') params.social_account_id = filters.socialAccountId;
  if (filters.brandId) params.brand_id = filters.brandId;

  const res = await apiClient.get<OverviewReportResponse>('/analytics/overview-report', { params });
  return res.data;
}

export async function fetchAccountSnapshots(filters: AnalyticsFilterState): Promise<AccountAnalyticsResponse> {
  const params: Record<string, any> = {};
  if (filters.startDate) params.start_date = filters.startDate;
  if (filters.endDate) params.end_date = filters.endDate;
  if (filters.platform && filters.platform !== 'all') params.platform = filters.platform;
  if (filters.socialAccountId && filters.socialAccountId !== 'all') params.social_account_id = filters.socialAccountId;
  if (filters.brandId) params.brand_id = filters.brandId;

  const res = await apiClient.get<AccountAnalyticsResponse>('/analytics/accounts/snapshots', { params });
  return res.data;
}

export async function fetchPlatformBreakdown(filters: AnalyticsFilterState): Promise<PlatformBreakdownResponse> {
  const params: Record<string, any> = {};
  if (filters.startDate) params.start_date = filters.startDate;
  if (filters.endDate) params.end_date = filters.endDate;
  if (filters.brandId) params.brand_id = filters.brandId;

  const res = await apiClient.get<PlatformBreakdownResponse>('/analytics/platforms', { params });
  return res.data;
}

export async function fetchPostsPerformance(
  filters: AnalyticsFilterState,
  sort: PostSortState,
  pagination: PostPaginationState
): Promise<PostPerformanceListResponse> {
  const params: Record<string, any> = {
    order_by: sort.orderBy,
    order_dir: sort.orderDir,
    limit: pagination.limit,
    offset: pagination.offset,
  };
  if (filters.startDate) params.start_date = filters.startDate;
  if (filters.endDate) params.end_date = filters.endDate;
  if (filters.platform && filters.platform !== 'all') params.platform = filters.platform;
  if (filters.socialAccountId && filters.socialAccountId !== 'all') params.social_account_id = filters.socialAccountId;
  if (filters.brandId) params.brand_id = filters.brandId;

  const res = await apiClient.get<PostPerformanceListResponse>('/analytics/posts', { params });
  return res.data;
}

// ── Formatting Utilities (Strict NULL vs ZERO preservation) ────────────────

/**
 * Formats a numeric metric cleanly (e.g. 1,234 or 12.4K).
 * Strict NULL rule:
 * - null or undefined -> "—"
 * - 0 -> "0"
 */
export function formatMetricNumber(val: number | null | undefined, compact = false): string {
  if (val === null || val === undefined) {
    return '—';
  }
  if (val === 0) {
    return '0';
  }
  if (compact) {
    if (Math.abs(val) >= 1_000_000) {
      return (val / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
    }
    if (Math.abs(val) >= 10_000) {
      return (val / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
    }
  }
  return val.toLocaleString();
}

/**
 * Formats a percentage metric cleanly.
 * Strict NULL rule:
 * - null or undefined -> "—"
 * - 0 -> "0.00%"
 */
export function formatPercentage(val: number | null | undefined, decimals = 2): string {
  if (val === null || val === undefined) {
    return '—';
  }
  return `${Number(val).toFixed(decimals)}%`;
}

/**
 * Returns formatted change object for growth metrics.
 */
export function formatGrowth(val: number | null | undefined, isRate = false): {
  text: string;
  direction: 'positive' | 'negative' | 'zero' | 'unavailable';
} {
  if (val === null || val === undefined) {
    return { text: '—', direction: 'unavailable' };
  }
  if (val === 0) {
    return { text: isRate ? '0.00%' : '0', direction: 'zero' };
  }
  const prefix = val > 0 ? '+' : '';
  const text = isRate ? `${prefix}${val.toFixed(2)}%` : `${prefix}${val.toLocaleString()}`;
  return {
    text,
    direction: val > 0 ? 'positive' : 'negative',
  };
}
