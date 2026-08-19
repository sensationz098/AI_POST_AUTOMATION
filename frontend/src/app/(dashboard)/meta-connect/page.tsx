'use client';

import React, { useState, useEffect } from 'react';
import {
  Share2, CheckCircle2, Facebook, Instagram, ShieldCheck,
  AlertCircle, Loader2, Unlink, Key, ArrowRight
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { SocialAccount } from '@/lib/types';

export default function MetaConnectPage() {
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(true);
  const [disconnectingId, setDisconnectingId] = useState<number | string | 'all' | null>(null);

  const [isOAuthStarting, setIsOAuthStarting] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [oauthSuccess, setOauthSuccess] = useState<string | null>(null);

  const [showManualMode, setShowManualMode] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [manualPageId, setManualPageId] = useState('');
  const [manualPageName, setManualPageName] = useState('');
  const [manualIgId, setManualIgId] = useState('');
  const [manualIgUsername, setManualIgUsername] = useState('');
  const [isSavingManual, setIsSavingManual] = useState(false);

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

  const handleConnectMetaOAuth = async () => {
    setIsOAuthStarting(true);
    setOauthError(null);
    setOauthSuccess(null);
    try {
      const res = await apiClient.get('/meta/oauth/start?redirect=false');
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      } else {
        const token = localStorage.getItem('social_ai_token') || '';
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        window.location.href = `${apiUrl}/meta/oauth/start?token=${token}`;
      }
    } catch (e: any) {
      console.error('Meta OAuth start error:', e);
      const token = localStorage.getItem('social_ai_token') || '';
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      window.location.href = `${apiUrl}/meta/oauth/start?token=${token}`;
    }
  };

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
      await apiClient.post('/social-accounts/connect', {
        brand_id: 1,
        platform: 'facebook',
        account_id: manualPageId.trim(),
        account_name: manualPageName.trim() || 'Facebook Page',
        access_token: token,
        logo_url: logoUrl,
      });

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
    <div className="space-y-6 max-w-4xl font-sans text-xs select-none">
      {/* Header Banner */}
      <div className="pub-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center text-[var(--accent-color)] flex-shrink-0">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
                Connect Meta Channels
              </h1>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                Authorize your Facebook Pages & Instagram Professional accounts via official Meta Graph API.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 flex-shrink-0">
            {socialAccounts.length > 0 && (
              <button
                onClick={handleDisconnectAll}
                disabled={disconnectingId === 'all'}
                className="btn-danger text-xs py-2 px-3 space-x-1.5"
              >
                {disconnectingId === 'all' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Unlink className="w-3.5 h-3.5" />
                )}
                <span>Disconnect All</span>
              </button>
            )}

            <button
              onClick={handleConnectMetaOAuth}
              disabled={isOAuthStarting}
              className="btn-primary text-xs py-2 px-4 space-x-2"
            >
              {isOAuthStarting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Facebook className="w-3.5 h-3.5" />
              )}
              <span>Connect with Meta</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-[11px] text-[var(--text-secondary)] bg-[var(--bg-tertiary)] p-3 rounded-md border border-[var(--border-color)]">
          <ShieldCheck className="w-4 h-4 text-[var(--success-color)] flex-shrink-0" />
          <span>
            Token Security: Access tokens remain encrypted server-side and are never stored in localStorage or exposed to the client.
          </span>
        </div>
      </div>

      {/* Notifications */}
      {oauthSuccess && (
        <div className="p-4 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--success-color)] text-xs flex items-center space-x-3">
          <CheckCircle2 className="w-5 h-5 text-[var(--success-color)] flex-shrink-0" />
          <span className="font-medium">{oauthSuccess}</span>
        </div>
      )}

      {oauthError && (
        <div className="p-4 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--danger-color)] text-xs flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-[var(--danger-color)] flex-shrink-0" />
          <span className="font-medium">{oauthError}</span>
        </div>
      )}

      {/* Connected Accounts */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[var(--text-primary)] flex items-center space-x-2">
            <Share2 className="w-4 h-4 text-[var(--accent-color)]" />
            <span>Connected Channels ({socialAccounts.length})</span>
          </h2>

          <button
            onClick={() => setShowManualMode(!showManualMode)}
            className="btn-tertiary text-xs font-mono"
          >
            <Key className="w-3.5 h-3.5 mr-1" />
            <span>{showManualMode ? 'Hide Developer Direct Entry' : 'Developer Direct Entry'}</span>
          </button>
        </div>

        {isLoadingAccounts ? (
          <div className="pub-card p-8 text-center space-y-2">
            <Loader2 className="w-5 h-5 animate-spin text-[var(--accent-color)] mx-auto" />
            <p className="text-xs text-[var(--text-secondary)]">Loading connected Meta channels...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {/* Facebook Pages */}
            <div className="pub-card p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-2.5">
                <span className="font-bold text-xs text-[var(--text-primary)] flex items-center space-x-2">
                  <Facebook className="w-4 h-4 text-[#1877F2]" />
                  <span>Facebook Pages ({fbPages.length})</span>
                </span>
                <span className="text-[11px] font-mono text-[var(--text-tertiary)]">FB Publishing Target</span>
              </div>

              {fbPages.length === 0 ? (
                <div className="p-4 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--text-secondary)] text-xs text-center">
                  No Facebook Pages connected. Click <strong>"Connect with Meta"</strong> above to sync.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {fbPages.map((acc) => (
                    <div key={acc.id} className="bg-[var(--bg-tertiary)] p-3 rounded-md border border-[var(--border-color)] flex items-center justify-between">
                      <div className="flex items-center space-x-3 min-w-0">
                        <img
                          src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                          alt={acc.account_name}
                          className="w-8 h-8 rounded object-cover border border-[var(--border-color)] flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <h4 className="text-xs font-semibold text-[var(--text-primary)] truncate">{acc.account_name}</h4>
                          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">ID: {acc.account_id}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className="px-2 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--success-color)] border border-[var(--border-color)] text-[10px] font-mono">
                          Connected
                        </span>
                        <button
                          onClick={() => handleDisconnectAccount(acc.id)}
                          disabled={disconnectingId === acc.id || disconnectingId === 'all'}
                          className="btn-danger py-1 px-2 text-[11px]"
                          title="Disconnect Account"
                        >
                          <Unlink className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Instagram Accounts */}
            <div className="pub-card p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-2.5">
                <span className="font-bold text-xs text-[var(--text-primary)] flex items-center space-x-2">
                  <Instagram className="w-4 h-4 text-[#E4405F]" />
                  <span>Instagram Accounts ({igAccounts.length})</span>
                </span>
                <span className="text-[11px] font-mono text-[var(--text-tertiary)]">IG Reels & Feed Target</span>
              </div>

              {igAccounts.length === 0 ? (
                <div className="p-4 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--text-secondary)] text-xs text-center">
                  No Instagram accounts connected yet. Link an IG Business profile to your Facebook Page to auto-discover via Meta.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {igAccounts.map((acc) => (
                    <div key={acc.id} className="bg-[var(--bg-tertiary)] p-3 rounded-md border border-[var(--border-color)] flex items-center justify-between">
                      <div className="flex items-center space-x-3 min-w-0">
                        <img
                          src={acc.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                          alt={acc.account_name}
                          className="w-8 h-8 rounded object-cover border border-[var(--border-color)] flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <h4 className="text-xs font-semibold text-[var(--text-primary)] truncate">{acc.account_name}</h4>
                          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">ID: {acc.account_id}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className="px-2 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--success-color)] border border-[var(--border-color)] text-[10px] font-mono">
                          Connected
                        </span>
                        <button
                          onClick={() => handleDisconnectAccount(acc.id)}
                          disabled={disconnectingId === acc.id || disconnectingId === 'all'}
                          className="btn-danger py-1 px-2 text-[11px]"
                          title="Disconnect Account"
                        >
                          <Unlink className="w-3 h-3" />
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

      {/* Manual Entry Form */}
      {showManualMode && (
        <form onSubmit={handleSaveManual} className="pub-card p-6 space-y-4">
          <div className="flex items-center space-x-2 border-b border-[var(--border-color)] pb-3">
            <Key className="w-4 h-4 text-[var(--accent-color)]" />
            <h3 className="text-sm font-bold text-[var(--text-primary)]">Developer Manual Entry</h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                Access Token *
              </label>
              <textarea
                rows={2}
                required
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                placeholder="EAABwz1XkREYBA..."
                className="input-field w-full font-mono text-xs resize-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Facebook Page ID *</label>
                <input
                  type="text"
                  required
                  value={manualPageId}
                  onChange={(e) => setManualPageId(e.target.value)}
                  placeholder="e.g. 109823471029481"
                  className="input-field w-full"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Facebook Page Name</label>
                <input
                  type="text"
                  value={manualPageName}
                  onChange={(e) => setManualPageName(e.target.value)}
                  placeholder="e.g. Apex Innovations Page"
                  className="input-field w-full"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Instagram Account ID</label>
                <input
                  type="text"
                  value={manualIgId}
                  onChange={(e) => setManualIgId(e.target.value)}
                  placeholder="e.g. 17841400928371902"
                  className="input-field w-full"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">Instagram Username</label>
                <input
                  type="text"
                  value={manualIgUsername}
                  onChange={(e) => setManualIgUsername(e.target.value)}
                  placeholder="e.g. apex_innovations"
                  className="input-field w-full"
                />
              </div>
            </div>
          </div>

          <div className="flex space-x-2 pt-2 border-t border-[var(--border-color)]">
            <button
              type="submit"
              disabled={isSavingManual}
              className="btn-primary text-xs flex items-center space-x-1.5"
            >
              {isSavingManual ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              <span>Save Developer Token</span>
            </button>
            <button
              type="button"
              onClick={() => setShowManualMode(false)}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
