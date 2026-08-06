'use client';

import React, { useState, useEffect } from 'react';
import { Layers, Plus, Sparkles, Check, Trash2, X, Loader2, Building2, Palette, MessageSquare, Target } from 'lucide-react';
import { BrandProfile } from '@/lib/types';
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

  // Fetch brands on mount
  const fetchBrands = async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get('/brands/');
      if (Array.isArray(res.data) && res.data.length > 0) {
        setBrands(res.data);
      } else {
        // Default brand if none returned
        setBrands([
          {
            id: 1,
            name: 'Apex Innovations',
            logo_url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80',
            brand_colors: ['#6366F1', '#06B6D4'],
            tone_of_voice: 'Professional, Energetic & Visionary',
            target_audience: 'Tech-savvy entrepreneurs, developers & agency leads',
            cta_style: 'Urgency-driven & Value focused',
            industry: 'Artificial Intelligence',
            user_id: 1,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }
        ]);
      }
    } catch {
      // Fallback local state if backend unreachable
      setBrands([
        {
          id: 1,
          name: 'Apex Innovations',
          logo_url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80',
          brand_colors: ['#6366F1', '#06B6D4'],
          tone_of_voice: 'Professional, Energetic & Visionary',
          target_audience: 'Tech-savvy entrepreneurs, developers & agency leads',
          cta_style: 'Urgency-driven & Value focused',
          industry: 'Artificial Intelligence',
          user_id: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <Layers className="w-5 h-5 text-purple-400" />
            <span>Brand Voice & Profile Studio</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Define brand personas, target audiences, tone of voice, visual color tokens, and CTA styles for AI generation.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs transition shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>Add Brand Profile</span>
        </button>
      </div>

      {notification && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center space-x-2">
          <Check className="w-4 h-4" />
          <span>{notification}</span>
        </div>
      )}

      {/* Brands Cards Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-slate-400 text-xs space-x-2">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
          <span>Loading Brand Profiles...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {brands.map((brand) => (
            <div key={brand.id} className="glass-panel p-6 rounded-2xl space-y-4 border border-slate-800 hover:border-indigo-500/40 transition relative group">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <img
                    src={brand.logo_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80'}
                    alt={brand.name}
                    className="w-12 h-12 rounded-xl object-cover border border-indigo-500/40"
                  />
                  <div>
                    <h3 className="text-base font-bold text-white">{brand.name}</h3>
                    <span className="text-[11px] font-semibold text-indigo-400">{brand.industry}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold">
                    Active
                  </span>
                  <button
                    onClick={() => handleDeleteBrand(brand.id)}
                    className="p-1.5 rounded-lg bg-slate-900 hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition"
                    title="Delete Brand"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="space-y-2.5 text-xs text-slate-300 bg-slate-950/40 p-4 rounded-xl border border-slate-900">
                <div>
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase tracking-wider mb-0.5">Tone of Voice</span>
                  <p className="font-medium text-white">{brand.tone_of_voice}</p>
                </div>

                <div>
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase tracking-wider mb-0.5">Target Audience</span>
                  <p className="font-medium text-slate-300">{brand.target_audience}</p>
                </div>

                <div>
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase tracking-wider mb-0.5">CTA Style</span>
                  <p className="font-medium text-purple-300">{brand.cta_style}</p>
                </div>

                <div>
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase tracking-wider mb-1">Brand Colors</span>
                  <div className="flex items-center space-x-2">
                    {brand.brand_colors?.map((color, idx) => (
                      <div key={idx} className="flex items-center space-x-1 bg-slate-900 border border-slate-800 px-2 py-1 rounded-lg">
                        <div className="w-3.5 h-3.5 rounded-full border border-slate-700" style={{ backgroundColor: color }} />
                        <span className="font-mono text-[10px] text-slate-400">{color}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
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
