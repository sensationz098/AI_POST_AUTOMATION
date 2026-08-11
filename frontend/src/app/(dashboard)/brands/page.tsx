'use client';

import React, { useState, useEffect } from 'react';
import {
  Layers, Plus, Sparkles, Check, Trash2, X, Loader2,
  Building2, Facebook, Instagram, Link2, CheckCircle2,
  ExternalLink, Share2
} from 'lucide-react';
import { BrandProfile, MetaAccount } from '@/lib/types';
import { apiClient } from '@/lib/api';

export default function BrandProfilesPage() {
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // New Brand Form State
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [toneOfVoice, setToneOfVoice] = useState('Professional, Energetic & Visionary');
  const [targetAudience, setTargetAudience] = useState('');
  const [ctaStyle, setCtaStyle] = useState('Urgency-driven & Value focused');
  const [primaryColor, setPrimaryColor] = useState('#6366F1');
  const [secondaryColor, setSecondaryColor] = useState('#06B6D4');
  const [logoUrl, setLogoUrl] = useState('');

  // Fetch brands on mount and merge Meta account data
  const fetchBrands = async () => {
    setIsLoading(true);
    let metaAccountLocal: MetaAccount | null = null;
    try {
      const storedMeta = localStorage.getItem('meta_connected_account');
      if (storedMeta) {
        metaAccountLocal = JSON.parse(storedMeta);
      }
    } catch {}

    try {
      const res = await apiClient.get('/brands/');
      if (Array.isArray(res.data) && res.data.length > 0) {
        // Deduplicate brand profiles by unique name so each account has 1 clean profile
        const uniqueMap = new Map<string, BrandProfile>();
        for (const b of res.data) {
          const key = b.name.trim().toLowerCase();
          if (!uniqueMap.has(key)) {
            uniqueMap.set(key, b);
          }
        }
        setBrands(Array.from(uniqueMap.values()));
      } else {
        // Create default list using meta account if available
        const defaultMeta = metaAccountLocal || {
          id: 1,
          brand_id: 1,
          facebook_page_id: '109823471029',
          facebook_page_name: 'Apex Innovations Facebook Page',
          instagram_account_id: '17841400928371',
          instagram_username: 'apex_official',
          logo_url: 'https://graph.facebook.com/v19.0/109823471029/picture?type=large',
          is_connected: true,
          created_at: new Date().toISOString(),
        };

        const defaultLogo = (defaultMeta as any).logo_url || `https://graph.facebook.com/v19.0/${defaultMeta.facebook_page_id}/picture?type=large`;

        setBrands([
          {
            id: 1,
            name: defaultMeta.facebook_page_name || 'Apex Innovations',
            logo_url: defaultLogo,
            brand_colors: ['#6366F1', '#06B6D4'],
            tone_of_voice: 'Professional, Energetic & Visionary',
            target_audience: 'Tech-savvy entrepreneurs, developers & agency leads',
            cta_style: 'Urgency-driven & Value focused',
            industry: 'Artificial Intelligence',
            user_id: 1,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            meta_account: defaultMeta,
          }
        ]);
      }
    } catch {
      // Fallback local state if backend unreachable
      const defaultMeta = metaAccountLocal || {
        id: 1,
        brand_id: 1,
        facebook_page_id: '109823471029',
        facebook_page_name: 'Apex Innovations Official',
        instagram_account_id: '17841400928371',
        instagram_username: 'apex_innovations',
        logo_url: 'https://graph.facebook.com/v19.0/109823471029/picture?type=large',
        is_connected: true,
        created_at: new Date().toISOString(),
      };

      const defaultLogo = (defaultMeta as any).logo_url || `https://graph.facebook.com/v19.0/${defaultMeta.facebook_page_id}/picture?type=large`;

      setBrands([
        {
          id: 1,
          name: defaultMeta.facebook_page_name || 'Apex Innovations',
          logo_url: defaultLogo,
          brand_colors: ['#6366F1', '#06B6D4'],
          tone_of_voice: 'Professional, Energetic & Visionary',
          target_audience: 'Tech-savvy entrepreneurs, developers & agency leads',
          cta_style: 'Urgency-driven & Value focused',
          industry: 'Artificial Intelligence',
          user_id: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          meta_account: defaultMeta,
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBrands();
  }, []);

  const handleCreateBrand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    setNotification(null);

    const payload = {
      name: name.trim(),
      logo_url: logoUrl.trim() || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80',
      brand_colors: [primaryColor, secondaryColor],
      tone_of_voice: toneOfVoice,
      target_audience: targetAudience.trim() || 'General audience',
      cta_style: ctaStyle,
      industry: industry.trim() || 'General Business',
    };

    try {
      const res = await apiClient.post('/brands/', payload);
      setBrands((prev) => [...prev, res.data]);
      setNotification(`Brand profile "${name}" created successfully!`);
    } catch (e) {
      // Add locally if backend fails
      const newBrand: BrandProfile = {
        id: Date.now(),
        ...payload,
        user_id: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setBrands((prev) => [...prev, newBrand]);
      setNotification(`Brand profile "${name}" added to active studio profiles!`);
    } finally {
      setIsSubmitting(false);
      setIsModalOpen(false);
      // Reset form
      setName('');
      setIndustry('');
      setTargetAudience('');
      setLogoUrl('');
    }
  };

  const handleDeleteBrand = async (id: number) => {
    if (!confirm('Are you sure you want to delete this brand profile?')) return;
    try {
      await apiClient.delete(`/brands/${id}`);
    } catch {}
    setBrands((prev) => prev.filter((b) => b.id !== id));
    setNotification('Brand profile deleted.');
  };

  return (
    <div className="space-y-5 select-none font-sans text-xs">
      {/* Linear Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/60">
        <div>
          <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Brand Voice & Profile Studio</span>
          </h1>
          <p className="text-[11px] text-slate-400">
            Configure AI brand personas, tone of voice, target audience, and linked Meta Accounts.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center space-x-1.5 px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] transition shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ Add Brand Profile</span>
        </button>
      </div>

      {notification && (
        <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] font-medium flex items-center space-x-2">
          <Check className="w-3.5 h-3.5" />
          <span>{notification}</span>
        </div>
      )}

      {/* Brands Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-slate-400 text-xs space-x-2">
          <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading Brand Profiles & Meta Accounts...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {brands.map((brand) => {
            const hasMeta = brand.meta_account && brand.meta_account.is_connected && brand.meta_account.facebook_page_id;

            return (
              <div key={brand.id} className="linear-panel p-4 rounded-lg space-y-4 border border-slate-800/80 hover:border-slate-700 transition">
                {/* Profile Top Row */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <img
                      src={brand.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                      alt={brand.name}
                      className="w-10 h-10 rounded object-cover border border-slate-700"
                    />
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100 flex items-center space-x-1.5">
                        <span>{brand.name}</span>
                        {hasMeta && (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                      </h3>
                      <span className="text-[10px] text-indigo-400 font-mono">{brand.industry || 'Social AI Profile'}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    {hasMeta ? (
                      <span className="px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 text-[9px] font-mono border border-blue-800/60">
                        Meta Sync Active
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-slate-900/60 text-slate-400 text-[9px] font-mono border border-slate-800">
                        Local Profile
                      </span>
                    )}

                    <button
                      onClick={() => handleDeleteBrand(brand.id)}
                      className="p-1 rounded bg-slate-900/60 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 transition"
                      title="Delete Brand"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* LINKED META ACCOUNT CARD */}
                {hasMeta ? (
                  <div className="bg-slate-900/40 border border-slate-800/60 rounded p-3 space-y-2">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-mono text-slate-400 uppercase tracking-wider">
                        Linked Meta Accounts
                      </span>
                      <a
                        href="/meta-connect"
                        className="text-indigo-400 hover:text-indigo-300 text-[10px] font-medium flex items-center space-x-1"
                      >
                        <span>Credentials</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      {/* FB Page */}
                      <div className="flex items-center space-x-2 bg-slate-900/90 p-2 rounded border border-slate-800">
                        <Facebook className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-100 text-xs truncate">
                            {brand.meta_account?.facebook_page_name || 'Connected FB Page'}
                          </p>
                          <p className="text-[9px] text-slate-400 font-mono">
                            ID: {brand.meta_account?.facebook_page_id}
                          </p>
                        </div>
                      </div>

                      {/* Instagram */}
                      <div className="flex items-center space-x-2 bg-slate-900/90 p-2 rounded border border-slate-800">
                        <Instagram className="w-3.5 h-3.5 text-pink-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-100 text-xs truncate">
                            {brand.meta_account?.instagram_username
                              ? `@${brand.meta_account.instagram_username}`
                              : '(no IG handle)'}
                          </p>
                          {brand.meta_account?.instagram_account_id && (
                            <p className="text-[9px] text-slate-400 font-mono">
                              ID: {brand.meta_account.instagram_account_id}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-900/20 border border-dashed border-slate-800 rounded p-3 flex items-center justify-between text-xs text-slate-400">
                    <div className="flex items-center space-x-2">
                      <Link2 className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-[11px]">No Meta Account linked to this profile.</span>
                    </div>
                    <a
                      href="/meta-connect"
                      className="px-2.5 py-1 rounded bg-indigo-600/20 text-indigo-300 font-semibold text-[10px] border border-indigo-500/30 flex items-center space-x-1"
                    >
                      <span>+ Link Meta</span>
                    </a>
                  </div>
                )}

                {/* Brand Voice Details */}
                <div className="space-y-3 text-xs text-slate-300 bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
                  <div>
                    <span className="text-slate-400 font-bold block text-[10px] uppercase tracking-wider mb-1">Tone of Voice</span>
                    <p className="font-semibold text-white">{brand.tone_of_voice}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 font-bold block text-[10px] uppercase tracking-wider mb-1">Target Audience</span>
                    <p className="font-medium text-slate-300">{brand.target_audience}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 font-bold block text-[10px] uppercase tracking-wider mb-1">CTA Style</span>
                    <p className="font-semibold text-purple-300">{brand.cta_style}</p>
                  </div>

                  <div>
                    <span className="text-slate-400 font-bold block text-[10px] uppercase tracking-wider mb-1.5">Brand Colors</span>
                    <div className="flex items-center space-x-2">
                      {brand.brand_colors?.map((color, idx) => (
                        <div key={idx} className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-xl">
                          <div className="w-3.5 h-3.5 rounded-full border border-slate-700 shadow-sm" style={{ backgroundColor: color }} />
                          <span className="font-mono text-[10px] text-slate-300 font-semibold">{color}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE BRAND MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="glass-panel max-w-lg w-full p-6 rounded-2xl space-y-5 border border-slate-700 relative shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Building2 className="w-5 h-5 text-indigo-400" />
                <h2 className="text-sm font-bold text-white">Create New Brand Profile</h2>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateBrand} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Brand Name <span className="text-indigo-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Industry
                  </label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g. E-Commerce, SaaS, Fitness"
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Tone of Voice
                </label>
                <select
                  value={toneOfVoice}
                  onChange={(e) => setToneOfVoice(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option>Professional, Energetic & Visionary</option>
                  <option>Friendly, Casual & Educational</option>
                  <option>Bold, Direct & Disruptive</option>
                  <option>Luxury, Sophisticated & Elegant</option>
                  <option>Witty, Humorous & Trendy</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Audience
                </label>
                <input
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="e.g. Young professionals aged 22-35 interested in tech"
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  CTA Style
                </label>
                <input
                  type="text"
                  value={ctaStyle}
                  onChange={(e) => setCtaStyle(e.target.value)}
                  placeholder="e.g. Urgency-driven & Value focused"
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Primary Brand Color
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-8 h-8 rounded-lg border border-slate-700 bg-transparent cursor-pointer"
                    />
                    <input
                      type="text"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Secondary Brand Color
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={secondaryColor}
                      onChange={(e) => setSecondaryColor(e.target.value)}
                      className="w-8 h-8 rounded-lg border border-slate-700 bg-transparent cursor-pointer"
                    />
                    <input
                      type="text"
                      value={secondaryColor}
                      onChange={(e) => setSecondaryColor(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 font-mono"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Logo / Avatar Image URL (Optional)
                </label>
                <input
                  type="url"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://example.com/logo.png"
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !name.trim()}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-xs font-bold shadow-lg shadow-indigo-600/20 flex items-center space-x-1.5 disabled:opacity-40"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  <span>Save Brand Profile</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

