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
  platform: 'facebook' | 'instagram' | 'youtube';
  account_id: string;
  account_name: string;
  token_type?: string;
  expires_at?: string;
  status: 'CONNECTED' | 'TOKEN_EXPIRED' | 'REVOKED';
  username?: string;
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

export type AutomationPlatform = 'facebook' | 'instagram';
export type AutomationStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED';
export type TriggerType = 'ANY_COMMENT' | 'KEYWORD';
export type PostTargetType = 'SPECIFIC_POST';

export interface PlatformPost {
  id: string; // Real Meta Platform ID (IG Media ID or FB Post ID)
  caption?: string;
  media_url?: string;
  thumbnail_url?: string;
  permalink?: string;
  created_time?: string;
  platform: 'instagram' | 'facebook';
  like_count?: number;
  comments_count?: number;
  internal_post_id?: number | null;
}

export interface PlatformPostsResponse {
  items: PlatformPost[];
  paging?: {
    cursors?: {
      before?: string;
      after?: string;
    };
    next?: string;
    previous?: string;
  };
}


export interface TriggerConfig {
  keywords?: string[];
}

export interface PublicReplyConfig {
  enabled: boolean;
  variations: string[];
}

export interface PrivateMessageConfig {
  enabled: boolean;
  message: string | null;
}

export interface ActionConfig {
  public_reply?: PublicReplyConfig;
  private_message?: PrivateMessageConfig;
}

export interface Automation {
  id: number;
  user_id: number;
  social_account_id: number;
  name: string;
  platform: AutomationPlatform;
  status: AutomationStatus;
  post_target_type: PostTargetType | string;
  external_post_id: string | null;
  internal_post_id: number | null;
  trigger_type: TriggerType | string;
  trigger_config: TriggerConfig;
  action_config: ActionConfig;
  metadata_json?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationCreateInput {
  name: string;
  platform: AutomationPlatform;
  social_account_id: number;
  post_target_type?: PostTargetType | string;
  internal_post_id?: number | null;
  external_post_id?: string | null;
  trigger_type: TriggerType | string;
  trigger_config: TriggerConfig;
  action_config: ActionConfig;
  metadata_json?: Record<string, any>;
}

export interface AutomationUpdateInput {
  name?: string;
  platform?: AutomationPlatform;
  social_account_id?: number;
  post_target_type?: PostTargetType | string;
  internal_post_id?: number | null;
  external_post_id?: string | null;
  trigger_type?: TriggerType | string;
  trigger_config?: TriggerConfig;
  action_config?: ActionConfig;
  metadata_json?: Record<string, any>;
}

export interface AutomationDeleteResponse {
  success: boolean;
  message: string;
  automation_id: number;
}

export type StoryStatus = 'DRAFT' | 'SCHEDULED' | 'PUBLISHING' | 'PUBLISHED' | 'FAILED';

export interface Story {
  id: number;
  brand_id: number;
  user_id: number;
  title?: string;
  caption?: string;
  media_url: string;
  media_type: 'image' | 'video' | string;
  thumbnail_url?: string;
  target_account_ids: number[];
  platforms: ('facebook' | 'instagram')[];
  status: StoryStatus;
  scheduled_at?: string;
  published_at?: string;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  fb_story_id?: string;
  ig_container_id?: string;
  ig_story_id?: string;
  created_at: string;
  updated_at: string;
}

export interface StoryCreateInput {
  brand_id: number;
  title?: string;
  caption?: string;
  media_url: string;
  media_type: 'image' | 'video' | string;
  thumbnail_url?: string;
  target_account_ids?: number[];
  platforms?: ('facebook' | 'instagram')[];
  status?: StoryStatus | string;
  scheduled_at?: string;
}

export interface StoryUpdateInput {
  title?: string;
  caption?: string;
  media_url?: string;
  media_type?: 'image' | 'video' | string;
  thumbnail_url?: string;
  target_account_ids?: number[];
  platforms?: ('facebook' | 'instagram')[];
  status?: StoryStatus | string;
  scheduled_at?: string;
}

export interface StoryValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  account_checks: {
    account_id?: number | string;
    account_name?: string;
    platform?: string;
    capable: boolean;
    reason?: string;
  }[];
}

export type SchedulerItemType = 'post' | 'story';

export interface SchedulerTargetAccount {
  id: number;
  account_id: string;
  account_name: string;
  platform: 'facebook' | 'instagram' | string;
  username?: string;
  logo_url?: string;
}

export interface SchedulerItem {
  id: number;
  item_type: SchedulerItemType;
  brand_id: number;
  user_id: number;
  title?: string;
  caption?: string;
  media_url?: string;
  media_type?: 'image' | 'video' | string;
  thumbnail_url?: string;
  platforms: ('facebook' | 'instagram')[];
  target_account_ids: number[];
  target_accounts: SchedulerTargetAccount[];
  status: PostStatus | StoryStatus | string;
  scheduled_at?: string;
  published_at?: string;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  fb_id?: string;
  ig_id?: string;
  fb_url?: string | null;
  ig_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface YouTubeUploadInitiateRequest {
  social_account_id: number;
  title: string;
  description?: string;
  privacy_status?: 'private' | 'unlisted' | 'public';
  filename?: string;
  mime_type?: string;
  file_size_bytes: number;
  client_mutation_id?: string;
}

export interface YouTubeUploadInitiateResponse {
  upload_id: string;
  client_mutation_id?: string | null;
  channel_id: string;
  channel_title: string;
  title: string;
  file_size_bytes: number;
  chunk_size_bytes: number;
  mime_type: string;
  status: string;
  next_byte_offset: number;
  message: string;
}

export interface YouTubeUploadChunkResponse {
  upload_id: string;
  status: 'RESUME_INCOMPLETE' | 'PROCESSING' | 'UPLOADING' | 'CANCELLED' | 'FAILED' | string;
  http_status: number;
  range_header?: string | null;
  last_byte_received?: number | null;
  next_byte_offset?: number | null;
  total_bytes: number;
  bytes_uploaded: number;
  progress_percentage: number;
  is_complete: boolean;
  video_id?: string | null;
  video_url?: string | null;
  processing_status?: string | null;
}

export interface YouTubeUploadStatusResponse {
  upload_id: string;
  client_mutation_id?: string | null;
  channel_id: string;
  channel_title?: string | null;
  title: string;
  file_size_bytes: number;
  bytes_uploaded: number;
  progress_percentage: number;
  mime_type: string;
  status: 'INITIATED' | 'UPLOADING' | 'PROCESSING' | 'READY' | 'FAILED' | 'CANCELLED' | string;
  processing_status?: 'uploaded' | 'processing' | 'succeeded' | 'failed' | 'terminated' | string | null;
  http_status?: number;
  range_header?: string | null;
  last_byte_received?: number | null;
  next_byte_offset?: number | null;
  is_complete: boolean;
  video_id?: string | null;
  video_url?: string | null;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface YouTubeUploadCancelResponse {
  upload_id: string;
  status: string;
  message: string;
  remote_cancelled: boolean;
}

export interface YouTubeUploadItem {
  id: number;
  upload_id: string;
  client_mutation_id?: string | null;
  social_account_id: number;
  channel_id: string;
  channel_title?: string | null;
  title: string;
  file_size_bytes: number;
  bytes_uploaded: number;
  progress_percentage: number;
  status: string;
  processing_status?: string | null;
  video_id?: string | null;
  video_url?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}
