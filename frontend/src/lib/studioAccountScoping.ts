export const SUPPORTED_STUDIO_POST_PLATFORMS = ['facebook', 'instagram'] as const;

export interface ScopedSocialAccount {
  id: number;
  platform: string;
  [key: string]: any;
}

/**
 * Filter social accounts to only those supported by Studio Post/Reel multi-account publishing.
 * (Facebook Pages and Instagram Accounts only; excludes YouTube channels).
 */
export function filterPostCapableAccounts<T extends ScopedSocialAccount>(accounts: T[]): T[] {
  if (!Array.isArray(accounts)) return [];
  return accounts.filter(
    a => a.platform === 'facebook' || a.platform === 'instagram'
  );
}

/**
 * Sanitize selected account IDs to ensure only post-capable account IDs are submitted for publishing.
 * Prevents orphan or invisible account IDs (e.g. YouTube IDs) from being sent to multi-publish.
 */
export function sanitizeTargetAccountIds<T extends ScopedSocialAccount>(
  selectedAccountIds: number[],
  postCapableAccounts: T[]
): number[] {
  if (!Array.isArray(selectedAccountIds) || !Array.isArray(postCapableAccounts)) return [];
  const capableIdSet = new Set(postCapableAccounts.map(a => a.id));
  return selectedAccountIds.filter(id => capableIdSet.has(id));
}
