'use client';

import React from 'react';
import { ThumbsUp, MessageSquare, Share2, Globe, MoreHorizontal, CheckCircle2, ExternalLink } from 'lucide-react';
import { BrandProfile } from '@/lib/types';

export interface FacebookPostPreviewProps {
  brand?: BrandProfile | null;
  caption?: string;
  hashtags?: string[];
  cta?: string;
  imageUrl?: string;
  mediaType?: string;
  accountName?: string;
  accountAvatar?: string;
  publishedAt?: string;
  permalink?: string;
  likeCount?: number;
  commentCount?: number;
  shareCount?: number;
  externalPostId?: string;
  isPublished?: boolean;
}

export const FacebookPostPreview: React.FC<FacebookPostPreviewProps> = ({
  brand,
  caption,
  hashtags,
  cta,
  imageUrl,
  mediaType,
  accountName,
  accountAvatar,
  publishedAt,
  permalink,
  likeCount,
  commentCount,
  shareCount,
  externalPostId,
  isPublished = false,
}) => {
  const metaAcc = brand?.meta_account;
  const brandName = accountName
    || metaAcc?.facebook_page_name
    || brand?.name
    || (isPublished ? 'Facebook Page' : brand === null ? 'No account connected' : 'Loading...');

  const logoUrl =
    accountAvatar ||
    (metaAcc as any)?.logo_url ||
    (metaAcc?.facebook_page_id ? `https://graph.facebook.com/v19.0/${metaAcc.facebook_page_id}/picture?type=large` : null) ||
    brand?.logo_url ||
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80';

  const timeLabel = publishedAt
    ? new Date(publishedAt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : (isPublished ? 'Published Post' : 'Just now');

  const likesDisplay = likeCount !== undefined ? likeCount.toLocaleString() : '142';
  const commentsDisplay = commentCount !== undefined ? `${commentCount.toLocaleString()} Comments` : '28 Comments';
  const sharesDisplay = shareCount !== undefined ? `${shareCount.toLocaleString()} Shares` : '19 Shares';

  const isVideo = imageUrl ? (
    imageUrl.endsWith('.mp4') ||
    imageUrl.endsWith('.mov') ||
    imageUrl.endsWith('.webm') ||
    imageUrl.startsWith('data:video/')
  ) : false;

  return (
    <div className="w-full max-w-lg bg-[#242526] text-[#E4E6EB] rounded-xl border border-[#3E4042] shadow-2xl overflow-hidden font-sans">
      {/* FB Post Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3 min-w-0">
          <img
            src={logoUrl}
            alt={brandName}
            className="w-10 h-10 rounded-full object-cover border border-indigo-500/50 flex-shrink-0"
          />
          <div className="min-w-0">
            <div className="flex items-center space-x-1.5 font-semibold text-sm text-white">
              <span className="truncate">{brandName}</span>
              <CheckCircle2 className="w-4 h-4 text-blue-500 fill-blue-500/20 flex-shrink-0" />
            </div>
            <div className="flex items-center space-x-1 text-xs text-[#B0B3B8] truncate">
              <span>{timeLabel}</span>
              <span>•</span>
              <Globe className="w-3 h-3 text-[#B0B3B8] flex-shrink-0" />
            </div>
          </div>
        </div>

        {permalink ? (
          <a
            href={permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#B0B3B8] hover:text-white hover:bg-[#3A3B3C] p-2 rounded-full transition flex-shrink-0"
            title="View Live on Facebook"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        ) : (
          <button className="text-[#B0B3B8] hover:bg-[#3A3B3C] p-2 rounded-full transition flex-shrink-0">
            <MoreHorizontal className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Post Text & Body */}
      <div className="px-4 pb-3 text-sm space-y-2 leading-relaxed text-[#E4E6EB] whitespace-pre-wrap">
        <p>{caption || (isPublished ? '' : 'Your AI generated Facebook caption will render live here...')}</p>
        {hashtags && hashtags.length > 0 && (
          <p className="text-blue-400 font-medium">{hashtags.join(' ')}</p>
        )}
        {cta && (
          <div className="mt-2 p-3 bg-[#3A3B3C]/70 rounded-lg border-l-4 border-indigo-500 text-xs font-semibold text-indigo-300">
            {cta}
          </div>
        )}
      </div>

      {/* Post Graphic / Image / Video */}
      {imageUrl ? (
        <div className="relative aspect-video w-full bg-black overflow-hidden group">
          {isVideo ? (
            <video
              src={imageUrl}
              controls
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-cover"
            />
          ) : (
            <img
              src={imageUrl}
              alt="Facebook Visual"
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
          )}
          <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded text-[10px] font-medium text-white/90">
            {isVideo ? 'Facebook Video 🎥' : (isPublished ? 'Facebook Post' : 'Facebook Post Preview')}
          </div>
        </div>
      ) : (
        <div className="w-full h-48 bg-[#18191A] border-y border-[#3E4042] flex flex-col items-center justify-center text-[#B0B3B8] space-y-2 p-6 text-center">
          <div className="w-10 h-10 rounded-full bg-[#3A3B3C] flex items-center justify-center text-indigo-400 text-sm">
            🖼️
          </div>
          <p className="text-xs">{isPublished ? 'Organic Facebook Content' : 'No image generated yet. Click "Generate AI Visual" above.'}</p>
        </div>
      )}

      {/* Engagement Counter */}
      <div className="px-4 py-2 flex items-center justify-between text-xs text-[#B0B3B8] border-b border-[#3E4042]">
        <div className="flex items-center space-x-1.5">
          <div className="w-4 h-4 rounded-full bg-blue-600 flex items-center justify-center text-[10px] text-white font-bold">
            👍
          </div>
          <span>{likesDisplay}</span>
        </div>
        <div className="flex space-x-3">
          <span>{commentsDisplay}</span>
          <span>{sharesDisplay}</span>
        </div>
      </div>

      {/* Like / Comment / Share Bar */}
      <div className="px-2 py-1 flex items-center justify-around text-xs font-semibold text-[#B0B3B8]">
        <button className="flex-1 flex items-center justify-center space-x-2 py-2 hover:bg-[#3A3B3C] rounded-md transition text-[#B0B3B8] hover:text-blue-400">
          <ThumbsUp className="w-4 h-4" />
          <span>Like</span>
        </button>
        <button className="flex-1 flex items-center justify-center space-x-2 py-2 hover:bg-[#3A3B3C] rounded-md transition text-[#B0B3B8] hover:text-white">
          <MessageSquare className="w-4 h-4" />
          <span>Comment</span>
        </button>
        <button className="flex-1 flex items-center justify-center space-x-2 py-2 hover:bg-[#3A3B3C] rounded-md transition text-[#B0B3B8] hover:text-white">
          <Share2 className="w-4 h-4" />
          <span>Share</span>
        </button>
      </div>
    </div>
  );
};

