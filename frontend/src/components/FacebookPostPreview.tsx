'use client';

import React, { useState } from 'react';
import { 
  ThumbsUp, 
  MessageSquare, 
  Share2, 
  Globe, 
  MoreHorizontal, 
  CheckCircle2, 
  Volume2, 
  ExternalLink
} from 'lucide-react';
import { BrandProfile } from '@/lib/types';
import { useTheme } from './ThemeProvider';

interface Props {
  brand?: BrandProfile | null;
  caption: string;
  hashtags: string[];
  cta?: string;
  imageUrl?: string;
  isVideo?: boolean;
}

const DEFAULT_POST_IMAGE = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80';

export const FacebookPostPreview: React.FC<Props> = ({
  brand,
  caption,
  hashtags,
  cta,
  imageUrl,
  isVideo = false,
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [isLiked, setIsLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(142);

  const displayImage = imageUrl && imageUrl.trim() !== '' ? imageUrl : DEFAULT_POST_IMAGE;

  const metaAcc = brand?.meta_account;
  const brandName = metaAcc?.facebook_page_name || brand?.name || 'Apex Innovations';
  const logoUrl =
    (metaAcc as any)?.logo_url ||
    (metaAcc?.facebook_page_id ? `https://graph.facebook.com/v19.0/${metaAcc.facebook_page_id}/picture?type=large` : null) ||
    brand?.logo_url ||
    DEFAULT_POST_IMAGE;

  const isMediaVideo =
    isVideo ||
    (displayImage &&
      (displayImage.endsWith('.mp4') ||
        displayImage.endsWith('.mov') ||
        displayImage.endsWith('.webm') ||
        displayImage.startsWith('data:video/')));

  const toggleLike = () => {
    setIsLiked(!isLiked);
    setLikeCount(prev => (isLiked ? prev - 1 : prev + 1));
  };

  // Color tokens matching authentic Facebook Light & Dark themes
  const colors = isDark
    ? {
        cardBg: '#242526',
        cardBorder: '#3E4042',
        textPrimary: '#E4E6EB',
        textSecondary: '#B0B3B8',
        btnHoverBg: '#3A3B3C',
        ctaBg: '#3A3B3C',
        ctaBtnBg: '#4E4F50',
        activeLikeBg: '#263951',
        activeLikeText: '#4599FF',
        dividerBorder: '#3E4042',
      }
    : {
        cardBg: '#FFFFFF',
        cardBorder: '#CED0D4',
        textPrimary: '#050505',
        textSecondary: '#65676B',
        btnHoverBg: '#F2F2F2',
        ctaBg: '#F0F2F5',
        ctaBtnBg: '#E4E6EB',
        activeLikeBg: '#E7F3FF',
        activeLikeText: '#1877F2',
        dividerBorder: '#CED0D4',
      };

  return (
    <div
      style={{
        backgroundColor: colors.cardBg,
        color: colors.textPrimary,
        borderColor: colors.cardBorder,
      }}
      className="w-full max-w-lg rounded-lg border shadow-md overflow-hidden font-sans select-none transition-colors duration-200"
    >
      {/* FB Post Header */}
      <div className="p-3.5 flex items-center justify-between" style={{ backgroundColor: colors.cardBg }}>
        <div className="flex items-center space-x-2.5">
          <img
            src={logoUrl}
            alt={brandName}
            className="w-10 h-10 rounded-full object-cover border border-[#0000001a]"
          />
          <div>
            <div className="flex items-center space-x-1 font-semibold text-sm" style={{ color: colors.textPrimary }}>
              <span>{brandName}</span>
              <CheckCircle2 className="w-4 h-4 text-[#1877F2] fill-[#1877F2] text-white flex-shrink-0" />
            </div>
            <div className="flex items-center space-x-1 text-xs" style={{ color: colors.textSecondary }}>
              <span>Just now</span>
              <span>•</span>
              <Globe className="w-3 h-3" style={{ color: colors.textSecondary }} />
            </div>
          </div>
        </div>
        <button className="p-2 rounded-full transition" style={{ color: colors.textSecondary }}>
          <MoreHorizontal className="w-5 h-5" />
        </button>
      </div>

      {/* Post Text Body */}
      <div className="px-3.5 pb-3 text-sm space-y-2 leading-normal whitespace-pre-wrap" style={{ color: colors.textPrimary, backgroundColor: colors.cardBg }}>
        <p>{caption || '🚀 Introducing our next-gen AI social media automation workflow! Schedule, manage, and publish content seamlessly.'}</p>
        {hashtags && hashtags.length > 0 ? (
          <p className="text-[#1877F2] font-normal">{hashtags.join(' ')}</p>
        ) : (
          <p className="text-[#1877F2] font-normal">#SocialMediaAI #MetaAutomation #Growth</p>
        )}
      </div>

      {/* Post Media (Image or Video) */}
      <div className="relative w-full bg-black overflow-hidden group">
        {isMediaVideo ? (
          <div className="relative aspect-video w-full flex items-center justify-center bg-black">
            <video
              src={displayImage}
              controls
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-contain"
            />
            <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-md text-white text-[10px] font-mono px-2 py-1 rounded flex items-center space-x-1 pointer-events-none">
              <Volume2 className="w-3 h-3" />
              <span>VIDEO</span>
            </div>
          </div>
        ) : (
          <div className="relative w-full overflow-hidden max-h-[500px] flex items-center justify-center" style={{ backgroundColor: colors.ctaBg }}>
            <img
              src={displayImage}
              alt="Facebook Post Media"
              className="w-full h-auto object-cover max-h-[500px]"
            />
          </div>
        )}
      </div>

      {/* CTA / Facebook Link Preview Card Box */}
      <div className="p-3 flex items-center justify-between transition cursor-pointer" style={{ backgroundColor: colors.ctaBg, borderTop: `1px solid ${colors.dividerBorder}` }}>
        <div className="space-y-0.5 min-w-0 pr-2">
          <span className="text-[10px] font-mono uppercase tracking-wider block" style={{ color: colors.textSecondary }}>
            SENSATIONZ.AI
          </span>
          <p className="text-xs font-bold truncate" style={{ color: colors.textPrimary }}>{cta || '👉 Click link in bio to learn more!'}</p>
          <p className="text-[11px] truncate" style={{ color: colors.textSecondary }}>Official AI Publishing Platform</p>
        </div>
        <div className="px-3 py-1.5 rounded text-xs font-semibold flex-shrink-0 flex items-center space-x-1" style={{ backgroundColor: colors.ctaBtnBg, color: colors.textPrimary, border: `1px solid ${colors.dividerBorder}` }}>
          <span>Learn More</span>
          <ExternalLink className="w-3 h-3" style={{ color: colors.textSecondary }} />
        </div>
      </div>

      {/* Engagement Counters Bar */}
      <div className="px-3.5 py-2.5 flex items-center justify-between text-xs" style={{ color: colors.textSecondary, borderTop: `1px solid ${colors.dividerBorder}`, borderBottom: `1px solid ${colors.dividerBorder}`, backgroundColor: colors.cardBg }}>
        <div className="flex items-center space-x-1.5">
          <div className="flex -space-x-1">
            <div className="w-4 h-4 rounded-full bg-[#1877F2] flex items-center justify-center text-[10px] text-white shadow-sm">
              👍
            </div>
            <div className="w-4 h-4 rounded-full bg-[#FA383E] flex items-center justify-center text-[10px] text-white shadow-sm">
              ❤️
            </div>
          </div>
          <span className="font-medium" style={{ color: colors.textSecondary }}>{likeCount}</span>
        </div>
        <div className="flex space-x-3 font-normal" style={{ color: colors.textSecondary }}>
          <span>28 Comments</span>
          <span>19 Shares</span>
        </div>
      </div>

      {/* Action Buttons (Like / Comment / Share) */}
      <div className="px-2 py-1 flex items-center justify-around text-xs font-semibold" style={{ backgroundColor: colors.cardBg }}>
        <button
          onClick={toggleLike}
          className="flex-1 flex items-center justify-center space-x-2 py-1.5 rounded transition"
          style={
            isLiked
              ? { backgroundColor: colors.activeLikeBg, color: colors.activeLikeText }
              : { color: colors.textSecondary }
          }
        >
          <ThumbsUp className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
          <span>Like</span>
        </button>
        <button className="flex-1 flex items-center justify-center space-x-2 py-1.5 rounded transition" style={{ color: colors.textSecondary }}>
          <MessageSquare className="w-4 h-4" />
          <span>Comment</span>
        </button>
        <button className="flex-1 flex items-center justify-center space-x-2 py-1.5 rounded transition" style={{ color: colors.textSecondary }}>
          <Share2 className="w-4 h-4" />
          <span>Share</span>
        </button>
      </div>
    </div>
  );
};
