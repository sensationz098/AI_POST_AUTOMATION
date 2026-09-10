'use client';

import React, { useState, useEffect } from 'react';
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
  RefreshCw
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import {
  SocialAccount,
  YouTubeUploadInitiateResponse,
  YouTubeUploadChunkResponse,
  YouTubeUploadStatusResponse
} from '@/lib/types';

interface YouTubeChunkTestModalProps {
  isOpen: boolean;
  onClose: () => void;
  channels: SocialAccount[];
  defaultChannelId?: number;
}

export function YouTubeChunkTestModal({
  isOpen,
  onClose,
  channels,
  defaultChannelId,
}: YouTubeChunkTestModalProps) {
  const [selectedAccountId, setSelectedAccountId] = useState<number>(
    defaultChannelId || (channels.length > 0 ? channels[0].id : 0)
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>('Test Resumable Video Chunk');
  const [description, setDescription] = useState<string>('Milestone 2A Proof of Concept chunk upload test');
  const [privacyStatus, setPrivacyStatus] = useState<'private' | 'unlisted' | 'public'>('private');

  // Execution states
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<string>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Result details
  const [initiateResult, setInitiateResult] = useState<YouTubeUploadInitiateResponse | null>(null);
  const [chunkResult, setChunkResult] = useState<YouTubeUploadChunkResponse | null>(null);
  const [chunkSizeSent, setChunkSizeSent] = useState<number>(0);
  const [statusResult, setStatusResult] = useState<YouTubeUploadStatusResponse | null>(null);
  const [isQueryingStatus, setIsQueryingStatus] = useState<boolean>(false);

  // Synchronize selected channel state when modal opens or channel list / defaultChannelId changes
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

  if (!isOpen) return null;

  const CHUNK_SIZE_BYTES = 2 * 1024 * 1024; // 2 MB test chunk (8 * 256 KB)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setErrorMsg(null);
      setInitiateResult(null);
      setChunkResult(null);
      setStatusResult(null);
      if (!title || title === 'Test Resumable Video Chunk') {
        setTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleStartProofOfConcept = async () => {
    const selectedChannel = channels.find((c) => c.id === selectedAccountId);
    if (!selectedAccountId || !selectedChannel) {
      setErrorMsg('Please select a connected YouTube channel.');
      return;
    }
    if (!selectedFile) {
      setErrorMsg('Please select a local video file.');
      return;
    }

    setIsProcessing(true);
    setErrorMsg(null);
    setInitiateResult(null);
    setChunkResult(null);
    setStatusResult(null);

    try {
      // ── Step 1: Initiate Resumable Upload Session ───────────────────────────
      setCurrentStep('initiating');
      const initPayload = {
        social_account_id: selectedAccountId,
        title: title.trim() || selectedFile.name,
        description: description.trim(),
        privacy_status: privacyStatus,
        filename: selectedFile.name,
        mime_type: selectedFile.type || 'video/mp4',
        file_size_bytes: selectedFile.size,
      };

      const initRes = await apiClient.post<YouTubeUploadInitiateResponse>(
        '/youtube/upload/initiate',
        initPayload
      );
      const initData = initRes.data;
      setInitiateResult(initData);

      // ── Step 2: Slice FIRST 2 MB Chunk ──────────────────────────────────────
      setCurrentStep('slicing_chunk');
      const totalSize = selectedFile.size;
      const endByte = Math.min(CHUNK_SIZE_BYTES, totalSize);
      const chunkBlob = selectedFile.slice(0, endByte);
      setChunkSizeSent(endByte);

      // ── Step 3: Forward Chunk via Backend Proxy ─────────────────────────────
      setCurrentStep('uploading_chunk');
      const contentRangeHeader = `bytes 0-${endByte - 1}/${totalSize}`;
      const contentTypeHeader = selectedFile.type || 'video/mp4';

      const chunkRes = await apiClient.put<YouTubeUploadChunkResponse>(
        `/youtube/upload/${initData.upload_id}/chunk`,
        chunkBlob,
        {
          headers: {
            'Content-Range': contentRangeHeader,
            'Content-Type': contentTypeHeader,
          },
        }
      );

      setChunkResult(chunkRes.data);
      setCurrentStep('completed_test');
    } catch (err: any) {
      console.error('[YOUTUBE_CHUNK_TEST_ERROR]', err);
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'An error occurred during the chunk upload test.';
      setErrorMsg(msg);
      setCurrentStep('error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleQueryStatus = async () => {
    if (!initiateResult?.upload_id) return;
    setIsQueryingStatus(true);
    try {
      const res = await apiClient.get<YouTubeUploadStatusResponse>(
        `/youtube/upload/${initiateResult.upload_id}/status`
      );
      setStatusResult(res.data);
    } catch (err: any) {
      console.error('[YOUTUBE_STATUS_QUERY_ERROR]', err);
      setErrorMsg(err.response?.data?.detail || 'Failed to query live upload status.');
    } finally {
      setIsQueryingStatus(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
              <Youtube className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>YouTube Resumable Chunk POC</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">
                  Milestone 2A
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Validates server-side authenticated 1-chunk (2 MB) upload & YouTube 308 Range response
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto custom-scrollbar flex-1 text-xs">
          {/* Security Banner */}
          <div className="flex items-start space-x-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="text-emerald-300 font-semibold">Zero Browser Token Exposure:</strong> All Google
              OAuth access tokens and refresh tokens remain 100% server-side. The browser transmits the 2 MB slice to
              FastAPI, which securely forwards it to Google.
            </div>
          </div>

          {/* Form Inputs */}
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
                disabled={isProcessing || channels.length === 0}
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
                disabled={isProcessing}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none"
              >
                <option value="private">Private (Recommended for testing)</option>
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
                disabled={isProcessing}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none"
                placeholder="Enter test video title"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isProcessing}
                rows={2}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-xs focus:ring-1 focus:ring-red-500 focus:outline-none resize-none"
                placeholder="Enter video description"
              />
            </div>
          </div>

          {/* File Picker */}
          <div className="space-y-1.5">
            <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider">
              Select Local Test Video
            </label>
            <div className="p-4 border-2 border-dashed border-slate-700 hover:border-red-500 rounded-xl bg-slate-950/40 transition text-center cursor-pointer relative group">
              <input
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                disabled={isProcessing}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <div className="flex flex-col items-center space-y-1.5">
                <FileVideo className="w-6 h-6 text-slate-400 group-hover:text-red-400 transition" />
                {selectedFile ? (
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold text-slate-200">{selectedFile.name}</p>
                    <p className="text-[10px] text-slate-400">
                      Total Size: {formatBytes(selectedFile.size)} • First Chunk to send:{' '}
                      <span className="text-red-400 font-mono font-bold">
                        {formatBytes(Math.min(CHUNK_SIZE_BYTES, selectedFile.size))}
                      </span>
                    </p>
                  </div>
                ) : (
                  <div>
                    <span className="text-xs font-semibold text-slate-300 group-hover:text-white">
                      Click to choose video file (MP4, MOV, etc.)
                    </span>
                    <p className="text-[10px] text-slate-500">Only the first 2 MB chunk will be uploaded</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Error Alert */}
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Results Panel */}
          {(initiateResult || chunkResult) && (
            <div className="space-y-3 p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <h4 className="text-xs font-bold text-slate-200 flex items-center space-x-2 border-b border-slate-800 pb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>POC Test Results</span>
              </h4>

              {/* Step 1 Result */}
              {initiateResult && (
                <div className="space-y-1 text-[11px] font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <div className="text-emerald-400 font-bold flex items-center space-x-1.5">
                    <Check className="w-3.5 h-3.5" />
                    <span>1. Resumable Session Created</span>
                  </div>
                  <div className="text-slate-400 grid grid-cols-2 gap-1 pt-1">
                    <span>Session ID:</span>
                    <span className="text-slate-200 truncate">{initiateResult.upload_id}</span>
                    <span>Channel ID:</span>
                    <span className="text-slate-200">{initiateResult.channel_id}</span>
                    <span>File Size:</span>
                    <span className="text-slate-200">{formatBytes(initiateResult.file_size_bytes)}</span>
                  </div>
                </div>
              )}

              {/* Step 2 Result */}
              {chunkResult && (
                <div className="space-y-1.5 text-[11px] font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <div className="flex items-center justify-between">
                    <div className="text-emerald-400 font-bold flex items-center space-x-1.5">
                      <Check className="w-3.5 h-3.5" />
                      <span>
                        {chunkResult.is_complete
                          ? `2. Upload Completed (${formatBytes(chunkResult.total_bytes || (selectedFile?.size ?? chunkSizeSent))})`
                          : `2. Chunk 1 Uploaded (${formatBytes(chunkSizeSent)})`}
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        chunkResult.http_status === 308
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      }`}
                    >
                      HTTP {chunkResult.http_status} {chunkResult.status}
                    </span>
                  </div>

                  <div className="text-slate-400 space-y-1 pt-1">
                    <div className="flex justify-between">
                      <span>YouTube Range Header:</span>
                      <span className={chunkResult.range_header ? 'text-amber-300 font-bold' : 'text-slate-400'}>
                        {chunkResult.range_header || (chunkResult.is_complete ? 'None (Upload Completed)' : 'None')}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Confirmed Bytes Stored:</span>
                      <span className="text-slate-200 font-bold">
                        {chunkResult.is_complete
                          ? formatBytes(chunkResult.total_bytes || (selectedFile?.size ?? 0))
                          : chunkResult.last_byte_received !== null && chunkResult.last_byte_received !== undefined
                          ? formatBytes(chunkResult.last_byte_received + 1)
                          : '0 B'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Authoritative Next Offset:</span>
                      <span className={chunkResult.is_complete ? 'text-slate-400' : 'text-emerald-400 font-bold'}>
                        {chunkResult.is_complete
                          ? 'N/A'
                          : chunkResult.next_byte_offset !== null && chunkResult.next_byte_offset !== undefined
                          ? `${chunkResult.next_byte_offset} (Byte ${chunkResult.next_byte_offset})`
                          : 'N/A'}
                      </span>
                    </div>
                    {chunkResult.is_complete && chunkResult.video_id && (
                      <div className="flex justify-between pt-1 border-t border-slate-800">
                        <span>Video URL:</span>
                        <a
                          href={chunkResult.video_url || '#'}
                          target="_blank"
                          rel="noreferrer"
                          className="text-red-400 underline font-semibold"
                        >
                          {chunkResult.video_url}
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Optional: Check Live Status button */}
              {initiateResult && (
                <div className="pt-2 flex items-center justify-between border-t border-slate-800">
                  <span className="text-[10px] text-slate-400">
                    Query Google upload status directly (GET /upload/{'{id}'}/status):
                  </span>
                  <button
                    onClick={handleQueryStatus}
                    disabled={isQueryingStatus}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition flex items-center space-x-1.5 disabled:opacity-50"
                  >
                    {isQueryingStatus ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3 h-3" />
                    )}
                    <span>Query Live Status</span>
                  </button>
                </div>
              )}

              {statusResult && (
                <div className="text-[10px] font-mono bg-slate-900 p-2.5 rounded border border-slate-800 text-slate-300 space-y-1">
                  <div>Live YouTube Status: <span className="text-amber-300 font-bold">{statusResult.status} (HTTP {statusResult.http_status})</span></div>
                  <div>Confirmed Range: <span className="text-emerald-400">{statusResult.range_header || (statusResult.is_complete ? 'None (Upload Completed)' : 'None')}</span></div>
                  <div>Confirmed Bytes Stored: <span className="text-slate-100">{statusResult.is_complete ? formatBytes(statusResult.file_size_bytes) : (statusResult.last_byte_received !== null && statusResult.last_byte_received !== undefined ? formatBytes(statusResult.last_byte_received + 1) : '0 B')}</span></div>
                  <div>Next Expected Byte: <span className="text-slate-100">{statusResult.is_complete ? 'N/A' : (statusResult.next_byte_offset ?? 'N/A')}</span></div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            disabled={isProcessing}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition"
          >
            Close
          </button>

          <button
            type="button"
            onClick={handleStartProofOfConcept}
            disabled={isProcessing || !selectedFile || channels.length === 0 || !selectedAccountId}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs transition flex items-center space-x-2 shadow-lg shadow-red-500/25 disabled:opacity-50"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>
                  {currentStep === 'initiating'
                    ? 'Creating Session...'
                    : currentStep === 'slicing_chunk'
                    ? 'Slicing 2 MB...'
                    : 'Transmitting Chunk 1...'}
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4" />
                <span>Run 1-Chunk POC Test</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
