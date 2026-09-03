'use client';

import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  Facebook, 
  Instagram, 
  RefreshCw, 
  AlertCircle, 
  Loader2, 
  Clock, 
  User, 
  ShieldCheck,
  CheckCircle2,
  CornerDownRight,
  Send,
  X,
  ExternalLink,
  Image as ImageIcon,
  Video,
  FileText,
  Trash2,
  Filter,
  Share2,
  Target,
  Megaphone,
  Search,
  LayoutDashboard,
  Layers,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { SocialComment, SocialCommentPostContext, SocialCommentAccountContext, SocialCommentReply, SocialAccount, MetaAdCommentContext } from '@/lib/types';

// Types for Overview & Indices
interface OverviewMetrics {
  total_comments: number;
  total_ad_comments: number;
  total_post_comments: number;
  recent_ads: Array<{
    id: number;
    meta_ad_id: string;
    name: string;
    campaign_name?: string;
    effective_status?: string;
    comment_count: number;
  }>;
  recent_posts: Array<{
    id: number | string;
    external_post_id: string;
    title: string;
    platform: string;
    comment_count: number;
  }>;
}

interface AdItem {
  id: number;
  meta_ad_id: string;
  name: string;
  campaign_name?: string;
  adset_name?: string;
  effective_status?: string;
  facebook_page_id?: string;
  facebook_post_id?: string;
  created_at?: string;
  comment_count: number;
}

interface PostItem {
  id: number | string;
  external_post_id: string;
  title: string;
  caption?: string;
  image_url?: string;
  media_type?: string;
  platform: string;
  published_at?: string;
  comment_count: number;
}

// 1. Post Context Card Component
function PostContextCard({
  post,
  account,
  metaAd,
  externalPostId,
  platform,
}: {
  post?: SocialCommentPostContext | null;
  account?: SocialCommentAccountContext | null;
  metaAd?: MetaAdCommentContext | null;
  externalPostId?: string;
  platform: 'facebook' | 'instagram';
}) {
  const isFb = platform === 'facebook';
  const isAdComment = Boolean(metaAd);
  const accountDisplayName = account?.account_name || account?.display_name || (isFb ? 'Facebook Page' : 'Instagram Account');

  return (
    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/90 flex flex-col space-y-2 mb-3.5 shadow-sm">
      <div className="flex items-center justify-between text-[11px] pb-2 border-b border-slate-900/80">
        <div className="flex items-center space-x-2 min-w-0 flex-wrap gap-y-1">
          {isFb ? (
            <span className="px-2 py-0.5 rounded bg-blue-950/90 text-blue-300 border border-blue-800/70 font-bold text-[10px] flex items-center space-x-1 flex-shrink-0">
              <Facebook className="w-3 h-3 fill-current" />
              <span>Facebook Page</span>
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-pink-950/90 text-pink-300 border border-pink-800/70 font-bold text-[10px] flex items-center space-x-1 flex-shrink-0">
              <Instagram className="w-3 h-3" />
              <span>Instagram</span>
            </span>
          )}

          {isAdComment ? (
            <span className="px-2 py-0.5 rounded bg-purple-950/90 text-purple-300 border border-purple-800/70 font-bold text-[10px] flex items-center space-x-1 flex-shrink-0">
              <Target className="w-3 h-3 text-purple-400" />
              <span>Ad Comment</span>
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700/70 font-bold text-[10px] flex items-center space-x-1 flex-shrink-0">
              <FileText className="w-3 h-3 text-slate-400" />
              <span>Post Comment</span>
            </span>
          )}

          <span className="font-semibold text-slate-200 truncate">
            {isFb ? accountDisplayName : `@${accountDisplayName.replace(/^@/, '')}`}
          </span>
        </div>

        {metaAd ? (
          <Link
            href={`/comments/ads/${metaAd.id}`}
            className="px-2 py-0.5 rounded bg-purple-900/40 hover:bg-purple-900/80 border border-purple-700/60 text-purple-200 text-[10px] font-semibold transition flex items-center space-x-1 flex-shrink-0"
          >
            <span>View Ad Context</span>
            <ChevronRight className="w-3 h-3 text-purple-300" />
          </Link>
        ) : post?.permalink ? (
          <a
            href={post.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700/70 text-indigo-300 hover:text-white text-[10px] font-semibold transition flex items-center space-x-1 flex-shrink-0"
          >
            <span>View Post</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        ) : null}
      </div>

      {isAdComment && metaAd ? (
        <div className="space-y-1 pt-0.5">
          <div className="flex items-center space-x-2 truncate">
            <Megaphone className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
            <span className="font-bold text-xs text-purple-200 truncate">{metaAd.name}</span>
          </div>
          <div className="flex items-center space-x-3 text-[10px] text-slate-400 font-mono">
            {metaAd.campaign_name && <span>Campaign: {metaAd.campaign_name}</span>}
            {metaAd.effective_status && (
              <span className={`px-1.5 py-0.2 rounded ${metaAd.effective_status === 'ACTIVE' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'}`}>
                ● {metaAd.effective_status}
              </span>
            )}
          </div>
        </div>
      ) : post ? (
        <div className="flex items-start space-x-3 pt-0.5">
          {post.thumbnail_url || post.image_url ? (
            <img
              src={post.thumbnail_url || post.image_url || ''}
              alt="Post thumbnail"
              className="w-10 h-10 object-cover rounded-md border border-slate-800 flex-shrink-0 bg-slate-900"
            />
          ) : (
            <div className="w-10 h-10 rounded-md bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 flex-shrink-0">
              <ImageIcon className="w-4 h-4" />
            </div>
          )}

          <div className="flex-1 min-w-0 space-y-0.5">
            <h4 className="text-xs font-semibold text-slate-200 truncate">{post.title}</h4>
            {post.caption && (
              <p className="text-[11px] text-slate-400 truncate max-w-xl">{post.caption}</p>
            )}
          </div>
        </div>
      ) : externalPostId ? (
        <div className="text-[11px] text-slate-400 font-mono truncate pt-0.5">
          Post ID: {externalPostId}
        </div>
      ) : null}
    </div>
  );
}

export default function EngagementDashboardPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = searchParams.get('tab') || 'overview';

  // Social account filter state
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('ALL');

  // Overview Data
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(false);

  // Ads Data & Filters
  const [ads, setAds] = useState<AdItem[]>([]);
  const [loadingAds, setLoadingAds] = useState(false);
  const [adSearch, setAdSearch] = useState('');
  const [adStatusFilter, setAdStatusFilter] = useState('ACTIVE');

  // Posts Data & Filters
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [postSearch, setPostSearch] = useState('');
  const [postPlatformFilter, setPostPlatformFilter] = useState('ALL');

  // Comments Stream Data
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [commentsError, setCommentsError] = useState<string | null>(null);

  // Reply composer & Deletion
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState('');
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);
  const [replySuccess, setReplySuccess] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const fetchSocialAccounts = async () => {
    try {
      const res = await apiClient.get('/social-accounts/');
      setSocialAccounts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch social accounts:', e);
    }
  };

  const fetchOverview = async () => {
    setLoadingOverview(true);
    try {
      const res = await apiClient.get('/social-comments/overview');
      setOverview(res.data);
    } catch (e) {
      console.error('Failed to fetch overview metrics:', e);
    } finally {
      setLoadingOverview(false);
    }
  };

  const fetchAds = async () => {
    setLoadingAds(true);
    try {
      const params = new URLSearchParams();
      if (adSearch.trim()) params.append('q', adSearch.trim());
      if (adStatusFilter && adStatusFilter !== 'ALL') params.append('status', adStatusFilter);

      const res = await apiClient.get(`/social-comments/ads?${params.toString()}`);
      setAds(res.data || []);
    } catch (e) {
      console.error('Failed to fetch ads index:', e);
    } finally {
      setLoadingAds(false);
    }
  };

  const fetchPosts = async () => {
    setLoadingPosts(true);
    try {
      const params = new URLSearchParams();
      if (postSearch.trim()) params.append('q', postSearch.trim());
      if (postPlatformFilter && postPlatformFilter !== 'ALL') params.append('platform', postPlatformFilter.toLowerCase());

      const res = await apiClient.get(`/social-comments/posts?${params.toString()}`);
      setPosts(res.data || []);
    } catch (e) {
      console.error('Failed to fetch posts index:', e);
    } finally {
      setLoadingPosts(false);
    }
  };

  const fetchCommentsFeed = async () => {
    setLoadingComments(true);
    setCommentsError(null);
    try {
      let endpoint = '/social-comments/?skip=0&limit=50';
      if (selectedAccountId !== 'ALL') {
        endpoint += `&social_account_id=${selectedAccountId}`;
      }
      const res = await apiClient.get(endpoint);
      setComments(res.data || []);
    } catch (e: any) {
      console.error('Failed to fetch comments feed:', e);
      setCommentsError(e?.response?.data?.detail || 'Failed to load comments feed.');
    } finally {
      setLoadingComments(false);
    }
  };

  useEffect(() => {
    fetchSocialAccounts();
  }, []);

  useEffect(() => {
    if (activeTab === 'overview') fetchOverview();
    if (activeTab === 'ads') fetchAds();
    if (activeTab === 'posts') fetchPosts();
    if (activeTab === 'comments') fetchCommentsFeed();
  }, [activeTab, selectedAccountId, adStatusFilter, postPlatformFilter]);

  const handleTabChange = (tab: string) => {
    router.push(`/comments?tab=${tab}`);
  };

  const handleSendReply = async (commentId: number) => {
    if (!replyText.trim()) return;
    setIsSubmittingReply(true);
    setReplyError(null);
    setReplySuccess(null);
    try {
      const res = await apiClient.post(`/social-comments/${commentId}/reply`, {
        message: replyText.trim(),
      });

      setComments((prev) =>
        prev.map((c) => {
          if (c.id === commentId) {
            const updated = [...(c.replies || []), res.data.reply];
            return { ...c, replies: updated };
          }
          return c;
        })
      );

      setReplySuccess('Reply sent successfully!');
      setReplyText('');
      setReplyingToId(null);
      setTimeout(() => setReplySuccess(null), 4000);
    } catch (e: any) {
      console.error('Failed to reply:', e);
      setReplyError(e?.response?.data?.detail || 'Failed to send reply.');
    } finally {
      setIsSubmittingReply(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!confirm('Are you sure you want to delete this comment?')) return;
    setDeletingId(commentId);
    try {
      await apiClient.delete(`/social-comments/${commentId}`);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to delete comment.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Top Header & Page Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center space-x-2">
            <MessageSquare className="w-6 h-6 text-indigo-400" />
            <span>Social Engagement Hub</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Content-centric social moderation for Meta Ads and organic posts.
          </p>
        </div>

        {/* Social Account Selector Dropdown */}
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center">
            <Filter className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg pl-8 pr-8 py-2 font-medium outline-none focus:border-indigo-500 transition appearance-none cursor-pointer"
            >
              <option value="ALL">All Connected Accounts</option>
              {socialAccounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.platform.toUpperCase()}: {acc.account_name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              if (activeTab === 'overview') fetchOverview();
              if (activeTab === 'ads') fetchAds();
              if (activeTab === 'posts') fetchPosts();
              if (activeTab === 'comments') fetchCommentsFeed();
            }}
            className="px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition flex items-center space-x-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="flex items-center space-x-1 border-b border-slate-800/80 pb-px">
        <button
          onClick={() => handleTabChange('overview')}
          className={`px-4 py-2.5 rounded-t-lg font-semibold text-xs transition-colors flex items-center space-x-2 ${
            activeTab === 'overview'
              ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500 border-x border-slate-800/80'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <LayoutDashboard className="w-3.5 h-3.5" />
          <span>Overview</span>
        </button>

        <button
          onClick={() => handleTabChange('ads')}
          className={`px-4 py-2.5 rounded-t-lg font-semibold text-xs transition-colors flex items-center space-x-2 ${
            activeTab === 'ads'
              ? 'bg-slate-900 text-purple-400 border-t-2 border-purple-500 border-x border-slate-800/80'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Target className="w-3.5 h-3.5 text-purple-400" />
          <span>Meta Ads</span>
          {overview?.total_ad_comments ? (
            <span className="px-1.5 py-0.2 rounded-full bg-purple-950 text-purple-300 border border-purple-800/80 text-[10px]">
              {overview.total_ad_comments}
            </span>
          ) : null}
        </button>

        <button
          onClick={() => handleTabChange('posts')}
          className={`px-4 py-2.5 rounded-t-lg font-semibold text-xs transition-colors flex items-center space-x-2 ${
            activeTab === 'posts'
              ? 'bg-slate-900 text-blue-400 border-t-2 border-blue-500 border-x border-slate-800/80'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <FileText className="w-3.5 h-3.5 text-blue-400" />
          <span>Organic Posts</span>
          {overview?.total_post_comments ? (
            <span className="px-1.5 py-0.2 rounded-full bg-blue-950 text-blue-300 border border-blue-800/80 text-[10px]">
              {overview.total_post_comments}
            </span>
          ) : null}
        </button>

        <button
          onClick={() => handleTabChange('comments')}
          className={`px-4 py-2.5 rounded-t-lg font-semibold text-xs transition-colors flex items-center space-x-2 ${
            activeTab === 'comments'
              ? 'bg-slate-900 text-emerald-400 border-t-2 border-emerald-500 border-x border-slate-800/80'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
          <span>All Comments Stream</span>
        </button>
      </div>

      {/* TAB 1: OVERVIEW METRICS DASHBOARD */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Engagement</p>
                <h3 className="text-3xl font-extrabold text-slate-100 mt-1">
                  {overview ? overview.total_comments : 0}
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Ingested social discussions</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-indigo-950/80 border border-indigo-800/80 flex items-center justify-center text-indigo-400">
                <MessageSquare className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider">Meta Ad Comments</p>
                <h3 className="text-3xl font-extrabold text-purple-300 mt-1">
                  {overview ? overview.total_ad_comments : 0}
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Active paid ads engagement</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-purple-950/80 border border-purple-800/80 flex items-center justify-center text-purple-400">
                <Target className="w-6 h-6" />
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Organic Post Comments</p>
                <h3 className="text-3xl font-extrabold text-blue-300 mt-1">
                  {overview ? overview.total_post_comments : 0}
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Facebook & Instagram page posts</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-blue-950/80 border border-blue-800/80 flex items-center justify-center text-blue-400">
                <FileText className="w-6 h-6" />
              </div>
            </div>
          </div>

          {/* Active Discussions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top Meta Ads Card */}
            <div className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
                  <Target className="w-4 h-4 text-purple-400" />
                  <span>Recent Active Meta Ads</span>
                </h3>
                <button
                  onClick={() => handleTabChange('ads')}
                  className="text-xs text-purple-400 hover:text-purple-300 font-semibold flex items-center space-x-1"
                >
                  <span>View All Ads</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {loadingOverview ? (
                <div className="py-8 text-center"><Loader2 className="w-6 h-6 animate-spin text-purple-400 mx-auto" /></div>
              ) : !overview?.recent_ads || overview.recent_ads.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  No active Meta Ad comments found. Sync active comments in Meta Accounts to get started.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {overview.recent_ads.map((ad) => (
                    <div
                      key={ad.id}
                      className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl flex items-center justify-between hover:border-purple-800/60 transition group"
                    >
                      <div className="min-w-0 pr-2">
                        <h4 className="text-xs font-bold text-slate-200 truncate group-hover:text-purple-300 transition">
                          {ad.name}
                        </h4>
                        <p className="text-[10px] text-slate-400 truncate mt-0.5">
                          {ad.campaign_name || 'Meta Ad Campaign'}
                        </p>
                      </div>
                      <div className="flex items-center space-x-3 flex-shrink-0">
                        <span className="px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800 text-[10px] font-bold">
                          {ad.comment_count} comments
                        </span>
                        <Link
                          href={`/comments/ads/${ad.id}`}
                          className="p-1.5 rounded-lg bg-slate-900 hover:bg-purple-900/60 text-purple-300 transition"
                          title="View Ad Comments"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Top Organic Posts Card */}
            <div className="bg-slate-900/60 border border-slate-800/90 rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-blue-400" />
                  <span>Recent Organic Discussions</span>
                </h3>
                <button
                  onClick={() => handleTabChange('posts')}
                  className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center space-x-1"
                >
                  <span>View All Posts</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {loadingOverview ? (
                <div className="py-8 text-center"><Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" /></div>
              ) : !overview?.recent_posts || overview.recent_posts.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800/60">
                  No organic post comments recorded yet.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {overview.recent_posts.map((p) => (
                    <div
                      key={p.id}
                      className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl flex items-center justify-between hover:border-blue-800/60 transition group"
                    >
                      <div className="min-w-0 pr-2">
                        <h4 className="text-xs font-bold text-slate-200 truncate group-hover:text-blue-300 transition">
                          {p.title}
                        </h4>
                        <p className="text-[10px] text-slate-400 capitalize mt-0.5">
                          Platform: {p.platform}
                        </p>
                      </div>
                      <div className="flex items-center space-x-3 flex-shrink-0">
                        <span className="px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800 text-[10px] font-bold">
                          {p.comment_count} comments
                        </span>
                        <Link
                          href={`/comments/posts/${p.external_post_id}`}
                          className="p-1.5 rounded-lg bg-slate-900 hover:bg-blue-900/60 text-blue-300 transition"
                          title="View Post Comments"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: META ADS INDEX VIEW */}
      {activeTab === 'ads' && (
        <div className="space-y-4">
          {/* Controls & Search */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800/90">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={adSearch}
                onChange={(e) => setAdSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchAds()}
                placeholder="Search ad name, campaign, or ad set..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-purple-500 text-xs rounded-lg pl-9 pr-3 py-2.5 text-slate-100 placeholder-slate-500 outline-none transition"
              />
            </div>

            <div className="flex items-center space-x-3">
              <select
                value={adStatusFilter}
                onChange={(e) => setAdStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2.5 font-medium outline-none focus:border-purple-500 transition cursor-pointer"
              >
                <option value="ACTIVE">Active Ads Only</option>
                <option value="PAUSED">Paused Ads Only</option>
                <option value="ALL">All Meta Ads</option>
              </select>

              <button
                onClick={fetchAds}
                className="px-3.5 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs transition flex items-center space-x-1.5"
              >
                <Search className="w-3.5 h-3.5" />
                <span>Filter</span>
              </button>
            </div>
          </div>

          {/* Ads Grid / Table */}
          {loadingAds ? (
            <div className="py-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <Loader2 className="w-8 h-8 text-purple-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400 mt-2">Loading Meta Ads...</p>
            </div>
          ) : ads.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-2">
              <Target className="w-8 h-8 text-slate-500 mx-auto" />
              <h4 className="text-sm font-bold text-slate-200">No Meta Ads Found</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No synced ads match your current status or search filter.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ads.map((ad) => (
                <div
                  key={ad.id}
                  className="bg-slate-900/60 border border-slate-800/90 hover:border-purple-700/60 rounded-xl p-4 transition-all shadow-sm space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-sm text-slate-100 line-clamp-1">{ad.name}</h3>
                      <span
                        className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold flex-shrink-0 border ${
                          ad.effective_status === 'ACTIVE'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800'
                        }`}
                      >
                        ● {ad.effective_status || 'UNKNOWN'}
                      </span>
                    </div>

                    <div className="text-xs text-slate-400 space-y-1">
                      <p><span className="text-slate-500 font-semibold">Campaign:</span> {ad.campaign_name || 'N/A'}</p>
                      <p><span className="text-slate-500 font-semibold">Ad Set:</span> {ad.adset_name || 'N/A'}</p>
                      <p className="font-mono text-[10px] text-slate-500">ID: {ad.meta_ad_id}</p>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <div className="flex items-center space-x-1 text-xs text-purple-300 font-semibold">
                      <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
                      <span>{ad.comment_count} Comments</span>
                    </div>

                    <Link
                      href={`/comments/ads/${ad.id}`}
                      className="px-3 py-1.5 rounded-lg bg-purple-950/80 hover:bg-purple-900 text-purple-200 border border-purple-800/80 font-semibold text-xs transition flex items-center space-x-1"
                    >
                      <span>Manage Comments</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ORGANIC POSTS INDEX VIEW */}
      {activeTab === 'posts' && (
        <div className="space-y-4">
          {/* Controls & Search */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800/90">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={postSearch}
                onChange={(e) => setPostSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchPosts()}
                placeholder="Search organic post title or caption..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 text-xs rounded-lg pl-9 pr-3 py-2.5 text-slate-100 placeholder-slate-500 outline-none transition"
              />
            </div>

            <div className="flex items-center space-x-3">
              <select
                value={postPlatformFilter}
                onChange={(e) => setPostPlatformFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2.5 font-medium outline-none focus:border-blue-500 transition cursor-pointer"
              >
                <option value="ALL">All Platforms</option>
                <option value="FACEBOOK">Facebook Only</option>
                <option value="INSTAGRAM">Instagram Only</option>
              </select>

              <button
                onClick={fetchPosts}
                className="px-3.5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs transition flex items-center space-x-1.5"
              >
                <Search className="w-3.5 h-3.5" />
                <span>Filter</span>
              </button>
            </div>
          </div>

          {/* Posts Grid / Table */}
          {loadingPosts ? (
            <div className="py-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400 mt-2">Loading Organic Posts...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-2">
              <FileText className="w-8 h-8 text-slate-500 mx-auto" />
              <h4 className="text-sm font-bold text-slate-200">No Organic Posts Found</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No organic posts match your platform or search criteria.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {posts.map((p) => (
                <div
                  key={p.id}
                  className="bg-slate-900/60 border border-slate-800/90 hover:border-blue-700/60 rounded-xl p-4 transition-all shadow-sm space-y-3 flex flex-col justify-between"
                >
                  <div className="flex items-start space-x-3">
                    {p.image_url ? (
                      <img src={p.image_url} alt="Post" className="w-12 h-12 object-cover rounded-lg border border-slate-800 flex-shrink-0" />
                    ) : (
                      <div className="w-12 h-12 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-500 flex-shrink-0">
                        <FileText className="w-5 h-5" />
                      </div>
                    )}
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase flex items-center space-x-1 ${p.platform === 'facebook' ? 'bg-blue-950 text-blue-300 border border-blue-800' : 'bg-pink-950 text-pink-300 border border-pink-800'}`}>
                          {p.platform === 'facebook' ? <Facebook className="w-2.5 h-2.5 fill-current" /> : <Instagram className="w-2.5 h-2.5" />}
                          <span>{p.platform}</span>
                        </span>
                      </div>
                      <h3 className="font-bold text-xs text-slate-100 truncate">{p.title}</h3>
                      {p.caption && <p className="text-[11px] text-slate-400 line-clamp-1">{p.caption}</p>}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <div className="flex items-center space-x-1 text-xs text-blue-300 font-semibold">
                      <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
                      <span>{p.comment_count} Comments</span>
                    </div>

                    <Link
                      href={`/comments/posts/${p.external_post_id}`}
                      className="px-3 py-1.5 rounded-lg bg-blue-950/80 hover:bg-blue-900 text-blue-200 border border-blue-800/80 font-semibold text-xs transition flex items-center space-x-1"
                    >
                      <span>Manage Comments</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: UNIFIED COMMENTS STREAM */}
      {activeTab === 'comments' && (
        <div className="space-y-4">
          {replySuccess && (
            <div className="p-3.5 rounded-xl bg-emerald-950/50 border border-emerald-800/80 text-emerald-300 text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>{replySuccess}</span>
            </div>
          )}

          {commentsError && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-sm flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span>{commentsError}</span>
            </div>
          )}

          {loadingComments ? (
            <div className="py-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400 mt-2">Loading all social comments...</p>
            </div>
          ) : comments.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-2">
              <MessageSquare className="w-8 h-8 text-slate-500 mx-auto" />
              <h4 className="text-sm font-bold text-slate-200">No Social Comments Found</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No comments exist for the selected account filter.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {comments.map((comment) => {
                const commenterName = comment.commenter_name || comment.commenter_id || 'Anonymous User';
                const initial = commenterName.charAt(0).toUpperCase();

                return (
                  <div
                    key={comment.id}
                    className="bg-slate-900/60 border border-slate-800/90 rounded-xl p-4 transition-colors hover:border-slate-700/80 space-y-3 shadow-sm"
                  >
                    {/* Post Context Preview Header */}
                    <PostContextCard
                      post={comment.post}
                      account={comment.account}
                      metaAd={comment.meta_ad}
                      externalPostId={comment.external_post_id}
                      platform={comment.platform}
                    />

                    {/* Header: Commenter Identity & Timestamp */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center space-x-3 min-w-0">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-sm">
                          {initial}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-sm text-slate-100 truncate">
                              {commenterName}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                            <Clock className="w-3 h-3 text-slate-500" />
                            <span>
                              {comment.created_at ? new Date(comment.created_at).toLocaleString() : 'Recent'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteComment(comment.id)}
                        disabled={deletingId === comment.id}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 border border-transparent hover:border-rose-800/50 transition"
                        title="Delete Comment"
                      >
                        {deletingId === comment.id ? (
                          <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>

                    {/* Comment Message Body */}
                    <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800/60 text-sm text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
                      {comment.comment_text}
                    </div>

                    {/* Reply History */}
                    {comment.replies && comment.replies.length > 0 && (
                      <div className="pl-4 border-l-2 border-indigo-500/40 space-y-2 mt-2">
                        <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider">
                          Replies ({comment.replies.length})
                        </span>
                        {comment.replies.map((reply: SocialCommentReply) => (
                          <div key={reply.id} className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/50 text-xs text-slate-300 flex items-start space-x-2">
                            <CornerDownRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <p className="text-slate-200">{reply.message}</p>
                              <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1">
                                <span>{reply.created_at ? new Date(reply.created_at).toLocaleString() : 'Sent'}</span>
                                <span className="text-emerald-400 font-semibold">● Sent</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Reply Composer */}
                    {replyingToId === comment.id ? (
                      <div className="space-y-2 pt-2 border-t border-slate-800/60">
                        {replyError && (
                          <div className="text-xs text-rose-400 flex items-center space-x-1">
                            <AlertCircle className="w-3 h-3" />
                            <span>{replyError}</span>
                          </div>
                        )}
                        <textarea
                          value={replyText}
                          onChange={(e) => setReplyText(e.target.value)}
                          placeholder="Write an official reply..."
                          rows={2}
                          className="w-full bg-slate-950 border border-indigo-800/80 focus:border-indigo-500 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 outline-none transition"
                        />
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => {
                              setReplyingToId(null);
                              setReplyText('');
                              setReplyError(null);
                            }}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSendReply(comment.id)}
                            disabled={isSubmittingReply || !replyText.trim()}
                            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center space-x-1.5 disabled:opacity-50"
                          >
                            {isSubmittingReply ? (
                              <Loader2 className="w-3 h-3 animate-spin text-white" />
                            ) : (
                              <Send className="w-3 h-3" />
                            )}
                            <span>{isSubmittingReply ? 'Sending...' : 'Post Reply'}</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex justify-end pt-1">
                        <button
                          onClick={() => {
                            setReplyingToId(comment.id);
                            setReplyText('');
                            setReplyError(null);
                          }}
                          className="px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-indigo-300 hover:text-white border border-slate-700/60 text-xs font-medium transition flex items-center space-x-1.5"
                        >
                          <CornerDownRight className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Reply</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
