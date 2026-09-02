'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Share2, CheckCircle2, Facebook, Instagram, ShieldCheck,
  ChevronRight, ExternalLink, RefreshCw, AlertCircle,
  Loader2, Unlink, Link2, Edit3, Sparkles, Key, Lock, ArrowRight,
  Megaphone, Globe, DollarSign, ChevronDown, Layers, FileText, Check, HelpCircle,
  Search, ChevronLeft, Filter, X
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialAccount, MetaAdAccount, MetaAd } from '@/lib/types';

export default function MetaConnectPage() {
  // Connected Accounts State
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(true);
  const [disconnectingId, setDisconnectingId] = useState<number | string | 'all' | null>(null);

  // Meta Ad Accounts State
  const [adAccounts, setAdAccounts] = useState<MetaAdAccount[]>([]);
  const [isLoadingAdAccounts, setIsLoadingAdAccounts] = useState(false);
  const [isSyncingAdAccounts, setIsSyncingAdAccounts] = useState(false);
  const [adAccountError, setAdAccountError] = useState<string | null>(null);
  const [adAccountSuccess, setAdAccountSuccess] = useState<string | null>(null);

  // Meta Ads & Creative Engagement Mappings State
  const [adsByAccount, setAdsByAccount] = useState<Record<string, MetaAd[]>>({});
  const [expandedAdAccountId, setExpandedAdAccountId] = useState<string | null>(null);
  const [isSyncingAds, setIsSyncingAds] = useState<Record<string, boolean>>({});
  const [isLoadingAds, setIsLoadingAds] = useState<Record<string, boolean>>({});
  const [adSyncError, setAdSyncError] = useState<Record<string, string | null>>({});
  const [adSyncSuccess, setAdSyncSuccess] = useState<Record<string, string | null>>({});

  // Meta Ads Search, Filter & Pagination State
  const [adStatusFilter, setAdStatusFilter] = useState<string>('ALL');
  const [adSearchQuery, setAdSearchQuery] = useState<string>('');
  const [adCurrentPage, setAdCurrentPage] = useState<number>(1);
  const AD_PAGE_SIZE = 25;

  // Reset filter, search & pagination when expanded ad account changes
  useEffect(() => {
    setAdStatusFilter('ALL');
    setAdSearchQuery('');
    setAdCurrentPage(1);
  }, [expandedAdAccountId]);

  // Derived state for Meta Ads filtering & pagination
  const currentExpandedAds = useMemo(() => {
    if (!expandedAdAccountId) return [];
    return adsByAccount[expandedAdAccountId] || [];
  }, [expandedAdAccountId, adsByAccount]);

  const uniqueStatuses = useMemo(() => {
    const statusSet = new Set<string>();
    currentExpandedAds.forEach(ad => {
      if (ad.effective_status) {
        statusSet.add(ad.effective_status);
      }
    });
    return Array.from(statusSet).sort();
  }, [currentExpandedAds]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { ALL: currentExpandedAds.length };
    currentExpandedAds.forEach(ad => {
      const st = ad.effective_status || 'UNKNOWN';
      counts[st] = (counts[st] || 0) + 1;
    });
    return counts;
  }, [currentExpandedAds]);

  const filteredAds = useMemo(() => {
    return currentExpandedAds.filter(ad => {
      // 1. Status Filter
      if (adStatusFilter !== 'ALL') {
        const st = ad.effective_status || 'UNKNOWN';
        if (st !== adStatusFilter) {
          return false;
        }
      }

      // 2. Search Filter
      if (adSearchQuery.trim() !== '') {
        const q = adSearchQuery.toLowerCase().trim();
        const matchName = ad.name?.toLowerCase().includes(q);
        const matchAdId = ad.meta_ad_id?.toLowerCase().includes(q);
        const matchCampName = ad.campaign_name?.toLowerCase().includes(q);
        const matchCampId = ad.campaign_id?.toLowerCase().includes(q);
        const matchAdsetName = ad.adset_name?.toLowerCase().includes(q);
        const matchAdsetId = ad.adset_id?.toLowerCase().includes(q);

        if (!matchName && !matchAdId && !matchCampName && !matchCampId && !matchAdsetName && !matchAdsetId) {
          return false;
        }
      }

      return true;
    });
  }, [currentExpandedAds, adStatusFilter, adSearchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredAds.length / AD_PAGE_SIZE));
  const validCurrentPage = Math.min(Math.max(1, adCurrentPage), totalPages);

  const paginatedAds = useMemo(() => {
    const start = (validCurrentPage - 1) * AD_PAGE_SIZE;
    return filteredAds.slice(start, start + AD_PAGE_SIZE);
  }, [filteredAds, validCurrentPage]);

  // OAuth State
  const [isOAuthStarting, setIsOAuthStarting] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [oauthSuccess, setOauthSuccess] = useState<string | null>(null);

  // Optional Advanced Developer Manual Mode toggle
  const [showManualMode, setShowManualMode] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [manualPageId, setManualPageId] = useState('');
  const [manualPageName, setManualPageName] = useState('');
  const [manualIgId, setManualIgId] = useState('');
  const [manualIgUsername, setManualIgUsername] = useState('');
  const [isSavingManual, setIsSavingManual] = useState(false);

  // Fetch connected multi-destination social accounts
  const fetchSocialAccounts = async () => {
    setIsLoadingAccounts(true);
    try {
      const res = await apiClient.get('/social-accounts/');
      if (Array.isArray(res.data)) {
        const fakeIds = new Set(['109823471029', '17841400928371', '17841400928372', '17841400928373', '109823471030', 'sandbox']);
        const realAccounts = res.data.filter(a => !fakeIds.has(a.account_id) && !a.account_name?.includes('Apex Innovations Page'));
        setSocialAccounts(realAccounts);
      }
    } catch (e) {
      console.error('Failed to load social accounts:', e);
    } finally {
      setIsLoadingAccounts(false);
    }
  };

  // Fetch stored Meta Ad Accounts
  const fetchAdAccounts = async () => {
    setIsLoadingAdAccounts(true);
    setAdAccountError(null);
    try {
      const res = await apiClient.get('/meta/ad-accounts');
      if (Array.isArray(res.data)) {
        setAdAccounts(res.data);
      }
    } catch (e: any) {
      console.error('Failed to load Meta Ad Accounts:', e);
    } finally {
      setIsLoadingAdAccounts(false);
    }
  };

  // Sync Meta Ad Accounts from Meta Graph API
  const handleSyncAdAccounts = async () => {
    setIsSyncingAdAccounts(true);
    setAdAccountError(null);
    setAdAccountSuccess(null);
    try {
      const res = await apiClient.post('/meta/ad-accounts/sync');
      if (res.data?.accounts && Array.isArray(res.data.accounts)) {
        setAdAccounts(res.data.accounts);
        setAdAccountSuccess(res.data.message || `Successfully synced ${res.data.synced_count} Meta Ad Account(s).`);
      }
    } catch (e: any) {
      console.error('Failed to sync Meta Ad Accounts:', e);
      const errMsg = e?.response?.data?.detail || 'Failed to sync Meta Ad Accounts. Please check permissions and try again.';
      setAdAccountError(errMsg);
    } finally {
      setIsSyncingAdAccounts(false);
    }
  };

  // Fetch cached ads for a specific Ad Account
  const fetchAdsForAccount = async (adAccountId: string) => {
    setIsLoadingAds(prev => ({ ...prev, [adAccountId]: true }));
    setAdSyncError(prev => ({ ...prev, [adAccountId]: null }));
    try {
      const res = await apiClient.get(`/meta/ad-accounts/${adAccountId}/ads`);
      if (Array.isArray(res.data)) {
        setAdsByAccount(prev => ({ ...prev, [adAccountId]: res.data }));
      }
    } catch (e: any) {
      console.error(`Failed to fetch ads for account ${adAccountId}:`, e);
    } finally {
      setIsLoadingAds(prev => ({ ...prev, [adAccountId]: false }));
    }
  };

  // Sync ads & creative engagement mappings for a specific Ad Account
  const handleSyncAdsForAccount = async (adAccountId: string) => {
    setIsSyncingAds(prev => ({ ...prev, [adAccountId]: true }));
    setAdSyncError(prev => ({ ...prev, [adAccountId]: null }));
    setAdSyncSuccess(prev => ({ ...prev, [adAccountId]: null }));
    try {
      const res = await apiClient.post(`/meta/ad-accounts/${adAccountId}/ads/sync`);
      if (res.data?.ads && Array.isArray(res.data.ads)) {
        setAdsByAccount(prev => ({ ...prev, [adAccountId]: res.data.ads }));
        setExpandedAdAccountId(adAccountId);
        const mapped = res.data.mapped_count ?? 0;
        const partial = res.data.partially_mapped_count ?? 0;
        const unmapped = res.data.unmapped_count ?? 0;
        const total = res.data.synced_count ?? res.data.ads.length;
        const msg = res.data.message || `Successfully synced ${total} Ad(s) (${mapped} mapped, ${partial} partially mapped, ${unmapped} unmapped).`;
        setAdSyncSuccess(prev => ({ ...prev, [adAccountId]: msg }));
        setAdSyncError(prev => ({ ...prev, [adAccountId]: null }));
      }
    } catch (e: any) {
      console.error(`Failed to sync ads for account ${adAccountId}:`, e);
      let errMsg = e?.response?.data?.detail;
      if (!errMsg) {
        if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
          errMsg = 'Ad sync request timed out. Please check your network connection and try again.';
        } else if (e?.response?.status === 400) {
          errMsg = 'Unable to sync Meta Ads. Please verify permissions or reconnect your Meta account.';
        } else if (e?.response?.status === 404) {
          errMsg = 'Meta Ad Account not found or access denied.';
        } else {
          errMsg = 'An unexpected error occurred while syncing Meta Ads. Please try again.';
        }
      }
      setAdSyncError(prev => ({ ...prev, [adAccountId]: errMsg }));
    } finally {
      setIsSyncingAds(prev => ({ ...prev, [adAccountId]: false }));
    }
  };

  const toggleExpandAdAccount = (adAccountId: string) => {
    if (expandedAdAccountId === adAccountId) {
      setExpandedAdAccountId(null);
    } else {
      setExpandedAdAccountId(adAccountId);
      if (!adsByAccount[adAccountId]) {
        fetchAdsForAccount(adAccountId);
      }
    }
  };

  useEffect(() => {
    fetchSocialAccounts();
    fetchAdAccounts();

    // Check OAuth return params
    if (typeof window !== 'undefined') {
      const searchParams = new URLSearchParams(window.location.search);
      if (searchParams.get('connected') === 'true') {
        const pagesCount = searchParams.get('pages') || '0';
        const igCount = searchParams.get('ig') || '0';
        setOauthSuccess(`✓ Meta connected successfully! Discovered ${pagesCount} Facebook Page(s) & ${igCount} Instagram Professional account(s).`);
      } else if (searchParams.get('error')) {
        setOauthError(decodeURIComponent(searchParams.get('error') || 'Meta OAuth authorization failed.'));
      }
    }
  }, []);

  // Initiate Real Meta OAuth Flow - Uses authenticated API call to retrieve Meta Authorization Dialog URL
  const handleConnectMetaOAuth = async () => {
    setIsOAuthStarting(true);
    setOauthError(null);
    setOauthSuccess(null);
    try {
      const res = await apiClient.get('/meta/oauth/start?redirect=false');
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      } else {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        window.location.href = `${apiUrl}/meta/oauth/start`;
      }
    } catch (e: any) {
      console.error('Meta OAuth start error:', e);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      window.location.href = `${apiUrl}/meta/oauth/start`;
    }
  };


  // Disconnect a single social account
  const handleDisconnectAccount = async (id: number | string) => {
    if (!confirm('Are you sure you want to disconnect this social account?')) return;
    setDisconnectingId(id);
    setOauthError(null);
    setOauthSuccess(null);
    try {
      await apiClient.delete(`/social-accounts/${id}`);
      setSocialAccounts((prev) => prev.filter((a) => a.id !== id && a.account_id !== String(id)));
      setOauthSuccess('Social account disconnected successfully.');
      if (typeof window !== 'undefined') {
        localStorage.removeItem('meta_connected_account');
      }
    } catch (e: any) {
      console.error('Failed to disconnect social account:', e);
      const errMsg = e?.response?.data?.detail || 'Failed to disconnect social account. Please try again.';
      setOauthError(errMsg);
    } finally {
      setDisconnectingId(null);
    }
  };

  // Disconnect all Meta accounts
  const handleDisconnectAll = async () => {
    if (!confirm('Are you sure you want to disconnect all Meta connected accounts?')) return;
    setDisconnectingId('all');
    setOauthError(null);
    setOauthSuccess(null);
    try {
      try {
        await apiClient.delete('/meta/disconnect');
      } catch {
        await apiClient.delete('/social-accounts/disconnect-all');
      }
      setSocialAccounts([]);
      setOauthSuccess('All Meta social accounts disconnected successfully.');
      if (typeof window !== 'undefined') {
        localStorage.removeItem('meta_connected_account');
      }
    } catch (e: any) {
      console.error('Failed to disconnect all Meta accounts:', e);
      const errMsg = e?.response?.data?.detail || 'Failed to disconnect Meta accounts. Please try again.';
      setOauthError(errMsg);
    } finally {
      setDisconnectingId(null);
    }
  };

  // Developer Manual Entry Handler
  const handleSaveManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualPageId.trim() || !manualToken.trim()) {
      alert('Please provide at least a Facebook Page ID and Access Token.');
      return;
    }
    setIsSavingManual(true);
    setOauthError(null);

    const logoUrl = `https://graph.facebook.com/v19.0/${manualPageId.trim()}/picture?type=large`;
    const token = manualToken.trim();

    try {
      // Register Facebook Social Account
      await apiClient.post('/social-accounts/connect', {
        brand_id: 1,
        platform: 'facebook',
        account_id: manualPageId.trim(),
        account_name: manualPageName.trim() || 'Facebook Page',
        access_token: token,
        logo_url: logoUrl,
      });

      // Register Instagram Social Account if provided
      if (manualIgId.trim() || manualIgUsername.trim()) {
        await apiClient.post('/social-accounts/connect', {
          brand_id: 1,
          platform: 'instagram',
          account_id: manualIgId.trim() || 'ig_account',
          account_name: `@${manualIgUsername.trim() || 'instagram_account'}`,
          access_token: token,
          logo_url: logoUrl,
        });
      }

      setOauthSuccess('Social accounts connected via developer entry successfully!');
      fetchSocialAccounts();
      setShowManualMode(false);
      setManualToken('');
      setManualPageId('');
      setManualPageName('');
      setManualIgId('');
      setManualIgUsername('');
    } catch (e: any) {
      setOauthError(e?.response?.data?.detail || 'Failed to save developer credentials.');
    } finally {
      setIsSavingManual(false);
    }
  };

  const fbPages = socialAccounts.filter(a => a.platform === 'facebook');
  const igAccounts = socialAccounts.filter(a => a.platform === 'instagram');

  return (
    <div className="space-y-8 max-w-4xl select-none font-sans text-xs">
      {/* SaaS Linear Header Banner */}
      <div className="linear-panel p-6 rounded-2xl space-y-4 border border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-11 h-11 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400 shadow-sm flex-shrink-0">
              <Share2 className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100 tracking-tight">
                Connect Meta Accounts
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Authorize your Facebook Pages & Instagram Professional accounts seamlessly through Meta.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 flex-shrink-0">
            {socialAccounts.length > 0 && (
              <button
                onClick={handleDisconnectAll}
                disabled={disconnectingId === 'all'}
                className="px-4 py-3 rounded-xl bg-rose-950/80 hover:bg-rose-900 border border-rose-800/80 text-rose-200 hover:text-white font-bold text-xs transition flex items-center space-x-2 shadow-lg disabled:opacity-50"
              >
                {disconnectingId === 'all' ? (
                  <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                ) : (
                  <Unlink className="w-4 h-4 text-rose-400" />
                )}
                <span>Disconnect Meta</span>
              </button>
            )}

            {/* Primary Meta OAuth Connect Button */}
            <button
              onClick={handleConnectMetaOAuth}
              disabled={isOAuthStarting}
              className="px-5 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs transition flex items-center space-x-2.5 shadow-lg shadow-indigo-500/25 disabled:opacity-50"
            >
              {isOAuthStarting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Facebook className="w-4 h-4 text-white fill-white" />
              )}
              <span>Connect with Meta</span>
              <ArrowRight className="w-3.5 h-3.5 text-blue-200" />
            </button>
          </div>
        </div>

        {/* Security Assurance Disclaimer */}
        <div className="flex items-center space-x-2 text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
          <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>
            Strict Token Security: No passwords requested. Access tokens remain server-side and are never exposed to the frontend.
          </span>
        </div>
      </div>

      {/* Notification Alerts */}
      {oauthSuccess && (
        <div className="bg-emerald-950/50 border border-emerald-800/80 rounded-xl p-4 text-xs text-emerald-200 flex items-center space-x-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span className="font-medium">{oauthSuccess}</span>
        </div>
      )}

      {oauthError && (
        <div className="bg-rose-950/50 border border-rose-800/80 rounded-xl p-4 text-xs text-rose-200 flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <span className="font-medium">{oauthError}</span>
        </div>
      )}

      {/* Connected Social Destinations Breakdown */}
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
            <Share2 className="w-4 h-4 text-indigo-400" />
            <span>Connected Social Accounts ({socialAccounts.length})</span>
          </h2>

          <button
            onClick={() => setShowManualMode(!showManualMode)}
            className="text-[10px] font-mono text-slate-400 hover:text-indigo-300 flex items-center space-x-1"
          >
            <Key className="w-3 h-3" />
            <span>{showManualMode ? 'Hide Developer Direct Entry' : 'Developer Direct Entry'}</span>
          </button>
        </div>

        {isLoadingAccounts ? (
          <div className="linear-panel p-8 rounded-xl text-center space-y-2 border border-slate-800">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400 mx-auto" />
            <p className="text-xs text-slate-400">Loading connected Meta accounts...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5">
            {/* Facebook Pages Card */}
            <div className="linear-panel p-5 rounded-xl space-y-3 border border-slate-800">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <span className="font-bold text-xs text-blue-300 flex items-center space-x-2">
                  <Facebook className="w-4 h-4 text-blue-400 fill-blue-400/20" />
                  <span>Facebook Pages ({fbPages.length})</span>
                </span>
                <span className="text-[10px] font-mono text-slate-400">Target for FB Posts</span>
              </div>

              {fbPages.length === 0 ? (
                <div className="p-4 rounded bg-slate-900/40 border border-slate-800 text-slate-400 text-xs text-center">
                  No Facebook Pages connected yet. Click <strong>"Connect with Meta"</strong> above to discover your pages.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {fbPages.map((acc) => (
                    <div key={acc.id} className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                      <div className="flex items-center space-x-3 min-w-0">
                        <img
                          src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                          alt={acc.account_name}
                          className="w-8 h-8 rounded-lg object-cover border border-slate-700 flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <h4 className="text-xs font-semibold text-slate-100 truncate">{acc.account_name}</h4>
                          <span className="text-[10px] font-mono text-slate-400">ID: {acc.account_id}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 text-[9px] font-mono">
                          ● Connected
                        </span>
                        <button
                          onClick={() => handleDisconnectAccount(acc.id)}
                          disabled={disconnectingId === acc.id || disconnectingId === 'all'}
                          className="px-2.5 py-1 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-800/80 text-rose-300 hover:text-white transition flex items-center space-x-1.5 disabled:opacity-50 text-[11px] font-semibold"
                          title="Disconnect Account"
                        >
                          {disconnectingId === acc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-400" />
                          ) : (
                            <Unlink className="w-3.5 h-3.5 text-rose-400" />
                          )}
                          <span>Disconnect</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Instagram Professional Accounts Card */}
            <div className="linear-panel p-5 rounded-xl space-y-3 border border-slate-800">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <span className="font-bold text-xs text-indigo-300 flex items-center space-x-2">
                  <Instagram className="w-4 h-4 text-indigo-400" />
                  <span>Instagram Professional Accounts ({igAccounts.length})</span>
                </span>
                <span className="text-[10px] font-mono text-slate-400">Target for IG Reels & Feed</span>
              </div>

              {igAccounts.length === 0 ? (
                <div className="p-4 rounded bg-slate-900/40 border border-slate-800 text-slate-400 text-xs text-center">
                  No Instagram Professional accounts connected yet. Link an IG Business account to your Facebook Page to auto-discover it via Meta.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {igAccounts.map((acc) => (
                    <div key={acc.id} className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                      <div className="flex items-center space-x-3 min-w-0">
                        <img
                          src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                          alt={acc.account_name}
                          className="w-8 h-8 rounded-lg object-cover border border-slate-700 flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <h4 className="text-xs font-semibold text-slate-100 truncate">{acc.account_name}</h4>
                          <span className="text-[10px] font-mono text-slate-400">ID: {acc.account_id}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 text-[9px] font-mono">
                          ● Connected
                        </span>
                        <button
                          onClick={() => handleDisconnectAccount(acc.id)}
                          disabled={disconnectingId === acc.id || disconnectingId === 'all'}
                          className="px-2.5 py-1 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-800/80 text-rose-300 hover:text-white transition flex items-center space-x-1.5 disabled:opacity-50 text-[11px] font-semibold"
                          title="Disconnect Account"
                        >
                          {disconnectingId === acc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-400" />
                          ) : (
                            <Unlink className="w-3.5 h-3.5 text-rose-400" />
                          )}
                          <span>Disconnect</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        )}
      </div>

      {/* Meta Ad Accounts Discovery Section */}
      <div className="linear-panel p-5 rounded-xl space-y-4 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-950/60 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
              <Megaphone className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                Meta Ad Accounts ({adAccounts.length})
              </h2>
              <p className="text-[10px] text-slate-400">
                Discovered accessible Meta Ad Accounts via ads_read permission.
              </p>
            </div>
          </div>

          <button
            onClick={handleSyncAdAccounts}
            disabled={isSyncingAdAccounts || isLoadingAdAccounts}
            className="px-3.5 py-2 rounded-lg bg-indigo-600/90 hover:bg-indigo-500 text-white font-semibold text-xs transition flex items-center space-x-2 shadow-md disabled:opacity-50 flex-shrink-0"
          >
            {isSyncingAdAccounts ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-indigo-200" />
            )}
            <span>{isSyncingAdAccounts ? 'Syncing...' : 'Sync Ad Accounts'}</span>
          </button>
        </div>

        {adAccountSuccess && (
          <div className="bg-emerald-950/40 border border-emerald-800/60 rounded-lg p-3 text-xs text-emerald-300 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{adAccountSuccess}</span>
          </div>
        )}

        {adAccountError && (
          <div className="bg-rose-950/40 border border-rose-800/60 rounded-lg p-3 text-xs text-rose-300 flex items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{adAccountError}</span>
            </div>
            {adAccountError.toLowerCase().includes('permission') && (
              <button
                onClick={handleConnectMetaOAuth}
                className="px-2.5 py-1 bg-rose-900 hover:bg-rose-800 text-white rounded text-[10px] font-bold transition flex-shrink-0"
              >
                Reconnect Meta
              </button>
            )}
          </div>
        )}

        {isLoadingAdAccounts ? (
          <div className="p-6 text-center space-y-2">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400 mx-auto" />
            <p className="text-xs text-slate-400">Loading accessible Meta Ad Accounts...</p>
          </div>
        ) : adAccounts.length === 0 ? (
          <div className="p-5 rounded-lg bg-slate-900/40 border border-slate-800/80 text-center space-y-2">
            <Megaphone className="w-6 h-6 text-slate-600 mx-auto" />
            <p className="text-xs font-semibold text-slate-300">No Meta Ad Accounts Discovered</p>
            <p className="text-[11px] text-slate-400 max-w-md mx-auto">
              Ensure your Meta user account has access to Ad Accounts in Meta Business Manager and that <strong>ads_read</strong> permission was granted.
            </p>
            <button
              onClick={handleSyncAdAccounts}
              disabled={isSyncingAdAccounts}
              className="mt-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium transition"
            >
              Sync Ad Accounts Now
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {adAccounts.map((acc) => {
              const isActive = acc.status_label === 'ACTIVE' || acc.account_status === 1;
              const acctId = acc.meta_ad_account_id;
              const isExpanded = expandedAdAccountId === acctId;
              const ads = adsByAccount[acctId] || [];
              const syncing = isSyncingAds[acctId] || false;
              const loading = isLoadingAds[acctId] || false;
              const sError = adSyncError[acctId];
              const sSuccess = adSyncSuccess[acctId];

              return (
                <div key={acc.id} className="bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
                  {/* Ad Account Header */}
                  <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/80">
                    <div className="space-y-1 min-w-0 pr-2">
                      <div className="flex items-center space-x-2">
                        <h4 className="text-xs font-bold text-slate-100 truncate">{acc.name || 'Meta Ad Account'}</h4>
                        <span
                          className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold flex-shrink-0 border ${
                            isActive
                              ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                              : 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                          }`}
                        >
                          ● {acc.status_label || (isActive ? 'ACTIVE' : 'DISABLED')}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3 text-[10px] text-slate-400 font-mono">
                        <span>ID: {acctId}</span>
                        {acc.currency && (
                          <span className="flex items-center space-x-1">
                            <DollarSign className="w-3 h-3 text-slate-500" />
                            <span>{acc.currency}</span>
                          </span>
                        )}
                        {acc.timezone_name && (
                          <span className="flex items-center space-x-1 truncate max-w-[140px]" title={acc.timezone_name}>
                            <Globe className="w-3 h-3 text-slate-500" />
                            <span className="truncate">{acc.timezone_name}</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <button
                        onClick={() => handleSyncAdsForAccount(acctId)}
                        disabled={syncing || loading}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 text-white font-medium text-xs transition flex items-center space-x-1.5 disabled:opacity-50"
                      >
                        {syncing ? (
                          <Loader2 className="w-3 h-3 animate-spin text-white" />
                        ) : (
                          <RefreshCw className="w-3 h-3 text-indigo-200" />
                        )}
                        <span>{syncing ? 'Syncing Ads...' : 'Sync Ads'}</span>
                      </button>

                      <button
                        onClick={() => toggleExpandAdAccount(acctId)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition flex items-center space-x-1 border border-slate-700/60"
                      >
                        <span>{isExpanded ? 'Hide Ads' : `View Ads (${ads.length})`}</span>
                        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                  </div>

                  {/* Sync Feedback messages */}
                  {sSuccess && (
                    <div className="mx-4 mt-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg p-2.5 text-xs text-emerald-300 flex items-center space-x-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      <span>{sSuccess}</span>
                    </div>
                  )}

                  {sError && (
                    <div className="mx-4 mt-3 bg-rose-950/40 border border-rose-800/60 rounded-lg p-2.5 text-xs text-rose-300 flex items-center justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                        <span>{sError}</span>
                      </div>
                      {sError.toLowerCase().includes('permission') && (
                        <button
                          onClick={handleConnectMetaOAuth}
                          className="px-2 py-0.5 bg-rose-900 hover:bg-rose-800 text-white rounded text-[10px] font-bold transition flex-shrink-0"
                        >
                          Reconnect Meta
                        </button>
                      )}
                    </div>
                  )}

                  {/* Expanded Ads & Engagement Mappings List */}
                  {isExpanded && (
                    <div className="p-4 border-t border-slate-800/80 bg-slate-950/50 space-y-4">
                      {loading ? (
                        <div className="p-4 text-center space-y-2">
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-400 mx-auto" />
                          <p className="text-[11px] text-slate-400">Loading discovered ads for account...</p>
                        </div>
                      ) : ads.length === 0 ? (
                        <div className="p-4 text-center space-y-1 bg-slate-900/40 rounded-lg border border-slate-800/60">
                          <FileText className="w-5 h-5 text-slate-600 mx-auto" />
                          <p className="text-xs font-semibold text-slate-300">No Ads Discovered</p>
                          <p className="text-[11px] text-slate-400">Click "Sync Ads" to fetch ads and extract engagement mappings from Meta.</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {/* Search & Dynamic Status Filter Bar */}
                          <div className="bg-slate-900/90 rounded-lg p-3 border border-slate-800/90 space-y-3">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                              {/* Search Input */}
                              <div className="relative flex-1 min-w-[220px]">
                                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                                <input
                                  type="text"
                                  value={adSearchQuery}
                                  onChange={(e) => {
                                    setAdSearchQuery(e.target.value);
                                    setAdCurrentPage(1);
                                  }}
                                  placeholder="Search ads, campaigns or ad sets..."
                                  className="w-full pl-9 pr-8 py-1.5 bg-slate-950/80 text-slate-200 placeholder-slate-500 rounded-md border border-slate-700/80 text-xs focus:outline-none focus:border-indigo-500 transition"
                                />
                                {adSearchQuery && (
                                  <button
                                    onClick={() => {
                                      setAdSearchQuery('');
                                      setAdCurrentPage(1);
                                    }}
                                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-0.5"
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </button>
                                )}
                              </div>

                              {/* Dynamic Status Filter Pills */}
                              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                                <button
                                  onClick={() => {
                                    setAdStatusFilter('ALL');
                                    setAdCurrentPage(1);
                                  }}
                                  className={`px-2.5 py-1 rounded-md text-[11px] transition ${
                                    adStatusFilter === 'ALL'
                                      ? 'bg-indigo-600 text-white font-bold shadow-sm'
                                      : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 border border-slate-700/60 font-medium'
                                  }`}
                                >
                                  All ({statusCounts.ALL || 0})
                                </button>
                                {uniqueStatuses.map((st) => (
                                  <button
                                    key={st}
                                    onClick={() => {
                                      setAdStatusFilter(st);
                                      setAdCurrentPage(1);
                                    }}
                                    className={`px-2.5 py-1 rounded-md text-[11px] font-mono transition ${
                                      adStatusFilter === st
                                        ? 'bg-indigo-600 text-white font-bold shadow-sm'
                                        : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 border border-slate-700/60 font-medium'
                                    }`}
                                  >
                                    {st} ({statusCounts[st] || 0})
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Summary Bar */}
                            <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/60 pt-2 px-0.5 gap-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-semibold text-slate-300">
                                  {filteredAds.length === 0
                                    ? '0 ads found'
                                    : `Showing ${
                                        (validCurrentPage - 1) * AD_PAGE_SIZE + 1
                                      }–${Math.min(
                                        validCurrentPage * AD_PAGE_SIZE,
                                        filteredAds.length
                                      )} of ${filteredAds.length} ${
                                        adStatusFilter !== 'ALL' ? `${adStatusFilter} ` : ''
                                      }ads`}
                                </span>
                                {adSearchQuery.trim() !== '' && (
                                  <span className="px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px] italic">
                                    matching "{adSearchQuery}"
                                  </span>
                                )}
                              </div>

                              <span className="text-[10px] text-slate-500 font-mono">
                                Total Synced: {currentExpandedAds.length}
                              </span>
                            </div>
                          </div>

                          {/* Empty Filter Results State */}
                          {filteredAds.length === 0 ? (
                            <div className="p-6 text-center space-y-2 bg-slate-900/40 rounded-lg border border-slate-800/60">
                              <Filter className="w-5 h-5 text-slate-500 mx-auto" />
                              <p className="text-xs font-semibold text-slate-300">No Ads Match Filter Criteria</p>
                              <p className="text-[11px] text-slate-400">
                                Try adjusting your search query or status filter.
                              </p>
                              <button
                                onClick={() => {
                                  setAdStatusFilter('ALL');
                                  setAdSearchQuery('');
                                  setAdCurrentPage(1);
                                }}
                                className="mt-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs rounded-md border border-slate-700 transition"
                              >
                                Reset Filters
                              </button>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {/* Render Paginated Cards */}
                              {paginatedAds.map((ad) => {
                                const isMapped = ad.mapping_status === 'MAPPED';
                                const isPartial = ad.mapping_status === 'PARTIALLY_MAPPED';

                                return (
                                  <div key={ad.id} className="bg-slate-900/90 rounded-lg p-3 border border-slate-800/90 space-y-2">
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                      <div className="space-y-0.5 min-w-0">
                                        <div className="flex items-center space-x-2">
                                          <h5 className="text-xs font-bold text-slate-100 truncate">{ad.name || 'Meta Ad'}</h5>
                                          {ad.effective_status && (
                                            <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                              {ad.effective_status}
                                            </span>
                                          )}
                                        </div>
                                        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] font-mono text-slate-400">
                                          <span>Ad ID: {ad.meta_ad_id}</span>
                                          {ad.campaign_name && <span>Campaign: {ad.campaign_name}</span>}
                                          {ad.adset_name && <span>AdSet: {ad.adset_name}</span>}
                                          {ad.creative_id && <span>Creative ID: {ad.creative_id}</span>}
                                        </div>
                                      </div>

                                      {/* Mapping Status Badge */}
                                      <span
                                        className={`px-2.5 py-1 rounded-md text-[10px] font-bold flex items-center space-x-1 border flex-shrink-0 self-start sm:self-center ${
                                          isMapped
                                            ? 'bg-emerald-950/70 text-emerald-300 border-emerald-800/70'
                                            : isPartial
                                            ? 'bg-amber-950/70 text-amber-300 border-amber-800/70'
                                            : 'bg-slate-800/80 text-slate-400 border-slate-700/60'
                                        }`}
                                      >
                                        {isMapped ? (
                                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                        ) : isPartial ? (
                                          <AlertCircle className="w-3 h-3 text-amber-400" />
                                        ) : (
                                          <HelpCircle className="w-3 h-3 text-slate-400" />
                                        )}
                                        <span>
                                          {isMapped
                                            ? 'Engagement Object Mapped'
                                            : isPartial
                                            ? 'Partially Mapped'
                                            : 'No Engagement Object'}
                                        </span>
                                      </span>
                                    </div>

                                    {/* Engagement Object Details Box */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-800/60 text-[11px]">
                                      {/* Facebook Engagement */}
                                      <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80 space-y-1">
                                        <div className="flex items-center space-x-1.5 text-blue-400 font-semibold text-[10px]">
                                          <Facebook className="w-3.5 h-3.5 text-blue-400" />
                                          <span>Facebook Engagement Object</span>
                                        </div>
                                        {ad.facebook_post_id ? (
                                          <div className="space-y-0.5 font-mono text-[10px] text-slate-300">
                                            <div className="truncate"><span className="text-slate-500">Post ID:</span> {ad.facebook_post_id}</div>
                                            {ad.facebook_page_id && <div className="truncate"><span className="text-slate-500">Page ID:</span> {ad.facebook_page_id}</div>}
                                          </div>
                                        ) : (
                                          <p className="text-[10px] text-slate-500 italic">No Facebook Post linked</p>
                                        )}
                                      </div>

                                      {/* Instagram Engagement */}
                                      <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80 space-y-1">
                                        <div className="flex items-center space-x-1.5 text-pink-400 font-semibold text-[10px]">
                                          <Instagram className="w-3.5 h-3.5 text-pink-400" />
                                          <span>Instagram Engagement Object</span>
                                        </div>
                                        {ad.instagram_media_id ? (
                                          <div className="space-y-0.5 font-mono text-[10px] text-slate-300">
                                            <div className="truncate"><span className="text-slate-500">Media ID:</span> {ad.instagram_media_id}</div>
                                            {ad.instagram_account_id && <div className="truncate"><span className="text-slate-500">IG Account ID:</span> {ad.instagram_account_id}</div>}
                                          </div>
                                        ) : (
                                          <p className="text-[10px] text-slate-500 italic">No Instagram Media linked</p>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}

                              {/* Pagination Navigation Footer */}
                              {totalPages > 1 && (
                                <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                                  <button
                                    disabled={validCurrentPage <= 1}
                                    onClick={() => setAdCurrentPage((prev) => Math.max(1, prev - 1))}
                                    className="flex items-center space-x-1 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:hover:bg-slate-900 text-slate-300 rounded-md border border-slate-800 transition font-medium text-[11px]"
                                  >
                                    <ChevronLeft className="w-3.5 h-3.5" />
                                    <span>Previous</span>
                                  </button>

                                  <span className="text-[11px] font-medium text-slate-400 font-mono">
                                    Page <strong className="text-slate-200">{validCurrentPage}</strong> of{' '}
                                    <strong className="text-slate-200">{totalPages}</strong>
                                  </span>

                                  <button
                                    disabled={validCurrentPage >= totalPages}
                                    onClick={() => setAdCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                                    className="flex items-center space-x-1 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:hover:bg-slate-900 text-slate-300 rounded-md border border-slate-800 transition font-medium text-[11px]"
                                  >
                                    <span>Next</span>
                                    <ChevronRight className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Developer Direct Entry Modal Form */}
      {showManualMode && (
        <form onSubmit={handleSaveManual} className="linear-panel p-6 rounded-2xl space-y-4 border border-indigo-500/30">
          <div className="flex items-center space-x-2">
            <Key className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-bold text-slate-100">Developer Direct Entry (Manual Token Mode)</h3>
          </div>
          <p className="text-[11px] text-slate-400">
            For local testing or Graph API Explorer tokens. Enter custom Page ID, Access Token, and Instagram ID manually.
          </p>

          <div className="space-y-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Access Token (User or Page Token) <span className="text-rose-400">*</span>
              </label>
              <textarea
                rows={2}
                required
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                placeholder="EAABwz1XkREYBAIJlLUXdAZBfq..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-indigo-300 font-mono focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Facebook Page ID *</label>
                <input
                  type="text"
                  required
                  value={manualPageId}
                  onChange={(e) => setManualPageId(e.target.value)}
                  placeholder="e.g. 109823471029481"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Facebook Page Name</label>
                <input
                  type="text"
                  value={manualPageName}
                  onChange={(e) => setManualPageName(e.target.value)}
                  placeholder="e.g. Apex Innovations Page"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Instagram Business Account ID</label>
                <input
                  type="text"
                  value={manualIgId}
                  onChange={(e) => setManualIgId(e.target.value)}
                  placeholder="e.g. 17841400928371902"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Instagram Username</label>
                <input
                  type="text"
                  value={manualIgUsername}
                  onChange={(e) => setManualIgUsername(e.target.value)}
                  placeholder="e.g. apex_innovations"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="flex space-x-2 pt-2">
            <button
              type="submit"
              disabled={isSavingManual}
              className="py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition flex items-center space-x-2 disabled:opacity-50"
            >
              {isSavingManual ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
              <span>Save Developer Credentials</span>
            </button>
            <button
              type="button"
              onClick={() => setShowManualMode(false)}
              className="py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
