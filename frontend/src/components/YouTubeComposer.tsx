'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Youtube,
  UploadCloud,
  FileVideo,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Check,
  RefreshCw,
  Pause,
  Play,
  Trash2,
  ExternalLink,
  Film,
  Sparkles,
  Zap,
  Layers,
  Globe,
  Lock,
  EyeOff,
  UserCheck,
  Tag,
  Copy,
  Info,
  Sliders,
  Share2,
  Clock,
  Flame,
  HelpCircle,
  X
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import {
  SocialAccount,
  YouTubeUploadInitiateResponse,
  YouTubeUploadChunkResponse,
  YouTubeUploadStatusResponse,
  YouTubeUploadCancelResponse
} from '@/lib/types';
import toast from 'react-hot-toast';

export interface YouTubeComposerProps {
  channels: SocialAccount[];
  defaultChannelId?: number;
  onUploadSuccess?: (upload: YouTubeUploadStatusResponse) => void;
}

type UploadPhase =
  | 'idle'
  | 'initiating'
  | 'uploading'
  | 'paused'
  | 'processing'
  | 'ready'
  | 'failed'
  | 'cancelled';

const YOUTUBE_CATEGORIES = [
  { id: '28', name: 'Science & Technology' },
  { id: '27', name: 'Education' },
  { id: '24', name: 'Entertainment' },
  { id: '22', name: 'People & Blogs' },
  { id: '26', name: 'Howto & Style' },
  { id: '20', name: 'Gaming' },
  { id: '10', name: 'Music' },
  { id: '23', name: 'Comedy' },
  { id: '17', name: 'Sports' },
  { id: '1', name: 'Film & Animation' },
  { id: '2', name: 'Autos & Vehicles' },
  { id: '15', name: 'Pets & Animals' },
  { id: '19', name: 'Travel & Events' },
  { id: '25', name: 'News & Politics' },
  { id: '29', name: 'Nonprofits & Activism' },
];

export function YouTubeComposer({
  channels,
  defaultChannelId,
  onUploadSuccess,
}: YouTubeComposerProps) {
  // Channel Selection
  const [selectedAccountId, setSelectedAccountId] = useState<number>(
    defaultChannelId || (channels.length > 0 ? channels[0].id : 0)
  );

  // Video File & Technical State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [videoWidth, setVideoWidth] = useState<number | null>(null);
  const [videoHeight, setVideoHeight] = useState<number | null>(null);
  const videoElementRef = useRef<HTMLVideoElement | null>(null);

  // Content Metadata
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [category, setCategory] = useState<string>('28');
  const [privacyStatus, setPrivacyStatus] = useState<'public' | 'unlisted' | 'private'>('public');
  const [madeForKids, setMadeForKids] = useState<boolean>(false);

  // Tags State
  const [tags, setTags] = useState<string[]>(['SocialAI', 'Automation']);
  const [tagInput, setTagInput] = useState<string>('');

  // Upload Engine Execution State
  const [uploadPhase, setUploadPhase] = useState<UploadPhase>('idle');
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [clientMutationId, setClientMutationId] = useState<string>('');
  const [bytesUploaded, setBytesUploaded] = useState<number>(0);
  const [totalBytes, setTotalBytes] = useState<number>(0);
  const [chunkSizeBytes, setChunkSizeBytes] = useState<number>(8 * 1024 * 1024);
  const [currentChunkIndex, setCurrentChunkIndex] = useState<number>(0);
  const [totalChunks, setTotalChunks] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);
  const [statusDetail, setStatusDetail] = useState<YouTubeUploadStatusResponse | null>(null);

  // Controls & Timers
  const isCancelledRef = useRef<boolean>(false);
  const isPausedRef = useRef<boolean>(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);

  // Synchronize default channel
  useEffect(() => {
    if (defaultChannelId && channels.some((c) => c.id === defaultChannelId)) {
      setSelectedAccountId(defaultChannelId);
    } else if (channels.length > 0 && (!selectedAccountId || !channels.some((c) => c.id === selectedAccountId))) {
      setSelectedAccountId(channels[0].id);
    }
  }, [defaultChannelId, channels]);

  // Clean up object URL & polling timers on unmount
  useEffect(() => {
    return () => {
      if (videoPreviewUrl && videoPreviewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(videoPreviewUrl);
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [videoPreviewUrl]);

  // Determine if video qualifies as a YouTube Short
  const isShortsDetected = useMemo(() => {
    if (!videoDuration && !videoWidth && !videoHeight) return false;
    const isUnder60 = videoDuration !== null ? videoDuration <= 61 : true;
    const isVerticalOrSquare =
      videoWidth !== null && videoHeight !== null ? videoWidth <= videoHeight : false;
    return isUnder60 && (isVerticalOrSquare || (videoDuration !== null && videoDuration <= 60));
  }, [videoDuration, videoWidth, videoHeight]);

  const selectedChannel = useMemo(() => {
    return channels.find((c) => c.id === selectedAccountId) || null;
  }, [channels, selectedAccountId]);

  // Format bytes helper
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Helper for exponential backoff sleep
  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  // Handle local video file change & metadata extraction
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setTotalBytes(file.size);
      setErrorMsg(null);
      setUploadPhase('idle');
      setUploadId(null);
      setBytesUploaded(0);
      setStatusDetail(null);

      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '));
      }

      // Create preview blob URL
      if (videoPreviewUrl && videoPreviewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(videoPreviewUrl);
      }
      const url = URL.createObjectURL(file);
      setVideoPreviewUrl(url);
    }
  };

  // Extract video dimensions and duration when loaded in hidden/preview video
  const handleVideoMetadataLoaded = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const vid = e.currentTarget;
    setVideoDuration(vid.duration || null);
    setVideoWidth(vid.videoWidth || null);
    setVideoHeight(vid.videoHeight || null);
  };

  // Tag Management
  const handleAddTag = (tagToAdd: string) => {
    const trimmed = tagToAdd.trim().replace(/^#/, '');
    if (trimmed && !tags.includes(trimmed) && tags.length < 30) {
      setTags([...tags, trimmed]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddTag(tagInput);
    }
  };

  const handleInsertDescriptionHashtag = (hashtag: string) => {
    const space = description.endsWith(' ') || description.length === 0 ? '' : ' ';
    setDescription((prev) => prev + space + hashtag);
  };

  // ── Step 1: Initiate Upload Session ──────────────────────────────────────────
  const handleStartUpload = async () => {
    if (!selectedAccountId || !selectedChannel) {
      setErrorMsg('Please select a connected YouTube channel.');
      toast.error('Please select a connected YouTube channel.');
      return;
    }
    if (!selectedFile) {
      setErrorMsg('Please select a video file to upload.');
      toast.error('Please select a video file.');
      return;
    }
    if (!title.trim()) {
      setErrorMsg('Please enter a video title.');
      toast.error('Video title is required.');
      return;
    }

    // Reset runtime flags
    isCancelledRef.current = false;
    isPausedRef.current = false;
    setErrorMsg(null);
    setUploadPhase('initiating');

    // Generate or reuse client mutation ID for idempotency
    const mutationId =
      clientMutationId ||
      (typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `mutation_${Date.now()}`);
    setClientMutationId(mutationId);

    try {
      const initPayload = {
        social_account_id: selectedAccountId,
        title: title.trim(),
        description: description.trim(),
        tags: tags.length > 0 ? tags : undefined,
        category_id: category,
        privacy_status: privacyStatus,
        made_for_kids: madeForKids,
        filename: selectedFile.name,
        mime_type: selectedFile.type || 'video/mp4',
        file_size_bytes: selectedFile.size,
        client_mutation_id: mutationId,
      };

      const initRes = await apiClient.post<YouTubeUploadInitiateResponse>(
        '/youtube/upload/initiate',
        initPayload
      );

      const initData = initRes.data;
      setUploadId(initData.upload_id);
      const chunkSize = initData.chunk_size_bytes || 8 * 1024 * 1024;
      setChunkSizeBytes(chunkSize);
      const calculatedChunks = Math.ceil(selectedFile.size / chunkSize);
      setTotalChunks(calculatedChunks);

      // Start multi-chunk upload loop from authoritative start offset
      const startOffset = initData.next_byte_offset || 0;
      setBytesUploaded(startOffset);
      await runChunkUploadLoop(initData.upload_id, startOffset, chunkSize, selectedFile);
    } catch (err: any) {
      console.error('[YOUTUBE_COMPOSER_INITIATE_ERROR]', err);
      const msg =
        err.response?.data?.detail || err.message || 'Failed to initiate YouTube upload session.';
      setErrorMsg(msg);
      setUploadPhase('failed');
      toast.error(`Upload initialization failed: ${msg}`);
    }
  };

  // ── Step 2: Multi-Chunk Resumable Upload Loop ────────────────────────────────
  const runChunkUploadLoop = async (
    currentUploadId: string,
    initialOffset: number,
    chunkSize: number,
    file: File
  ) => {
    setUploadPhase('uploading');
    let offset = initialOffset;
    const totalSize = file.size;

    while (offset < totalSize) {
      if (isCancelledRef.current) {
        setUploadPhase('cancelled');
        return;
      }

      if (isPausedRef.current) {
        setUploadPhase('paused');
        return;
      }

      const chunkIndex = Math.floor(offset / chunkSize);
      setCurrentChunkIndex(chunkIndex + 1);

      const endByte = Math.min(offset + chunkSize, totalSize);
      const chunkBlob = file.slice(offset, endByte);
      const contentRangeHeader = `bytes ${offset}-${endByte - 1}/${totalSize}`;
      const contentTypeHeader = file.type || 'video/mp4';

      let success = false;
      let attempt = 0;
      const MAX_RETRIES = 5;

      while (!success && attempt < MAX_RETRIES) {
        if (isCancelledRef.current || isPausedRef.current) return;

        try {
          const chunkRes = await apiClient.put<YouTubeUploadChunkResponse>(
            `/youtube/upload/${currentUploadId}/chunk`,
            chunkBlob,
            {
              headers: {
                'Content-Range': contentRangeHeader,
                'Content-Type': contentTypeHeader,
              },
            }
          );

          const resData = chunkRes.data;
          setRetryCount(0);

          if (resData.is_complete || resData.http_status === 200 || resData.http_status === 201) {
            setBytesUploaded(totalSize);
            setUploadPhase('processing');
            toast.success('Upload complete! YouTube is now processing the video.');
            startProcessingPolling(currentUploadId);
            return;
          } else if (resData.http_status === 308) {
            const nextOffset = resData.next_byte_offset ?? endByte;
            offset = nextOffset;
            setBytesUploaded(nextOffset);
            success = true;
          } else {
            throw new Error(`Unexpected chunk response HTTP ${resData.http_status}`);
          }
        } catch (chunkErr: any) {
          attempt++;
          setRetryCount(attempt);
          console.warn(
            `[CHUNK_UPLOAD_RETRY] Attempt ${attempt}/${MAX_RETRIES} for chunk ${chunkIndex + 1}:`,
            chunkErr
          );

          if (chunkErr.response?.status === 409) {
            setErrorMsg(chunkErr.response?.data?.detail || 'Upload session is cancelled.');
            setUploadPhase('cancelled');
            return;
          }

          if (attempt >= MAX_RETRIES) {
            const msg =
              chunkErr.response?.data?.detail ||
              chunkErr.message ||
              'Chunk upload failed after maximum retries.';
            setErrorMsg(msg);
            setUploadPhase('failed');
            toast.error(`Upload failed: ${msg}`);
            return;
          }

          // Exponential backoff
          const backoffDelay = Math.min(1000 * Math.pow(2, attempt), 16000) + Math.random() * 500;
          await sleep(backoffDelay);

          // Authoritative range query before retrying chunk
          try {
            const statusRes = await apiClient.get<YouTubeUploadStatusResponse>(
              `/youtube/upload/${currentUploadId}/status?refresh=true`
            );
            if (statusRes.data.is_complete) {
              setBytesUploaded(totalSize);
              setUploadPhase('processing');
              startProcessingPolling(currentUploadId);
              return;
            }
            if (
              statusRes.data.next_byte_offset !== null &&
              statusRes.data.next_byte_offset !== undefined
            ) {
              offset = statusRes.data.next_byte_offset;
              setBytesUploaded(offset);
            }
          } catch (statusErr) {
            console.warn('[RANGE_RECOVERY_QUERY_FAILED]', statusErr);
          }
        }
      }
    }
  };

  // ── Step 3: Authoritative Processing Polling ────────────────────────────────
  const startProcessingPolling = (targetUploadId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    const pollStatus = async () => {
      try {
        const res = await apiClient.get<YouTubeUploadStatusResponse>(
          `/youtube/upload/${targetUploadId}/status?refresh=false`
        );
        const data = res.data;
        setStatusDetail(data);

        if (data.status === 'READY' || data.processing_status === 'succeeded') {
          setUploadPhase('ready');
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          toast.success('🎉 Video is live and ready on YouTube!');
          if (onUploadSuccess) onUploadSuccess(data);
        } else if (
          data.status === 'FAILED' ||
          data.processing_status === 'failed' ||
          data.processing_status === 'terminated'
        ) {
          setUploadPhase('failed');
          setErrorMsg(data.error_message || 'YouTube processing failed.');
          toast.error(`Processing failed: ${data.error_message || 'Unknown error'}`);
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        }
      } catch (err: any) {
        console.warn('[PROCESSING_POLL_ERROR]', err);
      }
    };

    pollStatus();
    pollingIntervalRef.current = setInterval(pollStatus, 3500);
  };

  // ── Pause / Resume / Cancel Controls ────────────────────────────────────────
  const handlePause = () => {
    isPausedRef.current = true;
    setUploadPhase('paused');
    toast('Upload paused', { icon: '⏸️' });
  };

  const handleResume = async () => {
    if (!uploadId || !selectedFile) return;
    isPausedRef.current = false;
    isCancelledRef.current = false;
    setErrorMsg(null);
    setUploadPhase('uploading');
    toast.success('Resuming upload...');

    try {
      const res = await apiClient.get<YouTubeUploadStatusResponse>(
        `/youtube/upload/${uploadId}/status?refresh=true`
      );
      const nextOffset = res.data.next_byte_offset || bytesUploaded;
      setBytesUploaded(nextOffset);
      await runChunkUploadLoop(uploadId, nextOffset, chunkSizeBytes, selectedFile);
    } catch (err: any) {
      console.error('[RESUME_FAILED]', err);
      setErrorMsg('Failed to resume upload session.');
      setUploadPhase('failed');
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this YouTube upload?')) return;
    isCancelledRef.current = true;
    isPausedRef.current = true;
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    if (uploadId) {
      try {
        await apiClient.post<YouTubeUploadCancelResponse>(`/youtube/upload/${uploadId}/cancel`);
      } catch (err) {
        console.warn('[CANCEL_API_ERROR]', err);
      }
    }

    setUploadPhase('cancelled');
    setErrorMsg('Upload was cancelled.');
    toast.error('Upload cancelled.');
  };

  const handleResetForNewUpload = () => {
    setSelectedFile(null);
    if (videoPreviewUrl && videoPreviewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(videoPreviewUrl);
    }
    setVideoPreviewUrl(null);
    setVideoDuration(null);
    setVideoWidth(null);
    setVideoHeight(null);
    setTitle('');
    setDescription('');
    setTags(['SocialAI', 'Automation']);
    setUploadPhase('idle');
    setUploadId(null);
    setClientMutationId('');
    setBytesUploaded(0);
    setTotalBytes(0);
    setStatusDetail(null);
    setErrorMsg(null);
  };

  const handleCopyLink = () => {
    if (statusDetail?.video_url) {
      navigator.clipboard.writeText(statusDetail.video_url);
      setCopiedLink(true);
      toast.success('YouTube URL copied to clipboard!');
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  const progressPercentage =
    totalBytes > 0 ? Math.min(100, Math.round((bytesUploaded / totalBytes) * 100)) : 0;

  // Empty State if no YouTube accounts connected
  if (channels.length === 0) {
    return (
      <div className="glass-panel p-8 sm:p-12 rounded-3xl border border-slate-800 text-center space-y-6 max-w-2xl mx-auto shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400 mx-auto shadow-lg shadow-red-600/10">
          <Youtube className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-bold text-white tracking-tight">
            Connect Your YouTube Channel
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            To publish YouTube Videos and Shorts directly from the Studio workspace, authorize your
            YouTube channel in Social Accounts.
          </p>
        </div>
        <div className="pt-2">
          <a
            href="/meta-connect"
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs transition shadow-lg shadow-red-500/25"
          >
            <Youtube className="w-4 h-4 fill-white" />
            <span>Go to Connect YouTube</span>
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hidden video element for metadata inspection */}
      {videoPreviewUrl && (
        <video
          ref={videoElementRef}
          src={videoPreviewUrl}
          onLoadedMetadata={handleVideoMetadataLoaded}
          className="hidden"
          preload="metadata"
        />
      )}

      {/* Top Bar: Target Channel Selector & Persona Banner */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-600 to-rose-700 flex items-center justify-center text-white shadow-lg shadow-red-600/20 flex-shrink-0">
            <Youtube className="w-5 h-5 fill-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-white tracking-tight">YouTube Composer Studio</h2>
              <span className="px-2 py-0.5 rounded-full bg-red-950/80 text-red-300 border border-red-800/60 text-[10px] font-mono font-semibold">
                8 MB Resumable
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Publish high-definition Standard Videos & YouTube Shorts with chunked upload reliability
            </p>
          </div>
        </div>

        {/* Channel Dropdown */}
        <div className="flex items-center space-x-2">
          <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider hidden md:block">
            Channel:
          </label>
          <div className="relative min-w-[220px]">
            <select
              value={selectedAccountId || ''}
              onChange={(e) => setSelectedAccountId(Number(e.target.value))}
              disabled={uploadPhase !== 'idle'}
              className="w-full pl-3 pr-8 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs font-semibold text-white focus:outline-none focus:border-red-500 disabled:opacity-50 appearance-none shadow-inner"
            >
              {channels.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.account_name} {c.metadata_json?.custom_url ? `(${c.metadata_json.custom_url})` : ''}
                </option>
              ))}
            </select>
            <div className="absolute right-3 top-2.5 pointer-events-none text-slate-400">
              ▼
            </div>
          </div>
        </div>
      </div>

      {/* Main Dual-Column Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Column: Media & Metadata Form (7 Cols) ───────────────────── */}
        <div className="lg:col-span-7 space-y-6">
          {/* File Picker & Drag-Drop Card */}
          <div className="glass-panel p-6 rounded-2xl space-y-4 border-l-4 border-red-500 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <FileVideo className="w-4 h-4 text-red-400" />
                <span>1. Select Video Asset</span>
              </h3>
              {selectedFile && (
                <button
                  type="button"
                  onClick={handleResetForNewUpload}
                  disabled={uploadPhase === 'uploading'}
                  className="text-[11px] text-slate-400 hover:text-red-400 font-semibold transition disabled:opacity-30"
                >
                  Change Video
                </button>
              )}
            </div>

            {!selectedFile ? (
              <label className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-slate-700 hover:border-red-500 rounded-2xl bg-slate-900/60 cursor-pointer transition text-center group space-y-3">
                <div className="w-14 h-14 rounded-2xl bg-red-950/60 border border-red-800/60 flex items-center justify-center text-red-400 group-hover:scale-105 transition">
                  <UploadCloud className="w-7 h-7" />
                </div>
                <div className="space-y-1">
                  <span className="text-xs font-bold text-slate-200 block group-hover:text-white">
                    Click to select or drag and drop video file
                  </span>
                  <p className="text-[11px] text-slate-400">
                    MP4, MOV, WebM, MKV, AVI (Supports large files up to 256 GB)
                  </p>
                </div>
                <span className="inline-block px-3 py-1 rounded-full bg-slate-800 text-[10px] font-mono text-slate-300 border border-slate-700">
                  ⚡ Automatic Shorts & Widescreen Detection
                </span>
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            ) : (
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-red-950/80 border border-red-800/80 flex items-center justify-center text-red-400 flex-shrink-0">
                      <Film className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-100 truncate">{selectedFile.name}</p>
                      <p className="text-[11px] text-slate-400 font-mono">
                        {formatBytes(selectedFile.size)} • {selectedFile.type || 'video/mp4'}
                      </p>
                    </div>
                  </div>

                  {/* Shorts vs Video Badge */}
                  <div>
                    {isShortsDetected ? (
                      <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-red-600/30 to-pink-600/30 text-red-300 border border-red-500/40 text-[10px] font-bold shadow-sm">
                        <Zap className="w-3 h-3 text-red-400" />
                        <span>YouTube Short</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-bold">
                        <Film className="w-3 h-3 text-indigo-400" />
                        <span>Standard Video</span>
                      </span>
                    )}
                  </div>
                </div>

                {isShortsDetected && (
                  <div className="p-2.5 rounded-lg bg-red-950/30 border border-red-500/20 text-[11px] text-red-200 flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-red-400 flex-shrink-0" />
                    <span>
                      <strong>Shorts Detected:</strong> Video is under 60 seconds with vertical/square framing. It will be indexed as a YouTube Short.
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Details & Metadata Card */}
          <div className="glass-panel p-6 rounded-2xl space-y-5 border border-slate-800 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-red-400" />
                <span>2. Video Details & SEO Metadata</span>
              </h3>
            </div>

            {/* Title Input */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-slate-200">
                  Title (Required)
                </label>
                <span className={`text-[10px] font-mono ${title.length > 90 ? 'text-amber-400 font-bold' : 'text-slate-500'}`}>
                  {title.length} / 100
                </span>
              </div>
              <input
                type="text"
                value={title}
                maxLength={100}
                onChange={(e) => setTitle(e.target.value)}
                disabled={uploadPhase !== 'idle'}
                placeholder="Add a title that describes your video (e.g. Next-Gen Social AI Automation Demo)"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 disabled:opacity-50 transition"
              />
            </div>

            {/* Description Textarea */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-slate-200">
                  Description
                </label>
                <span className="text-[10px] font-mono text-slate-500">
                  {description.length} / 5000
                </span>
              </div>
              <textarea
                value={description}
                maxLength={5000}
                onChange={(e) => setDescription(e.target.value)}
                disabled={uploadPhase !== 'idle'}
                rows={4}
                placeholder="Tell viewers about your video, links, and hashtags..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 disabled:opacity-50 resize-none transition leading-relaxed"
              />

              {/* Quick Hashtag Inserters */}
              <div className="flex items-center flex-wrap gap-1.5 pt-1">
                <span className="text-[10px] text-slate-500 font-semibold mr-1">Insert:</span>
                {['#Shorts', '#Automation', '#AI', '#Viral', '#Marketing'].map((ht) => (
                  <button
                    key={ht}
                    type="button"
                    onClick={() => handleInsertDescriptionHashtag(ht)}
                    disabled={uploadPhase !== 'idle'}
                    className="px-2 py-0.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[10px] font-semibold text-slate-300 hover:text-red-300 transition"
                  >
                    + {ht}
                  </button>
                ))}
              </div>
            </div>

            {/* Tags Pill Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-slate-200 flex items-center space-x-1.5">
                  <Tag className="w-3.5 h-3.5 text-red-400" />
                  <span>Tags / Keywords</span>
                </label>
                <span className="text-[10px] font-mono text-slate-500">
                  {tags.length} / 30 tags
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleTagKeyDown}
                  disabled={uploadPhase !== 'idle'}
                  placeholder="Type tag and press Enter or comma (e.g. ai, tech, tutorial)"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => handleAddTag(tagInput)}
                  disabled={!tagInput.trim() || uploadPhase !== 'idle'}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition disabled:opacity-40"
                >
                  Add
                </button>
              </div>

              {/* Tags List */}
              {tags.length > 0 && (
                <div className="flex items-center flex-wrap gap-1.5 pt-1">
                  {tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-red-950/40 text-red-200 border border-red-800/50 text-[11px] font-medium"
                    >
                      <span>#{t}</span>
                      {uploadPhase === 'idle' && (
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(t)}
                          className="text-red-400 hover:text-white transition p-0.5"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Category Select */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-200">
                YouTube Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={uploadPhase !== 'idle'}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-red-500 disabled:opacity-50"
              >
                {YOUTUBE_CATEGORIES.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            {/* COPPA Made for Kids Section */}
            <div className="space-y-2 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div className="flex items-center space-x-2">
                <UserCheck className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-white">Audience & Made for Kids (COPPA)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Regardless of your location, you’re legally required to comply with COPPA and other laws.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setMadeForKids(false)}
                  disabled={uploadPhase !== 'idle'}
                  className={`p-3 rounded-xl border text-left transition flex items-start space-x-2.5 ${
                    !madeForKids
                      ? 'bg-red-950/40 border-red-500/80 text-white shadow-sm'
                      : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="text-base mt-0.5">{!madeForKids ? '●' : '○'}</span>
                  <div>
                    <span className="text-xs font-bold block">No, not made for kids</span>
                    <span className="text-[10px] text-slate-400">Standard audience (recommended)</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setMadeForKids(true)}
                  disabled={uploadPhase !== 'idle'}
                  className={`p-3 rounded-xl border text-left transition flex items-start space-x-2.5 ${
                    madeForKids
                      ? 'bg-red-950/40 border-red-500/80 text-white shadow-sm'
                      : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="text-base mt-0.5">{madeForKids ? '●' : '○'}</span>
                  <div>
                    <span className="text-xs font-bold block">Yes, it’s made for kids</span>
                    <span className="text-[10px] text-slate-400">Child-directed content</span>
                  </div>
                </button>
              </div>
            </div>

            {/* Visibility & Privacy Cards */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-200">
                3. Visibility & Publishing Privacy
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {/* Public */}
                <button
                  type="button"
                  onClick={() => setPrivacyStatus('public')}
                  disabled={uploadPhase !== 'idle'}
                  className={`p-3.5 rounded-xl border text-left transition flex flex-col justify-between space-y-2 ${
                    privacyStatus === 'public'
                      ? 'bg-gradient-to-br from-red-950/50 to-rose-950/50 border-red-500 text-white shadow-md'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <Globe className="w-4 h-4 text-emerald-400" />
                    {privacyStatus === 'public' && <Check className="w-4 h-4 text-red-400" />}
                  </div>
                  <div>
                    <span className="text-xs font-bold block text-white">Public</span>
                    <span className="text-[10px] text-slate-400">Everyone can watch and search</span>
                  </div>
                </button>

                {/* Unlisted */}
                <button
                  type="button"
                  onClick={() => setPrivacyStatus('unlisted')}
                  disabled={uploadPhase !== 'idle'}
                  className={`p-3.5 rounded-xl border text-left transition flex flex-col justify-between space-y-2 ${
                    privacyStatus === 'unlisted'
                      ? 'bg-gradient-to-br from-red-950/50 to-rose-950/50 border-red-500 text-white shadow-md'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <EyeOff className="w-4 h-4 text-amber-400" />
                    {privacyStatus === 'unlisted' && <Check className="w-4 h-4 text-red-400" />}
                  </div>
                  <div>
                    <span className="text-xs font-bold block text-white">Unlisted</span>
                    <span className="text-[10px] text-slate-400">Anyone with the link can view</span>
                  </div>
                </button>

                {/* Private */}
                <button
                  type="button"
                  onClick={() => setPrivacyStatus('private')}
                  disabled={uploadPhase !== 'idle'}
                  className={`p-3.5 rounded-xl border text-left transition flex flex-col justify-between space-y-2 ${
                    privacyStatus === 'private'
                      ? 'bg-gradient-to-br from-red-950/50 to-rose-950/50 border-red-500 text-white shadow-md'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <Lock className="w-4 h-4 text-rose-400" />
                    {privacyStatus === 'private' && <Check className="w-4 h-4 text-red-400" />}
                  </div>
                  <div>
                    <span className="text-xs font-bold block text-white">Private</span>
                    <span className="text-[10px] text-slate-400">Only you can view</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right Column: Live Video Player Preview & Status (5 Cols) ─────── */}
        <div className="lg:col-span-5 space-y-6">
          {/* Live YouTube Player Preview Card */}
          <div className="glass-panel p-5 rounded-2xl space-y-4 sticky top-20 border border-slate-800 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <Film className="w-4 h-4 text-red-400" />
                <span>Live YouTube Preview</span>
              </h3>
              {isShortsDetected && (
                <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 font-mono text-[9px] font-bold">
                  9:16 Shorts Mode
                </span>
              )}
            </div>

            {/* Video Container */}
            <div
              className={`relative rounded-xl overflow-hidden bg-black border border-slate-800 flex items-center justify-center mx-auto ${
                isShortsDetected ? 'max-w-[240px] aspect-[9/16]' : 'w-full aspect-video'
              }`}
            >
              {videoPreviewUrl ? (
                <video
                  src={videoPreviewUrl}
                  controls
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center justify-center p-6 text-center space-y-2 text-slate-500">
                  <FileVideo className="w-10 h-10 text-slate-600 animate-pulse" />
                  <span className="text-xs font-medium">Select a video file to generate live preview</span>
                </div>
              )}
            </div>

            {/* Video Details Preview */}
            <div className="space-y-2 bg-slate-900/70 p-3.5 rounded-xl border border-slate-800/80 text-xs">
              <h4 className="font-bold text-white text-sm line-clamp-2 leading-snug">
                {title || 'Untitled Video'}
              </h4>

              <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                <span className="font-semibold text-slate-200">
                  {selectedChannel?.account_name || 'YouTube Channel'}
                </span>
                <span>•</span>
                <span className="capitalize font-mono text-red-400 font-semibold">{privacyStatus}</span>
                {videoDuration && (
                  <>
                    <span>•</span>
                    <span className="font-mono">{Math.round(videoDuration)}s</span>
                  </>
                )}
              </div>

              {description && (
                <p className="text-[11px] text-slate-400 line-clamp-3 whitespace-pre-line pt-1 border-t border-slate-800/60">
                  {description}
                </p>
              )}
            </div>

            {/* Security Assurance Banner */}
            <div className="flex items-start space-x-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[10px] text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-emerald-300 font-semibold">Resumable Chunk Engine:</strong> Video is streamed via 8 MB encrypted chunks through server-side authorization.
              </div>
            </div>

            {/* ── Live Upload Progress Stage Card ───────────────────────────── */}
            {uploadPhase !== 'idle' && (
              <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-3.5 shadow-2xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {uploadPhase === 'uploading' && (
                      <Loader2 className="w-4 h-4 animate-spin text-red-400" />
                    )}
                    {uploadPhase === 'processing' && (
                      <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                    )}
                    {uploadPhase === 'ready' && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    )}
                    {uploadPhase === 'paused' && <Pause className="w-4 h-4 text-amber-400" />}
                    {uploadPhase === 'failed' && <AlertCircle className="w-4 h-4 text-rose-400" />}
                    {uploadPhase === 'cancelled' && <X className="w-4 h-4 text-rose-400" />}

                    <span className="font-bold text-xs text-white uppercase tracking-wider">
                      {uploadPhase === 'initiating' && 'Initiating Session...'}
                      {uploadPhase === 'uploading' && `Uploading (${currentChunkIndex}/${totalChunks} chunks)`}
                      {uploadPhase === 'paused' && 'Upload Paused'}
                      {uploadPhase === 'processing' && 'YouTube Processing Status...'}
                      {uploadPhase === 'ready' && 'Video Published & Live!'}
                      {uploadPhase === 'failed' && 'Upload Failed'}
                      {uploadPhase === 'cancelled' && 'Upload Cancelled'}
                    </span>
                  </div>

                  <span className="font-mono text-xs font-bold text-red-400">
                    {progressPercentage}%
                  </span>
                </div>

                {/* Real Progress Bar */}
                <div className="w-full bg-slate-900 rounded-full h-3 overflow-hidden p-0.5 border border-slate-800">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      uploadPhase === 'ready'
                        ? 'bg-emerald-500'
                        : uploadPhase === 'processing'
                        ? 'bg-gradient-to-r from-amber-500 to-indigo-500 animate-pulse'
                        : uploadPhase === 'failed' || uploadPhase === 'cancelled'
                        ? 'bg-rose-500'
                        : 'bg-gradient-to-r from-red-600 via-rose-500 to-pink-500'
                    }`}
                    style={{ width: `${progressPercentage}%` }}
                  />
                </div>

                {/* Progress Numbers */}
                <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 font-mono">
                  <div>
                    <span>Transferred: </span>
                    <span className="text-slate-200 font-bold">{formatBytes(bytesUploaded)}</span>
                    <span> / {formatBytes(totalBytes)}</span>
                  </div>
                  <div className="text-right">
                    {retryCount > 0 && (
                      <span className="text-amber-400 font-bold mr-1">
                        Retry {retryCount}/5 •
                      </span>
                    )}
                    <span>Chunk Size: 8 MB</span>
                  </div>
                </div>

                {/* Processing State Details */}
                {uploadPhase === 'processing' && (
                  <p className="text-[11px] text-amber-300/90 font-medium bg-amber-950/30 p-2.5 rounded-lg border border-amber-500/20">
                    ⏳ Chunk transfer complete! YouTube background poller is checking video processing status...
                  </p>
                )}

                {/* Action Controls */}
                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
                  {uploadPhase === 'uploading' && (
                    <button
                      type="button"
                      onClick={handlePause}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center space-x-1"
                    >
                      <Pause className="w-3.5 h-3.5" />
                      <span>Pause</span>
                    </button>
                  )}

                  {uploadPhase === 'paused' && (
                    <button
                      type="button"
                      onClick={handleResume}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition flex items-center space-x-1"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Resume</span>
                    </button>
                  )}

                  {(uploadPhase === 'uploading' || uploadPhase === 'paused') && (
                    <button
                      type="button"
                      onClick={handleCancel}
                      className="px-3 py-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold transition flex items-center space-x-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Cancel</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* ── Success / READY Card ───────────────────────────────────────── */}
            {uploadPhase === 'ready' && statusDetail && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-950/60 to-slate-900 border border-emerald-500/50 space-y-3 shadow-2xl animate-in fade-in">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold text-xs">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span>Video Successfully Published on YouTube!</span>
                </div>

                <p className="text-[11px] text-slate-300">
                  Your video is ready to view and share across the web.
                </p>

                {statusDetail.video_url && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        readOnly
                        value={statusDetail.video_url}
                        className="flex-1 bg-slate-950 border border-emerald-600/40 rounded-lg px-2.5 py-1.5 text-[11px] font-mono text-emerald-300"
                      />
                      <button
                        type="button"
                        onClick={handleCopyLink}
                        className="px-2.5 py-1.5 rounded-lg bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 text-xs font-semibold transition flex items-center space-x-1"
                      >
                        {copiedLink ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedLink ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>

                    <div className="flex items-center space-x-2 pt-1">
                      <a
                        href={statusDetail.video_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-lg shadow-red-600/30"
                      >
                        <Film className="w-3.5 h-3.5" />
                        <span>Watch on YouTube</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>

                      <button
                        type="button"
                        onClick={handleResetForNewUpload}
                        className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
                      >
                        Upload Another
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {errorMsg && (
              <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{errorMsg}</span>
              </div>
            )}

            {/* Primary Submit Button */}
            {uploadPhase === 'idle' && (
              <button
                type="button"
                onClick={handleStartUpload}
                disabled={!selectedFile || !selectedAccountId || !title.trim()}
                className="w-full py-3 rounded-2xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs transition flex items-center justify-center space-x-2 shadow-xl shadow-red-600/25 disabled:opacity-40"
              >
                <UploadCloud className="w-4 h-4" />
                <span>Upload to YouTube</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}

            {(uploadPhase === 'failed' || uploadPhase === 'cancelled') && (
              <button
                type="button"
                onClick={handleStartUpload}
                className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition flex items-center justify-center space-x-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry Upload</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
