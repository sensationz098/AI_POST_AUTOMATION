'use client';

import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Send, Calendar, RefreshCw, Image as ImageIcon, 
  Hash, Music, Video, Plus, Trash2, CheckCircle2, AlertCircle, 
  Loader2, Wand2, Layers, Globe, Facebook, Instagram, ShieldCheck, ChevronRight,
  Upload, Link2, X, Play
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { PostStatusBadge } from '@/components/PostStatusBadge';
import { FacebookPostPreview } from '@/components/FacebookPostPreview';
import { InstagramPostPreview } from '@/components/InstagramPostPreview';
import { BrandProfile, SocialAccount, SocialPost } from '@/lib/types';
import Link from 'next/link';

export default function StudioPage() {
  // Brand & Social Accounts state
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<number | string>('1');
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);

  // Post Content state
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [topic, setTopic] = useState('');
  const [caption, setCaption] = useState('');
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [hashtagInput, setHashtagInput] = useState('');
  const [cta, setCta] = useState('👉 Click link in bio to learn more!');
  
  // Media State (Images and Videos)
  const [imageUrl, setImageUrl] = useState('');
  const [mediaType, setMediaType] = useState<'image' | 'video'>('image');
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [activeMediaTab, setActiveMediaTab] = useState<'upload' | 'ai' | 'url'>('upload');

  // Audio state
  const [audioUrl, setAudioUrl] = useState('');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string>('');

  // Target Platforms & Schedule
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['facebook', 'instagram']);
  const [scheduledAt, setScheduledAt] = useState('');

  // AI & Upload Loading states
  const [isGeneratingText, setIsGeneratingText] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isGeneratingHashtags, setIsGeneratingHashtags] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishingMessage, setPublishingMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Preview Mode state ('facebook' | 'instagram' | 'both')
  const [previewPlatform, setPreviewPlatform] = useState<'both' | 'facebook' | 'instagram'>('both');

  // Load active brands & connected social destinations
  useEffect(() => {
    async function loadInitialData() {
      try {
        const brandsRes = await apiClient.get('/brands/');
        if (Array.isArray(brandsRes.data) && brandsRes.data.length > 0) {
          setBrands(brandsRes.data);
          setSelectedBrandId(brandsRes.data[0].id);
        }
      } catch (e) {
        console.warn('Backend brands query:', e);
      }

      try {
        const accsRes = await apiClient.get('/social-accounts/');
        if (Array.isArray(accsRes.data) && accsRes.data.length > 0) {
          setSocialAccounts(accsRes.data);
          setSelectedAccountIds(accsRes.data.map(a => String(a.id)));
        }
      } catch (e) {
        console.warn('Backend accounts query:', e);
      }
    }
    loadInitialData();
  }, []);

  const activeBrand = brands.find(b => String(b.id) === String(selectedBrandId)) || (brands[0] || null);
  const fbAccount = socialAccounts.find(a => a.platform === 'facebook');
  const igAccount = socialAccounts.find(a => a.platform === 'instagram');

  // Media File Upload Handler (Image & Video)
  const handleMediaFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setMediaFile(file);
      const isVid = file.type.startsWith('video/');
      setMediaType(isVid ? 'video' : 'image');
      
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64Data = reader.result as string;
        console.log("MEDIA TYPE:", typeof base64Data);
        console.log("MEDIA PREFIX:", typeof base64Data === "string" ? base64Data.substring(0, 100) : base64Data);
        setImageUrl(base64Data);
      };
      reader.readAsDataURL(file);
    }
  };

  // AI Generation Handlers
  const handleGenerateCaption = async () => {
    if (!topic.trim() && !prompt.trim()) {
      setErrorMessage('Please enter a post topic or prompt first.');
      return;
    }
    setIsGeneratingText(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.post('/ai/generate', {
        prompt: prompt.trim() || topic.trim(),
        topic: topic.trim(),
        brand_id: selectedBrandId ? Number(selectedBrandId) : 1,
        platform: selectedPlatforms[0] || 'facebook',
      });
      if (res.data?.caption) {
        setCaption(res.data.caption);
        if (res.data.hashtags && Array.isArray(res.data.hashtags)) {
          setHashtags(res.data.hashtags);
        }
        if (res.data.title) setTitle(res.data.title);
      }
    } catch (e: any) {
      console.warn('AI Generation fallback:', e);
      setCaption(`🚀 ${topic || 'Introducing our new AI-powered workflow'}! Streamline your content creation and schedule posts directly to Facebook & Instagram with Sensationz.`);
      if (hashtags.length === 0) {
        setHashtags(['#SocialMediaAI', '#MetaGraphAPI', '#Automation']);
      }
    } finally {
      setIsGeneratingText(false);
    }
  };

  const handleGenerateImage = async () => {
    setIsGeneratingImage(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.post('/ai/generate-image', {
        prompt: prompt.trim() || topic.trim() || 'Modern professional tech workspace with clean editorial typography',
      });
      if (res.data?.image_url) {
        setImageUrl(res.data.image_url);
        setMediaType('image');
      }
    } catch (e: any) {
      console.warn('AI Image Generation fallback:', e);
      const stockImages = [
        'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80',
        'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80',
        'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80',
      ];
      setImageUrl(stockImages[Math.floor(Math.random() * stockImages.length)]);
      setMediaType('image');
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const handleGenerateHashtags = async () => {
    setIsGeneratingHashtags(true);
    try {
      const res = await apiClient.post('/ai/suggest-hashtags', {
        topic: topic || caption || 'AI Social Automation',
      });
      if (res.data?.hashtags && Array.isArray(res.data.hashtags)) {
        setHashtags(res.data.hashtags);
      }
    } catch (e) {
      setHashtags(['#SocialAI', '#MetaGraphAPI', '#ContentCreator', '#DigitalMarketing']);
    } finally {
      setIsGeneratingHashtags(false);
    }
  };

  const handleAddHashtag = () => {
    if (!hashtagInput.trim()) return;
    const tag = hashtagInput.trim().startsWith('#') ? hashtagInput.trim() : `#${hashtagInput.trim()}`;
    if (!hashtags.includes(tag)) {
      setHashtags([...hashtags, tag]);
    }
    setHashtagInput('');
  };

  const handleRemoveHashtag = (tag: string) => {
    setHashtags(hashtags.filter(h => h !== tag));
  };

  // Audio Upload Handler
  const handleAudioFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAudioFile(file);
      const url = URL.createObjectURL(file);
      setAudioPreviewUrl(url);
      setAudioUrl(url);
    }
  };

  // Clear media
  const handleClearMedia = () => {
    setImageUrl('');
    setMediaFile(null);
    setMediaType('image');
  };

  // Publish / Schedule Handler
  const handlePublish = async (isScheduled: boolean = false) => {
    if (!caption.trim() && !imageUrl.trim()) {
      setErrorMessage('Please provide a caption or image/video before publishing.');
      return;
    }
    if (selectedPlatforms.length === 0) {
      setErrorMessage('Please select at least one social destination platform.');
      return;
    }

    setIsPublishing(true);
    setPublishingMessage(null);
    setErrorMessage(null);

    console.log("MEDIA TYPE:", typeof imageUrl);
    console.log("MEDIA PREFIX:", typeof imageUrl === "string" ? imageUrl.substring(0, 100) : imageUrl);

    const postPayload = {
      brand_id: Number(selectedBrandId) || 1,
      title: title.trim() || topic.trim() || 'Social AI Post',
      caption: caption,
      hashtags: hashtags || [],
      cta: cta || null,
      seo_keywords: [],
      image_prompt: topic || title || null,
      image_url: imageUrl || null,
      platforms: selectedPlatforms,
      status: isScheduled ? 'SCHEDULED' : 'PUBLISHED',
      scheduled_at: isScheduled && scheduledAt ? new Date(scheduledAt).toISOString() : null,
    };

    try {
      setPublishingMessage("Publishing to social platforms, please wait...");
      const endpoint = isScheduled ? '/posts/schedule' : '/posts/publish-now';
      const res = await apiClient.post(endpoint, postPayload, { timeout: 60000 });
      
      if (res.data?.status === 'FAILED' || res.data?.last_error) {
        setPublishingMessage(null);
        setErrorMessage(`Publishing Warning: ${res.data.last_error}`);
      } else {
        setPublishingMessage(
          isScheduled
            ? `✓ Post queued for scheduling on ${new Date(scheduledAt).toLocaleString()}`
            : '✓ Post published successfully to Meta Graph API!'
        );
      }
    } catch (e: any) {
      setPublishingMessage(null);
      console.error('Backend post publish error:', e);
      const detail = e.response?.data?.detail || e.message || 'Failed to publish post. Please check your connected Meta channel & token permissions.';
      setErrorMessage(`Publishing Error: ${detail}`);
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="space-y-6 font-sans text-xs select-none max-w-[1400px] mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-[var(--accent-color)]" />
            <span>AI Content Studio & Publisher</span>
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Craft, preview, and schedule editorial posts for Meta Graph API channels.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto">
          <div className="flex items-center space-x-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] px-3 py-1.5 rounded-md">
            <span className="text-xs font-semibold text-[var(--text-secondary)]">Brand Persona:</span>
            <select
              value={selectedBrandId}
              onChange={(e) => setSelectedBrandId(e.target.value)}
              className="bg-transparent text-xs text-[var(--text-primary)] font-medium focus:outline-none cursor-pointer"
            >
              {brands.map((b) => (
                <option key={b.id} value={b.id} className="bg-[var(--bg-secondary)] text-[var(--text-primary)]">
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          <Link href="/posts" className="btn-secondary text-xs py-1.5 px-3">
            View Post Queue →
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {publishingMessage && (
        <div className="p-4 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--success-color)] text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-[var(--success-color)]" />
            <span className="font-semibold">{publishingMessage}</span>
          </div>
          <button onClick={() => setPublishingMessage(null)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">
            ✕
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--danger-color)] text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-[var(--danger-color)]" />
            <span className="font-semibold">{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">
            ✕
          </button>
        </div>
      )}

      {/* Main Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form & AI Controls */}
        <div className="lg:col-span-7 space-y-5">
          <div className="pub-card p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <h2 className="text-sm font-bold text-[var(--text-primary)] flex items-center space-x-2">
                <Wand2 className="w-4 h-4 text-[var(--accent-color)]" />
                <span>Post Composer & Media Studio</span>
              </h2>
              <span className="text-[11px] font-mono text-[var(--text-tertiary)]">Drafting Mode</span>
            </div>

            {/* Prompt & Topic Input */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                AI Generation Prompt / Core Topic
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => {
                    setTopic(e.target.value);
                    setPrompt(e.target.value);
                  }}
                  placeholder="e.g. Announcing our spring product release for AI marketers"
                  className="input-field flex-1"
                />
                <button
                  type="button"
                  onClick={handleGenerateCaption}
                  disabled={isGeneratingText}
                  className="btn-primary text-xs flex items-center space-x-1.5 flex-shrink-0"
                >
                  {isGeneratingText ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  <span>Generate Caption</span>
                </button>
              </div>
            </div>

            {/* Post Title */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[var(--text-secondary)]">
                Post Title / Campaign Identifier
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Spring AI Release Launch Post"
                className="input-field w-full"
              />
            </div>

            {/* Caption Text Area */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-medium text-[var(--text-secondary)]">
                  Caption & Post Content
                </label>
                <span className="text-[11px] font-mono text-[var(--text-tertiary)]">
                  {caption.length} characters
                </span>
              </div>
              <textarea
                rows={5}
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="Write or edit your social media post caption here..."
                className="input-field w-full leading-relaxed resize-none"
              />
            </div>

            {/* CTA Field */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[var(--text-secondary)]">
                Call to Action (CTA) / Website Link
              </label>
              <input
                type="text"
                value={cta}
                onChange={(e) => setCta(e.target.value)}
                placeholder="e.g. 👉 Click link in bio to learn more!"
                className="input-field w-full"
              />
            </div>

            {/* Hashtags Section */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-medium text-[var(--text-secondary)]">
                  Hashtags ({hashtags.length})
                </label>
                <button
                  type="button"
                  onClick={handleGenerateHashtags}
                  disabled={isGeneratingHashtags}
                  className="btn-tertiary text-xs"
                >
                  {isGeneratingHashtags ? 'Suggesting...' : '+ AI Suggest Hashtags'}
                </button>
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={hashtagInput}
                  onChange={(e) => setHashtagInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddHashtag())}
                  placeholder="Add hashtag (e.g. #ApexAI) and press Enter"
                  className="input-field flex-1"
                />
                <button
                  type="button"
                  onClick={handleAddHashtag}
                  className="btn-secondary text-xs px-3"
                >
                  Add
                </button>
              </div>

              <div className="flex flex-wrap gap-1.5 pt-1">
                {hashtags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--accent-color)] text-xs font-mono"
                  >
                    <span>{tag}</span>
                    <button
                      onClick={() => handleRemoveHashtag(tag)}
                      className="text-[var(--text-tertiary)] hover:text-[var(--danger-color)] ml-1"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* MEDIA ATTACHMENT SECTION (Images & Videos) */}
            <div className="space-y-3 pt-3 border-t border-[var(--border-color)]">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-[var(--text-primary)] flex items-center space-x-2">
                  <ImageIcon className="w-4 h-4 text-[var(--accent-color)]" />
                  <span>Media Attachment (Images & Videos)</span>
                </label>

                {/* Media Tab Selector */}
                <div className="flex items-center space-x-1 bg-[var(--bg-tertiary)] p-0.5 rounded border border-[var(--border-color)] font-mono text-[10px]">
                  <button
                    type="button"
                    onClick={() => setActiveMediaTab('upload')}
                    className={`px-2 py-1 rounded font-medium transition ${
                      activeMediaTab === 'upload' ? 'bg-[var(--accent-color)] text-white' : 'text-[var(--text-secondary)]'
                    }`}
                  >
                    📁 Upload File
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveMediaTab('ai')}
                    className={`px-2 py-1 rounded font-medium transition ${
                      activeMediaTab === 'ai' ? 'bg-[var(--accent-color)] text-white' : 'text-[var(--text-secondary)]'
                    }`}
                  >
                    🪄 AI Generate
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveMediaTab('url')}
                    className={`px-2 py-1 rounded font-medium transition ${
                      activeMediaTab === 'url' ? 'bg-[var(--accent-color)] text-white' : 'text-[var(--text-secondary)]'
                    }`}
                  >
                    🔗 Media URL
                  </button>
                </div>
              </div>

              {/* Tab 1: Upload File (Images & Videos) */}
              {activeMediaTab === 'upload' && (
                <div className="space-y-2">
                  <div className="border-2 border-dashed border-[var(--border-color)] hover:border-[var(--accent-color)] rounded-lg p-5 text-center transition bg-[var(--bg-tertiary)] relative cursor-pointer">
                    <input
                      type="file"
                      accept="image/*,video/*"
                      onChange={handleMediaFileUpload}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    />
                    <div className="flex flex-col items-center space-y-2">
                      <div className="w-10 h-10 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-center text-[var(--accent-color)]">
                        <Upload className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-[var(--text-primary)]">
                          Click or drag to upload an Image or Video file
                        </p>
                        <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">
                          Supports PNG, JPG, WEBP, MP4, MOV, WEBM (Max 50MB)
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: AI Generate Image */}
              {activeMediaTab === 'ai' && (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter visual prompt for AI image generation..."
                    className="input-field flex-1"
                  />
                  <button
                    type="button"
                    onClick={handleGenerateImage}
                    disabled={isGeneratingImage}
                    className="btn-secondary text-xs flex items-center space-x-1.5 flex-shrink-0"
                  >
                    {isGeneratingImage ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                    <span>Generate AI Image</span>
                  </button>
                </div>
              )}

              {/* Tab 3: Direct Media URL */}
              {activeMediaTab === 'url' && (
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={imageUrl}
                    onChange={(e) => {
                      setImageUrl(e.target.value);
                      const isVid = e.target.value.endsWith('.mp4') || e.target.value.endsWith('.mov') || e.target.value.endsWith('.webm');
                      setMediaType(isVid ? 'video' : 'image');
                    }}
                    placeholder="https://example.com/media.mp4 or image.jpg"
                    className="input-field flex-1 font-mono text-xs"
                  />
                  {imageUrl && (
                    <button
                      type="button"
                      onClick={handleClearMedia}
                      className="btn-danger text-xs px-3"
                    >
                      Clear
                    </button>
                  )}
                </div>
              )}

              {/* Media Preview Box */}
              {imageUrl && (
                <div className="p-3 bg-[var(--bg-tertiary)] rounded-md border border-[var(--border-color)] flex items-center justify-between">
                  <div className="flex items-center space-x-3 min-w-0">
                    {mediaType === 'video' || imageUrl.endsWith('.mp4') || imageUrl.endsWith('.mov') || imageUrl.startsWith('data:video/') ? (
                      <div className="w-12 h-12 bg-black rounded flex items-center justify-center text-white flex-shrink-0 border border-[var(--border-color)] relative overflow-hidden">
                        <video src={imageUrl} className="w-full h-full object-cover" />
                        <Play className="w-4 h-4 absolute text-white fill-white" />
                      </div>
                    ) : (
                      <img
                        src={imageUrl}
                        alt="Media Preview"
                        className="w-12 h-12 rounded object-cover border border-[var(--border-color)] flex-shrink-0"
                      />
                    )}
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-[var(--text-primary)] truncate">
                        {mediaFile ? mediaFile.name : 'Attached Media Asset'}
                      </p>
                      <span className="text-[10px] font-mono text-[var(--accent-color)] uppercase">
                        {mediaType === 'video' ? '🎬 Video File' : '🖼️ Image File'}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleClearMedia}
                    className="p-1.5 rounded hover:bg-[var(--bg-secondary)] text-[var(--text-tertiary)] hover:text-[var(--danger-color)] transition"
                    title="Remove Media"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Audio Attachment Control */}
            <div className="space-y-2 pt-2 border-t border-[var(--border-color)]">
              <label className="block text-xs font-medium text-[var(--text-secondary)] flex items-center space-x-1.5">
                <Music className="w-4 h-4 text-[var(--accent-color)]" />
                <span>Attach Audio Track / Background Music (For IG Reels)</span>
              </label>
              <input
                type="file"
                accept="audio/*"
                onChange={handleAudioFileChange}
                className="block w-full text-xs text-[var(--text-secondary)] file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-[var(--bg-tertiary)] file:text-[var(--text-primary)] hover:file:bg-[var(--border-color)] cursor-pointer"
              />
              {audioPreviewUrl && (
                <div className="p-2.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)]">
                  <audio controls src={audioPreviewUrl} className="w-full h-8" />
                </div>
              )}
            </div>

            {/* Target Destinations & Schedule Options */}
            <div className="space-y-4 pt-3 border-t border-[var(--border-color)]">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-2">
                  Select Target Channels
                </label>
                <div className="flex flex-wrap items-center gap-3">
                  {/* Facebook Target Channel Card */}
                  <label
                    className={`flex items-center space-x-2.5 cursor-pointer bg-[var(--bg-tertiary)] border px-3.5 py-2 rounded-md transition ${
                      selectedPlatforms.includes('facebook')
                        ? 'border-[#1877F2] bg-[#1877F2]/5'
                        : 'border-[var(--border-color)]'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.includes('facebook')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          if (!selectedPlatforms.includes('facebook')) setSelectedPlatforms([...selectedPlatforms, 'facebook']);
                        } else {
                          setSelectedPlatforms(selectedPlatforms.filter(p => p !== 'facebook'));
                        }
                      }}
                      className="rounded accent-[#1877F2]"
                    />
                    <Facebook className="w-4 h-4 text-[#1877F2] flex-shrink-0" />
                    <div>
                      <span className="font-semibold text-xs text-[var(--text-primary)] block">
                        {fbAccount?.account_name || activeBrand?.meta_account?.facebook_page_name || activeBrand?.name || 'Facebook Page'}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase block">
                        Facebook Page
                      </span>
                    </div>
                  </label>

                  {/* Instagram Target Channel Card */}
                  <label
                    className={`flex items-center space-x-2.5 cursor-pointer bg-[var(--bg-tertiary)] border px-3.5 py-2 rounded-md transition ${
                      selectedPlatforms.includes('instagram')
                        ? 'border-[#E4405F] bg-[#E4405F]/5'
                        : 'border-[var(--border-color)]'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.includes('instagram')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          if (!selectedPlatforms.includes('instagram')) setSelectedPlatforms([...selectedPlatforms, 'instagram']);
                        } else {
                          setSelectedPlatforms(selectedPlatforms.filter(p => p !== 'instagram'));
                        }
                      }}
                      className="rounded accent-[#E4405F]"
                    />
                    <Instagram className="w-4 h-4 text-[#E4405F] flex-shrink-0" />
                    <div>
                      <span className="font-semibold text-xs text-[var(--text-primary)] block">
                        {igAccount?.account_name || (activeBrand?.meta_account?.instagram_username ? `@${activeBrand.meta_account.instagram_username}` : (activeBrand?.name ? `@${activeBrand.name.toLowerCase().replace(/\s+/g, '_')}` : 'Instagram Account'))}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase block">
                        Instagram Account
                      </span>
                    </div>
                  </label>
                </div>
              </div>

              {/* Scheduled Date Picker */}
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-[var(--text-secondary)]">
                  Schedule Date & Time (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  className="input-field w-full font-mono text-xs"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3 pt-3">
                {scheduledAt ? (
                  <button
                    type="button"
                    onClick={() => handlePublish(true)}
                    disabled={isPublishing}
                    className="btn-secondary text-xs flex items-center space-x-1.5"
                  >
                    <Calendar className="w-4 h-4 text-[var(--accent-color)]" />
                    <span>Schedule Post</span>
                  </button>
                ) : null}

                <button
                  type="button"
                  onClick={() => handlePublish(false)}
                  disabled={isPublishing}
                  className="btn-primary text-xs py-2 px-4 flex items-center space-x-1.5"
                >
                  {isPublishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  <span>Publish to FB Page & Instagram</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Real-World Social Preview Cards */}
        <div className="lg:col-span-5 space-y-4">
          <div className="pub-card p-5 space-y-4 sticky top-20">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center space-x-2">
                <Globe className="w-4 h-4 text-[var(--accent-color)]" />
                <span>Live Feed Preview</span>
              </h3>

              {/* Toggle Platform Preview Filter */}
              <div className="flex items-center space-x-1 bg-[var(--bg-tertiary)] p-0.5 rounded border border-[var(--border-color)]">
                <button
                  onClick={() => setPreviewPlatform('both')}
                  className={`px-2 py-1 text-[10px] font-semibold rounded ${
                    previewPlatform === 'both' ? 'bg-[var(--accent-color)] text-white' : 'text-[var(--text-secondary)]'
                  }`}
                >
                  Both
                </button>
                <button
                  onClick={() => setPreviewPlatform('facebook')}
                  className={`px-2 py-1 text-[10px] font-semibold rounded ${
                    previewPlatform === 'facebook' ? 'bg-[#1877F2] text-white' : 'text-[var(--text-secondary)]'
                  }`}
                >
                  FB
                </button>
                <button
                  onClick={() => setPreviewPlatform('instagram')}
                  className={`px-2 py-1 text-[10px] font-semibold rounded ${
                    previewPlatform === 'instagram' ? 'bg-[#E4405F] text-white' : 'text-[var(--text-secondary)]'
                  }`}
                >
                  IG
                </button>
              </div>
            </div>

            {/* Social Previews Scroll Container */}
            <div className="space-y-6 max-h-[750px] overflow-y-auto pr-1">
              {(previewPlatform === 'both' || previewPlatform === 'facebook') && (
                <div className="space-y-2">
                  <span className="text-[10px] font-mono font-semibold uppercase text-[var(--text-tertiary)] flex items-center space-x-1.5">
                    <Facebook className="w-3.5 h-3.5 text-[#1877F2]" />
                    <span>Facebook Feed Preview</span>
                  </span>
                  <FacebookPostPreview
                    brand={activeBrand}
                    caption={caption}
                    hashtags={hashtags}
                    cta={cta}
                    imageUrl={imageUrl}
                    isVideo={mediaType === 'video'}
                  />
                </div>
              )}

              {(previewPlatform === 'both' || previewPlatform === 'instagram') && (
                <div className="space-y-2 pt-2">
                  <span className="text-[10px] font-mono font-semibold uppercase text-[var(--text-tertiary)] flex items-center space-x-1.5">
                    <Instagram className="w-3.5 h-3.5 text-[#E4405F]" />
                    <span>Instagram Feed Preview</span>
                  </span>
                  <InstagramPostPreview
                    brand={activeBrand}
                    caption={caption}
                    hashtags={hashtags}
                    cta={cta}
                    imageUrl={imageUrl}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
