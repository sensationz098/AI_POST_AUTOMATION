'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Youtube,
  Film,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Image as ImageIcon,
  Tag,
  Globe,
  EyeOff,
  Lock,
  UserCheck,
  RefreshCw,
  ExternalLink,
  Upload,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import {
  YouTubeVideoDetailResponse,
  YouTubeVideoUpdateRequest,
  YouTubeThumbnailUploadResponse,
  YOUTUBE_CATEGORIES,
} from '@/lib/types';
import toast from 'react-hot-toast';

export interface YouTubeVideoEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoId: string;
  channelTitle?: string | null;
  onVideoUpdated?: (updated: YouTubeVideoDetailResponse) => void;
}

export function YouTubeVideoEditModal({
  isOpen,
  onClose,
  videoId,
  channelTitle,
  onVideoUpdated,
}: YouTubeVideoEditModalProps) {
  // Loading & State
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form Fields
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState<string>('');
  const [categoryId, setCategoryId] = useState<string>('28');
  const [privacyStatus, setPrivacyStatus] = useState<'public' | 'unlisted' | 'private'>('public');
  const [madeForKids, setMadeForKids] = useState<boolean>(false);

  // Thumbnail State
  const [currentThumbnailUrl, setCurrentThumbnailUrl] = useState<string | null>(null);
  const [newThumbnailUrl, setNewThumbnailUrl] = useState<string | null>(null);
  const [newThumbnailPreviewUrl, setNewThumbnailPreviewUrl] = useState<string | null>(null);
  const [thumbnailUploading, setThumbnailUploading] = useState<boolean>(false);
  const [thumbnailValidationError, setThumbnailValidationError] = useState<string | null>(null);
  const thumbnailInputRef = useRef<HTMLInputElement | null>(null);

  // Video metadata details
  const [videoData, setVideoData] = useState<YouTubeVideoDetailResponse | null>(null);

  // Fetch initial video metadata when modal opens
  useEffect(() => {
    if (!isOpen || !videoId) return;

    let isMounted = true;
    setIsLoading(true);
    setErrorMsg(null);

    apiClient
      .get<YouTubeVideoDetailResponse>(`/youtube/videos/${videoId}`)
      .then((res) => {
        if (!isMounted) return;
        const data = res.data;
        setVideoData(data);
        setTitle(data.title || '');
        setDescription(data.description || '');
        setTags(data.tags || []);
        setCategoryId(data.category_id || '28');
        setPrivacyStatus((data.privacy_status as any) || 'public');
        setMadeForKids(Boolean(data.made_for_kids));
        setCurrentThumbnailUrl(data.thumbnail_url || null);
        setNewThumbnailUrl(null);
        setNewThumbnailPreviewUrl(null);
      })
      .catch((err) => {
        if (!isMounted) return;
        const msg = err.response?.data?.detail || err.message || 'Failed to load video metadata.';
        setErrorMsg(msg);
        toast.error(`Error loading video: ${msg}`);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
      if (newThumbnailPreviewUrl && newThumbnailPreviewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(newThumbnailPreviewUrl);
      }
    };
  }, [isOpen, videoId]);

  if (!isOpen) return null;

  // Add tag handler
  const handleAddTag = () => {
    const trimmed = tagInput.trim().replace(/^#/, '');
    if (!trimmed) return;
    if (tags.length >= 30) {
      toast.error('Maximum 30 tags allowed.');
      return;
    }
    if (!tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  // Thumbnail selection & upload
  const handleThumbnailChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setThumbnailValidationError(null);

      const validMimes = ['image/jpeg', 'image/png', 'image/jpg'];
      const isValidExt = file.name.match(/\.(jpe?g|png)$/i);
      if (!validMimes.includes(file.type) && !isValidExt) {
        setThumbnailValidationError('Custom thumbnails must be JPEG or PNG format.');
        return;
      }

      if (file.size > 2 * 1024 * 1024) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        setThumbnailValidationError(`Thumbnail size (${sizeMb} MB) exceeds maximum allowed limit of 2 MB.`);
        return;
      }

      // Local preview
      const preview = URL.createObjectURL(file);
      setNewThumbnailPreviewUrl(preview);

      // Upload via existing trusted endpoint
      try {
        setThumbnailUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        const res = await apiClient.post<YouTubeThumbnailUploadResponse>('/youtube/upload-thumbnail', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setNewThumbnailUrl(res.data.thumbnail_url);
        toast.success('Thumbnail uploaded and ready to apply!');
      } catch (uploadErr: any) {
        const errDetail = uploadErr.response?.data?.detail || 'Failed to upload thumbnail.';
        setThumbnailValidationError(errDetail);
        toast.error(errDetail);
      } finally {
        setThumbnailUploading(false);
      }
    }
  };

  const handleRemoveCustomThumbnail = () => {
    setNewThumbnailUrl(null);
    if (newThumbnailPreviewUrl && newThumbnailPreviewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(newThumbnailPreviewUrl);
    }
    setNewThumbnailPreviewUrl(null);
    if (thumbnailInputRef.current) {
      thumbnailInputRef.current.value = '';
    }
  };

  // Save changes handler
  const handleSaveChanges = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      toast.error('Video title is required.');
      return;
    }
    if (title.length > 100) {
      toast.error('Video title must be 100 characters or less.');
      return;
    }
    if (description.length > 5000) {
      toast.error('Video description must be 5000 characters or less.');
      return;
    }

    setIsSaving(true);
    setErrorMsg(null);

    const payload: YouTubeVideoUpdateRequest = {
      title: title.trim(),
      description: description.trim(),
      tags: tags,
      category_id: categoryId,
      privacy_status: privacyStatus,
      made_for_kids: madeForKids,
      ...(newThumbnailUrl ? { thumbnail_url: newThumbnailUrl } : {}),
    };

    try {
      const res = await apiClient.put<YouTubeVideoDetailResponse>(`/youtube/videos/${videoId}`, payload);
      const updated = res.data;
      toast.success('YouTube video details updated successfully!');
      if (onVideoUpdated) {
        onVideoUpdated(updated);
      }
      onClose();
    } catch (saveErr: any) {
      const msg = saveErr.response?.data?.detail || saveErr.message || 'Failed to update video metadata.';
      setErrorMsg(msg);
      toast.error(`Update failed: ${msg}`);
    } finally {
      setIsSaving(false);
    }
  };

  const displayedThumbnail = newThumbnailPreviewUrl || newThumbnailUrl || currentThumbnailUrl;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/50 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-red-600/10 text-red-400 border border-red-500/20">
              <Youtube className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Edit YouTube Video</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono font-normal">
                  {videoId}
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                {channelTitle || videoData?.channel_title || 'Connected YouTube Channel'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {isLoading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-red-500" />
              <p className="text-xs font-semibold">Loading current video metadata from YouTube...</p>
            </div>
          ) : errorMsg && !videoData ? (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold">Failed to load video</p>
                <p>{errorMsg}</p>
                <button
                  type="button"
                  onClick={() => {
                    setIsLoading(true);
                    setErrorMsg(null);
                    apiClient
                      .get<YouTubeVideoDetailResponse>(`/youtube/videos/${videoId}`)
                      .then((res) => {
                        setVideoData(res.data);
                        setTitle(res.data.title || '');
                        setDescription(res.data.description || '');
                        setTags(res.data.tags || []);
                        setCategoryId(res.data.category_id || '28');
                        setPrivacyStatus((res.data.privacy_status as any) || 'public');
                        setMadeForKids(Boolean(res.data.made_for_kids));
                        setCurrentThumbnailUrl(res.data.thumbnail_url || null);
                      })
                      .catch((e) => setErrorMsg(e.response?.data?.detail || e.message))
                      .finally(() => setIsLoading(false));
                  }}
                  className="mt-2 px-3 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-200 rounded-lg text-xs font-semibold flex items-center space-x-1"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Try Again</span>
                </button>
              </div>
            </div>
          ) : (
            <form id="edit-youtube-video-form" onSubmit={handleSaveChanges} className="space-y-6">
              {/* Error Banner if update error occurs */}
              {errorMsg && (
                <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-2.5">
                  <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Top Row: Video Preview & Thumbnail */}
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-5 p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                {/* Thumbnail Display (5 Cols) */}
                <div className="sm:col-span-5 space-y-2">
                  <label className="block text-xs font-bold text-slate-300">
                    Video Thumbnail
                  </label>
                  <div className="relative aspect-video rounded-xl overflow-hidden bg-black border border-slate-800 flex items-center justify-center">
                    {displayedThumbnail ? (
                      <img
                        src={displayedThumbnail}
                        alt="Video Thumbnail"
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center text-slate-500 text-xs space-y-1">
                        <ImageIcon className="w-8 h-8 text-slate-600" />
                        <span>No Thumbnail</span>
                      </div>
                    )}

                    {thumbnailUploading && (
                      <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center text-xs text-white space-y-1">
                        <Loader2 className="w-6 h-6 animate-spin text-red-500" />
                        <span>Uploading thumbnail...</span>
                      </div>
                    )}
                  </div>

                  {/* Thumbnail Controls */}
                  <div className="flex items-center space-x-2 pt-1">
                    <input
                      ref={thumbnailInputRef}
                      type="file"
                      accept="image/jpeg,image/png,image/jpg"
                      onChange={handleThumbnailChange}
                      className="hidden"
                      id="edit-video-thumbnail-input"
                    />
                    <button
                      type="button"
                      onClick={() => thumbnailInputRef.current?.click()}
                      disabled={thumbnailUploading || isSaving}
                      className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center justify-center space-x-1 border border-slate-700 disabled:opacity-50"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>{displayedThumbnail ? 'Change Thumbnail' : 'Upload Thumbnail'}</span>
                    </button>

                    {newThumbnailUrl && (
                      <button
                        type="button"
                        onClick={handleRemoveCustomThumbnail}
                        className="py-1.5 px-2.5 rounded-lg bg-slate-800/80 hover:bg-rose-950/60 hover:text-rose-300 hover:border-rose-800 text-slate-400 text-xs transition border border-slate-700"
                        title="Revert to existing thumbnail"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  {thumbnailValidationError && (
                    <p className="text-[11px] text-rose-400 font-medium">{thumbnailValidationError}</p>
                  )}
                  <p className="text-[10px] text-slate-500">
                    JPEG or PNG, max 2 MB. Recommended 16:9 (1280x720).
                  </p>
                </div>

                {/* Quick Info & YouTube Link (7 Cols) */}
                <div className="sm:col-span-7 flex flex-col justify-between space-y-3">
                  <div className="space-y-1.5">
                    <span className="text-[10px] uppercase font-bold text-red-400 tracking-wider">
                      Published Video
                    </span>
                    <h3 className="text-sm font-bold text-white line-clamp-2 leading-snug">
                      {title || 'Untitled Video'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      Channel: <strong className="text-slate-300">{channelTitle || videoData?.channel_title}</strong>
                    </p>
                  </div>

                  {videoData?.video_url && (
                    <div className="pt-2 border-t border-slate-800/80">
                      <a
                        href={videoData.video_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1.5 text-xs text-red-400 hover:text-red-300 font-semibold"
                      >
                        <Film className="w-3.5 h-3.5" />
                        <span>Watch on YouTube</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Title Field with live character counter */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-200 flex items-center space-x-1">
                    <span>Title</span>
                    <span className="text-red-400">*</span>
                  </label>
                  <span className={`text-[11px] font-mono ${title.length > 100 ? 'text-rose-400 font-bold' : 'text-slate-400'}`}>
                    {title.length}/100
                  </span>
                </div>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={100}
                  placeholder="Enter video title..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition"
                  required
                />
              </div>

              {/* Description Field with character counter */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-200">Description</label>
                  <span className={`text-[11px] font-mono ${description.length > 5000 ? 'text-rose-400 font-bold' : 'text-slate-400'}`}>
                    {description.length}/5000
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={5000}
                  placeholder="Tell viewers about your video..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition resize-y"
                />
              </div>

              {/* Category & Visibility Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Category Selection */}
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">Category</label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500 transition"
                  >
                    {YOUTUBE_CATEGORIES.map((cat) => (
                      <option key={cat.id} value={cat.id} className="bg-slate-900 text-white">
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Privacy Visibility */}
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">Visibility</label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setPrivacyStatus('public')}
                      className={`p-2 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 border transition ${
                        privacyStatus === 'public'
                          ? 'bg-red-600/20 text-red-300 border-red-500/50 font-bold'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>Public</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setPrivacyStatus('unlisted')}
                      className={`p-2 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 border transition ${
                        privacyStatus === 'unlisted'
                          ? 'bg-amber-600/20 text-amber-300 border-amber-500/50 font-bold'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <EyeOff className="w-3.5 h-3.5" />
                      <span>Unlisted</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setPrivacyStatus('private')}
                      className={`p-2 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 border transition ${
                        privacyStatus === 'private'
                          ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/50 font-bold'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <Lock className="w-3.5 h-3.5" />
                      <span>Private</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Tags Input */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
                    <Tag className="w-3.5 h-3.5 text-slate-400" />
                    <span>Tags</span>
                  </label>
                  <span className="text-[11px] text-slate-400 font-mono">{tags.length}/30 tags</span>
                </div>

                {/* Tag Pills */}
                <div className="flex flex-wrap gap-1.5 min-h-[36px] p-2 rounded-xl bg-slate-950 border border-slate-800">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 text-xs font-medium border border-slate-700"
                    >
                      <span>#{tag}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="text-slate-400 hover:text-rose-400 ml-1"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}

                  <div className="inline-flex items-center space-x-1 flex-1 min-w-[120px]">
                    <input
                      type="text"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ',') {
                          e.preventDefault();
                          handleAddTag();
                        }
                      }}
                      placeholder="Add tag and press Enter..."
                      className="bg-transparent text-xs text-white placeholder-slate-600 focus:outline-none w-full px-1"
                    />
                  </div>
                </div>
              </div>

              {/* Audience / Made for Kids Declaration (COPPA) */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
                <label className="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
                  <UserCheck className="w-4 h-4 text-indigo-400" />
                  <span>Audience (COPPA Declaration)</span>
                </label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2.5 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="radio"
                      name="editMadeForKids"
                      checked={madeForKids === true}
                      onChange={() => setMadeForKids(true)}
                      className="text-red-600 focus:ring-red-500 bg-slate-900 border-slate-700"
                    />
                    <span>Yes, it&apos;s made for kids (features like comments and personalized ads are disabled)</span>
                  </label>
                  <label className="flex items-center space-x-2.5 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="radio"
                      name="editMadeForKids"
                      checked={madeForKids === false}
                      onChange={() => setMadeForKids(false)}
                      className="text-red-600 focus:ring-red-500 bg-slate-900 border-slate-700"
                    />
                    <span>No, it&apos;s not made for kids</span>
                  </label>
                </div>
              </div>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/50 flex-shrink-0">
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition disabled:opacity-50"
          >
            Cancel
          </button>

          <button
            type="submit"
            form="edit-youtube-video-form"
            disabled={isLoading || isSaving || !title.trim()}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold transition flex items-center space-x-2 shadow-lg shadow-red-600/25 disabled:opacity-40"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Saving Changes...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
