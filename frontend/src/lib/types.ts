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
  external_reply_id?: string;
  created_at: string;
}

export interface SocialComment {
  id: number;
  social_account_id: number;
  platform: 'facebook' | 'instagram';
  external_comment_id: string;
  external_post_id?: string;
  parent_comment_id?: string;
  comment_text?: string;
  commenter_id?: string;
  commenter_name?: string;
  event_timestamp?: string;
  webhook_object: string;
  processing_status: 'RECEIVED' | string;
  created_at: string;
  replies?: SocialCommentReply[];
}

