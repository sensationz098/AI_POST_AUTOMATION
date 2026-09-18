'use client';

import React from 'react';
import { 
  Instagram, 
  Facebook, 
  Youtube, 
  Share2, 
  Users, 
  Eye, 
  BarChart2, 
  MessageCircle, 
  Heart, 
  Share, 
  Bookmark, 
  Percent 
} from 'lucide-react';
import { 
  PlatformBreakdownItem, 
  formatMetricNumber, 
  formatPercentage 
} from '@/lib/analyticsApi';

interface PlatformBreakdownSectionProps {
  platforms: PlatformBreakdownItem[];
}

export const PlatformBreakdownSection: React.FC<PlatformBreakdownSectionProps> = ({ platforms }) => {
  const getPlatformMeta = (name: string) => {
    switch (name.toLowerCase()) {
      case 'instagram':
        return {
          displayName: 'Instagram',
          icon: Instagram,
          badgeColor: 'text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-950/40 border-pink-200 dark:border-pink-800/40',
          iconColor: 'text-pink-600 dark:text-pink-400',
        };
      case 'facebook':
        return {
          displayName: 'Facebook',
          icon: Facebook,
          badgeColor: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800/40',
          iconColor: 'text-blue-600 dark:text-blue-400',
        };
      case 'youtube':
        return {
          displayName: 'YouTube',
          icon: Youtube,
          badgeColor: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800/40',
          iconColor: 'text-red-600 dark:text-red-400',
        };
      default:
        return {
          displayName: name.charAt(0).toUpperCase() + name.slice(1),
          icon: Share2,
          badgeColor: 'text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700',
          iconColor: 'text-slate-600 dark:text-slate-400',
        };
    }
  };

  // Ensure Instagram, Facebook, and YouTube entries are represented
  const displayPlatforms = React.useMemo(() => {
    const required = ['instagram', 'facebook', 'youtube'];
    const map = new Map<string, PlatformBreakdownItem>();
    platforms.forEach((p) => map.set(p.platform.toLowerCase(), p));

    return required.map((plat) => {
      if (map.has(plat)) return map.get(plat)!;
      return {
        platform: plat,
        connected_accounts_count: 0,
        total_followers: null,
        total_posts: 0,
        total_likes: null,
        total_comments: null,
        total_shares: null,
        total_saves: null,
        total_reach: null,
        total_impressions: null,
        total_views: null,
        aggregate_engagement_rate: null,
      };
    });
  }, [platforms]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Platform Breakdown
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Channel-specific metrics, reach, engagement rates, and video view counts.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {displayPlatforms.map((item) => {
          const meta = getPlatformMeta(item.platform);
          const Icon = meta.icon;
          const isYouTube = item.platform.toLowerCase() === 'youtube';

          return (
            <div
              key={item.platform}
              className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 shadow-xs space-y-4 hover:border-slate-300 dark:hover:border-slate-700/80 transition-colors"
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className={`p-2 rounded-lg ${meta.badgeColor}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {meta.displayName}
                    </h4>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      {item.connected_accounts_count}{' '}
                      {item.connected_accounts_count === 1 ? 'account' : 'accounts'}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">
                    Followers
                  </span>
                  <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {formatMetricNumber(item.total_followers)}
                  </span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60 text-xs">
                {/* Posts */}
                <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                    Posts
                  </span>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    {formatMetricNumber(item.total_posts)}
                  </p>
                </div>

                {/* Engagement Rate */}
                <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                    Engagement Rate
                  </span>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    {formatPercentage(item.aggregate_engagement_rate)}
                  </p>
                </div>

                {/* Reach (Instagram/Facebook) or Views (YouTube) */}
                {isYouTube ? (
                  <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                      Video Views
                    </span>
                    <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                      {formatMetricNumber(item.total_views)}
                    </p>
                  </div>
                ) : (
                  <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                      Reach
                    </span>
                    <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                      {formatMetricNumber(item.total_reach)}
                    </p>
                  </div>
                )}

                {/* Impressions (Instagram/Facebook) or Reach placeholder (YouTube) */}
                {isYouTube ? (
                  <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                      Reach / Imp
                    </span>
                    <p className="font-semibold text-slate-400 dark:text-slate-500 text-sm">
                      —
                    </p>
                  </div>
                ) : (
                  <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                      Impressions
                    </span>
                    <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                      {formatMetricNumber(item.total_impressions)}
                    </p>
                  </div>
                )}

                {/* Interactions Row: Likes & Comments */}
                <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium flex items-center space-x-1">
                    <Heart className="w-3 h-3 text-rose-500 inline" />
                    <span>Likes</span>
                  </span>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    {formatMetricNumber(item.total_likes)}
                  </p>
                </div>

                <div className="bg-slate-50 dark:bg-slate-900/40 p-2 rounded-lg space-y-0.5">
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium flex items-center space-x-1">
                    <MessageCircle className="w-3 h-3 text-blue-500 inline" />
                    <span>Comments</span>
                  </span>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    {formatMetricNumber(item.total_comments)}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
