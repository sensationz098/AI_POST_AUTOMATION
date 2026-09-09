/**
 * Story URL Validation and Helper Utilities.
 * Ensures the application never generates or opens broken Meta Story URLs such as:
 * - https://www.facebook.com/{page_id}
 * - https://www.instagram.com/stories/ (missing username)
 */

import { SchedulerItem } from './types';

/**
 * Validates that an Instagram URL is a legitimate active story link or valid media permalink.
 * Rejects bare /stories/ with no username.
 */
export function isValidInstagramStoryUrl(url?: string | null): boolean {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();

  // Reject bare roots or bare /stories/
  if (/^https?:\/\/(www\.)?instagram\.com\/?$/i.test(trimmed)) return false;
  if (/^https?:\/\/(www\.)?instagram\.com\/stories\/?$/i.test(trimmed)) return false;
  if (/^https?:\/\/(www\.)?instagram\.com\/stories\/\/?$/i.test(trimmed)) return false;

  // Match /stories/<username>/ (optional media ID)
  const storyMatch = trimmed.match(
    /^https?:\/\/(www\.)?instagram\.com\/stories\/([a-zA-Z0-9._]{1,30})(?:\/\d+)?\/?(\?.*)?$/i
  );
  if (storyMatch) {
    const userSegment = storyMatch[2]?.toLowerCase();
    if (!userSegment || ['stories', 'story', 'undefined', 'null', 'none', 'n/a', 'unknown'].includes(userSegment)) {
      return false;
    }
    return true;
  }

  // Accept highlights: /stories/highlights/...
  if (/^https?:\/\/(www\.)?instagram\.com\/stories\/highlights\/\d+\/?(\?.*)?$/i.test(trimmed)) {
    return true;
  }

  // Also accept valid post/reel permalink
  return /^https?:\/\/(www\.)?instagram\.com\/(p|reel|tv)\/[a-zA-Z0-9_-]+\/?(\?.*)?$/i.test(trimmed);
}

/**
 * Validates that a Facebook URL is a legitimate individual Story permalink or valid post link.
 * Rejects bare numeric IDs like https://www.facebook.com/123456789.
 */
export function isValidFacebookStoryUrl(url?: string | null): boolean {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();

  // Reject bare root, bare /stories/, bare numeric post/page IDs
  if (/^https?:\/\/(www\.)?facebook\.com\/?$/i.test(trimmed)) return false;
  if (/^https?:\/\/(www\.)?facebook\.com\/stories\/?$/i.test(trimmed)) return false;
  if (/^https?:\/\/(www\.)?facebook\.com\/stories\/\d+\/?$/i.test(trimmed)) return false;
  if (/^https?:\/\/(www\.)?facebook\.com\/\d+\/?$/i.test(trimmed)) return false;

  if (
    !trimmed.startsWith('https://www.facebook.com/') &&
    !trimmed.startsWith('https://facebook.com/') &&
    !trimmed.startsWith('https://fb.watch/')
  ) {
    return false;
  }

  return true;
}

export interface ValidStoryUrls {
  fbUrl: string | null;
  igUrl: string | null;
  hasFb: boolean;
  hasIg: boolean;
}

/**
 * Resolves verified, platform-safe Story URLs from a SchedulerItem.
 * Only returns URLs that pass strict validation and correspond to published platform IDs.
 */
export function getValidStoryUrls(item: SchedulerItem): ValidStoryUrls {
  // Only published or partially published items can have live story links
  const isPublishedState = item.status === 'PUBLISHED' || item.status === 'PARTIALLY_DELETED';
  if (!isPublishedState && !item.fb_id && !item.ig_id) {
    return { fbUrl: null, igUrl: null, hasFb: false, hasIg: false };
  }

  // Facebook Story URL
  let fbUrl: string | null = null;
  if (item.fb_id && item.fb_url && isValidFacebookStoryUrl(item.fb_url)) {
    fbUrl = item.fb_url;
  }

  // Instagram Story URL
  let igUrl: string | null = null;
  if (item.ig_id) {
    if (item.ig_url && isValidInstagramStoryUrl(item.ig_url)) {
      igUrl = item.ig_url;
    } else {
      // Try resolving username from target_accounts if available
      const igAcc = item.target_accounts?.find(
        (a) => a.platform === 'instagram' && a.username && a.username.trim()
      );
      if (igAcc?.username) {
        const cleanUser = igAcc.username.trim().replace(/^@/, '');
        const candidateUrl = `https://www.instagram.com/stories/${cleanUser}/`;
        if (isValidInstagramStoryUrl(candidateUrl)) {
          igUrl = candidateUrl;
        }
      }
    }
  }

  return {
    fbUrl,
    igUrl,
    hasFb: Boolean(fbUrl),
    hasIg: Boolean(igUrl),
  };
}
