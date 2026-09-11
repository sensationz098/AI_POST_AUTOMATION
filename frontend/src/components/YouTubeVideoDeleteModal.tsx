'use client';

import React, { useState } from 'react';
import {
  X,
  Trash2,
  AlertTriangle,
  Loader2,
  Film,
  Globe,
  EyeOff,
  Lock,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { YouTubeVideoItem, YouTubeVideoDeleteResponse } from '@/lib/types';
import toast from 'react-hot-toast';

export interface YouTubeVideoDeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  video: YouTubeVideoItem | null;
  channelTitle?: string | null;
  socialAccountId?: number | null;
  onVideoDeleted: (videoId: string) => void;
}

export function YouTubeVideoDeleteModal({
  isOpen,
  onClose,
  video,
  channelTitle,
  socialAccountId,
  onVideoDeleted,
}: YouTubeVideoDeleteModalProps) {
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !video) return null;

  const handleDelete = async () => {
    setIsDeleting(true);
    setErrorMsg(null);

    const params: Record<string, any> = {};
    if (socialAccountId) {
      params.social_account_id = socialAccountId;
    }

    try {
      const res = await apiClient.delete<YouTubeVideoDeleteResponse>(
        `/youtube/videos/${video.video_id}`,
        { params }
      );
      toast.success(res.data.message || 'Video permanently deleted from YouTube!');
      onVideoDeleted(video.video_id);
      onClose();
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Failed to delete video from YouTube. Please try again.';
      setErrorMsg(msg);
      toast.error(msg);
    } finally {
      setIsDeleting(false);
    }
  };

  const renderPrivacyBadge = (status?: string | null) => {
    const s = (status || 'private').toLowerCase();
    if (s === 'public') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-950/80 border border-emerald-800/80 text-emerald-300 text-[10px] font-bold uppercase tracking-wider">
          <Globe className="w-2.5 h-2.5" />
          <span>Public</span>
        </span>
      );
    }
    if (s === 'unlisted') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-amber-950/80 border border-amber-800/80 text-amber-300 text-[10px] font-bold uppercase tracking-wider">
          <EyeOff className="w-2.5 h-2.5" />
          <span>Unlisted</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-800/80 text-indigo-300 text-[10px] font-bold uppercase tracking-wider">
        <Lock className="w-2.5 h-2.5" />
        <span>Private</span>
      </span>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-video-title"
    >
      <div
        className="w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-slate-200 animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center justify-center shadow-inner">
              <Trash2 className="w-5 h-5" />
            </div>
            <div>
              <h2 id="delete-video-title" className="text-base font-bold text-white tracking-tight">
                Delete YouTube Video
              </h2>
              <p className="text-xs text-slate-400">
                Permanent deletion on YouTube channel {channelTitle ? `"${channelTitle}"` : ''}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
            title="Cancel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto">
          {/* Warning Banner */}
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-200 text-xs flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold text-rose-100">This action is permanent and cannot be undone.</p>
              <p className="text-slate-300 leading-relaxed">
                The video, along with its comments, likes, and analytics, will be permanently removed from your connected YouTube channel.
              </p>
            </div>
          </div>

          {/* Video Preview Card */}
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/90 space-y-3">
            <div className="flex space-x-3.5 items-start">
              {/* Thumbnail */}
              <div className="relative w-28 aspect-video rounded-lg overflow-hidden bg-black flex-shrink-0 border border-slate-800">
                {video.thumbnail_url ? (
                  <img
                    src={video.thumbnail_url}
                    alt={video.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-600">
                    <Film className="w-6 h-6" />
                  </div>
                )}
                <div className="absolute top-1 left-1">
                  {renderPrivacyBadge(video.privacy_status)}
                </div>
              </div>

              {/* Info */}
              <div className="min-w-0 flex-1 space-y-1">
                <h3 className="text-xs font-bold text-white line-clamp-2 leading-snug">
                  {video.title || 'Untitled Video'}
                </h3>
                <p className="text-[11px] text-slate-400 font-mono">
                  ID: <span className="text-slate-300">{video.video_id}</span>
                </p>
                {channelTitle && (
                  <p className="text-[11px] text-slate-400 truncate">
                    Channel: <span className="text-slate-300 font-medium">{channelTitle}</span>
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Error Message */}
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">Deletion Error</p>
                <p className="text-slate-300 text-[11px] mt-0.5">{errorMsg}</p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition border border-slate-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-lg shadow-rose-950/40 disabled:opacity-50"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Deleting from YouTube...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                <span>Delete Permanently</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
