'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Facebook, Instagram, ExternalLink, ChevronRight, FileText, Image as ImageIcon, MessageSquare, Clock } from 'lucide-react';

interface PostCardProps {
  post: {
    id: number | string;
    external_post_id: string;
    title: string;
    caption?: string;
    image_url?: string;
    media_type?: string;
    platform: string;
    published_at?: string;
    comment_count: number;
    top_level_comment_count?: number;
    permalink?: string;
  };
  selectedAccountId?: string;
  accountName?: string;
  onViewComments?: (postId: string) => void;
  children?: React.ReactNode;
}

export default function PostCardComponent({
  post,
  selectedAccountId = 'ALL',
  accountName,
  onViewComments,
  children,
}: PostCardProps) {
  const [showFullCaption, setShowFullCaption] = useState(false);
  const isFb = post.platform?.toLowerCase() === 'facebook';

  const commentCountToDisplay = post.top_level_comment_count !== undefined
    ? post.top_level_comment_count
    : post.comment_count;

  const drilldownHref = `/comments/posts/${post.external_post_id}${
    selectedAccountId !== 'ALL' ? `?social_account_id=${selectedAccountId}` : ''
  }`;

  return (
    <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl overflow-hidden shadow-sm transition hover:border-slate-700/80 flex flex-col justify-between space-y-3">
      {/* 1. Header: Account Profile & Platform Badge */}
      <div className="p-4 pb-0 flex items-center justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div
            className={`w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0 shadow-sm ${
              isFb ? 'bg-blue-600' : 'bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600'
            }`}
          >
            {isFb ? <Facebook className="w-4 h-4 fill-current" /> : <Instagram className="w-4 h-4" />}
          </div>

          <div className="min-w-0">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-xs text-slate-100 truncate">
                {accountName || (isFb ? 'Facebook Post' : 'Instagram Media')}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase flex items-center space-x-1 ${
                  isFb
                    ? 'bg-blue-950 text-blue-300 border border-blue-800'
                    : 'bg-pink-950 text-pink-300 border border-pink-800'
                }`}
              >
                <span>{post.platform}</span>
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono truncate mt-0.5">
              Post ID: {post.external_post_id}
            </p>
          </div>
        </div>

        {/* External Link Button */}
        {post.permalink && (post.permalink.startsWith('http://') || post.permalink.startsWith('https://')) && (
          <a
            href={post.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1.5 rounded-lg bg-blue-950/70 hover:bg-blue-900/80 border border-blue-700/70 text-blue-200 text-[11px] font-semibold transition flex items-center space-x-1 flex-shrink-0"
          >
            <span>View Post</span>
            <ExternalLink className="w-3 h-3 text-blue-300" />
          </a>
        )}
      </div>

      {/* 2. Media Preview Banner & Caption */}
      <div className="px-4 space-y-2.5">
        {post.image_url ? (
          <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800 max-h-64 flex items-center justify-center">
            <img
              src={post.image_url}
              alt={post.title || 'Organic Post Media'}
              className="w-full h-48 object-cover rounded-xl"
            />
          </div>
        ) : (
          <div className="h-20 bg-slate-950/70 rounded-xl border border-slate-800/80 flex items-center justify-center space-x-2 text-slate-500 text-xs">
            <FileText className="w-4 h-4" />
            <span>Organic Content</span>
          </div>
        )}

        {/* Title / Caption */}
        <div className="space-y-1">
          <h3 className="font-bold text-xs text-slate-100 leading-snug">{post.title}</h3>
          {post.caption && (
            <div>
              <p
                className={`text-[11px] text-slate-300 leading-relaxed font-sans ${
                  !showFullCaption && post.caption.length > 120 ? 'line-clamp-2' : ''
                }`}
              >
                {post.caption}
              </p>
              {post.caption.length > 120 && (
                <button
                  onClick={() => setShowFullCaption(!showFullCaption)}
                  className="text-[10px] font-bold text-blue-400 hover:underline mt-0.5"
                >
                  {showFullCaption ? 'Show less' : 'Read more'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 3. Embedded Conversations Thread Container (If Passed as Child) */}
      {children && <div className="px-4 pt-1">{children}</div>}

      {/* 4. Footer: Engagement Bar & Action Button */}
      <div className="p-4 pt-3 border-t border-slate-800/80 flex items-center justify-between bg-slate-950/40">
        <div className="flex items-center space-x-2 text-xs text-blue-300 font-semibold">
          <MessageSquare className="w-4 h-4 text-blue-400" />
          <span>{commentCountToDisplay} Comments</span>
        </div>

        <div className="flex items-center space-x-2">
          {onViewComments ? (
            <button
              onClick={() => onViewComments(post.external_post_id)}
              className="px-3.5 py-1.5 rounded-xl bg-blue-950/80 hover:bg-blue-900 text-blue-200 border border-blue-800/80 font-bold text-xs transition flex items-center space-x-1"
            >
              <span>Inspect Conversations</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <Link
              href={drilldownHref}
              className="px-3.5 py-1.5 rounded-xl bg-blue-950/80 hover:bg-blue-900 text-blue-200 border border-blue-800/80 font-bold text-xs transition flex items-center space-x-1"
            >
              <span>Inspect Conversations</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
