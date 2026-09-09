'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import toast from 'react-hot-toast';
import {
  Sparkles,
  Image as ImageIcon,
  Send,
  Calendar,
  Layers,
  RefreshCw,
  UploadCloud,
  X,
  CheckSquare,
  Square,
  AlertTriangle,
  Film,
  Camera,
  CheckCircle2,
  Share2,
  Clock,
  Play,
  Volume2
} from 'lucide-react';
import { apiClient, PUBLISHING_TIMEOUT_MS } from '@/lib/api';
import {
  BrandProfile,
  SocialAccount,
  Story,
  StoryValidationResult
} from '@/lib/types';
import { StoryMediaEditorModal } from './StoryMediaEditorModal';

interface StoryComposerProps {
  brands: BrandProfile[];
  selectedBrand: BrandProfile | null;
  onSelectBrand: (b: BrandProfile) => void;
  socialAccounts: SocialAccount[];
}

export function StoryComposer({
  brands,
  selectedBrand,
  onSelectBrand,
  socialAccounts
}: StoryComposerProps) {
  // Media State
  const [mediaUrl, setMediaUrl] = useState<string>('');
  const [originalMediaUrl, setOriginalMediaUrl] = useState<string>('');
  const [isEdited, setIsEdited] = useState<boolean>(false);
  const [isEditorOpen, setIsEditorOpen] = useState<boolean>(false);

  const [mediaType, setMediaType] = useState<'image' | 'video'>('image');
  const [title, setTitle] = useState<string>('');
  const [caption, setCaption] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  // Platform selection (account IDs)
  const [selectedAccountIds, setSelectedAccountIds] = useState<number[]>([]);

  // Story state & Actions
  const [isPublishing, setIsPublishing] = useState<boolean>(false);
  const [isScheduling, setIsScheduling] = useState<boolean>(false);
  const [scheduledDateTime, setScheduledDateTime] = useState<string>('');
  const [previewPlatform, setPreviewPlatform] = useState<'instagram' | 'facebook'>('instagram');

  // Preflight validation
  const [validationResult, setValidationResult] = useState<StoryValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);

  // Filter accounts for Stories: only connected Facebook Pages and Instagram Business accounts
  const capableAccounts = socialAccounts.filter(acc => {
    if (acc.status !== 'CONNECTED') return false;
    if (acc.platform === 'instagram') {
      const meta = acc.metadata_json || {};
      const type = String(meta.account_type || '').toUpperCase();
      if (type === 'CREATOR' && !meta.creator_story_publishing_supported) return false;
      return true;
    }
    if (acc.platform === 'facebook') {
      return Boolean(acc.account_id);
    }
    return false;
  });

  const handleSelectAll = () => {
    setSelectedAccountIds(capableAccounts.map(a => a.id));
  };

  const handleClearAll = () => {
    setSelectedAccountIds([]);
  };

  // Memoize selected platforms to prevent new array references on every render
  const selectedPlatforms: ('facebook' | 'instagram')[] = useMemo(() => {
    return Array.from(
      new Set(
        capableAccounts
          .filter(a => selectedAccountIds.includes(a.id))
          .map(a => a.platform)
      )
    );
  }, [capableAccounts, selectedAccountIds]);

  // Stable serialized key for selected accounts to prevent effect loop
  const selectedAccountIdsKey = useMemo(() => {
    return selectedAccountIds.slice().sort((a, b) => a - b).join(',');
  }, [selectedAccountIds]);

  const selectedBrandId = selectedBrand?.id;
  const lastValidatedKeyRef = useRef<string>('');

  // Validate preflight on media or account change (only when actual inputs change)
  useEffect(() => {
    if (!mediaUrl || !selectedBrandId || selectedAccountIds.length === 0) {
      setValidationResult(null);
      lastValidatedKeyRef.current = '';
      return;
    }

    const currentKey = `${selectedBrandId}|${mediaUrl}|${mediaType}|${selectedAccountIdsKey}`;
    if (currentKey === lastValidatedKeyRef.current) {
      return;
    }

    const timer = setTimeout(async () => {
      if (currentKey === lastValidatedKeyRef.current) return;
      lastValidatedKeyRef.current = currentKey;
      setIsValidating(true);
      console.info('[STORY_PREFLIGHT_START]', {
        brand_id: selectedBrandId,
        media_type: mediaType,
        target_account_ids: selectedAccountIds,
        count: selectedAccountIds.length
      });

      try {
        const res = await apiClient.post('/stories/validate-preflight', {
          brand_id: selectedBrandId,
          media_url: mediaUrl,
          media_type: mediaType,
          target_account_ids: selectedAccountIds,
          platforms: selectedPlatforms.length > 0 ? selectedPlatforms : ['instagram', 'facebook']
        });
        console.info('[STORY_PREFLIGHT_SUCCESS]', res.data);
        setValidationResult(res.data);
      } catch (err: any) {
        console.error('[STORY_PREFLIGHT_ERROR]', err);
      } finally {
        setIsValidating(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [mediaUrl, mediaType, selectedAccountIdsKey, selectedBrandId, selectedPlatforms, selectedAccountIds]);

  // Media File Upload Handler (streaming to backend / upload-media)
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isVid = file.type.startsWith('video/') || file.name.match(/\.(mp4|mov|webm|m4v)$/i);
    const mType = isVid ? 'video' : 'image';
    setMediaType(mType);

    const formData = new FormData();
    formData.append('file', file);

    setIsUploading(true);
    setUploadProgress(10);
    const uploadToast = toast.loading(`Uploading Story ${mType}...`);

    try {
      const res = await apiClient.post('/stories/upload-media', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        }
      });

      if (res.data?.url) {
        setMediaUrl(res.data.url);
        setOriginalMediaUrl(res.data.url);
        setIsEdited(false);
        toast.success(`Story ${mType} uploaded successfully!`, { id: uploadToast });
      } else {
        throw new Error('No URL returned from upload');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Media upload failed';
      toast.error(msg, { id: uploadToast });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const toggleAccount = (accountId: number) => {
    setSelectedAccountIds(prev =>
      prev.includes(accountId)
        ? prev.filter(id => id !== accountId)
        : [...prev, accountId]
    );
  };

  // Publish Story Immediately
  const handlePublishNow = async () => {
    if (!selectedBrand) {
      toast.error('Please select a brand profile.');
      return;
    }
    if (!mediaUrl) {
      toast.error('Please upload an image or video for your Story.');
      return;
    }
    if (selectedAccountIds.length === 0) {
      toast.error('Please select at least one Story destination account.');
      return;
    }

    setIsPublishing(true);
    console.info('[STORY_PUBLISH_INITIATED]', {
      brand_id: selectedBrand.id,
      media_type: mediaType,
      target_account_ids: selectedAccountIds,
      count: selectedAccountIds.length
    });
    const pubToast = toast.loading('Publishing Story to Meta Graph API...');

    let storyId: number | null = null;
    try {
      const payload = {
        brand_id: selectedBrand.id,
        title: title || 'SocialAI Story',
        caption: caption || undefined,
        media_url: mediaUrl,
        media_type: mediaType,
        target_account_ids: selectedAccountIds,
        platforms: selectedPlatforms
      };

      // 1. Create the Story record
      const createRes = await apiClient.post('/stories', payload);
      storyId = createRes.data?.id;
      if (!storyId) {
        throw new Error('Failed to create Story record.');
      }
      console.info('[STORY_CREATED_TRIGGERING_PUBLISH_NOW]', { storyId, target_account_ids: selectedAccountIds });

      // 2. Publish immediately via dedicated /publish-now endpoint with extended publishing window (300s)
      const pubRes = await apiClient.post(`/stories/${storyId}/publish-now`, null, {
        timeout: PUBLISHING_TIMEOUT_MS
      });
      console.info('[STORY_PUBLISH_COMPLETED]', pubRes.data);
      toast.success('🎉 Story published successfully!', { id: pubToast });
    } catch (err: any) {
      console.error('[STORY_PUBLISH_ERROR]', err);
      // Resilience: If client encountered a network error / timeout, check if server actually succeeded
      if (storyId) {
        try {
          const statusRes = await apiClient.get(`/stories/${storyId}`);
          if (statusRes.data?.status === 'PUBLISHED') {
            console.info('[STORY_PUBLISH_STATUS_RECOVERED]', statusRes.data);
            toast.success('🎉 Story published successfully!', { id: pubToast });
            return;
          }
        } catch (pollErr) {
          console.warn('[STORY_STATUS_CHECK_FAILED]', pollErr);
        }
      }
      const msg = err.response?.data?.detail || err.message || 'Story publishing failed.';
      toast.error(msg, { id: pubToast, duration: 6000 });
    } finally {
      setIsPublishing(false);
    }
  };

  // Schedule Story
  const handleSchedule = async () => {
    if (!selectedBrand) {
      toast.error('Please select a brand profile.');
      return;
    }
    if (!mediaUrl) {
      toast.error('Please upload an image or video for your Story.');
      return;
    }
    if (selectedAccountIds.length === 0) {
      toast.error('Please select at least one Story destination account.');
      return;
    }
    if (!scheduledDateTime) {
      toast.error('Please select a future date and time.');
      return;
    }

    const scheduledDate = new Date(scheduledDateTime);
    if (scheduledDate.getTime() <= Date.now()) {
      toast.error('Scheduled time must be in the future.');
      return;
    }

    setIsPublishing(true);
    const schedToast = toast.loading('Scheduling Story...');

    try {
      const payload = {
        brand_id: selectedBrand.id,
        title: title || 'Scheduled Story',
        caption: caption || undefined,
        media_url: mediaUrl,
        media_type: mediaType,
        target_account_ids: selectedAccountIds,
        platforms: selectedPlatforms,
        status: 'SCHEDULED',
        scheduled_at: scheduledDate.toISOString()
      };

      await apiClient.post('/stories', payload);
      toast.success(`📅 Story scheduled for ${scheduledDate.toLocaleString()}`, { id: schedToast });
      setIsScheduling(false);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to schedule Story.';
      toast.error(msg, { id: schedToast });
    } finally {
      setIsPublishing(false);
    }
  };

  // Save Draft
  const handleSaveDraft = async () => {
    if (!selectedBrand || !mediaUrl) {
      toast.error('Brand and media URL are required to save a draft.');
      return;
    }
    try {
      await apiClient.post('/stories', {
        brand_id: selectedBrand.id,
        title: title || 'Story Draft',
        caption: caption || undefined,
        media_url: mediaUrl,
        media_type: mediaType,
        target_account_ids: selectedAccountIds,
        platforms: selectedPlatforms,
        status: 'DRAFT'
      });
      toast.success('Story draft saved!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to save draft.');
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-4 max-w-7xl mx-auto text-slate-100">
      {/* ── Left Column: Configuration & Media Upload (7 Cols) ── */}
      <div className="lg:col-span-7 space-y-6">
        {/* Brand Selector Banner */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-fuchsia-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-fuchsia-500/20">
                <Camera className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-100">Stories Automation Studio</h2>
                <p className="text-xs text-slate-400">Create, preview & schedule 24-hour Stories for Instagram & Facebook</p>
              </div>
            </div>

            {/* Brand Dropdown */}
            {brands.length > 0 && (
              <select
                value={selectedBrand?.id || ''}
                onChange={(e) => {
                  const b = brands.find(item => item.id === Number(e.target.value));
                  if (b) onSelectBrand(b);
                }}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                {brands.map(b => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Media Upload Area (9:16 Optimized) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <UploadCloud className="w-4 h-4 text-indigo-400" />
              <span>Story Media Asset</span>
            </label>
            <span className="text-[11px] font-medium text-fuchsia-400 bg-fuchsia-500/10 px-2.5 py-0.5 rounded-full border border-fuchsia-500/20">
              Recommended: 9:16 Vertical (1080×1920)
            </span>
          </div>

          {mediaUrl ? (
            <div className="relative rounded-2xl overflow-hidden border border-slate-700/80 bg-slate-950 p-3.5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 truncate">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 flex-shrink-0">
                    {mediaType === 'video' ? <Film className="w-5 h-5" /> : <ImageIcon className="w-5 h-5" />}
                  </div>
                  <div className="truncate">
                    <p className="text-xs font-semibold text-slate-200 truncate">
                      {mediaUrl.split('/').pop() || 'Story Asset'}
                    </p>
                    <div className="flex items-center space-x-2 mt-0.5">
                      <p className="text-[10px] text-emerald-400 flex items-center space-x-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span className="capitalize">{mediaType} Story Ready</span>
                      </p>
                      {isEdited && (
                        <span className="text-[9px] font-bold text-fuchsia-300 bg-fuchsia-500/20 border border-fuchsia-500/30 px-2 py-0.5 rounded-full flex items-center space-x-1">
                          <Sparkles className="w-2.5 h-2.5 text-fuchsia-400" />
                          <span>9:16 Custom Edited</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setIsEditorOpen(true)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-fuchsia-600/20 transition hover:scale-105"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>✏ Edit Story</span>
                  </button>

                  {isEdited && (
                    <button
                      type="button"
                      onClick={() => {
                        setMediaUrl(originalMediaUrl);
                        setIsEdited(false);
                        toast.success('Reverted back to original uploaded media.');
                      }}
                      className="text-[11px] bg-slate-800 hover:bg-slate-700 text-amber-300 font-medium px-2.5 py-1.5 rounded-xl transition"
                      title="Revert back to original media"
                    >
                      Revert
                    </button>
                  )}

                  <label className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1.5 rounded-xl cursor-pointer transition font-medium">
                    Replace
                    <input
                      type="file"
                      accept="image/*,video/*"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setMediaUrl('');
                      setOriginalMediaUrl('');
                      setIsEdited(false);
                    }}
                    className="p-1.5 text-slate-400 hover:text-rose-400 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <label className="relative flex flex-col items-center justify-center p-8 border-2 border-dashed border-slate-700 hover:border-indigo-500/80 rounded-2xl bg-slate-950/60 cursor-pointer transition-all duration-200 group overflow-hidden">
              <div className="flex flex-col items-center justify-center space-y-2 text-center">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition">
                  <Film className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-xs font-semibold text-slate-200">
                    {isUploading ? `Uploading (${uploadProgress}%)...` : 'Click or Drag & Drop Story Media'}
                  </span>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Images (JPG, PNG) or Videos (MP4, MOV up to 60s)
                  </p>
                </div>
              </div>
              <input
                type="file"
                accept="image/*,video/*"
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
              />
            </label>
          )}

          {/* Or Paste Direct Public HTTPS URL */}
          <div className="space-y-1.5 pt-1">
            <label className="text-[11px] font-semibold text-slate-400">Or Media URL (HTTPS):</label>
            <input
              type="url"
              placeholder="https://your-cdn.com/story-media.mp4"
              value={mediaUrl}
              onChange={(e) => {
                const val = e.target.value;
                setMediaUrl(val);
                setOriginalMediaUrl(val);
                setIsEdited(false);
                if (val.match(/\.(mp4|mov|webm)$/i)) setMediaType('video');
                else setMediaType('image');
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
        </div>

        {/* Story Details (Optional Title & Internal Note) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-fuchsia-400" />
            <span>Story Details (Optional)</span>
          </label>

          <div className="space-y-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-400">Story Title / Descriptor</label>
              <input
                type="text"
                placeholder="e.g. Summer Flash Sale Launch"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400">Internal Notes / Caption</label>
              <textarea
                rows={2}
                placeholder="Story internal reference note..."
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>
          </div>
        </div>

        {/* Destination Platform / Accounts Selection */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <Share2 className="w-4 h-4 text-indigo-400" />
              <span>Target Story Destinations</span>
            </label>
            <div className="flex items-center space-x-2">
              {capableAccounts.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="text-[10px] font-semibold text-indigo-400 hover:text-indigo-300 px-2.5 py-1 rounded-lg bg-indigo-950/60 border border-indigo-800/60 hover:border-indigo-700 transition"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={handleClearAll}
                    className="text-[10px] font-semibold text-slate-400 hover:text-slate-300 px-2.5 py-1 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition"
                  >
                    Clear
                  </button>
                </>
              )}
              <span className="text-[10px] text-slate-400 font-mono ml-1">
                {selectedAccountIds.length} account{selectedAccountIds.length === 1 ? '' : 's'} selected
              </span>
            </div>
          </div>

          <p className="text-[11px] text-slate-400">
            The Story will be published <span className="text-slate-200 font-medium">ONLY</span> to the exact checked account(s) below.
          </p>

          {capableAccounts.length === 0 ? (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">No connected Story-capable accounts found.</p>
                <p className="text-[11px] text-amber-300/80 mt-0.5">
                  Please connect an Instagram Business or Facebook Page account in the Meta Connect settings.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {capableAccounts.map((acc) => {
                const isSelected = selectedAccountIds.includes(acc.id);
                return (
                  <button
                    key={acc.id}
                    type="button"
                    onClick={() => toggleAccount(acc.id)}
                    className={`flex items-center space-x-3 p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'bg-indigo-600/15 border-indigo-500 text-slate-100 shadow-md shadow-indigo-500/10'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex-shrink-0">
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-600" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold truncate text-slate-200">
                        {acc.account_name}
                      </p>
                      <p className="text-[10px] text-indigo-400 font-medium capitalize">
                        {acc.platform === 'instagram' ? 'Instagram Story' : 'Facebook Page Story'}
                      </p>
                      <p className="text-[9px] text-slate-500 truncate">
                        ID: {acc.id} &bull; {acc.platform === 'instagram' ? 'Business Account' : 'Facebook Page'}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Validation Feedback Banner */}
        {validationResult && (
          <div className={`p-4 rounded-2xl border text-xs space-y-2 ${
            validationResult.is_valid
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
          }`}>
            <div className="flex items-center space-x-2 font-semibold">
              {validationResult.is_valid ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-400" />
              )}
              <span>{validationResult.is_valid ? 'Ready to Publish Story' : 'Validation Checks Required'}</span>
            </div>

            {validationResult.errors.length > 0 && (
              <ul className="list-disc list-inside space-y-0.5 text-[11px] text-rose-300/90 pl-1">
                {validationResult.errors.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            )}

            {validationResult.warnings.length > 0 && (
              <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-300/90 pl-1">
                {validationResult.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Action Controls: Publish Now, Schedule, Save Draft */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleSaveDraft}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
          >
            Save Draft
          </button>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() => setIsScheduling(!isScheduling)}
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            >
              <Calendar className="w-3.5 h-3.5 text-indigo-400" />
              <span>Schedule</span>
            </button>

            <button
              type="button"
              onClick={handlePublishNow}
              disabled={isPublishing || !mediaUrl || selectedAccountIds.length === 0}
              className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-fuchsia-600/20 transition duration-150"
            >
              {isPublishing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              <span>{isPublishing ? 'Publishing...' : 'Publish Story Now'}</span>
            </button>
          </div>
        </div>

        {/* Schedule Date & Time Picker Accordion */}
        {isScheduling && (
          <div className="p-4 rounded-2xl bg-slate-900 border border-slate-700/80 space-y-3 animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center space-x-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                <span>Select Publication Date & Time</span>
              </span>
              <button
                type="button"
                onClick={() => setIsScheduling(false)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3">
              <input
                type="datetime-local"
                value={scheduledDateTime}
                onChange={(e) => setScheduledDateTime(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={handleSchedule}
                disabled={isPublishing || !scheduledDateTime}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition shadow-md"
              >
                Confirm Schedule
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Right Column: 9:16 Mobile Mockup Preview (5 Cols) ── */}
      <div className="lg:col-span-5 flex flex-col items-center space-y-4">
        {/* Preview Platform Switcher */}
        <div className="flex items-center bg-slate-900/90 border border-slate-800 rounded-xl p-1 space-x-1">
          <button
            type="button"
            onClick={() => setPreviewPlatform('instagram')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              previewPlatform === 'instagram'
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Instagram Story
          </button>
          <button
            type="button"
            onClick={() => setPreviewPlatform('facebook')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              previewPlatform === 'facebook'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Facebook Story
          </button>
        </div>

        {/* 9:16 Vertical Phone Frame */}
        <div className="relative w-[300px] h-[533px] sm:w-[320px] sm:h-[568px] rounded-[36px] bg-black border-4 border-slate-800 shadow-2xl overflow-hidden flex flex-col justify-between">
          {/* Top Notch / Speaker bar */}
          <div className="absolute top-2 left-1/2 transform -translate-x-1/2 w-28 h-4 bg-slate-900 rounded-full z-20 flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-slate-950 mr-2" />
            <div className="w-8 h-1 rounded-full bg-slate-800" />
          </div>

          {/* Media Canvas */}
          <div className="absolute inset-0 bg-slate-950 flex items-center justify-center overflow-hidden">
            {mediaUrl ? (
              mediaType === 'video' ? (
                <video
                  src={mediaUrl}
                  controls={false}
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                />
              ) : (
                <img
                  src={mediaUrl}
                  alt="Story preview"
                  className="w-full h-full object-cover"
                />
              )
            ) : (
              <div className="flex flex-col items-center justify-center text-slate-600 space-y-2 p-6 text-center">
                <Camera className="w-10 h-10 stroke-1 text-slate-700" />
                <p className="text-xs font-medium">9:16 Story Preview</p>
                <p className="text-[10px] text-slate-600">Upload media to see live Story mockup</p>
              </div>
            )}
          </div>

          {/* Story UI Overlays */}
          {/* 1. Progress Bar (Top) */}
          <div className="relative z-10 pt-8 px-3">
            <div className="flex items-center space-x-1">
              <div className="h-0.5 flex-1 bg-white/80 rounded-full shadow-sm" />
              <div className="h-0.5 flex-1 bg-white/30 rounded-full" />
              <div className="h-0.5 flex-1 bg-white/30 rounded-full" />
            </div>

            {/* Story Header (Avatar, Account Name, Time) */}
            <div className="flex items-center justify-between mt-2.5">
              <div className="flex items-center space-x-2">
                <div className={`w-8 h-8 rounded-full p-0.5 ${
                  previewPlatform === 'instagram'
                    ? 'bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600'
                    : 'bg-blue-600'
                }`}>
                  <div className="w-full h-full rounded-full bg-slate-900 overflow-hidden flex items-center justify-center text-[10px] font-bold text-white">
                    {selectedBrand?.logo_url ? (
                      <img src={selectedBrand.logo_url} alt="" className="w-full h-full object-cover" />
                    ) : (
                      selectedBrand?.name?.[0] || 'S'
                    )}
                  </div>
                </div>

                <div className="text-white drop-shadow-md">
                  <p className="text-xs font-bold leading-none">
                    {selectedBrand?.name || 'Your Brand'}
                  </p>
                  <p className="text-[9px] text-white/80 leading-none mt-0.5">
                    Just now • {previewPlatform === 'instagram' ? 'Instagram' : 'Facebook'}
                  </p>
                </div>
              </div>

              <div className="text-white/80 text-xs">✕</div>
            </div>
          </div>

          {/* 2. Optional Caption Overlay / Footer */}
          <div className="relative z-10 pb-6 px-4">
            {caption && (
              <div className="bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-xl text-white text-xs font-medium text-center shadow-lg mb-3">
                {caption}
              </div>
            )}

            {/* Simulated Reply Bar */}
            <div className="flex items-center space-x-2">
              <div className="flex-1 bg-black/40 border border-white/20 rounded-full px-3 py-1.5 text-[11px] text-white/60 backdrop-blur-sm">
                Send message...
              </div>
              <div className="w-8 h-8 rounded-full bg-black/40 border border-white/20 flex items-center justify-center text-white/80">
                ❤️
              </div>
            </div>
          </div>

          {/* Quick Edit Overlay Button on Mockup */}
          {mediaUrl && (
            <button
              type="button"
              onClick={() => setIsEditorOpen(true)}
              className="absolute bottom-20 left-1/2 -translate-x-1/2 z-30 flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-black/75 hover:bg-black/90 border border-white/20 text-white text-xs font-bold backdrop-blur-md shadow-xl transition hover:scale-105"
            >
              <Sparkles className="w-3.5 h-3.5 text-fuchsia-400" />
              <span>Edit Media</span>
            </button>
          )}
        </div>
      </div>

      {/* Story Media Visual Editor Modal */}
      <StoryMediaEditorModal
        isOpen={isEditorOpen}
        onClose={() => setIsEditorOpen(false)}
        mediaUrl={originalMediaUrl || mediaUrl}
        mediaType={mediaType}
        onSave={({ processedUrl, originalUrl }) => {
          setMediaUrl(processedUrl);
          setOriginalMediaUrl(originalUrl);
          setIsEdited(true);
          console.info('[STORY_MEDIA_SAVED]', {
            originalUrl,
            processedUrl,
            target_account_ids: selectedAccountIds
          });
        }}
      />
    </div>
  );
}
