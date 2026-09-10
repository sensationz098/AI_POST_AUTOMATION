'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Youtube,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileVideo,
  ArrowRight,
  ShieldCheck,
  Check,
  RefreshCw,
  Pause,
  Play,
  Trash2,
  ExternalLink,
  Film
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import {
  SocialAccount,
  YouTubeUploadInitiateResponse,
  YouTubeUploadChunkResponse,
  YouTubeUploadStatusResponse,
  YouTubeUploadCancelResponse
} from '@/lib/types';

interface YouTubeUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  channels: SocialAccount[];
  defaultChannelId?: number;
  onUploadSuccess?: (upload: YouTubeUploadStatusResponse) => void;
}

type UploadPhase = 'idle' | 'initiating' | 'uploading' | 'paused' | 'processing' | 'ready' | 'failed' | 'cancelled';

export function YouTubeUploadModal({
  isOpen,
  onClose,
  channels,
  defaultChannelId,
  onUploadSuccess,
}: YouTubeUploadModalProps) {
  const [selectedAccountId, setSelectedAccountId] = useState<number>(
    defaultChannelId || (channels.length > 0 ? channels[0].id : 0)
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [privacyStatus, setPrivacyStatus] = useState<'private' | 'unlisted' | 'public'>('private');

  // Execution states
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

  // Cancellation and pause refs
  const isCancelledRef = useRef<boolean>(false);
  const isPausedRef = useRef<boolean>(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Synchronize channel selection when modal opens
  useEffect(() => {
    if (!isOpen) return;

    if (defaultChannelId && channels.some((c) => c.id === defaultChannelId)) {
      setSelectedAccountId(defaultChannelId);
    } else if (channels.length > 0) {
      setSelectedAccountId((prev) => (channels.some((c) => c.id === prev) ? prev : channels[0].id));
    } else {
      setSelectedAccountId(0);
    }
  }, [isOpen, defaultChannelId, channels]);

  // Cleanup polling timer on unmount or close
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  if (!isOpen) return null;

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
        setTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Helper for exponential backoff sleep
  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  // ── Step 1: Initiate Upload Session ──────────────────────────────────────────
  const handleStartUpload = async () => {
    const selectedChannel = channels.find((c) => c.id === selectedAccountId);
    if (!selectedAccountId || !selectedChannel) {
      setErrorMsg('Please select a connected YouTube channel.');
      return;
    }
    if (!selectedFile) {
      setErrorMsg('Please select a local video file.');
      return;
    }

    // Reset controls
    isCancelledRef.current = false;
    isPausedRef.current = false;
    setErrorMsg(null);
    setUploadPhase('initiating');

    // Generate or reuse client mutation ID for idempotency
    const mutationId = clientMutationId || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `mutation_${Date.now()}`);
    setClientMutationId(mutationId);

    try {
      const initPayload = {
        social_account_id: selectedAccountId,
        title: title.trim() || selectedFile.name,
        description: description.trim(),
        privacy_status: privacyStatus,
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

      // Start multi-chunk upload loop from authoritative starting offset
      const startOffset = initData.next_byte_offset || 0;
      setBytesUploaded(startOffset);
      await runChunkUploadLoop(initData.upload_id, startOffset, chunkSize, selectedFile);
    } catch (err: any) {
      console.error('[YOUTUBE_UPLOAD_INITIATE_ERROR]', err);
      const msg = err.response?.data?.detail || err.message || 'Failed to initiate YouTube upload session.';
      setErrorMsg(msg);
      setUploadPhase('failed');
    }
  };

  // ── Step 2: Multi-Chunk Upload Loop with Exponential Backoff ─────────────────
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
      // Check for user cancellation
      if (isCancelledRef.current) {
        setUploadPhase('cancelled');
        return;
      }

      // Check for user pause
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
            // Upload complete!
            setBytesUploaded(totalSize);
            setUploadPhase('processing');
            startProcessingPolling(currentUploadId);
            return;
          } else if (resData.http_status === 308) {
            // Resume incomplete: advance offset
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
          console.warn(`[CHUNK_UPLOAD_RETRY] Attempt ${attempt}/${MAX_RETRIES} for chunk ${chunkIndex + 1}:`, chunkErr);

          if (chunkErr.response?.status === 409) {
            // Upload was cancelled or in invalid state
            setErrorMsg(chunkErr.response?.data?.detail || 'Upload session is cancelled.');
            setUploadPhase('cancelled');
            return;
          }

          if (attempt >= MAX_RETRIES) {
            const msg = chunkErr.response?.data?.detail || chunkErr.message || 'Chunk upload failed after maximum retries.';
            setErrorMsg(msg);
            setUploadPhase('failed');
            return;
          }

          // Exponential backoff delay
          const backoffDelay = Math.min(1000 * Math.pow(2, attempt), 16000) + Math.random() * 500;
          await sleep(backoffDelay);

          // Authoritative Range query before retrying chunk
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
            if (statusRes.data.next_byte_offset !== null && statusRes.data.next_byte_offset !== undefined) {
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

  // ── Step 3: Background Video Processing Polling ──────────────────────────────
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
          if (onUploadSuccess) onUploadSuccess(data);
        } else if (data.status === 'FAILED' || data.processing_status === 'failed' || data.processing_status === 'terminated') {
          setUploadPhase('failed');
          setErrorMsg(data.error_message || 'YouTube processing failed.');
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        }
      } catch (err: any) {
        console.warn('[PROCESSING_POLL_ERROR]', err);
      }
    };

    // Initial poll then every 4 seconds
    pollStatus();
    pollingIntervalRef.current = setInterval(pollStatus, 4000);
  };

  // ── Pause / Resume Handlers ──────────────────────────────────────────────────
  const handlePause = () => {
    isPausedRef.current = true;
    setUploadPhase('paused');
  };

  const handleResume = async () => {
    if (!uploadId || !selectedFile) return;
    isPausedRef.current = false;
    isCancelledRef.current = false;
    setErrorMsg(null);
    setUploadPhase('uploading');

    // Query status to get authoritative byte offset
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

  // ── Cancellation Handler ─────────────────────────────────────────────────────
  const handleCancel = async () => {
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
  };

  const progressPercentage = totalBytes > 0 ? Math.min(100, Math.round((bytesUploaded / totalBytes) * 100)) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
              <Youtube className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>Upload Video to YouTube</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-mono">
                  8 MB Resumable
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Chunked resumable upload with auto-retry, interruption recovery, and processing monitoring
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={uploadPhase === 'uploading'}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition disabled:opacity-30"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto custom-scrollbar flex-1 text-xs">
          {/* Security & Token Banner */}
          <div className="flex items-start space-x-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="text-emerald-300 font-semibold">Zero Token Exposure & Streaming Safety:</strong>{' '}
              Video is uploaded in bounded 8 MB chunks through our secure backend proxy. Google OAuth credentials remain server-side.
            </div>
          </div>

          {/* Upload Configuration Form (Disabled once upload starts) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Channel Select */}
            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Target YouTube Channel
              </label>
              <select
                value={selectedAccountId || ''}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setSelectedAccountId(val);
                  if (errorMsg === 'Please select a connected YouTube channel.') {
                    setErrorMsg(null);
                  }
                }}
                disabled={uploadPhase !== 'idle' || channels.length === 0}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none disabled:opacity-50"
              >
                {channels.length === 0 ? (
                  <option value="">No connected YouTube channel found</option>
                ) : (
                  channels.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.account_name} ({c.account_id})
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Privacy Select */}
            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Privacy Status
              </label>
              <select
                value={privacyStatus}
                onChange={(e) => setPrivacyStatus(e.target.value as any)}
                disabled={uploadPhase !== 'idle'}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none disabled:opacity-50"
              >
                <option value="private">Private (Default)</option>
                <option value="unlisted">Unlisted</option>
                <option value="public">Public</option>
              </select>
            </div>
          </div>

          {/* Title & Description */}
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Video Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={uploadPhase !== 'idle'}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none disabled:opacity-50"
                placeholder="Enter video title"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Description (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={uploadPhase !== 'idle'}
                rows={2}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none resize-none disabled:opacity-50"
                placeholder="Enter video description"
              />
            </div>
          </div>

          {/* File Picker */}
          {uploadPhase === 'idle' && (
            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Select Video File
              </label>
              <div className="p-5 border-2 border-dashed border-slate-700 hover:border-red-500 rounded-xl bg-slate-950/40 transition text-center cursor-pointer relative group">
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                />
                <div className="flex flex-col items-center space-y-2">
                  <FileVideo className="w-8 h-8 text-slate-400 group-hover:text-red-400 transition" />
                  {selectedFile ? (
                    <div className="space-y-0.5">
                      <p className="text-xs font-semibold text-slate-200">{selectedFile.name}</p>
                      <p className="text-[10px] text-slate-400">
                        Total Size: <span className="text-slate-200 font-bold">{formatBytes(selectedFile.size)}</span> •
                        Estimated Chunks: <span className="text-red-400 font-bold">{Math.ceil(selectedFile.size / (8 * 1024 * 1024))}</span> (8 MB each)
                      </p>
                    </div>
                  ) : (
                    <div>
                      <span className="text-xs font-semibold text-slate-300 group-hover:text-white">
                        Click to browse video file (MP4, MOV, MKV, WebM)
                      </span>
                      <p className="text-[10px] text-slate-500">Supports videos of any size via resumable chunking</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Live Upload Progress Section */}
          {uploadPhase !== 'idle' && (
            <div className="space-y-3 p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {uploadPhase === 'uploading' && <Loader2 className="w-4 h-4 animate-spin text-red-400" />}
                  {uploadPhase === 'processing' && <Loader2 className="w-4 h-4 animate-spin text-amber-400" />}
                  {uploadPhase === 'ready' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                  {uploadPhase === 'paused' && <Pause className="w-4 h-4 text-amber-400" />}
                  {uploadPhase === 'cancelled' && <AlertCircle className="w-4 h-4 text-rose-400" />}
                  {uploadPhase === 'failed' && <AlertCircle className="w-4 h-4 text-rose-400" />}

                  <span className="font-bold text-slate-200 uppercase tracking-wider text-[11px]">
                    {uploadPhase === 'initiating' && 'Initiating Session...'}
                    {uploadPhase === 'uploading' && `Uploading Chunks (${currentChunkIndex}/${totalChunks})`}
                    {uploadPhase === 'paused' && 'Upload Paused'}
                    {uploadPhase === 'processing' && 'YouTube Processing Video...'}
                    {uploadPhase === 'ready' && 'Video Published & Ready!'}
                    {uploadPhase === 'cancelled' && 'Upload Cancelled'}
                    {uploadPhase === 'failed' && 'Upload Failed'}
                  </span>
                </div>

                <span className="font-mono text-xs font-bold text-red-400">
                  {progressPercentage}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    uploadPhase === 'ready'
                      ? 'bg-emerald-500'
                      : uploadPhase === 'processing'
                      ? 'bg-amber-500 animate-pulse'
                      : uploadPhase === 'failed' || uploadPhase === 'cancelled'
                      ? 'bg-rose-500'
                      : 'bg-gradient-to-r from-red-600 to-rose-500'
                  }`}
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>

              {/* Progress Details */}
              <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 font-mono pt-1">
                <div>
                  <span>Transferred: </span>
                  <span className="text-slate-200 font-semibold">{formatBytes(bytesUploaded)}</span>
                  <span> / {formatBytes(totalBytes)}</span>
                </div>
                <div className="text-right">
                  {retryCount > 0 && (
                    <span className="text-amber-400 font-semibold mr-2">
                      Retry {retryCount}/5
                    </span>
                  )}
                  <span>Session: </span>
                  <span className="text-slate-300 truncate">{uploadId ? `${uploadId.substring(0, 8)}...` : 'Pending'}</span>
                </div>
              </div>

              {/* In-Flight Controls */}
              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800/80">
                {uploadPhase === 'uploading' && (
                  <button
                    type="button"
                    onClick={handlePause}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold transition flex items-center space-x-1"
                  >
                    <Pause className="w-3 h-3" />
                    <span>Pause</span>
                  </button>
                )}

                {uploadPhase === 'paused' && (
                  <button
                    type="button"
                    onClick={handleResume}
                    className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition flex items-center space-x-1"
                  >
                    <Play className="w-3 h-3" />
                    <span>Resume</span>
                  </button>
                )}

                {(uploadPhase === 'uploading' || uploadPhase === 'paused') && (
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-2.5 py-1 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[11px] font-semibold transition flex items-center space-x-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Cancel</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Success Card */}
          {uploadPhase === 'ready' && statusDetail && (
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/80 space-y-2">
              <div className="flex items-center space-x-2 text-emerald-400 font-bold text-xs">
                <CheckCircle2 className="w-4 h-4" />
                <span>Upload & YouTube Processing Complete!</span>
              </div>
              <p className="text-[11px] text-slate-300">
                Your video is published and ready to watch on YouTube.
              </p>
              {statusDetail.video_url && (
                <div className="pt-2 flex items-center space-x-3">
                  <a
                    href={statusDetail.video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-red-600/30"
                  >
                    <Film className="w-3.5 h-3.5" />
                    <span>Watch on YouTube</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                  <a
                    href={`https://studio.youtube.com/video/${statusDetail.video_id}/edit`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center space-x-1"
                  >
                    <span>Open in YouTube Studio</span>
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Error Alert */}
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            disabled={uploadPhase === 'uploading'}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition disabled:opacity-50"
          >
            {uploadPhase === 'ready' ? 'Done' : 'Close'}
          </button>

          {uploadPhase === 'idle' && (
            <button
              type="button"
              onClick={handleStartUpload}
              disabled={!selectedFile || channels.length === 0 || !selectedAccountId}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs transition flex items-center space-x-2 shadow-lg shadow-red-500/25 disabled:opacity-50"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Start Upload</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {(uploadPhase === 'failed' || uploadPhase === 'cancelled') && (
            <button
              type="button"
              onClick={handleStartUpload}
              className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition flex items-center space-x-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Upload</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
