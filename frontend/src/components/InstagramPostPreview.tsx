'use client';

import React, { useState } from 'react';
import { Heart, MessageCircle, Send, Bookmark, MoreHorizontal } from 'lucide-react';
import { BrandProfile } from '@/lib/types';
import { useTheme } from './ThemeProvider';

interface Props {
  brand?: BrandProfile | null;
  caption: string;
  hashtags: string[];
  cta?: string;
  imageUrl?: string;
}

const DEFAULT_POST_IMAGE = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80';

export const InstagramPostPreview: React.FC<Props> = ({
  brand,
  caption,
  hashtags,
  cta,
  imageUrl,
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [isLiked, setIsLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(1842);

  const displayImage = imageUrl && imageUrl.trim() !== '' ? imageUrl : DEFAULT_POST_IMAGE;

  const metaAcc = brand?.meta_account;
  const username = metaAcc?.instagram_username
    ? metaAcc.instagram_username
    : (brand?.name ? brand.name.toLowerCase().replace(/\s+/g, '_') : 'apex_official');
    
  const logoUrl =
    (metaAcc as any)?.logo_url ||
    (metaAcc?.facebook_page_id ? `https://graph.facebook.com/v19.0/${metaAcc.facebook_page_id}/picture?type=large` : null) ||
    brand?.logo_url ||
    DEFAULT_POST_IMAGE;

  const isMediaVideo =
    displayImage &&
    (displayImage.endsWith('.mp4') ||
      displayImage.endsWith('.mov') ||
      displayImage.endsWith('.webm') ||
      displayImage.startsWith('data:video/'));

  const toggleLike = () => {
    setIsLiked(!isLiked);
    setLikeCount(prev => (isLiked ? prev - 1 : prev + 1));
  };

  const colors = isDark
    ? {
        cardBg: '#000000',
        cardBorder: '#262626',
        textPrimary: '#FFFFFF',
        textSecondary: '#A8A8A8',
        mediaBg: '#121212',
      }
    : {
        cardBg: '#FFFFFF',
        cardBorder: '#DBDBDB',
        textPrimary: '#000000',
        textSecondary: '#737373',
        mediaBg: '#FAFAFA',
      };

  return (
    <div
      style={{
        backgroundColor: colors.cardBg,
        color: colors.textPrimary,
        borderColor: colors.cardBorder,
      }}
      className="w-full rounded-2xl border shadow-xl overflow-hidden font-sans select-none transition-colors duration-200"
    >
      {/* IG Header */}
      <div className="p-3 flex items-center justify-between border-b" style={{ backgroundColor: colors.cardBg, borderColor: colors.cardBorder }}>
        <div className="flex items-center space-x-2.5">
          <div className="p-0.5 rounded-full bg-gradient-to-tr from-[#FBAA47] via-[#D91A46] to-[#A60F93]">
            <img
              src={logoUrl}
              alt={username}
              className="w-7 h-7 rounded-full object-cover border border-black"
            />
          </div>
          <div>
            <p className="text-xs font-semibold leading-tight" style={{ color: colors.textPrimary }}>{username}</p>
            <p className="text-[10px]" style={{ color: colors.textSecondary }}>Sponsored</p>
          </div>
        </div>
        <button style={{ color: colors.textSecondary }} className="hover:opacity-70 transition">
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>

      {/* IG Media Frame (1:1 Ratio or Video Container) */}
      <div className="relative aspect-square w-full overflow-hidden flex items-center justify-center" style={{ backgroundColor: colors.mediaBg }}>
        {isMediaVideo ? (
          <video
            src={displayImage}
            controls
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover"
          />
        ) : (
          <img
            src={displayImage}
            alt="Instagram Post"
            className="w-full h-full object-cover"
          />
        )}
      </div>

      {/* Action Bar (Heart, Comment, Share, Bookmark) */}
      <div className="p-3 space-y-2" style={{ backgroundColor: colors.cardBg }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <button onClick={toggleLike} className="hover:opacity-70 transition">
              <Heart className={`w-5 h-5 ${isLiked ? 'text-[#FF3040] fill-[#FF3040]' : ''}`} style={{ color: isLiked ? '#FF3040' : colors.textPrimary }} />
            </button>
            <button className="hover:opacity-70 transition" style={{ color: colors.textPrimary }}>
              <MessageCircle className="w-5 h-5" />
            </button>
            <button className="hover:opacity-70 transition" style={{ color: colors.textPrimary }}>
              <Send className="w-5 h-5" />
            </button>
          </div>
          <button className="hover:opacity-70 transition" style={{ color: colors.textPrimary }}>
            <Bookmark className="w-5 h-5" />
          </button>
        </div>

        {/* Likes Count */}
        <p className="text-xs font-semibold" style={{ color: colors.textPrimary }}>{likeCount.toLocaleString()} likes</p>

        {/* Caption & Hashtags */}
        <div className="text-xs space-y-1 leading-normal">
          <p style={{ color: colors.textPrimary }}>
            <span className="font-semibold mr-1.5" style={{ color: colors.textPrimary }}>{username}</span>
            {caption || '🚀 Introducing our next-gen AI social media automation workflow! Schedule, manage, and publish content seamlessly.'}
          </p>
          {cta && <p className="font-medium text-[11px] text-[#0095F6]">{cta}</p>}
          {hashtags && hashtags.length > 0 ? (
            <p className="text-[#0095F6] font-normal text-[11px]">{hashtags.join(' ')}</p>
          ) : (
            <p className="text-[#0095F6] font-normal text-[11px]">#SocialMediaAI #MetaAutomation #Growth</p>
          )}
        </div>

        <p className="text-[10px] uppercase tracking-wide pt-1" style={{ color: colors.textSecondary }}>
          2 hours ago
        </p>
      </div>
    </div>
  );
};
