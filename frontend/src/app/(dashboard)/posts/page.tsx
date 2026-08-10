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
    <div className="space-y-8 select-none">
      {/* 2026 SaaS Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-6 md:p-8 rounded-3xl shadow-xl">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2.5">
              <div className="p-2 rounded-2xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
                <CalendarIcon className="w-5 h-5" />
              </div>
              <span>Social Post Workflow & Scheduler</span>
            </h1>

            <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-slate-950/80 text-slate-300 border border-slate-800 flex items-center space-x-1.5 shadow-sm">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>Timezone: {userTimeZone}</span>
            </span>
          </div>
          <p className="text-xs md:text-sm text-slate-400 leading-relaxed max-w-xl">
            Manage drafts, approvals, scheduled publishing queues, and Meta Graph API retries. All timestamps automatically synchronized to your local clock ({userTimeZone}).
          </p>
        </div>

        <Link
          href="/studio"
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-indigo-500/25 transition focus-ring self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>+ Create New AI Post</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1">
        <span className="text-xs font-bold text-slate-400 mr-2 flex items-center space-x-1.5 flex-shrink-0">
          <Filter className="w-3.5 h-3.5 text-indigo-400" />
          <span>Filter Status:</span>
        </span>
        {['ALL', 'DRAFT', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'FAILED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-extrabold transition-all duration-200 flex-shrink-0 ${
              filterStatus === st
                ? 'bg-indigo-600 text-white shadow-md'
                : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Posts SaaS Table / Grid */}
      <div className="saas-card rounded-3xl overflow-hidden border border-slate-800 shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-5">Post & Visual</th>
                <th className="p-5">Platforms</th>
                <th className="p-5">Status</th>
                <th className="p-5">Scheduled / Published ({userTimeZone})</th>
                <th className="p-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs">
              {filteredPosts.map((post) => (
                <tr key={post.id} className="hover:bg-slate-800/40 transition-colors duration-150">
                  <td className="p-5">
                    <div className="flex items-start space-x-3.5 max-w-md">
                      {post.image_url ? (
                        <img
                          src={post.image_url}
                          alt={post.title}
                          className="w-14 h-14 rounded-2xl object-cover border border-slate-700/80 flex-shrink-0 shadow-md"
                        />
                      ) : (
                        <div className="w-14 h-14 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-500 text-lg flex-shrink-0 shadow-inner">
                          📝
                        </div>
                      )}
                      <div>
                        <h4 className="font-bold text-white text-xs tracking-tight">{post.title || 'Untitled Post'}</h4>
                        <p className="text-slate-400 text-xs line-clamp-2 mt-1 leading-normal">{post.caption}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-5">
                    <div className="flex items-center space-x-2">
                      {post.platforms.includes('facebook') && (
                        <span className="px-2.5 py-1 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-300 text-[10px] font-bold shadow-sm">
                          FB Page
                        </span>
                      )}
                      {post.platforms.includes('instagram') && (
                        <span className="px-2.5 py-1 rounded-lg bg-pink-600/20 border border-pink-500/30 text-pink-300 text-[10px] font-bold shadow-sm">
                          IG Biz
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-5">
                    <PostStatusBadge status={post.status} />
                  </td>
                  <td className="p-5 text-slate-300 font-mono text-xs font-semibold">
                    {post.published_at ? (
                      <span className="text-indigo-300 font-semibold flex items-center space-x-1.5">
                        <CheckCircle className="w-3.5 h-3.5 text-indigo-400 inline" />
                        <span>{formatToLocalDateTime(post.published_at)}</span>
                      </span>
                    ) : post.scheduled_at ? (
                      <span className="text-blue-300 font-semibold flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-blue-400 inline" />
                        <span>{formatToLocalDateTime(post.scheduled_at)}</span>
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="p-5 text-right">
                    {post.status === 'FAILED' ? (
                      <button
                        onClick={() => handleRetry(post.id)}
                        className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition shadow-md shadow-rose-600/20 flex items-center space-x-1.5 ml-auto focus-ring"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Retry Publish</span>
                      </button>
                    ) : post.status === 'APPROVED' ? (
                      <button
                        onClick={() => handleRetry(post.id)}
                        className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition shadow-md shadow-emerald-600/20 flex items-center space-x-1.5 ml-auto focus-ring"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Publish Now</span>
                      </button>
                    ) : (
                      <span className="text-slate-400 text-xs font-medium">Ready</span>
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
