'use client';

import React from 'react';
import { 
  Instagram, 
  Facebook, 
  Youtube, 
  Sparkles, 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight, 
  Heart, 
  MessageSquare, 
  Share2, 
  Bookmark, 
  Eye, 
  TrendingUp, 
  Calendar 
} from 'lucide-react';
import { 
  PostPerformanceItem, 
  PostSortState, 
  PostPaginationState, 
  formatMetricNumber, 
  formatPercentage 
} from '@/lib/analyticsApi';

interface PostPerformanceTableProps {
  posts: PostPerformanceItem[];
  total: number;
  sort: PostSortState;
  onSortChange: (sort: PostSortState) => void;
  pagination: PostPaginationState;
  onPaginationChange: (pagination: PostPaginationState) => void;
  isLoading?: boolean;
}

export const PostPerformanceTable: React.FC<PostPerformanceTableProps> = ({
  posts,
  total,
  sort,
  onSortChange,
  pagination,
  onPaginationChange,
  isLoading,
}) => {
  const totalPages = Math.ceil(total / pagination.limit) || 1;
  const currentPage = Math.floor(pagination.offset / pagination.limit) + 1;

  const handleSortSelect = (field: PostSortState['orderBy']) => {
    if (sort.orderBy === field) {
      // Toggle direction
      onSortChange({
        orderBy: field,
        orderDir: sort.orderDir === 'asc' ? 'desc' : 'asc',
      });
    } else {
      // Default to desc for metrics, desc for date
      onSortChange({
        orderBy: field,
        orderDir: 'desc',
      });
    }
  };

  const handlePrevPage = () => {
    if (pagination.offset >= pagination.limit) {
      onPaginationChange({
        ...pagination,
        offset: pagination.offset - pagination.limit,
      });
    }
  };

  const handleNextPage = () => {
    if (pagination.offset + pagination.limit < total) {
      onPaginationChange({
        ...pagination,
        offset: pagination.offset + pagination.limit,
      });
    }
  };

  return (
    <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-xl p-5 shadow-xs space-y-4">
      {/* Table Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/60 pb-3">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Content Performance
            </h3>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              {total} {total === 1 ? 'post' : 'posts'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Post-level engagement metrics, reach, and interaction breakdowns.
          </p>
        </div>

        {/* Server-Side Sort Selector */}
        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Sort by:</span>
          <select
            value={`${sort.orderBy}-${sort.orderDir}`}
            onChange={(e) => {
              const [orderBy, orderDir] = e.target.value.split('-') as [PostSortState['orderBy'], 'asc' | 'desc'];
              onSortChange({ orderBy, orderDir });
            }}
            className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-800 dark:text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none cursor-pointer"
          >
            <option value="published_at-desc">Latest Published</option>
            <option value="published_at-asc">Oldest Published</option>
            <option value="engagement_rate-desc">Highest Engagement Rate</option>
            <option value="likes-desc">Most Likes</option>
            <option value="comments-desc">Most Comments</option>
            <option value="reach-desc">Highest Reach</option>
            <option value="impressions-desc">Highest Impressions</option>
          </select>
        </div>
      </div>

      {/* Posts Table */}
      {posts.length === 0 ? (
        <div className="py-12 px-6 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 text-center space-y-3">
          <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 mx-auto">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              No published posts found in this period
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Try choosing a broader date filter or publishing content via the Studio.
            </p>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-left border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800/80 text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="pb-3 pr-4">Post & Caption</th>
                <th className="pb-3 px-3">Platform</th>
                <th
                  onClick={() => handleSortSelect('published_at')}
                  className="pb-3 px-3 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center space-x-1">
                    <span>Published</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSortSelect('likes')}
                  className="pb-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Likes</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSortSelect('comments')}
                  className="pb-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Comments</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSortSelect('reach')}
                  className="pb-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Reach</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSortSelect('impressions')}
                  className="pb-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Impressions</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSortSelect('engagement_rate')}
                  className="pb-3 pl-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>Eng. Rate</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
              {posts.map((post) => {
                const img = post.thumbnail_url || post.image_url;
                const formattedDate = post.published_at
                  ? new Date(post.published_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })
                  : 'Unpublished';

                return (
                  <tr
                    key={post.post_id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Post & Caption */}
                    <td className="py-3 pr-4 max-w-[280px]">
                      <div className="flex items-center space-x-3">
                        {img ? (
                          <img
                            src={img}
                            alt=""
                            className="w-11 h-11 rounded-lg object-cover border border-slate-200 dark:border-slate-800 flex-shrink-0"
                          />
                        ) : (
                          <div className="w-11 h-11 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 flex-shrink-0">
                            <Sparkles className="w-4 h-4" />
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                            {post.title || post.caption || 'Untitled Post'}
                          </p>
                          {post.caption && post.title && (
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                              {post.caption}
                            </p>
                          )}
                          <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                            ID: #{post.post_id}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Platform badges */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        {post.platforms.map((p) => {
                          const plat = p.toLowerCase();
                          if (plat === 'instagram') {
                            return (
                              <span
                                key={p}
                                className="p-1 rounded-md bg-pink-50 dark:bg-pink-950/40 text-pink-600 dark:text-pink-400 border border-pink-200 dark:border-pink-800/40"
                                title="Instagram"
                              >
                                <Instagram className="w-3 h-3" />
                              </span>
                            );
                          }
                          if (plat === 'facebook') {
                            return (
                              <span
                                key={p}
                                className="p-1 rounded-md bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40"
                                title="Facebook"
                              >
                                <Facebook className="w-3 h-3" />
                              </span>
                            );
                          }
                          if (plat === 'youtube') {
                            return (
                              <span
                                key={p}
                                className="p-1 rounded-md bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800/40"
                                title="YouTube"
                              >
                                <Youtube className="w-3 h-3" />
                              </span>
                            );
                          }
                          return (
                            <span
                              key={p}
                              className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                            >
                              {p}
                            </span>
                          );
                        })}
                      </div>
                    </td>

                    {/* Published Date */}
                    <td className="py-3 px-3 whitespace-nowrap text-slate-600 dark:text-slate-400">
                      {formattedDate}
                    </td>

                    {/* Likes */}
                    <td className="py-3 px-3 text-right font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {formatMetricNumber(post.likes)}
                    </td>

                    {/* Comments */}
                    <td className="py-3 px-3 text-right font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {formatMetricNumber(post.comments)}
                    </td>

                    {/* Reach */}
                    <td className="py-3 px-3 text-right font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {formatMetricNumber(post.reach)}
                    </td>

                    {/* Impressions */}
                    <td className="py-3 px-3 text-right font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {formatMetricNumber(post.impressions)}
                    </td>

                    {/* Engagement Rate */}
                    <td className="py-3 pl-3 text-right font-semibold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">
                      {formatPercentage(post.engagement_rate)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Controls */}
      {total > 0 && (
        <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800/60 text-xs">
          <span className="text-slate-500 dark:text-slate-400">
            Showing {pagination.offset + 1}–{Math.min(pagination.offset + pagination.limit, total)} of {total} posts
          </span>

          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrevPage}
              disabled={pagination.offset === 0 || isLoading}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 font-medium text-slate-700 dark:text-slate-300">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={pagination.offset + pagination.limit >= total || isLoading}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
