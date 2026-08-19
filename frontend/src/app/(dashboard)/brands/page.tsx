'use client';

import React, { useState, useEffect } from 'react';
import {
  Layers, Plus, Check, Trash2, X, Loader2,
  Building2, Facebook, Instagram, Link2, CheckCircle2,
  ExternalLink
} from 'lucide-react';
import { BrandProfile } from '@/lib/types';
import { apiClient } from '@/lib/api';

export default function BrandProfilesPage() {
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [toneOfVoice, setToneOfVoice] = useState('Professional, Energetic & Visionary');
  const [targetAudience, setTargetAudience] = useState('');
  const [ctaStyle, setCtaStyle] = useState('Urgency-driven & Value focused');
  const [primaryColor, setPrimaryColor] = useState('#0066CC');
  const [secondaryColor, setSecondaryColor] = useState('#047857');
  const [logoUrl, setLogoUrl] = useState('');

  const fetchBrands = async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get('/brands/');
      if (Array.isArray(res.data)) {
        const uniqueMap = new Map<string, BrandProfile>();
        for (const b of res.data) {
          const key = b.name.trim().toLowerCase();
          if (!uniqueMap.has(key)) {
            uniqueMap.set(key, b);
          }
        }
        setBrands(Array.from(uniqueMap.values()));
      } else {
        setBrands([]);
      }
    } catch {
      setBrands([]);
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
    <div className="space-y-6 font-sans text-xs select-none">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight flex items-center space-x-2">
            <Layers className="w-5 h-5 text-[var(--accent-color)]" />
            <span>Brand Voice & Personas</span>
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Define tone of voice guidelines, visual brand colors, and target audience personas for AI post generation.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary text-xs py-2 px-3.5 space-x-1.5 self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ Add Brand Profile</span>
        </button>
      </div>

      {notification && (
        <div className="p-3.5 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--success-color)] text-xs font-medium flex items-center space-x-2">
          <Check className="w-4 h-4 text-[var(--success-color)]" />
          <span>{notification}</span>
        </div>
      )}

      {/* Brands Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-[var(--text-tertiary)] text-xs space-x-2">
          <Loader2 className="w-4 h-4 animate-spin text-[var(--accent-color)]" />
          <span>Loading Brand Profiles & Personas...</span>
        </div>
      ) : brands.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {brands.map((brand) => {
            const hasMeta = brand.meta_account && brand.meta_account.is_connected && brand.meta_account.facebook_page_id;

            return (
              <div key={brand.id} className="pub-card p-5 space-y-4">
                {/* Profile Top Row */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <img
                      src={brand.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                      alt={brand.name}
                      className="w-10 h-10 rounded object-cover border border-[var(--border-color)]"
                    />
                    <div>
                      <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center space-x-1.5">
                        <span>{brand.name}</span>
                        {hasMeta && (
                          <CheckCircle2 className="w-4 h-4 text-[var(--success-color)]" />
                        )}
                      </h3>
                      <span className="text-[11px] text-[var(--accent-color)] font-mono">{brand.industry || 'Social AI Profile'}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    {hasMeta ? (
                      <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--accent-color)] text-[10px] font-mono border border-[var(--border-color)] font-medium">
                        Meta Linked
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] text-[10px] font-mono border border-[var(--border-color)]">
                        Local Profile
                      </span>
                    )}

                    <button
                      onClick={() => handleDeleteBrand(brand.id)}
                      className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--danger-color)] transition"
                      title="Delete Brand"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Linked Meta Account Box */}
                {hasMeta ? (
                  <div className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-md p-3 space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-mono text-[var(--text-secondary)] font-semibold uppercase tracking-wider">
                        Linked Meta Channel
                      </span>
                      <a
                        href="/meta-connect"
                        className="text-[var(--accent-color)] hover:underline text-[11px] font-medium flex items-center space-x-1"
                      >
                        <span>Manage</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div className="flex items-center space-x-2 bg-[var(--bg-secondary)] p-2 rounded border border-[var(--border-color)]">
                        <Facebook className="w-4 h-4 text-[#1877F2] flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="font-medium text-[var(--text-primary)] text-xs truncate">
                            {brand.meta_account?.facebook_page_name || 'Connected FB Page'}
                          </p>
                          <p className="text-[10px] text-[var(--text-tertiary)] font-mono truncate">
                            ID: {brand.meta_account?.facebook_page_id}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 bg-[var(--bg-secondary)] p-2 rounded border border-[var(--border-color)]">
                        <Instagram className="w-4 h-4 text-[#E4405F] flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="font-medium text-[var(--text-primary)] text-xs truncate">
                            {brand.meta_account?.instagram_username
                              ? `@${brand.meta_account.instagram_username}`
                              : '(no IG handle)'}
                          </p>
                          {brand.meta_account?.instagram_account_id && (
                            <p className="text-[10px] text-[var(--text-tertiary)] font-mono truncate">
                              ID: {brand.meta_account.instagram_account_id}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-[var(--bg-tertiary)] border border-dashed border-[var(--border-color)] rounded-md p-3 flex items-center justify-between text-xs text-[var(--text-secondary)]">
                    <div className="flex items-center space-x-2">
                      <Link2 className="w-4 h-4 text-[var(--text-tertiary)]" />
                      <span className="text-xs">No Meta Channel linked yet.</span>
                    </div>
                    <a
                      href="/meta-connect"
                      className="btn-secondary text-[11px] py-1 px-2.5"
                    >
                      + Link Meta
                    </a>
                  </div>
                )}

                {/* Brand Guidelines Details */}
                <div className="space-y-3 text-xs text-[var(--text-secondary)] bg-[var(--bg-tertiary)] p-4 rounded-md border border-[var(--border-color)]">
                  <div>
                    <span className="text-[var(--text-tertiary)] font-semibold block text-[10px] uppercase tracking-wider mb-1">Tone of Voice</span>
                    <p className="font-medium text-[var(--text-primary)]">{brand.tone_of_voice}</p>
                  </div>

                  <div>
                    <span className="text-[var(--text-tertiary)] font-semibold block text-[10px] uppercase tracking-wider mb-1">Target Audience</span>
                    <p className="font-normal text-[var(--text-secondary)]">{brand.target_audience}</p>
                  </div>

                  <div>
                    <span className="text-[var(--text-tertiary)] font-semibold block text-[10px] uppercase tracking-wider mb-1">CTA Style</span>
                    <p className="font-medium text-[var(--accent-color)]">{brand.cta_style}</p>
                  </div>

                  <div>
                    <span className="text-[var(--text-tertiary)] font-semibold block text-[10px] uppercase tracking-wider mb-1.5">Brand Colors</span>
                    <div className="flex items-center space-x-2">
                      {brand.brand_colors?.map((color, idx) => (
                        <div key={idx} className="flex items-center space-x-1.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] px-2.5 py-1 rounded">
                          <div className="w-3.5 h-3.5 rounded-full border border-[var(--border-color)]" style={{ backgroundColor: color }} />
                          <span className="font-mono text-[10px] text-[var(--text-primary)] font-semibold">{color}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="pub-card p-12 text-center space-y-3">
          <Building2 className="w-10 h-10 text-[var(--text-tertiary)] mx-auto" />
          <div>
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">No Brand Profiles Found</h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Create a brand profile to customize AI voice tone, target audience personas, and visual styling.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary text-xs py-2 px-4 inline-flex items-center space-x-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Brand Profile</span>
          </button>
        </div>
      )}

      {/* CREATE BRAND MODAL */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <div className="flex items-center space-x-2">
                <Building2 className="w-5 h-5 text-[var(--accent-color)]" />
                <h2 className="text-base font-bold text-[var(--text-primary)]">Create Brand Profile</h2>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateBrand} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Brand Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Industry
                  </label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g. E-Commerce, SaaS, Fitness"
                    className="input-field w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Tone of Voice
                </label>
                <select
                  value={toneOfVoice}
                  onChange={(e) => setToneOfVoice(e.target.value)}
                  className="input-field w-full cursor-pointer"
                >
                  <option>Professional, Energetic & Visionary</option>
                  <option>Friendly, Casual & Educational</option>
                  <option>Bold, Direct & Disruptive</option>
                  <option>Luxury, Sophisticated & Elegant</option>
                  <option>Witty, Humorous & Trendy</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Target Audience
                </label>
                <input
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="e.g. Young professionals aged 22-35"
                  className="input-field w-full"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  CTA Style
                </label>
                <input
                  type="text"
                  value={ctaStyle}
                  onChange={(e) => setCtaStyle(e.target.value)}
                  placeholder="e.g. Urgency-driven & Value focused"
                  className="input-field w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Primary Brand Color
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-8 h-8 rounded border border-[var(--border-color)] bg-transparent cursor-pointer"
                    />
                    <input
                      type="text"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="input-field w-full font-mono text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Secondary Brand Color
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={secondaryColor}
                      onChange={(e) => setSecondaryColor(e.target.value)}
                      className="w-8 h-8 rounded border border-[var(--border-color)] bg-transparent cursor-pointer"
                    />
                    <input
                      type="text"
                      value={secondaryColor}
                      onChange={(e) => setSecondaryColor(e.target.value)}
                      className="input-field w-full font-mono text-xs"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Logo Image URL (Optional)
                </label>
                <input
                  type="url"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://example.com/logo.png"
                  className="input-field w-full"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-[var(--border-color)]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !name.trim()}
                  className="btn-primary text-xs flex items-center space-x-1.5"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  <span>Save Profile</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
