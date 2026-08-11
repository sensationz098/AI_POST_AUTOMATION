'use client';

import React, { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  Send, 
  RefreshCw, 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  FileEdit,
  Plus,
  Filter
} from 'lucide-react';
import { PostStatusBadge } from '@/components/PostStatusBadge';
import { SocialPost } from '@/lib/types';
import { apiClient } from '@/lib/api';
import Link from 'next/link';


const samplePosts: SocialPost[] = [
  {
    id: 101,
    brand_id: 1,
    user_id: 1,
    title: 'Launching Next-Gen AI Social Automation Studio',
    caption: '🚀 Say goodbye to manual scheduling! Introducing Apex AI Social Studio—the ultimate AI engine for Facebook and Instagram publishing.',
    hashtags: ['#ApexAI', '#SocialMediaAutomation', '#MetaGraphAPI'],
    cta: '👉 Claim your 14-day free trial link in bio now!',
    seo_keywords: ['ai social media', 'facebook automation'],
    image_url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80',
    platforms: ['facebook', 'instagram'],
    status: 'PUBLISHED',
    published_at: new Date().toISOString(),
    retry_count: 0,
    max_retries: 3,
    fb_post_id: 'fb_post_1092834',
    ig_media_id: 'ig_media_9823471',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 102,
    brand_id: 1,
    user_id: 1,
    title: 'Top 5 AI Marketing Strategies for 2026',
    caption: '💡 Want to 10x your organic reach on Instagram without spending hours writing captions? Here are 5 data-backed AI growth tactics...',
    hashtags: ['#MarketingTips', '#AIGrowth', '#InstagramStrategy'],
    cta: '📲 Save this post for later!',
    seo_keywords: ['ai growth', 'instagram tips'],
    image_url: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80',
    platforms: ['instagram'],
    status: 'SCHEDULED',
    scheduled_at: new Date(Date.now() + 86400000).toISOString(),
    retry_count: 0,
    max_retries: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 103,
    brand_id: 1,
    user_id: 1,
    title: 'Weekend Tech Spotlight & Promo',
    caption: '⚡ Automate your Facebook Page posts effortlessly with multi-tenant brand controls.',
    hashtags: ['#TechSpotlight', '#FacebookPage'],
    cta: 'Learn more at apex.ai',
    seo_keywords: ['meta automation'],
    image_url: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80',
    platforms: ['facebook'],
    status: 'APPROVED',
    retry_count: 0,
    max_retries: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 104,
    brand_id: 1,
    user_id: 1,
    title: 'Experimental Graph API Carousel',
    caption: 'Drafting new seasonal product highlight for IG Business feed.',
    hashtags: ['#Draft', '#AICarousel'],
    seo_keywords: ['draft'],
    platforms: ['facebook', 'instagram'],
    status: 'DRAFT',
    retry_count: 0,
    max_retries: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export default function PostSchedulerPage() {
  const [posts, setPosts] = useState<SocialPost[]>(samplePosts);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  useEffect(() => {
    async function fetchPosts() {
      try {
        const res = await apiClient.get('/posts/brand/1');
        if (res.data && res.data.length > 0) {
          setPosts(res.data);
        }
      } catch (e) {
        // Keep sample posts if backend offline
      }
    }
    fetchPosts();
  }, []);

  const filteredPosts = filterStatus === 'ALL'
    ? posts
    : posts.filter((p) => p.status === filterStatus);

  const handleRetry = async (postId: number) => {
    try {
      await apiClient.post(`/posts/${postId}/retry`);
    } catch (e) {
      // Mock local state update if sandbox mode
    }
    setPosts((prev) =>
      prev.map((p) =>
        p.id === postId ? { ...p, status: 'PUBLISHED', published_at: new Date().toISOString() } : p
      )
    );
  };


  const userTimeZone = typeof window !== 'undefined'
    ? Intl.DateTimeFormat().resolvedOptions().timeZone
    : 'Local Time';

  const formatToLocalDateTime = (dateStr?: string) => {
    if (!dateStr) return '—';
    const normalizedStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
    const date = new Date(normalizedStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="space-y-5 select-none font-sans text-xs">
      {/* Linear Style Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/60">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
              <CalendarIcon className="w-4 h-4 text-indigo-400" />
              <span>Social Post Queue & Publishing Workflow</span>
            </h1>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-slate-900/60 text-slate-400 border border-slate-800">
              Timezone: {userTimeZone}
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Track drafts, scheduled queue times, and automated Meta Graph API retries.
          </p>
        </div>

        <Link
          href="/studio"
          className="inline-flex items-center space-x-1.5 px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] transition shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ Create Post</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
        <span className="text-[11px] font-bold text-slate-400 mr-1 flex items-center space-x-1 flex-shrink-0">
          <Filter className="w-3 h-3 text-indigo-400" />
          <span>Filter:</span>
        </span>
        {['ALL', 'DRAFT', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'FAILED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition flex-shrink-0 ${
              filterStatus === st
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Enterprise Single Surface Jira/Linear Queue Table */}
      <div className="linear-panel rounded-lg overflow-hidden border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-900/60 border-b border-slate-800/80 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-3">Post ID & Visual</th>
                <th className="p-3">Title & Summary</th>
                <th className="p-3">Platforms</th>
                <th className="p-3">Status</th>
                <th className="p-3">Scheduled / Published ({userTimeZone})</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredPosts.map((post) => (
                <tr key={post.id} className="hover:bg-slate-800/40 transition-colors duration-150">
                  <td className="p-3">
                    <div className="flex items-center space-x-2.5">
                      <span className="text-[10px] font-mono text-slate-500 font-bold">#{post.id}</span>
                      {post.image_url ? (
                        <img
                          src={post.image_url}
                          alt={post.title}
                          className="w-9 h-9 rounded object-cover border border-slate-700 flex-shrink-0"
                        />
                      ) : (
                        <div className="w-9 h-9 rounded bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 text-xs flex-shrink-0">
                          📝
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-3 max-w-sm">
                    <h4 className="font-semibold text-slate-100 text-xs truncate">{post.title || 'Untitled Post'}</h4>
                    <p className="text-slate-400 text-[11px] truncate mt-0.5">{post.caption}</p>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center space-x-1.5">
                      {post.platforms.includes('facebook') && (
                        <span className="px-1.5 py-0.5 rounded bg-blue-950/60 border border-blue-800/60 text-blue-300 text-[9px] font-mono font-medium">
                          FB Page
                        </span>
                      )}
                      {post.platforms.includes('instagram') && (
                        <span className="px-1.5 py-0.5 rounded bg-pink-950/60 border border-pink-800/60 text-pink-300 text-[9px] font-mono font-medium">
                          IG Biz
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    <PostStatusBadge status={post.status} />
                  </td>
                  <td className="p-3 text-slate-300 font-mono text-[11px]">
                    {post.published_at ? (
                      <span className="text-indigo-300 flex items-center space-x-1">
                        <CheckCircle className="w-3 h-3 text-indigo-400 inline" />
                        <span>{formatToLocalDateTime(post.published_at)}</span>
                      </span>
                    ) : post.scheduled_at ? (
                      <span className="text-sky-300 flex items-center space-x-1">
                        <Clock className="w-3 h-3 text-sky-400 inline" />
                        <span>{formatToLocalDateTime(post.scheduled_at)}</span>
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="p-3 text-right">
                    {post.status === 'FAILED' ? (
                      <button
                        onClick={() => handleRetry(post.id)}
                        className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[10px] transition flex items-center space-x-1 ml-auto focus-ring"
                      >
                        <RefreshCw className="w-3 h-3" />
                        <span>Retry</span>
                      </button>
                    ) : post.status === 'APPROVED' ? (
                      <button
                        onClick={() => handleRetry(post.id)}
                        className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[10px] transition flex items-center space-x-1 ml-auto focus-ring"
                      >
                        <Send className="w-3 h-3" />
                        <span>Publish Now</span>
                      </button>
                    ) : (
                      <span className="text-slate-500 text-[10px] font-mono">Ready</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
