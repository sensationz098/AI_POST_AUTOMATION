'use client';

import React from 'react';
import { Heart, MessageCircle, Send, Bookmark, MoreHorizontal } from 'lucide-react';
import { BrandProfile } from '@/lib/types';

interface Props {
  brand?: BrandProfile | null;
  caption: string;
  hashtags: string[];
  cta?: string;
  imageUrl?: string;
}

export const InstagramPostPreview: React.FC<Props> = ({
  brand,
  caption,
  hashtags,
  cta,
  imageUrl,
}) => {
  const metaAcc = brand?.meta_account;
  const username = metaAcc?.instagram_username
    ? metaAcc.instagram_username
    : (brand?.name ? brand.name.toLowerCase().replace(/\s+/g, '_') : 'apex_innovations');
    
  const logoUrl =
    (metaAcc as any)?.logo_url ||
    (metaAcc?.facebook_page_id ? `https://graph.facebook.com/v19.0/${metaAcc.facebook_page_id}/picture?type=large` : null) ||
    brand?.logo_url ||
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80';

  return (
    <div className="w-full max-w-sm bg-black text-white rounded-3xl border border-neutral-800 shadow-2xl overflow-hidden font-sans">
      {/* IG Header */}
      <div className="p-3.5 flex items-center justify-between border-b border-neutral-900">
        <div className="flex items-center space-x-2.5">
          <div className="p-0.5 rounded-full bg-gradient-to-tr from-yellow-500 via-pink-500 to-purple-600">
            <img
              src={logoUrl}
              alt={username}
              className="w-8 h-8 rounded-full object-cover border-2 border-black"
            />
          </div>
          <div>
            <p className="text-xs font-semibold hover:opacity-80 cursor-pointer">{username}</p>
            <p className="text-[10px] text-neutral-400">Sponsored</p>
          </div>
        </div>
        <button className="text-neutral-400 hover:text-white transition">
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>

      {/* IG Media Frame (1:1 Ratio or Video Container) */}
      <div className="relative aspect-square w-full bg-neutral-950 overflow-hidden flex items-center justify-center">
        {imageUrl ? (
          (imageUrl.endsWith('.mp4') || imageUrl.endsWith('.mov') || imageUrl.endsWith('.webm') || imageUrl.startsWith('data:video/')) ? (
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
              alt="Instagram Post"
              className="w-full h-full object-cover"
            />
          )
        ) : (
          <div className="flex flex-col items-center space-y-2 p-6 text-center text-neutral-500">
            <div className="w-12 h-12 rounded-full bg-neutral-900 flex items-center justify-center text-pink-500">
              📸
            </div>
            <p className="text-xs">Your AI generated Instagram visual will appear here.</p>
          </div>
        )}
        <div className="absolute top-2.5 right-2.5 bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-full text-[9px] font-semibold text-white">
          {(imageUrl?.endsWith('.mp4') || imageUrl?.endsWith('.mov') || imageUrl?.startsWith('data:video/')) ? 'Instagram Reel 🎥' : 'Instagram Feed'}
        </div>
      </div>

      {/* Action Bar (Heart, Comment, Share, Bookmark) */}
      <div className="p-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <button className="hover:text-red-500 transition">
              <Heart className="w-6 h-6" />
            </button>
            <button className="hover:text-neutral-400 transition">
              <MessageCircle className="w-6 h-6" />
            </button>
            <button className="hover:text-neutral-400 transition">
              <Send className="w-6 h-6" />
            </button>
          </div>
          <button className="hover:text-neutral-400 transition">
            <Bookmark className="w-6 h-6" />
          </button>
        </div>

        {/* Likes Count */}
        <p className="text-xs font-semibold text-white">1,842 likes</p>

        {/* Caption & Hashtags */}
        <div className="text-xs space-y-1.5 leading-relaxed">
          <p className="text-neutral-200">
            <span className="font-semibold text-white mr-1.5">{username}</span>
            {caption || 'Your AI generated Instagram caption preview...'}
          </p>
          {cta && <p className="text-pink-400 font-medium">{cta}</p>}
          {hashtags && hashtags.length > 0 && (
            <p className="text-sky-400 font-medium">{hashtags.join(' ')}</p>
          )}
        </div>

        <p className="text-[10px] text-neutral-500 uppercase tracking-wide pt-1">
          2 hours ago
        </p>
      </div>
    </div>
  );
};
