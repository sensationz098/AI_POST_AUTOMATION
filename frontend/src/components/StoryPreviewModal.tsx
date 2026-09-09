'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Send,
  Trash2,
  ExternalLink,
  Sparkles,
  Film,
  Image as ImageIcon,
  Layers,
  Share2,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Info,
  ShieldCheck
} from 'lucide-react';
import { SchedulerItem, SocialAccount } from '@/lib/types';
import { PostStatusBadge } from '@/components/PostStatusBadge';
import { getValidStoryUrls } from '@/lib/storyUrlHelper';

interface StoryPreviewModalProps {
  item: SchedulerItem | null;
  isOpen: boolean;
  onClose: () => void;
  onRetry?: (storyId: number) => Promise<void>;
  onPublishNow?: (storyId: number) => Promise<void>;
  onDelete?: (story: SchedulerItem) => void;
  userTimeZone?: string;
}

export function StoryPreviewModal({
  item,
  isOpen,
  onClose,
  onRetry,
  onPublishNow,
  onDelete,
  userTimeZone = 'Local Time'
}: StoryPreviewModalProps) {
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (isOpen && videoRef.current) {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  }, [isOpen, item]);

  if (!isOpen || !item) return null;

  const isVideo = item.media_type === 'video' || (item.media_url && Boolean(item.media_url.match(/\.(mp4|mov|webm)$/i)));

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const formatToLocalDateTime = (dateStr?: string) => {
    if (!dateStr) return '—';
    const normalizedStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : `${dateStr}Z`;
    const date = new Date(normalizedStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/85 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col md:flex-row max-h-[92vh]">
        
        {/* Left: 9:16 Vertical Mobile Phone Mockup */}
        <div className="w-full md:w-[380px] bg-slate-950 p-4 flex flex-col items-center justify-center border-b md:border-b-0 md:border-r border-slate-800/80 relative flex-shrink-0">
          <div className="relative w-[260px] h-[462px] sm:w-[280px] sm:h-[498px] rounded-[32px] overflow-hidden border-[6px] border-slate-800 bg-black shadow-2xl flex flex-col justify-between select-none">
            
            {/* Instagram Story Top Header Bar */}
            <div className="absolute top-0 inset-x-0 z-20 p-3 bg-gradient-to-b from-black/80 via-black/40 to-transparent">
              {/* Progress Bar Segment */}
              <div className="w-full h-1 bg-white/30 rounded-full overflow-hidden mb-2.5">
                <div className="w-full h-full bg-white rounded-full animate-pulse" />
              </div>

              {/* User / Brand Profile Bar */}
              <div className="flex items-center justify-between text-white">
                <div className="flex items-center space-x-2">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-amber-500 via-rose-500 to-fuchsia-600 p-[1.5px]">
                    <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center text-[10px] font-bold text-white uppercase">
                      ST
                    </div>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold text-white flex items-center space-x-1 drop-shadow">
                      <span>Story #{item.id}</span>
                    </p>
                    <p className="text-[9px] text-white/70">
                      {item.scheduled_at ? formatToLocalDateTime(item.scheduled_at) : 'Active Story'}
                    </p>
                  </div>
                </div>

                {/* Video controls */}
                {isVideo && (
                  <div className="flex items-center space-x-1.5">
                    <button
                      type="button"
                      onClick={toggleMute}
                      className="p-1 rounded-full bg-black/40 hover:bg-black/70 text-white transition"
                    >
                      {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      type="button"
                      onClick={togglePlay}
                      className="p-1 rounded-full bg-black/40 hover:bg-black/70 text-white transition"
                    >
                      {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Main Media Content in 9:16 Canvas */}
            <div className="w-full h-full relative flex items-center justify-center bg-slate-950">
              {isVideo ? (
                <video
                  ref={videoRef}
                  src={item.media_url}
                  className="w-full h-full object-cover"
                  autoPlay
                  loop
                  playsInline
                  muted={isMuted}
                  onClick={togglePlay}
                />
              ) : item.media_url ? (
                <img
                  src={item.media_url}
                  alt={item.title || 'Story Media'}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-slate-500 space-y-2 p-4 text-center">
                  <ImageIcon className="w-10 h-10" />
                  <span className="text-xs">No media URL available</span>
                </div>
              )}

              {/* Caption Overlay (if exists) */}
              {item.caption && (
                <div className="absolute bottom-10 inset-x-3 z-20">
                  <div className="p-2 rounded-xl bg-black/60 backdrop-blur-md border border-white/10 text-white text-[11px] leading-snug">
                    {item.caption}
                  </div>
                </div>
              )}
            </div>

            {/* Bottom 9:16 Safe Area Indicator */}
            <div className="absolute bottom-0 inset-x-0 p-2 text-center bg-gradient-to-t from-black/80 to-transparent z-10">
              <span className="text-[9px] font-mono text-white/50">9:16 Story Aspect</span>
            </div>
          </div>
        </div>

        {/* Right: Story Metadata & Actions Inspector */}
        <div className="flex-1 p-5 md:p-6 flex flex-col justify-between overflow-y-auto space-y-5">
          
          <div className="space-y-4">
            {/* Top Bar: Title & Close */}
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 rounded-full bg-gradient-to-r from-fuchsia-600 to-indigo-600 text-white text-[10px] font-extrabold uppercase tracking-wider shadow-sm flex items-center space-x-1">
                    <Sparkles className="w-3 h-3 text-fuchsia-300" />
                    <span>STORY</span>
                  </span>
                  <PostStatusBadge status={item.status} />
                  <span className="text-xs font-mono text-slate-500 font-bold">#{item.id}</span>
                </div>
                <h2 className="text-base font-bold text-slate-100 mt-1">
                  {item.title || item.caption || `Story #${item.id}`}
                </h2>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error or Warnings Banner */}
            {item.last_error && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-bold text-[11px] text-rose-200">Publishing Status Notice</p>
                  <p className="text-[11px] leading-relaxed">{item.last_error}</p>
                </div>
              </div>
            )}

            {/* Timing Information */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1">
                  <Clock className="w-3 h-3 text-indigo-400" />
                  <span>Scheduled Time</span>
                </p>
                <p className="text-xs font-mono font-semibold text-slate-200">
                  {formatToLocalDateTime(item.scheduled_at)}
                </p>
                <p className="text-[9px] text-slate-500">Timezone: {userTimeZone}</p>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>Published Time</span>
                </p>
                <p className="text-xs font-mono font-semibold text-slate-200">
                  {formatToLocalDateTime(item.published_at)}
                </p>
                <p className="text-[9px] text-slate-500">
                  {item.status === 'PUBLISHED' ? '24h Story Live' : 'Not yet published'}
                </p>
              </div>
            </div>

            {/* Authoritative Target Accounts Section */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2.5">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Authoritative Destination Targets ({item.target_account_ids.length})</span>
                </p>
                <span className="text-[9px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-medium">
                  Strict Target Isolation Active
                </span>
              </div>

              <p className="text-[11px] text-slate-400">
                This Story publishes exclusively to the following selected social accounts:
              </p>

              {item.target_accounts && item.target_accounts.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {item.target_accounts.map((acc) => (
                    <div
                      key={acc.id}
                      className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between space-x-2"
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <span
                          className={`w-2 h-2 rounded-full flex-shrink-0 ${
                            acc.platform === 'facebook' ? 'bg-blue-500 shadow-blue-500/50' : 'bg-pink-500 shadow-pink-500/50'
                          } shadow-sm`}
                        />
                        <div className="truncate">
                          <p className="text-xs font-semibold text-slate-200 truncate">{acc.account_name}</p>
                          <p className="text-[10px] text-slate-500 font-mono capitalize">
                            {acc.platform} {acc.platform === 'facebook' ? 'Page' : 'Business'}
                          </p>
                        </div>
                      </div>
                      <span className="text-[9px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                        ID: {acc.id}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center space-x-2 text-xs text-slate-400">
                  {item.platforms.map((p) => (
                    <span
                      key={p}
                      className="px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 font-mono text-[10px] text-slate-300 capitalize"
                    >
                      {p}
                    </span>
                  ))}
                  <span className="text-[10px] font-mono text-slate-500">
                    (Target IDs: {item.target_account_ids.join(', ') || 'None'})
                  </span>
                </div>
              )}
            </div>

            {/* Published External IDs & Live Platform Links */}
            {(item.fb_id || item.ig_id) && (() => {
              const { fbUrl, igUrl, hasFb, hasIg } = getValidStoryUrls(item);
              return (
                <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 space-y-1.5 text-xs">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Live Platform Links & Published Meta IDs
                  </p>
                  <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                    {item.fb_id && (
                      hasFb ? (
                        <a
                          href={fbUrl!}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center space-x-1.5 bg-blue-950/50 hover:bg-blue-900/60 border border-blue-800/60 text-blue-300 px-2.5 py-1 rounded-lg transition"
                          title="Open Facebook Story in new tab"
                        >
                          <ExternalLink className="w-3 h-3 text-blue-400" />
                          <span className="font-bold">FB Story:</span>
                          <span>{item.fb_id}</span>
                        </a>
                      ) : (
                        <div
                          className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-lg"
                          title="Story ID published (Direct URL unavailable from Meta)"
                        >
                          <span className="font-bold text-slate-300">FB Story:</span>
                          <span>{item.fb_id}</span>
                          <span className="text-[9px] text-slate-500">(Direct link unavailable)</span>
                        </div>
                      )
                    )}
                    {item.ig_id && (
                      hasIg ? (
                        <a
                          href={igUrl!}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center space-x-1.5 bg-pink-950/50 hover:bg-pink-900/60 border border-pink-800/60 text-pink-300 px-2.5 py-1 rounded-lg transition"
                          title="Open Instagram Story in new tab"
                        >
                          <ExternalLink className="w-3 h-3 text-pink-400" />
                          <span className="font-bold">IG Story:</span>
                          <span>{item.ig_id}</span>
                        </a>
                      ) : (
                        <div
                          className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-lg"
                          title="Story ID published (Username unavailable for direct link)"
                        >
                          <span className="font-bold text-slate-300">IG Story:</span>
                          <span>{item.ig_id}</span>
                          <span className="text-[9px] text-slate-500">(Username unavailable)</span>
                        </div>
                      )
                    )}
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Bottom Action Footer */}
          <div className="pt-4 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2.5">
            {onDelete && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onDelete(item);
                }}
                className="px-3 py-1.5 rounded-xl bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/50 text-rose-300 text-xs font-semibold transition flex items-center space-x-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{item.status === 'SCHEDULED' ? 'Cancel Schedule' : 'Delete Record'}</span>
              </button>
            )}

            <div className="flex items-center space-x-2 ml-auto">
              {item.status === 'FAILED' && onRetry && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={async () => {
                    setActionLoading(true);
                    try {
                      await onRetry(item.id);
                      onClose();
                    } finally {
                      setActionLoading(false);
                    }
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-rose-900/40 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? 'animate-spin' : ''}`} />
                  <span>Retry Publish</span>
                </button>
              )}

              {item.status === 'DRAFT' && onPublishNow && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={async () => {
                    setActionLoading(true);
                    try {
                      await onPublishNow(item.id);
                      onClose();
                    } finally {
                      setActionLoading(false);
                    }
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-emerald-900/40 disabled:opacity-50"
                >
                  <Send className={`w-3.5 h-3.5 ${actionLoading ? 'animate-spin' : ''}`} />
                  <span>Publish Story Now</span>
                </button>
              )}

              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
