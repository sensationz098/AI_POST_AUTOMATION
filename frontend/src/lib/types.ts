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
