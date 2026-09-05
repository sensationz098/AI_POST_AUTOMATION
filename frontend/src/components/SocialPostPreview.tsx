'use client';

import React from 'react';
import { FacebookPostPreview } from './FacebookPostPreview';
import { InstagramPostPreview } from './InstagramPostPreview';
import { BrandProfile } from '@/lib/types';

export interface SocialPostPreviewProps {
  platform?: string;
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
  className?: string;
}

export const SocialPostPreview: React.FC<SocialPostPreviewProps> = ({
  platform = 'facebook',
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
  isPublished = true,
  className,
}) => {
  const isIg = platform?.toLowerCase().includes('instagram');

  return (
    <div className={`flex justify-center w-full ${className || ''}`}>
      {isIg ? (
        <InstagramPostPreview
          brand={brand}
          caption={caption}
          hashtags={hashtags}
          cta={cta}
          imageUrl={imageUrl}
          mediaType={mediaType}
          accountName={accountName}
          accountAvatar={accountAvatar}
          publishedAt={publishedAt}
          permalink={permalink}
          likeCount={likeCount}
          commentCount={commentCount}
          externalPostId={externalPostId}
          isPublished={isPublished}
        />
      ) : (
        <FacebookPostPreview
          brand={brand}
          caption={caption}
          hashtags={hashtags}
          cta={cta}
          imageUrl={imageUrl}
          mediaType={mediaType}
          accountName={accountName}
          accountAvatar={accountAvatar}
          publishedAt={publishedAt}
          permalink={permalink}
          likeCount={likeCount}
          commentCount={commentCount}
          shareCount={shareCount}
          externalPostId={externalPostId}
          isPublished={isPublished}
        />
      )}
    </div>
  );
};

export default SocialPostPreview;
