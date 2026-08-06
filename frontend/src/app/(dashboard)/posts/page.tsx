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


  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <CalendarIcon className="w-5 h-5 text-blue-400" />
            <span>Social Post Workflow & Scheduler</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage drafts, approvals, scheduled publishing queues, and Meta Graph API retries.
          </p>
        </div>

        <Link
          href="/studio"
          className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold text-xs shadow-lg shadow-indigo-500/20 hover:opacity-95 transition"
        >
          <Plus className="w-4 h-4" />
          <span>Create New AI Post</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2">
        <span className="text-xs font-semibold text-slate-400 mr-2 flex items-center space-x-1">
          <Filter className="w-3.5 h-3.5" />
          <span>Filter:</span>
        </span>
        {['ALL', 'DRAFT', 'APPROVED', 'SCHEDULED', 'PUBLISHED', 'FAILED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
              filterStatus === st
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Posts Table / Grid */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-4">Post & Visual</th>
                <th className="p-4">Platforms</th>
                <th className="p-4">Status</th>
                <th className="p-4">Scheduled / Published</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {filteredPosts.map((post) => (
                <tr key={post.id} className="hover:bg-slate-800/30 transition">
                  <td className="p-4">
                    <div className="flex items-start space-x-3 max-w-md">
                      {post.image_url ? (
                        <img
                          src={post.image_url}
                          alt={post.title}
                          className="w-12 h-12 rounded-xl object-cover border border-slate-700 flex-shrink-0"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-500 flex-shrink-0">
                          📝
                        </div>
                      )}
                      <div>
                        <h4 className="font-bold text-white text-xs">{post.title || 'Untitled Post'}</h4>
                        <p className="text-slate-400 text-[11px] line-clamp-2 mt-0.5">{post.caption}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center space-x-1.5">
                      {post.platforms.includes('facebook') && (
                        <span className="px-2 py-0.5 rounded bg-blue-600/20 text-blue-400 text-[10px] font-bold">
                          FB Page
                        </span>
                      )}
                      {post.platforms.includes('instagram') && (
                        <span className="px-2 py-0.5 rounded bg-pink-600/20 text-pink-400 text-[10px] font-bold">
                          IG Biz
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-4">
                    <PostStatusBadge status={post.status} />
                  </td>
                  <td className="p-4 text-slate-300 font-mono text-[11px]">
                    {post.published_at ? (
                      <span className="text-indigo-400">
                        {new Date(post.published_at).toLocaleDateString()} {new Date(post.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    ) : post.scheduled_at ? (
                      <span className="text-blue-400">
                        {new Date(post.scheduled_at).toLocaleDateString()} {new Date(post.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="p-4 text-right">
                    {post.status === 'FAILED' ? (
                      <button
                        onClick={() => handleRetry(post.id)}
                        className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs transition flex items-center space-x-1 ml-auto"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Retry Publish</span>
                      </button>
                    ) : post.status === 'APPROVED' ? (
                      <button
                        onClick={() => handleRetry(post.id)}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition flex items-center space-x-1 ml-auto"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Publish Now</span>
                      </button>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Ready</span>
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
