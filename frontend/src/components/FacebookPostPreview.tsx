'use client';

import React from 'react';
import { ThumbsUp, MessageSquare, Share2, Globe, MoreHorizontal, CheckCircle2 } from 'lucide-react';
import { BrandProfile } from '@/lib/types';

interface Props {
  brand?: BrandProfile | null;
  caption: string;
  hashtags: string[];
  cta?: string;
  imageUrl?: string;
}

export const FacebookPostPreview: React.FC<Props> = ({
  brand,
  caption,
  hashtags,
  cta,
  imageUrl,
}) => {
  const brandName = brand?.name || 'Apex Innovations';
  const logoUrl = brand?.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80';

  return (
    <div className="w-full max-w-lg bg-[#242526] text-[#E4E6EB] rounded-xl border border-[#3E4042] shadow-2xl overflow-hidden font-sans">
      {/* FB Post Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <img
            src={logoUrl}
            alt={brandName}
            className="w-10 h-10 rounded-full object-cover border border-indigo-500/50"
          />
          <div>
            <div className="flex items-center space-x-1.5 font-semibold text-sm text-white">
              <span>{brandName}</span>
              <CheckCircle2 className="w-4 h-4 text-blue-500 fill-blue-500/20" />
            </div>
            <div className="flex items-center space-x-1 text-xs text-[#B0B3B8]">
              <span>Just now</span>
              <span>•</span>
              <Globe className="w-3 h-3 text-[#B0B3B8]" />
            </div>
          </div>
        </div>
        <button className="text-[#B0B3B8] hover:bg-[#3A3B3C] p-2 rounded-full transition">
          <MoreHorizontal className="w-5 h-5" />
        </button>
      </div>

      {/* Post Text & Body */}
      <div className="px-4 pb-3 text-sm space-y-2 leading-relaxed text-[#E4E6EB] whitespace-pre-wrap">
        <p>{caption || 'Your AI generated Facebook caption will render live here...'}</p>
        {hashtags && hashtags.length > 0 && (
          <p className="text-blue-400 font-medium">{hashtags.join(' ')}</p>
        )}
        {cta && (
          <div className="mt-2 p-3 bg-[#3A3B3C]/70 rounded-lg border-l-4 border-indigo-500 text-xs font-semibold text-indigo-300">
            {cta}
          </div>
        )}
      </div>

      {/* Post Graphic / Image */}
      {imageUrl ? (
        <div className="relative aspect-video w-full bg-black overflow-hidden group">
          <img
            src={imageUrl}
            alt="Facebook Visual"
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
          <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded text-[10px] font-medium text-white/90">
            Facebook Post Preview
          </div>
        </div>
      ) : (
        <div className="w-full h-56 bg-[#18191A] border-y border-[#3E4042] flex flex-col items-center justify-center text-[#B0B3B8] space-y-2 p-6 text-center">
          <div className="w-12 h-12 rounded-full bg-[#3A3B3C] flex items-center justify-center text-indigo-400">
            🖼️
          </div>
          <p className="text-xs">No image generated yet. Click "Generate AI Visual" above.</p>
        </div>
      )}

      {/* Engagement Counter */}
      <div className="px-4 py-2 flex items-center justify-between text-xs text-[#B0B3B8] border-b border-[#3E4042]">
        <div className="flex items-center space-x-1.5">
          <div className="w-4 h-4 rounded-full bg-blue-600 flex items-center justify-center text-[10px] text-white font-bold">
            👍
          </div>
          <span>142</span>
        </div>
        <div className="flex space-x-3">
          <span>28 Comments</span>
          <span>19 Shares</span>
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
