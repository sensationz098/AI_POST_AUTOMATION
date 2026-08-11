'use client';

import React, { useState, useEffect } from 'react';
import {
  Share2, CheckCircle2, Facebook, Instagram, ShieldCheck,
  ChevronRight, ExternalLink, RefreshCw, AlertCircle,
  Loader2, Unlink, Link2, Edit3, Sparkles, Key, Lock, ArrowRight
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialAccount } from '@/lib/types';

export default function MetaConnectPage() {
  // Connected Accounts State
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(true);

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

  useEffect(() => {
    fetchSocialAccounts();

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

  // Initiate Real Meta OAuth Flow
  const handleConnectMetaOAuth = async () => {
    setIsOAuthStarting(true);
    setOauthError(null);
    setOauthSuccess(null);
    try {
      const res = await apiClient.get('/meta/oauth/start');
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      } else {
        setOauthError('Failed to generate Meta authorization URL.');
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to initiate Meta OAuth authorization. Check server connection.';
      setOauthError(msg);
    } finally {
      setIsOAuthStarting(false);
    }
  };

  // Disconnect a single social account
  const handleDisconnectAccount = async (id: number) => {
    if (!confirm('Are you sure you want to disconnect this social destination?')) return;
    try {
      await apiClient.delete(`/social-accounts/${id}`);
      setSocialAccounts((prev) => prev.filter((a) => a.id !== id));
      setOauthSuccess('Social account disconnected successfully.');
    } catch (e) {
      alert('Failed to disconnect social account.');
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
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25 flex-shrink-0">
              <Share2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
                <span>Connect Meta Accounts</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 font-semibold">
                  OAuth 2.0
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Authorize your Facebook Pages & Instagram Professional accounts seamlessly through Meta.
              </p>
            </div>
          </div>

          {/* Primary Meta OAuth Connect Button */}
          <button
            onClick={handleConnectMetaOAuth}
            disabled={isOAuthStarting}
            className="px-5 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs transition flex items-center space-x-2.5 shadow-lg shadow-indigo-500/25 disabled:opacity-50 flex-shrink-0"
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
                          className="p-1 rounded bg-slate-950 hover:bg-rose-950 text-slate-500 hover:text-rose-400 transition"
                          title="Disconnect Account"
                        >
                          <Unlink className="w-3.5 h-3.5" />
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
                <span className="font-bold text-xs text-pink-300 flex items-center space-x-2">
                  <Instagram className="w-4 h-4 text-pink-400" />
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
                          className="p-1 rounded bg-slate-950 hover:bg-rose-950 text-slate-500 hover:text-rose-400 transition"
                          title="Disconnect Account"
                        >
                          <Unlink className="w-3.5 h-3.5" />
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
