export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'Admin' | 'Editor';
  is_active: boolean;
  created_at: string;
}

export interface BrandProfile {
  id: number;
  name: string;
  logo_url?: string;
  brand_colors: string[];
  tone_of_voice: string;
  target_audience?: string;
  cta_style: string;
  industry?: string;
  user_id: number;
  created_at: string;
  updated_at: string;
  meta_account?: MetaAccount;
}

export type PostStatus = 'DRAFT' | 'APPROVED' | 'SCHEDULED' | 'PUBLISHED' | 'FAILED';

export interface SocialPost {
  id: number;
  brand_id: number;
  user_id: number;
  title?: string;
  caption: string;
  hashtags: string[];
  cta?: string;
  seo_keywords: string[];
  image_prompt?: string;
  image_url?: string;
  media_type?: 'image' | 'video' | string;
  thumbnail_url?: string;
  thumbnail_type?: 'NONE' | 'FRAME' | 'CUSTOM' | string;
  thumbnail_offset_ms?: number;
  platforms: ('facebook' | 'instagram')[];
  status: PostStatus;
  scheduled_at?: string;
  published_at?: string;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  fb_post_id?: string;
  ig_media_id?: string;
  fb_post_url?: string | null;
  ig_media_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIGeneratedContent {
  caption: string;
  hashtags: string[];
  cta: string;
  seo_keywords: string[];
  image_prompt: string;
}

export interface MetaAccount {
  id: number;
  brand_id: number;
  facebook_page_id?: string;
  facebook_page_name?: string;
  instagram_account_id?: string;
  instagram_username?: string;
  is_connected: boolean;
  last_synced_at?: string;
  created_at: string;
}

export interface DashboardMetrics {
  overview: {
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
  };
  daily_trends: {
    date: string;
    reach: number;
    impressions: number;
    engagement: number;
  }[];
}

export interface AuditLog {
  id: number;
  user_id?: number;
  action: string;
  resource_type: string;
  resource_id?: number;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export interface SocialAccount {
  id: number;
  user_id: number;
  brand_id?: number;
  platform: 'facebook' | 'instagram';
  account_id: string;
  account_name: string;
  token_type?: string;
  expires_at?: string;
  status: 'CONNECTED' | 'TOKEN_EXPIRED' | 'REVOKED';
  logo_url?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface PublishingJob {
  id: number;
  batch_id: number;
  social_account_id: number;
  platform: 'facebook' | 'instagram';
  account_name?: string;
  status: 'QUEUED' | 'PROCESSING' | 'SUCCESS' | 'FAILED' | 'RETRYING';
  external_post_id?: string;
  error_code?: string;
  error_message?: string;
  attempts: number;
  published_at?: string;
}

export interface PublishingBatch {
  id: number;
  post_id: number;
  user_id: number;
  idempotency_key?: string;
  status: 'QUEUED' | 'PROCESSING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED';
  total_targets: number;
  successful_targets: number;
  failed_targets: number;
  created_at: string;
  completed_at?: string;
  jobs: PublishingJob[];
}

export interface SocialCommentReply {
  id: number;
  message: string;
  status: 'SUCCESS' | 'FAILED' | string;
  error_message?: string;
  external_reply_id?: string;
  created_at: string;
  event_timestamp?: string;
  commenter_name?: string | null;
  commenter_id?: string | null;
  source?: 'owner' | 'meta' | string;
}

export interface SocialCommentAccountContext {
  id: number;
  account_id: string;
  account_name: string;
  username?: string | null;
  display_name?: string | null;
  platform: 'facebook' | 'instagram';
  logo_url?: string | null;
}

export interface SocialCommentPostContext {
  id: number | string;
  title?: string;
  caption?: string;
  image_url?: string;
  media_type?: string;
  thumbnail_url?: string;
  permalink?: string;
  platform: 'facebook' | 'instagram';
  source?: 'local' | 'meta';
}

export interface MetaAdCommentContext {
  id: number;
  meta_ad_id: string;
  name?: string | null;
  campaign_name?: string | null;
  adset_name?: string | null;
  effective_status?: string | null;
  permalink?: string | null;
  platform?: 'facebook' | 'instagram' | string;
}

export interface SocialComment {
  id: number;
  social_account_id: number;
  meta_ad_id?: number | null;
  meta_ad?: MetaAdCommentContext | null;
  account?: SocialCommentAccountContext | null;
  platform: 'facebook' | 'instagram';
  external_comment_id: string;
  external_post_id?: string;
  parent_comment_id?: string;
  comment_text?: string;
  commenter_id?: string;
  commenter_name?: string;
  event_timestamp?: string;
  webhook_object: string;
  processing_status: 'RECEIVED' | 'DELETED' | string;
  is_deleted?: boolean;
  deleted_at?: string;
  created_at: string;
  post?: SocialCommentPostContext | null;
  replies?: SocialCommentReply[];
}

export interface SocialCommentDeleteResponse {
  status: 'success' | 'failed';
  message: string;
  comment_id?: number;
}

export interface MetaAdAccount {
  id: number;
  user_id: number;
  meta_ad_account_id: string;
  name?: string;
  account_status?: number;
  status_label?: string;
  currency?: string;
  timezone_name?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface MetaAd {
  id: number;
  user_id: number;
  meta_ad_account_id: string;
  ad_account_db_id?: number;
  meta_ad_id: string;
  name?: string;
  campaign_id?: string;
  campaign_name?: string;
  adset_id?: string;
  adset_name?: string;
  effective_status?: string;
  configured_status?: string;
  creative_id?: string;
  facebook_page_id?: string;
  facebook_post_id?: string;
  instagram_account_id?: string;
  instagram_media_id?: string;
  engagement_object_type?: 'FACEBOOK_POST' | 'INSTAGRAM_MEDIA' | 'BOTH' | 'UNKNOWN' | string;
  engagement_object_id?: string;
  mapping_status: 'MAPPED' | 'PARTIALLY_MAPPED' | 'NOT_AVAILABLE' | 'UNSUPPORTED' | 'ERROR' | string;
  metadata_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface MetaAdSyncResponse {
  success: boolean;
  message: string;
  synced_count: number;
  mapped_count: number;
  partially_mapped_count: number;
  unmapped_count: number;
  ads_fetched?: number;
  ads_synced?: number;
  unique_creatives?: number;
  creatives_enriched?: number;
  creative_fetch_failures?: number;
  mapping_summary?: {
    mapped: number;
    partially_mapped: number;
    not_available: number;
    error: number;
  };
  ads: MetaAd[];
}

export interface MetaAdCommentsResponse {
  ad: {
    id: number;
    meta_ad_id: string;
    name: string;
    campaign_name?: string;
    adset_name?: string;
    effective_status?: string;
    facebook_page_id?: string;
    facebook_post_id?: string;
    meta_ad_account_id?: string;
    permalink?: string;
    platform?: string;
  };
  top_level_comment_count?: number;
  reply_count?: number;
  total_interaction_count?: number;
  total_comments: number;
  filtered_top_level_count?: number;
  skip: number;
  limit: number;
  page: number;
  has_next: boolean;
  comments: SocialComment[];
}
