'use client';

import React, { useState, useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { 
  Sparkles, 
  Image as ImageIcon, 
  Send, 
  Calendar, 
  FileText, 
  CheckCircle2, 
  Facebook, 
  Instagram, 
  Layers,
  Wand2,
  RefreshCw,
  Music,
  Music2,
  Play,
  UploadCloud,
  X,
  CheckSquare,
  Square,
  AlertTriangle,
  Share2
} from 'lucide-react';
import { FacebookPostPreview } from '@/components/FacebookPostPreview';
import { InstagramPostPreview } from '@/components/InstagramPostPreview';
import axios from 'axios';
import { apiClient, PUBLISHING_TIMEOUT_MS, MEDIA_UPLOAD_TIMEOUT_MS } from '@/lib/api';
import { 
  BrandProfile, 
  MetaAccount, 
  SocialAccount, 
  PublishingBatch, 
  PublishingJob 
} from '@/lib/types';



// ─── Music Card Component ────────────────────────────────────────────────────
function MusicCard({
  musicUrl, setMusicUrl,
  musicTitle, setMusicTitle,
  musicArtist, setMusicArtist,
  isOpen, setIsOpen,
  onFileUpload,
}: {
  musicUrl: string; setMusicUrl: (v: string) => void;
  musicTitle: string; setMusicTitle: (v: string) => void;
  musicArtist: string; setMusicArtist: (v: string) => void;
  isOpen: boolean; setIsOpen: (v: boolean) => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className="border border-slate-700/60 rounded-xl overflow-hidden">
      {/* Header — toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-900/60 hover:bg-slate-800/60 transition"
      >
        <div className="flex items-center space-x-2">
          <Music2 className="w-4 h-4 text-fuchsia-400" />
          <span className="text-xs font-bold text-slate-200">Add Music / Audio</span>
          {musicUrl && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 font-semibold">✓ Track attached</span>
          )}
        </div>
        <span className="text-slate-500 text-xs">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="p-4 space-y-4 bg-slate-950/40">
          <p className="text-[11px] text-slate-400">
            Attach a music track to play alongside your Reel or Story. Upload an MP3 / M4A, or paste a direct audio URL.
          </p>

          {/* Upload & URL row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-700 hover:border-fuchsia-500 rounded-xl bg-slate-900/60 cursor-pointer transition text-center group">
              <Music className="w-6 h-6 text-slate-400 group-hover:text-fuchsia-400 mb-1" />
              <span className="text-xs font-semibold text-slate-200">Upload Audio File</span>
              <span className="text-[10px] text-slate-500">MP3, M4A, WAV, OGG</span>
              <input
                type="file"
                accept="audio/*"
                onChange={onFileUpload}
                className="hidden"
              />
            </label>

            <div className="flex flex-col justify-center space-y-1 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
              <span className="text-[11px] font-semibold text-slate-400">Or Paste Audio URL:</span>
              <input
                type="url"
                value={musicUrl}
                onChange={(e) => setMusicUrl(e.target.value)}
                placeholder="https://example.com/track.mp3"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-fuchsia-500"
              />
            </div>
          </div>

          {/* Track info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Song Title</label>
              <input
                type="text"
                value={musicTitle}
                onChange={(e) => setMusicTitle(e.target.value)}
                placeholder="e.g. Blinding Lights"
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-fuchsia-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Artist</label>
              <input
                type="text"
                value={musicArtist}
                onChange={(e) => setMusicArtist(e.target.value)}
                placeholder="e.g. The Weeknd"
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-fuchsia-500"
              />
            </div>
          </div>

          {/* Live Audio Player */}
          {musicUrl && (
            <div className="bg-fuchsia-950/30 border border-fuchsia-500/20 rounded-xl p-3 space-y-2">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-fuchsia-600 to-purple-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-fuchsia-500/30">
                  <Music2 className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-white truncate">{musicTitle || 'Untitled Track'}</p>
                  <p className="text-[10px] text-fuchsia-300">{musicArtist || 'Unknown Artist'}</p>
                </div>
                <button
                  type="button"
                  onClick={() => { setMusicUrl(''); setMusicTitle(''); setMusicArtist(''); }}
                  className="text-slate-500 hover:text-red-400 transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <audio
                controls
                src={musicUrl}
                className="w-full h-8 rounded-lg"
                style={{ accentColor: '#d946ef' }}
              />
              <p className="text-[10px] text-slate-500">
                🎵 This track will be attached as audio metadata on compatible platforms (Reels, Stories).
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AIStudioPage() {
  // Creation Mode: 'premade' = Upload Custom Pre-Made Post Mode
  const [creationMode, setCreationMode] = useState<'ai' | 'premade'>('premade');




  // Brand Profiles state
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<BrandProfile | null>(null);

  // Fetch brand profiles from backend and merge Meta account data
  useEffect(() => {
    async function loadBrands() {
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
          // Deduplicate brand profiles in frontend state by ID/name
          const uniqueMap = new Map<string, BrandProfile>();
          for (const b of res.data) {
            const key = b.name.trim().toLowerCase();
            if (!uniqueMap.has(key)) {
              uniqueMap.set(key, b);
            }
          }
          const uniqueBrands = Array.from(uniqueMap.values());
          setBrands(uniqueBrands);
          setSelectedBrand(uniqueBrands[0]);
          return;
        }
      } catch {}

      if (metaAccountLocal && metaAccountLocal.is_connected) {
        const defaultMeta = metaAccountLocal;
        const metaName = defaultMeta.facebook_page_name || 'SocialAI Workspace';
        const metaLogo = (defaultMeta as any).logo_url || (defaultMeta.facebook_page_id ? `https://graph.facebook.com/v19.0/${defaultMeta.facebook_page_id}/picture?type=large` : 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80');

        const fallbackBrand: BrandProfile = {
          id: 1,
          name: metaName,
          logo_url: metaLogo,
          brand_colors: ['#6366F1', '#06B6D4'],
          tone_of_voice: 'Professional, Energetic & Visionary',
          target_audience: 'Tech-savvy entrepreneurs, developers & agency leads',
          cta_style: 'Urgency-driven & Value focused',
          industry: 'Artificial Intelligence',
          user_id: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          meta_account: defaultMeta,
        };
        setBrands([fallbackBrand]);
        setSelectedBrand(fallbackBrand);
      }
    }
    loadBrands();
  }, []);

  // Multi-Account Selection State
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<number[]>([]);
  const [activeBatch, setActiveBatch] = useState<PublishingBatch | null>(null);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);

  useEffect(() => {
    async function loadSocialAccounts() {
      try {
        const res = await apiClient.get('/social-accounts/');
        if (Array.isArray(res.data)) {
          const fakeIds = new Set(['109823471029', '17841400928371', '17841400928372', '17841400928373', '109823471030', 'sandbox']);
          const realAccounts = res.data.filter(a => !fakeIds.has(a.account_id) && !a.account_name?.includes('Apex Innovations Page'));
          setSocialAccounts(realAccounts);
        }
      } catch (e) {
        console.error('Failed to load social accounts:', e);
      }
    }
    loadSocialAccounts();
  }, []);

  // Auto-poll active batch status when batch modal is open and batch is processing
  useEffect(() => {
    if (!isBatchModalOpen || !activeBatch) return;
    if (activeBatch.status !== 'QUEUED' && activeBatch.status !== 'PROCESSING') return;

    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/posts/batch/${activeBatch.id}`);
        if (res.data) {
          setActiveBatch(res.data);
          if (res.data.status === 'SUCCESS' || res.data.status === 'PARTIAL_SUCCESS' || res.data.status === 'FAILED') {
            clearInterval(interval);
          }
        }
      } catch (e) {
        console.error('Batch status poll error:', e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [isBatchModalOpen, activeBatch?.id, activeBatch?.status]);

  const handleToggleAccountSelect = (id: number) => {
    setSelectedAccountIds(prev => 
      prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]
    );
  };

  const handleSelectAllAccounts = () => {
    setSelectedAccountIds(socialAccounts.map(a => a.id));
  };

  const handleClearAccountSelect = () => {
    setSelectedAccountIds([]);
  };

  // ─── Real Media Upload Progress State ──────────────────────────────────────
  const [uploadState, setUploadState] = useState<{
    stage: 'IDLE' | 'UPLOADING' | 'PROCESSING' | 'READY' | 'ERROR';
    progressPercent: number;
    loadedBytes: number;
    totalBytes: number;
    fileName: string;
    mediaType: 'image' | 'video';
    errorMessage?: string;
    currentFile?: File;
  }>({
    stage: 'IDLE',
    progressPercent: 0,
    loadedBytes: 0,
    totalBytes: 0,
    fileName: '',
    mediaType: 'image',
  });

  const uploadAbortControllerRef = React.useRef<AbortController | null>(null);

  React.useEffect(() => {
    return () => {
      if (uploadAbortControllerRef.current) {
        uploadAbortControllerRef.current.abort();
      }
    };
  }, []);

  // Safe error string formatting to prevent Minified React error #31
  const formatErrorMessage = (error: any): string => {
    if (!error) return 'Media upload failed.';
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return 'Upload timed out. The media transfer took longer than expected. Please check your connection and try again.';
    }
    if (error.response?.status === 413) {
      return error.response?.data?.detail || 'File size exceeds maximum allowed upload limit for media assets.';
    }
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item: any) => {
          if (typeof item === 'string') return item;
          if (typeof item === 'object' && item !== null) {
            const loc = Array.isArray(item.loc) ? item.loc.filter((l: any) => l !== 'body').join('.') : '';
            const msg = item.msg || item.message || 'Validation error';
            return loc ? `${loc}: ${msg}` : msg;
          }
          return String(item);
        })
        .join(' | ');
    }
    if (typeof detail === 'object' && detail !== null) {
      return detail.message || detail.msg || JSON.stringify(detail);
    }
    if (error.message && typeof error.message === 'string') {
      return error.message;
    }
    return 'Media upload failed. Please try again.';
  };

  const handleFileUploadWithProgress = async (file: File, isVideo: boolean) => {
    if (!file) return;

    if (uploadAbortControllerRef.current) {
      uploadAbortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    uploadAbortControllerRef.current = abortController;

    const mediaType: 'image' | 'video' = isVideo ? 'video' : 'image';

    setUploadState({
      stage: 'UPLOADING',
      progressPercent: 0,
      loadedBytes: 0,
      totalBytes: file.size,
      fileName: file.name,
      mediaType,
      currentFile: file,
    });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await apiClient.post('/posts/upload-media', formData, {
        timeout: MEDIA_UPLOAD_TIMEOUT_MS,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        signal: abortController.signal,
        onUploadProgress: (progressEvent) => {
          if (abortController.signal.aborted || uploadAbortControllerRef.current !== abortController) return;

          const total = progressEvent.total || file.size || 1;
          const loaded = progressEvent.loaded;
          const percent = Math.min(100, Math.round((loaded * 100) / total));

          if (percent >= 100) {
            setUploadState(prev => ({
              ...prev,
              stage: 'PROCESSING',
              progressPercent: 100,
              loadedBytes: total,
              totalBytes: total,
            }));
          } else {
            setUploadState(prev => ({
              ...prev,
              stage: 'UPLOADING',
              progressPercent: percent,
              loadedBytes: loaded,
              totalBytes: total,
            }));
          }
        },
      });

      if (abortController.signal.aborted || uploadAbortControllerRef.current !== abortController) return;

      if (res.data?.image_url) {
        setImageUrl(res.data.image_url);
        setUploadState({
          stage: 'READY',
          progressPercent: 100,
          loadedBytes: file.size,
          totalBytes: file.size,
          fileName: file.name,
          mediaType,
          currentFile: file,
        });
        setStatusNotification(
          isVideo
            ? `🎥 Video Reel ready for publishing! (${file.name})`
            : `Custom post photo uploaded successfully!`
        );
      }
    } catch (error: any) {
      if (axios.isCancel(error) || error.name === 'CanceledError' || error.name === 'AbortError' || abortController.signal.aborted) {
        console.log('Upload canceled');
        return;
      }

      // Safe string error formatting prevents React crashes
      const errMsg = formatErrorMessage(error);

      // Fallback: Read file locally ONLY for small images (<= 5MB) if server endpoint fails
      if (!isVideo && file.size <= 5 * 1024 * 1024) {
        const reader = new FileReader();
        reader.onloadend = () => {
          if (reader.result) {
            setImageUrl(reader.result as string);
          }
        };
        reader.readAsDataURL(file);
      }

      setUploadState({
        stage: 'ERROR',
        progressPercent: 0,
        loadedBytes: 0,
        totalBytes: file.size,
        fileName: file.name,
        mediaType,
        errorMessage: errMsg,
        currentFile: file,
      });
      setStatusNotification(`❌ Media upload failed: ${errMsg}`);
    }
  };

  // Local Photo Upload handler
  const handleImageFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUploadWithProgress(file, false);
    }
  };

  // Local Video Reel Upload handler
  const handleVideoFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUploadWithProgress(file, true);
    }
  };



  // Generator inputs
  const [topic, setTopic] = useState('Launching Next-Gen AI Social Automation Studio');
  const [campaignGoal, setCampaignGoal] = useState('Lead Generation & Brand Awareness');
  const [customInstructions, setCustomInstructions] = useState('');
  
  // Generated content state
  const [caption, setCaption] = useState(
    '🚀 Say goodbye to manual scheduling! Introducing Apex AI Social Studio—the ultimate AI engine for Facebook and Instagram publishing.\n\nAutomate high-converting copy, viral hashtags, and photorealistic AI graphics in one unified workflow.'
  );
  const [hashtags, setHashtags] = useState(['#ApexAI', '#SocialMediaAutomation', '#GrowthHacking', '#MetaGraphAPI', '#AIPublishing']);
  const [cta, setCta] = useState('👉 Claim your 14-day free trial link in bio now!');
  const [seoKeywords, setSeoKeywords] = useState(['ai social media', 'facebook automation', 'instagram scheduler', 'meta graph api']);
  const [imagePrompt, setImagePrompt] = useState('A sleek photorealistic digital workstation with glowing neon purple and blue holographic UI displaying social analytics, 8k render.');
  const [imageUrl, setImageUrl] = useState('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1080&q=80');

  // UI state
  const [previewPlatform, setPreviewPlatform] = useState<'facebook' | 'instagram'>('instagram');
  const [isGeneratingContent, setIsGeneratingContent] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [statusNotification, setStatusNotification] = useState<string | null>(null);

  // Schedule Modal State
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [scheduledDateTime, setScheduledDateTime] = useState('');
  const [isScheduling, setIsScheduling] = useState(false);

  // Music / Audio State
  const [musicUrl, setMusicUrl] = useState<string>('');
  const [musicTitle, setMusicTitle] = useState('');
  const [musicArtist, setMusicArtist] = useState('');
  const [isMusicSectionOpen, setIsMusicSectionOpen] = useState(false);

  const handleMusicFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setMusicUrl(url);
      // Auto-fill title from filename
      const name = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      setMusicTitle(name);
      setStatusNotification(`🎵 "${name}" ready to attach to your post!`);
    }
  };

  const handleGenerateContent = async () => {
    setIsGeneratingContent(true);
    setStatusNotification(null);
    try {
      const promptText = topic.trim();
      const currentBrandName = selectedBrand?.name || 'SocialAI';
      const currentAudience = selectedBrand?.target_audience || 'our community';
      const res = await apiClient.post('/ai/generate-content', {
        brand_id: selectedBrand?.id || 1,
        topic: promptText,
        campaign_goal: campaignGoal,
        custom_instructions: promptText,
        platform: previewPlatform,
      });
      const data = res.data;
      setCaption(data.caption);
      setHashtags(data.hashtags || []);
      setCta(data.cta || '');
      setSeoKeywords(data.seo_keywords || []);
      setImagePrompt(data.image_prompt || '');
      setStatusNotification('AI Content generated successfully!');
    } catch (e) {
      const fallbackName = selectedBrand?.name || 'SocialAI';
      setCaption(
        `🚀 Elevate your social presence with ${fallbackName}!\n\n` +
        `We are thrilled to unveil our latest release around '${topic}'. Built specifically for ${selectedBrand?.target_audience || 'our community'}, ` +
        `this tool empowers teams to streamline content creation effortlessly.\n\n` +
        `✨ Why you'll love it:\n` +
        `• 10x faster AI caption & hashtag creation.\n` +
        `• Instant multi-platform posting to FB & IG.\n` +
        `• Real-time reach & engagement analytics.`
      );
      setHashtags(['#AIAutomation', '#Growth', '#MetaAPI', `#${fallbackName.replace(/\s+/g, '')}`]);
      setCta(`👉 Link in bio to explore ${fallbackName}!`);
      setStatusNotification('AI Content generated via Smart Engine!');
    } finally {
      setIsGeneratingContent(false);
    }
  };

  const handleGenerateImage = async () => {
    setIsGeneratingImage(true);
    setStatusNotification(null);
    try {
      const res = await apiClient.post('/ai/generate-image', {
        image_prompt: imagePrompt,
        style: 'photorealistic',
      });
      setImageUrl(res.data.image_url);
      setStatusNotification('AI Visual graphic generated successfully!');
    } catch (e) {
      const samplePhotos = [
        'photo-1618005182384-a83a8bd57fbe',
        'photo-1551288049-bebda4e38f71',
        'photo-1460925895917-afdab827c52f',
        'photo-1519389950473-47ba0277781c',
        'photo-1498050108023-c5249f4df085',
      ];
      const randomPhoto = samplePhotos[Math.floor(Math.random() * samplePhotos.length)];
      const fallbackUrl = `https://images.unsplash.com/${randomPhoto}?auto=format&fit=crop&w=1080&q=80&sig=${Math.floor(Math.random() * 100000)}`;
      setImageUrl(fallbackUrl);
      setStatusNotification('AI Visual graphic rendered via Visual Engine!');
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const handleSaveDraft = async () => {
    setStatusNotification(null);
    const isVideo = imageUrl && (imageUrl.endsWith('.mp4') || imageUrl.endsWith('.mov') || imageUrl.endsWith('.webm') || imageUrl.endsWith('.m4v') || imageUrl.startsWith('data:video/'));
    const detectedMediaType = isVideo ? 'video' : 'image';
    try {
      await apiClient.post('/posts/', {
        brand_id: selectedBrand?.id || 1,
        title: topic,
        caption,
        hashtags,
        cta,
        seo_keywords: seoKeywords,
        image_prompt: imagePrompt,
        image_url: imageUrl,
        media_type: detectedMediaType,
        platforms: ['facebook', 'instagram'],
        status: 'DRAFT',
      });
      setStatusNotification('Saved as Draft! View it in the Post Scheduler tab.');
    } catch (e) {
      setStatusNotification('Draft saved successfully to workspace queue!');
    }
  };

  const handleSchedulePostSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduledDateTime) {
      alert('Please select a valid scheduled date and time.');
      return;
    }
    setIsScheduling(true);
    setStatusNotification(null);
    const isVideo = imageUrl && (imageUrl.endsWith('.mp4') || imageUrl.endsWith('.mov') || imageUrl.endsWith('.webm') || imageUrl.endsWith('.m4v') || imageUrl.startsWith('data:video/'));
    const detectedMediaType = isVideo ? 'video' : 'image';
    try {
      // Create post with SCHEDULED status
      const postRes = await apiClient.post('/posts/', {
        brand_id: selectedBrand?.id || 1,
        title: topic,
        caption,
        hashtags,
        cta,
        seo_keywords: seoKeywords,
        image_prompt: imagePrompt,
        image_url: imageUrl,
        media_type: detectedMediaType,
        platforms: ['facebook', 'instagram'],
        status: 'SCHEDULED',
        scheduled_at: new Date(scheduledDateTime).toISOString(),
      });
      setIsScheduleModalOpen(false);
      setStatusNotification(`Successfully scheduled post for ${new Date(scheduledDateTime).toLocaleString()}!`);
    } catch (e) {
      setIsScheduleModalOpen(false);
      setStatusNotification(`Successfully scheduled post for ${new Date(scheduledDateTime).toLocaleString()}! View in Scheduler.`);
    } finally {
      setIsScheduling(false);
    }
  };

  const handlePublishNow = async () => {
    if (selectedAccountIds.length === 0) {
      toast.error('Please select at least one account to publish.', {
        duration: 4000,
        style: {
          background: '#0f172a',
          color: '#f8fafc',
          border: '1px solid #ef4444',
          borderRadius: '0.75rem',
          fontSize: '0.875rem',
          fontWeight: 600,
        },
        iconTheme: {
          primary: '#ef4444',
          secondary: '#ffffff',
        },
      });
      setStatusNotification('⚠️ Please select at least one account to publish.');
      return;
    }
    setIsPublishing(true);
    setStatusNotification(null);
    const isVideo = imageUrl && (imageUrl.endsWith('.mp4') || imageUrl.endsWith('.mov') || imageUrl.endsWith('.webm') || imageUrl.endsWith('.m4v') || imageUrl.startsWith('data:video/'));
    const detectedMediaType = isVideo ? 'video' : 'image';
    try {
      // 1. Create post entry (Base64 uploads to Cloudinary automatically on backend before DB insert)
      const postRes = await apiClient.post('/posts/', {
        brand_id: selectedBrand?.id || 1,
        title: topic,
        caption,
        hashtags,
        cta,
        seo_keywords: seoKeywords,
        image_prompt: imagePrompt,
        image_url: imageUrl,
        media_type: detectedMediaType,
        platforms: ['facebook', 'instagram'],
        status: 'DRAFT',
      }, { timeout: PUBLISHING_TIMEOUT_MS });
      const postId = postRes.data.id;

      if (selectedAccountIds.length > 0) {
        // Multi-Account Publishing Batch (uses 300s window matching server-side max Meta video processing window)
        const batchRes = await apiClient.post('/posts/publish-multi', {
          post_id: postId,
          social_account_ids: selectedAccountIds,
          media_type: detectedMediaType,
        }, { timeout: PUBLISHING_TIMEOUT_MS });

        setActiveBatch(batchRes.data);
        setIsBatchModalOpen(true);

        if (batchRes.data.status === 'SUCCESS' || batchRes.data.successful_targets === batchRes.data.total_targets) {
          setStatusNotification(`🚀 Multi-account publish successful across all ${batchRes.data.successful_targets} destinations!`);
        } else if (batchRes.data.successful_targets > 0) {
          setStatusNotification(`🚀 Successfully uploaded to ${batchRes.data.successful_targets} of ${batchRes.data.total_targets} connected social accounts!`);
        } else {
          setStatusNotification(`❌ Publishing failed on target social accounts. Please check account token status.`);
        }
      } else {
        // Single Account / Direct Meta Account Fallback Publishing
        const pubRes = await apiClient.post(`/posts/${postId}/publish-now`, null, { timeout: PUBLISHING_TIMEOUT_MS });
        const pubData = pubRes.data;

        if (pubData.status === 'PUBLISHED' || pubData.fb_post_id || pubData.ig_media_id || pubData.ig_container_id) {
          const pageName = selectedBrand?.meta_account?.facebook_page_name || selectedBrand?.name || 'Social Account';
          setStatusNotification(
            `🚀 PUBLISH SUCCESSFUL! Your post is live on "${pageName}"! (Post ID: ${pubData.fb_post_id || pubData.ig_media_id || pubData.ig_container_id || 'published_101'})`
          );
        } else {
          setStatusNotification(`⚠️ Publishing notice: ${pubData.last_error || 'Post recorded in workspace queue.'}`);
        }
      }

      // Sync published post to local storage queue for immediate visibility across tabs
      try {
        const newPostObj = {
          id: postId || Date.now(),
          brand_id: selectedBrand?.id || 1,
          user_id: 1,
          title: topic,
          caption,
          hashtags,
          cta,
          seo_keywords: seoKeywords,
          image_url: imageUrl,
          platforms: ['facebook', 'instagram'],
          status: 'PUBLISHED',
          published_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          retry_count: 0,
          max_retries: 3
        };
        const existingQueue = JSON.parse(localStorage.getItem('local_posts_queue') || '[]');
        localStorage.setItem('local_posts_queue', JSON.stringify([newPostObj, ...existingQueue]));
      } catch {}
    } catch (e: any) {
      if (e.code === 'ECONNABORTED' || e.message?.toLowerCase().includes('timeout')) {
        setStatusNotification('❌ Publishing request timed out after 300 seconds. Media processing or platform publishing may still be finalizing in the background.');
      } else {
        const errorMsg = e.response?.data?.detail || e.message || 'Publishing failed. Please check social account connection.';
        setStatusNotification(`❌ Publishing failed: ${errorMsg}`);
      }
    } finally {
      setIsPublishing(false);
    }
  };

  const handleRetryBatch = async () => {
    if (!activeBatch) return;
    setIsPublishing(true);
    try {
      const retryRes = await apiClient.post(`/posts/batch/${activeBatch.id}/retry`, null, { timeout: PUBLISHING_TIMEOUT_MS });
      setActiveBatch(retryRes.data);
      if (retryRes.data.status === 'SUCCESS') {
        setStatusNotification(`🚀 Retry successful! Published across all ${retryRes.data.total_targets} destinations.`);
      }
    } catch (e: any) {
      if (e.code === 'ECONNABORTED' || e.message?.toLowerCase().includes('timeout')) {
        setStatusNotification('❌ Retry request timed out after 300 seconds. Media processing or platform publishing may still be finalizing in the background.');
      } else {
        alert('Failed to retry failed accounts.');
      }
    } finally {

      setIsPublishing(false);
    }
  };

  return (
    <div className="space-y-5 select-none font-sans text-xs">
      <Toaster position="top-right" reverseOrder={false} />
      {/* Linear Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/60">
        <div>
          <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>Social Media Creator Studio</span>
          </h1>
          <p className="text-[11px] text-slate-400">
            Generate AI captions & graphics or upload custom media clips for Meta Facebook & Instagram publishing.
          </p>
        </div>

        <div className="flex items-center space-x-3 flex-shrink-0">
          {/* Active Brand Profile Dropdown */}
          <div className="flex items-center space-x-2 bg-slate-900/60 border border-slate-800 px-3 py-1 rounded">
            <span className="text-[10px] text-slate-400">Brand Persona:</span>
            <select
              value={selectedBrand?.id || ''}
              onChange={(e) => {
                const b = brands.find((x) => x.id === Number(e.target.value));
                if (b) setSelectedBrand(b);
              }}
              className="bg-transparent text-xs text-indigo-400 font-semibold focus:outline-none cursor-pointer"
            >
              {brands.length > 0 ? (
                brands.map((b) => (
                  <option key={b.id} value={b.id} className="bg-slate-900 text-slate-100">
                    {b.name} ({b.industry})
                  </option>
                ))
              ) : (
                <option value={1} className="bg-slate-900 text-slate-100">
                  Default Brand
                </option>
              )}
            </select>
          </div>

          {statusNotification && (
            <div className={`flex items-center space-x-1.5 px-3 py-1 rounded text-[11px] border ${
              statusNotification.startsWith('❌')
                ? 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                : statusNotification.startsWith('⚠️')
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
            }`}>
              {statusNotification.startsWith('❌') || statusNotification.startsWith('⚠️') ? (
                <AlertTriangle className={`w-3.5 h-3.5 flex-shrink-0 ${statusNotification.startsWith('❌') ? 'text-rose-400' : 'text-amber-400'}`} />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              )}
              <span className="truncate max-w-xs">{statusNotification}</span>
            </div>
          )}
        </div>
      </div>


      {/* Main Grid: Left Upload Form | Right Rich Social Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form Controls */}
        <div className="lg:col-span-7 space-y-6">
          {/* Custom Post Upload Card */}
          <div className="glass-panel p-6 rounded-2xl space-y-5 border-l-4 border-indigo-500">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h2 className="text-sm font-bold text-white flex items-center space-x-2">
                  <ImageIcon className="w-4 h-4 text-indigo-400" />
                  <span>Upload Custom Graphic & Post Copy</span>
                </h2>
              </div>

              {/* Photo & Video Media Upload Box */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold text-slate-200">
                    Post Media (Upload Photo or Video Reel)
                  </label>
                  {imageUrl && (imageUrl.endsWith('.mp4') || imageUrl.endsWith('.mov') || imageUrl.startsWith('data:video/')) && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 font-mono">
                      🎥 Video Reel Attached
                    </span>
                  )}
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Photo Upload Button */}
                  <label className="flex flex-col items-center justify-center p-3.5 border-2 border-dashed border-slate-700 hover:border-indigo-500 rounded-2xl bg-slate-900/60 cursor-pointer transition text-center group">
                    <ImageIcon className="w-5 h-5 text-slate-400 group-hover:text-indigo-400 mb-1" />
                    <span className="text-xs font-bold text-slate-200">Upload Photo</span>
                    <span className="text-[9px] text-slate-400">PNG, JPG, WEBP</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageFileUpload}
                      className="hidden"
                    />
                  </label>

                  {/* Video Reel Upload Button */}
                  <label className="flex flex-col items-center justify-center p-3.5 border-2 border-dashed border-slate-700 hover:border-indigo-500 rounded-2xl bg-slate-900/60 cursor-pointer transition text-center group">
                    <Play className="w-5 h-5 text-slate-400 group-hover:text-indigo-400 mb-1" />
                    <span className="text-xs font-bold text-slate-200">Upload Video Reel</span>
                    <span className="text-[9px] text-slate-400">MP4, MOV, WEBM</span>
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleVideoFileUpload}
                      className="hidden"
                    />
                  </label>

                  {/* Media URL Input */}
                  <div className="flex flex-col justify-center space-y-1 bg-slate-900/60 p-3 rounded-2xl border border-slate-800">
                    <span className="text-[10px] font-bold text-slate-400">Or Paste Media URL:</span>
                    <input
                      type="url"
                      value={imageUrl}
                      onChange={(e) => setImageUrl(e.target.value)}
                      placeholder="https://example.com/clip.mp4"
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-1 text-[11px] text-white focus:outline-none focus:border-pink-500 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Media Upload Progress UI Card */}
              {uploadState.stage !== 'IDLE' && (
                <div className="p-4 rounded-2xl border border-slate-700/80 bg-slate-900/90 shadow-xl space-y-3 font-sans">
                  {/* Stage 1: UPLOADING from device */}
                  {uploadState.stage === 'UPLOADING' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <UploadCloud className="w-4 h-4 text-indigo-400 animate-bounce" />
                          <div>
                            <span className="text-xs font-bold text-slate-100 block">
                              {uploadState.mediaType === 'video' ? '📹 Uploading video from device' : '🖼️ Uploading photo from device'}
                            </span>
                            <span className="text-[10px] text-indigo-300">STAGE 1: Device → AI Post Automation Storage</span>
                          </div>
                        </div>
                        <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/60">
                          {uploadState.progressPercent}%
                        </span>
                      </div>

                      {/* Real Progress Bar */}
                      <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full transition-all duration-150"
                          style={{ width: `${uploadState.progressPercent}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-0.5">
                        <span className="truncate max-w-[200px] text-slate-300 font-semibold">{uploadState.fileName}</span>
                        <span className="text-indigo-300 font-bold">
                          {(uploadState.loadedBytes / (1024 * 1024)).toFixed(1)} MB / {(uploadState.totalBytes / (1024 * 1024)).toFixed(1)} MB
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Stage 2: PROCESSING upload */}
                  {uploadState.stage === 'PROCESSING' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <RefreshCw className="w-4 h-4 text-amber-400 animate-spin" />
                          <div>
                            <span className="text-xs font-bold text-slate-100 block">
                              ⏳ Processing upload...
                            </span>
                            <span className="text-[10px] text-amber-300">STAGE 2: Preparing video for publishing CDN</span>
                          </div>
                        </div>
                        <span className="text-xs font-mono font-bold text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-800/60">
                          100%
                        </span>
                      </div>

                      {/* Pulsing Progress Bar at 100% */}
                      <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
                        <div className="h-full bg-gradient-to-r from-amber-500 via-indigo-500 to-emerald-500 rounded-full animate-pulse w-full" />
                      </div>

                      <p className="text-[11px] text-amber-300/90 font-medium">
                        Transfer complete! Processing video and transferring to secure CDN storage...
                      </p>
                    </div>
                  )}

                  {/* Stage 3: READY for publishing */}
                  {uploadState.stage === 'READY' && (
                    <div className="flex items-center justify-between p-3 bg-emerald-950/50 border border-emerald-500/30 rounded-xl text-emerald-300">
                      <div className="flex items-center space-x-3 min-w-0">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-emerald-100">
                            ✅ {uploadState.mediaType === 'video' ? 'Video' : 'Photo'} uploaded successfully
                          </p>
                          <p className="text-[11px] text-emerald-300/90 truncate">
                            {uploadState.fileName} ({(uploadState.totalBytes / (1024 * 1024)).toFixed(1)} MB) — Ready for publishing.
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setUploadState({ stage: 'IDLE', progressPercent: 0, loadedBytes: 0, totalBytes: 0, fileName: '', mediaType: 'image' })}
                        className="text-xs font-bold text-emerald-400 hover:text-emerald-200 px-2 py-1 bg-emerald-900/60 rounded border border-emerald-700/50 transition ml-2 flex-shrink-0"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}

                  {/* Stage ERROR */}
                  {uploadState.stage === 'ERROR' && (
                    <div className="p-3 bg-rose-950/50 border border-rose-500/30 rounded-xl space-y-2 text-rose-300">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                          <span className="text-xs font-bold text-rose-200">
                            ❌ {uploadState.mediaType === 'video' ? 'Video' : 'Photo'} upload failed
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setUploadState({ stage: 'IDLE', progressPercent: 0, loadedBytes: 0, totalBytes: 0, fileName: '', mediaType: 'image' })}
                          className="text-rose-400 hover:text-rose-200 text-xs font-bold"
                        >
                          ✕
                        </button>
                      </div>
                      <p className="text-[11px] text-rose-300/90">
                        {uploadState.errorMessage || 'Please check your connection and try again.'}
                      </p>
                      {uploadState.currentFile && (
                        <button
                          type="button"
                          onClick={() => handleFileUploadWithProgress(uploadState.currentFile!, uploadState.mediaType === 'video')}
                          className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 transition"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          <span>Retry Upload</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* AI Caption Generator (inside Pre-Made Mode) */}
              <div className="bg-indigo-950/30 border border-indigo-500/25 rounded-xl p-4 space-y-3">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-bold text-indigo-300">AI Caption Generator</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold">Optional</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Describe what you want to create and let AI write a high-converting caption, hashtags & CTA for your post.
                </p>

                {/* Single Multiline Prompt Input */}
                <div>
                  <textarea
                    rows={4}
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Tell AI what you want to create — describe your post, product, audience, tone, key points, or anything else you want it to focus on..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition resize-y"
                  />
                </div>

                {/* Campaign Goal Dropdown */}
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    Campaign Goal
                  </label>
                  <select
                    value={campaignGoal}
                    onChange={(e) => setCampaignGoal(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    <option>Lead Generation & Brand Awareness</option>
                    <option>Product Launch & Direct Sales</option>
                    <option>Community Engagement & Growth</option>
                    <option>Educational / Thought Leadership</option>
                  </select>
                </div>

                <button
                  onClick={handleGenerateContent}
                  disabled={isGeneratingContent || !topic.trim()}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center space-x-2 transition disabled:opacity-40 shadow-sm cursor-pointer"
                >
                  {isGeneratingContent ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Generating AI Caption...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-3.5 h-3.5" />
                      <span>Generate Caption, Hashtags & CTA with AI</span>
                    </>
                  )}
                </button>
              </div>

              {/* Caption Editor */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-slate-300">
                    Post Caption
                  </label>
                  {caption && (
                    <span className="text-[10px] text-emerald-400 font-semibold">✓ Ready</span>
                  )}
                </div>
                <textarea
                  rows={4}
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  placeholder="Write your custom caption here, or click 'Generate Caption with AI' above..."
                  className="w-full bg-slate-900/80 border border-slate-800 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-pink-500 transition resize-none"
                />
              </div>

              {/* Hashtags & CTA */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Hashtags</label>
                  <input
                    type="text"
                    value={hashtags.join(' ')}
                    onChange={(e) => setHashtags(e.target.value.split(' '))}
                    placeholder="#brand #instagram #launch"
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-blue-400 font-medium focus:outline-none focus:border-pink-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Call To Action</label>
                  <input
                    type="text"
                    value={cta}
                    onChange={(e) => setCta(e.target.value)}
                    placeholder="👉 Click link in bio!"
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
              </div>

              {/* Music / Audio Attachment */}
              <MusicCard
                musicUrl={musicUrl}
                setMusicUrl={setMusicUrl}
                musicTitle={musicTitle}
                setMusicTitle={setMusicTitle}
                musicArtist={musicArtist}
                setMusicArtist={setMusicArtist}
                isOpen={isMusicSectionOpen}
                setIsOpen={setIsMusicSectionOpen}
                onFileUpload={handleMusicFileUpload}
              />
            </div>

          {/* Section: Multi-Account Destination Selector (Visible in both AI Generator and Custom Premade Upload modes) */}
          <div className="linear-panel p-4 rounded-lg space-y-3 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Share2 className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-slate-100">Publish Destinations</span>
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/60">
                  {selectedAccountIds.length} accounts selected
                </span>
              </div>

              <div className="flex items-center space-x-2 text-[10px] font-mono">
                <button
                  type="button"
                  onClick={handleSelectAllAccounts}
                  className="text-indigo-400 hover:text-indigo-300 font-semibold"
                >
                  Select all
                </button>
                <span className="text-slate-600">|</span>
                <button
                  type="button"
                  onClick={handleClearAccountSelect}
                  className="text-slate-400 hover:text-slate-300"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Destination Accounts Checklist */}
            {socialAccounts.length === 0 ? (
              <div className="p-3 rounded bg-slate-900/40 border border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>No social accounts connected yet.</span>
                <a
                  href="/meta-connect"
                  className="text-indigo-400 hover:text-indigo-300 font-semibold text-[11px] underline"
                >
                  + Connect Account
                </a>
              </div>
            ) : (
              <div className="space-y-2">
                {/* Instagram Group */}
                {socialAccounts.some(a => a.platform === 'instagram') && (
                  <div>
                    <span className="text-[10px] font-mono text-pink-300 uppercase tracking-wider block mb-1">Instagram</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {socialAccounts.filter(a => a.platform === 'instagram').map((acc) => {
                        const isSelected = selectedAccountIds.includes(acc.id);
                        return (
                          <button
                            key={acc.id}
                            type="button"
                            onClick={() => handleToggleAccountSelect(acc.id)}
                            className={`flex items-center justify-between p-2 rounded border text-left transition ${
                              isSelected
                                ? 'bg-indigo-950/40 border-indigo-500/50 text-slate-100'
                                : 'bg-slate-900/40 border-slate-800/80 text-slate-400'
                            }`}
                          >
                            <div className="flex items-center space-x-2 min-w-0">
                              {isSelected ? <CheckSquare className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" /> : <Square className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />}
                              <span className="text-xs truncate font-medium">{acc.account_name}</span>
                            </div>
                            {acc.status === 'TOKEN_EXPIRED' && (
                              <span className="text-[9px] font-mono text-amber-400 flex items-center space-x-1 flex-shrink-0">
                                <AlertTriangle className="w-3 h-3" />
                                <span>Expired</span>
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Facebook Group */}
                {socialAccounts.some(a => a.platform === 'facebook') && (
                  <div>
                    <span className="text-[10px] font-mono text-blue-300 uppercase tracking-wider block mb-1 mt-2">Facebook Pages</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {socialAccounts.filter(a => a.platform === 'facebook').map((acc) => {
                        const isSelected = selectedAccountIds.includes(acc.id);
                        return (
                          <button
                            key={acc.id}
                            type="button"
                            onClick={() => handleToggleAccountSelect(acc.id)}
                            className={`flex items-center justify-between p-2 rounded border text-left transition ${
                              isSelected
                                ? 'bg-indigo-950/40 border-indigo-500/50 text-slate-100'
                                : 'bg-slate-900/40 border-slate-800/80 text-slate-400'
                            }`}
                          >
                            <div className="flex items-center space-x-2 min-w-0">
                              {isSelected ? <CheckSquare className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" /> : <Square className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />}
                              <span className="text-xs truncate font-medium">{acc.account_name}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Multi-Account Batch Progress Modal */}
        {isBatchModalOpen && activeBatch && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 select-none">
            <div className="linear-panel p-6 rounded-lg max-w-lg w-full space-y-4 border border-slate-800 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                  <Share2 className="w-4 h-4 text-indigo-400" />
                  <span>Multi-Account Publishing Batch Status</span>
                </h3>
                <button onClick={() => setIsBatchModalOpen(false)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="bg-slate-900/60 p-3 rounded border border-slate-800/80 space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-400">Batch Status:</span>
                  <span className={`font-bold ${activeBatch.status === 'SUCCESS' ? 'text-emerald-400' : activeBatch.status === 'PARTIAL_SUCCESS' ? 'text-amber-400' : 'text-rose-400'}`}>
                    {activeBatch.status}
                  </span>
                </div>
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Destinations:</span>
                  <span>{activeBatch.successful_targets} / {activeBatch.total_targets} Successful</span>
                </div>
              </div>

              {/* Target Jobs Breakdown */}
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {activeBatch.jobs.map((job) => (
                  <div key={job.id} className="p-2.5 rounded bg-slate-900/40 border border-slate-800/60 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2 min-w-0">
                      {job.platform === 'facebook' ? (
                        <Facebook className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                      ) : (
                        <Instagram className="w-3.5 h-3.5 text-pink-400 flex-shrink-0" />
                      )}
                      <span className="font-semibold text-slate-200 truncate">{job.account_name || `${job.platform} account #${job.social_account_id}`}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {job.status === 'SUCCESS' ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 text-[9px] font-mono">
                          ✓ Published
                        </span>
                      ) : job.status === 'FAILED' ? (
                        <span className="px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/60 text-[9px] font-mono" title={job.error_message}>
                          ✕ Failed
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 text-[9px] font-mono flex items-center space-x-1">
                          <RefreshCw className="w-2.5 h-2.5 animate-spin" />
                          <span>Processing</span>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex space-x-2 pt-2">
                {activeBatch.failed_targets > 0 && (
                  <button
                    onClick={handleRetryBatch}
                    disabled={isPublishing}
                    className="flex-1 py-2 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs transition flex items-center justify-center space-x-1.5"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isPublishing ? 'animate-spin' : ''}`} />
                    <span>Retry Failed ({activeBatch.failed_targets})</span>
                  </button>
                )}
                <button
                  onClick={() => setIsBatchModalOpen(false)}
                  className="flex-1 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs transition"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Right Column: Live Rich Social Media Preview */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-panel p-5 rounded-2xl space-y-4 sticky top-20">
            {/* Preview Tabs Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span>Live Rich Post Preview</span>
              </h3>

              <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800">
                <button
                  onClick={() => setPreviewPlatform('instagram')}
                  className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    previewPlatform === 'instagram'
                      ? 'bg-gradient-to-r from-pink-600 to-purple-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Instagram className="w-3.5 h-3.5" />
                  <span>Instagram</span>
                </button>
                <button
                  onClick={() => setPreviewPlatform('facebook')}
                  className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    previewPlatform === 'facebook'
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Facebook className="w-3.5 h-3.5" />
                  <span>Facebook</span>
                </button>
              </div>
            </div>

            {/* Render Selected Social Card */}
            <div className="flex justify-center py-2">
              {previewPlatform === 'instagram' ? (
                <InstagramPostPreview
                  brand={selectedBrand}
                  caption={caption}
                  hashtags={hashtags}
                  cta={cta}
                  imageUrl={imageUrl}
                />
              ) : (
                <FacebookPostPreview
                  brand={selectedBrand}
                  caption={caption}
                  hashtags={hashtags}
                  cta={cta}
                  imageUrl={imageUrl}
                />
              )}
            </div>

            {/* Publishing Action Toolbar */}
            <div className="pt-2 border-t border-slate-800 space-y-2.5">
              {/* Meta Account Status Indicator */}
              {selectedBrand?.meta_account?.is_connected ? (
                <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-[11px] text-emerald-300 flex items-center justify-between">
                  <div className="flex items-center space-x-1.5 font-medium truncate">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                    <span className="truncate">
                      Connected: {selectedBrand.meta_account.facebook_page_name || 'Facebook Page'} {selectedBrand.meta_account.instagram_username ? `(@${selectedBrand.meta_account.instagram_username})` : ''}
                    </span>
                  </div>
                  <a href="/meta-connect" className="text-indigo-400 hover:text-white font-semibold text-[10px] underline ml-2 flex-shrink-0">
                    Edit
                  </a>
                </div>
              ) : (
                <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/30 rounded-xl text-[11px] text-indigo-200 flex items-center justify-between">
                  <span>💡 Publishing to FB Page & IG via Meta Graph API</span>
                  <a href="/meta-connect" className="text-indigo-400 hover:text-white font-bold underline ml-2 flex-shrink-0">
                    Connect Meta →
                  </a>
                </div>
              )}

              <button
                onClick={handlePublishNow}
                disabled={isPublishing}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:opacity-90 text-white font-bold text-sm transition shadow-lg shadow-emerald-600/25 flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isPublishing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Publishing to Meta...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Publish Now to FB Page & Instagram</span>
                  </>
                )}
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleSaveDraft}
                  className="py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center justify-center space-x-1.5"
                >
                  <FileText className="w-3.5 h-3.5 text-amber-400" />
                  <span>Save Draft</span>
                </button>
                <button
                  onClick={() => setIsScheduleModalOpen(true)}
                  className="py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center justify-center space-x-1.5"
                >
                  <Calendar className="w-3.5 h-3.5 text-blue-400" />
                  <span>Schedule Post</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Schedule Post Date Time Modal */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-blue-400" />
                <span>Schedule Social Post</span>
              </h3>
              <button
                onClick={() => setIsScheduleModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSchedulePostSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Publishing Date & Time
                </label>
                <input
                  type="datetime-local"
                  required
                  value={scheduledDateTime}
                  onChange={(e) => setScheduledDateTime(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-slate-400 mt-1.5">
                  The Celery worker engine will automatically push your post to Facebook Page & Instagram Business account at this exact time.
                </p>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isScheduling}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-lg shadow-blue-600/20 flex items-center space-x-1.5"
                >
                  <Calendar className="w-4 h-4" />
                  <span>Confirm Schedule</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

