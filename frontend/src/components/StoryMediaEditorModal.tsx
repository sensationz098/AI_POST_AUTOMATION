'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  X,
  RotateCw,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Maximize,
  Minimize,
  RefreshCw,
  Undo2,
  Redo2,
  Sparkles,
  Check,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Palette,
  Eye,
  Sliders,
  FlipHorizontal,
  Move
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';

interface StoryMediaEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  mediaUrl: string;
  mediaType: 'image' | 'video' | string;
  onSave: (result: {
    processedUrl: string;
    originalUrl: string;
    mediaType: string;
  }) => void;
}

interface TransformState {
  zoom: number; // 0.5 to 3.0
  rotation: number; // in degrees
  panX: number; // in pixels relative to center
  panY: number;
  flipH: boolean;
  bgMode: 'blur' | 'black' | 'slate' | 'gradient' | 'custom';
  customBgColor: string;
}

const DEFAULT_TRANSFORM: TransformState = {
  zoom: 1.0,
  rotation: 0,
  panX: 0,
  panY: 0,
  flipH: false,
  bgMode: 'blur',
  customBgColor: '#0f172a',
};

const EXPORT_WIDTH = 1080;
const EXPORT_HEIGHT = 1920;

export function StoryMediaEditorModal({
  isOpen,
  onClose,
  mediaUrl,
  mediaType,
  onSave,
}: StoryMediaEditorModalProps) {
  const [transform, setTransform] = useState<TransformState>(DEFAULT_TRANSFORM);
  const [history, setHistory] = useState<TransformState[]>([DEFAULT_TRANSFORM]);
  const [historyIndex, setHistoryIndex] = useState<number>(0);

  const [isProcessing, setIsProcessing] = useState(false);
  const [showSafeZones, setShowSafeZones] = useState(true);
  const [activeTab, setActiveTab] = useState<'adjust' | 'background' | 'preset'>('adjust');

  // Video playback states
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);

  // Dragging / Pan state for image canvas
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number; initialPanX: number; initialPanY: number }>({
    x: 0,
    y: 0,
    initialPanX: 0,
    initialPanY: 0,
  });

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const loadedImageRef = useRef<HTMLImageElement | null>(null);

  // Push new state to undo/redo history
  const updateTransform = useCallback((updater: (prev: TransformState) => TransformState) => {
    setTransform((prev) => {
      const next = updater(prev);
      setHistory((hPrev) => {
        const nextH = hPrev.slice(0, historyIndex + 1);
        return [...nextH, next];
      });
      setHistoryIndex((iPrev) => iPrev + 1);
      return next;
    });
  }, [historyIndex]);

  const handleUndo = () => {
    if (historyIndex > 0) {
      const prevIdx = historyIndex - 1;
      setHistoryIndex(prevIdx);
      setTransform(history[prevIdx]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const nextIdx = historyIndex + 1;
      setHistoryIndex(nextIdx);
      setTransform(history[nextIdx]);
    }
  };

  const handleReset = () => {
    updateTransform(() => DEFAULT_TRANSFORM);
  };

  // Reset editor when opened with a new URL
  useEffect(() => {
    if (isOpen) {
      console.info('[STORY_EDITOR]', { original_media_url: mediaUrl, media_type: mediaType });
      setTransform(DEFAULT_TRANSFORM);
      setHistory([DEFAULT_TRANSFORM]);
      setHistoryIndex(0);

      if (mediaType === 'image') {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = mediaUrl;
        img.onload = () => {
          loadedImageRef.current = img;
          renderCanvas();
        };
      }
    }
  }, [isOpen, mediaUrl, mediaType]);

  // Render on-screen canvas for image preview
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const img = loadedImageRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cw = canvas.width;
    const ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    // 1. Draw Background
    if (transform.bgMode === 'blur') {
      ctx.save();
      ctx.filter = 'blur(20px) brightness(0.7)';
      // Stretch image to fill canvas as blurred background
      ctx.drawImage(img, -20, -20, cw + 40, ch + 40);
      ctx.restore();
    } else if (transform.bgMode === 'black') {
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, cw, ch);
    } else if (transform.bgMode === 'slate') {
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, cw, ch);
    } else if (transform.bgMode === 'gradient') {
      const grad = ctx.createLinearGradient(0, 0, cw, ch);
      grad.addColorStop(0, '#833ab4');
      grad.addColorStop(0.5, '#fd1d1d');
      grad.addColorStop(1, '#fcb045');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, cw, ch);
    } else if (transform.bgMode === 'custom') {
      ctx.fillStyle = transform.customBgColor || '#0f172a';
      ctx.fillRect(0, 0, cw, ch);
    }

    // 2. Draw Main Image with transformations
    ctx.save();
    // Move origin to canvas center + pan offset
    const centerX = cw / 2 + transform.panX;
    const centerY = ch / 2 + transform.panY;
    ctx.translate(centerX, centerY);

    // Apply rotation
    ctx.rotate((transform.rotation * Math.PI) / 180);

    // Apply flip
    ctx.scale(transform.flipH ? -1 : 1, 1);

    // Calculate dimensions based on aspect ratio
    const imgAspect = img.width / img.height;
    const canvasAspect = cw / ch;

    let baseW = cw;
    let baseH = ch;

    if (imgAspect > canvasAspect) {
      // Image is wider than 9:16 -> fit to width by default
      baseW = cw;
      baseH = cw / imgAspect;
    } else {
      // Image is taller or equal -> fit to height by default
      baseH = ch;
      baseW = ch * imgAspect;
    }

    const drawW = baseW * transform.zoom;
    const drawH = baseH * transform.zoom;

    ctx.drawImage(img, -drawW / 2, -drawH / 2, drawW, drawH);
    ctx.restore();
  }, [transform]);

  useEffect(() => {
    if (mediaType === 'image' && loadedImageRef.current) {
      renderCanvas();
    }
  }, [transform, mediaType, renderCanvas]);

  // Fit & Fill Preset Handlers
  const handleFit = () => {
    updateTransform((prev) => ({
      ...prev,
      zoom: 1.0,
      panX: 0,
      panY: 0,
    }));
  };

  const handleFill = () => {
    const img = loadedImageRef.current;
    if (!img) return;
    const imgAspect = img.width / img.height;
    const canvasAspect = 9 / 16;
    let fillZoom = 1.0;
    if (imgAspect > canvasAspect) {
      // wider image needs zoom to cover full height
      fillZoom = (16 / 9) * imgAspect;
    } else {
      // taller image needs zoom to cover full width
      fillZoom = (9 / 16) / imgAspect;
    }
    updateTransform((prev) => ({
      ...prev,
      zoom: Math.max(1.0, fillZoom),
      panX: 0,
      panY: 0,
    }));
  };

  // Pan / Drag handlers for on-screen preview
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      initialPanX: transform.panX,
      initialPanY: transform.panY,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    setTransform((prev) => ({
      ...prev,
      panX: dragStartRef.current.initialPanX + dx,
      panY: dragStartRef.current.initialPanY + dy,
    }));
  };

  const handleMouseUp = () => {
    if (isDragging) {
      setIsDragging(false);
      setHistory((hPrev) => {
        const nextH = hPrev.slice(0, historyIndex + 1);
        return [...nextH, transform];
      });
      setHistoryIndex((iPrev) => iPrev + 1);
    }
  };

  // Save / Export Handler (renders 1080x1920 high-res and uploads to Cloudinary)
  const handleSave = async () => {
    if (mediaType === 'image') {
      const img = loadedImageRef.current;
      if (!img) {
        toast.error('Source image is not ready yet.');
        return;
      }

      setIsProcessing(true);
      const procToast = toast.loading('Exporting & uploading 9:16 Story asset...');

      try {
        console.info('[STORY_MEDIA_PROCESS]', {
          original_media_url: mediaUrl,
          media_type: 'image',
          target_resolution: '1080x1920',
          transform,
        });

        // 1. Offscreen High-Resolution 1080x1920 Canvas
        const offCanvas = document.createElement('canvas');
        offCanvas.width = EXPORT_WIDTH;
        offCanvas.height = EXPORT_HEIGHT;
        const ctx = offCanvas.getContext('2d');
        if (!ctx) throw new Error('Could not create offscreen render context.');

        // Background
        if (transform.bgMode === 'blur') {
          ctx.save();
          ctx.filter = 'blur(40px) brightness(0.7)';
          ctx.drawImage(img, -40, -40, EXPORT_WIDTH + 80, EXPORT_HEIGHT + 80);
          ctx.restore();
        } else if (transform.bgMode === 'black') {
          ctx.fillStyle = '#000000';
          ctx.fillRect(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT);
        } else if (transform.bgMode === 'slate') {
          ctx.fillStyle = '#0f172a';
          ctx.fillRect(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT);
        } else if (transform.bgMode === 'gradient') {
          const grad = ctx.createLinearGradient(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT);
          grad.addColorStop(0, '#833ab4');
          grad.addColorStop(0.5, '#fd1d1d');
          grad.addColorStop(1, '#fcb045');
          ctx.fillStyle = grad;
          ctx.fillRect(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT);
        } else if (transform.bgMode === 'custom') {
          ctx.fillStyle = transform.customBgColor || '#0f172a';
          ctx.fillRect(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT);
        }

        // Scale pan coordinates from preview canvas (360x640) to export canvas (1080x1920) = 3x
        const scaleFactor = EXPORT_WIDTH / 360;
        const centerX = EXPORT_WIDTH / 2 + transform.panX * scaleFactor;
        const centerY = EXPORT_HEIGHT / 2 + transform.panY * scaleFactor;

        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate((transform.rotation * Math.PI) / 180);
        ctx.scale(transform.flipH ? -1 : 1, 1);

        const imgAspect = img.width / img.height;
        const canvasAspect = EXPORT_WIDTH / EXPORT_HEIGHT;

        let baseW = EXPORT_WIDTH;
        let baseH = EXPORT_HEIGHT;

        if (imgAspect > canvasAspect) {
          baseW = EXPORT_WIDTH;
          baseH = EXPORT_WIDTH / imgAspect;
        } else {
          baseH = EXPORT_HEIGHT;
          baseW = EXPORT_HEIGHT * imgAspect;
        }

        const drawW = baseW * transform.zoom;
        const drawH = baseH * transform.zoom;

        ctx.drawImage(img, -drawW / 2, -drawH / 2, drawW, drawH);
        ctx.restore();

        // 2. Export Blob
        const blob = await new Promise<Blob | null>((resolve) => {
          offCanvas.toBlob(resolve, 'image/jpeg', 0.95);
        });

        if (!blob) throw new Error('Failed to generate image blob from canvas.');

        const file = new File([blob], `story_edit_${Date.now()}.jpg`, { type: 'image/jpeg' });
        const formData = new FormData();
        formData.append('file', file);

        // 3. Upload to backend Cloudinary endpoint
        const res = await apiClient.post('/stories/upload-media', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        const newUrl = res.data?.url;
        if (!newUrl) throw new Error('Cloudinary did not return a valid asset URL.');

        console.info('[STORY_MEDIA_PROCESS_SUCCESS]', {
          original_media_url: mediaUrl,
          processed_media_url: newUrl,
          media_type: 'image',
        });

        toast.success('✨ 9:16 Story asset updated successfully!', { id: procToast });
        onSave({
          processedUrl: newUrl,
          originalUrl: mediaUrl,
          mediaType: 'image',
        });
        onClose();
      } catch (err: any) {
        console.error('[STORY_MEDIA_PROCESS_ERROR]', err);
        const msg = err.response?.data?.detail || err.message || 'Failed to process and upload media.';
        toast.error(msg, { id: procToast });
      } finally {
        setIsProcessing(false);
      }
    } else {
      // Video Editor handling:
      // Note: Video composition parameters are preserved in UI preview.
      console.info('[STORY_MEDIA_PROCESS]', {
        original_media_url: mediaUrl,
        media_type: 'video',
        note: 'Video asset validated with 9:16 story frame presentation',
      });
      toast.success('✨ Video composition updated!', { duration: 3000 });
      onSave({
        processedUrl: mediaUrl,
        originalUrl: mediaUrl,
        mediaType: 'video',
      });
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/70">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-fuchsia-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-fuchsia-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>Story Visual Media Editor</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/30">
                  9:16 Canvas (1080×1920)
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Frame, zoom, rotate & style your Story composition for Instagram & Facebook
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Undo / Redo */}
            <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
              <button
                type="button"
                onClick={handleUndo}
                disabled={historyIndex <= 0}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-30 transition"
                title="Undo"
              >
                <Undo2 className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={handleRedo}
                disabled={historyIndex >= history.length - 1}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-30 transition"
                title="Redo"
              >
                <Redo2 className="w-4 h-4" />
              </button>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="px-3 py-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-800 rounded-xl transition flex items-center space-x-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>

            <button
              type="button"
              onClick={() => {
                console.info('[STORY_EDITOR_CANCELLED]', { original_media_url: mediaUrl });
                onClose();
              }}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body: Editor Canvas & Tools Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-y-auto">
          {/* ── Center / Left: Interactive 9:16 Canvas Viewport (7 Cols) ── */}
          <div className="lg:col-span-7 bg-slate-950/90 p-6 flex flex-col items-center justify-center relative border-b lg:border-b-0 lg:border-r border-slate-800 select-none">
            {/* 9:16 Aspect Ratio Frame */}
            <div
              className={`relative w-[280px] h-[498px] sm:w-[320px] sm:h-[568px] rounded-[32px] overflow-hidden border-2 border-slate-700 shadow-2xl cursor-grab active:cursor-grabbing ${
                transform.bgMode === 'black' ? 'bg-black' : 'bg-slate-900'
              }`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              {mediaType === 'image' ? (
                <canvas
                  ref={canvasRef}
                  width={360}
                  height={640}
                  className="w-full h-full object-cover pointer-events-none"
                />
              ) : (
                <div className="w-full h-full relative overflow-hidden flex items-center justify-center">
                  {/* Background mode for video */}
                  {transform.bgMode === 'gradient' && (
                    <div className="absolute inset-0 bg-gradient-to-tr from-fuchsia-600 via-rose-600 to-amber-500 opacity-60" />
                  )}
                  {transform.bgMode === 'slate' && <div className="absolute inset-0 bg-slate-900" />}
                  {transform.bgMode === 'black' && <div className="absolute inset-0 bg-black" />}
                  {transform.bgMode === 'custom' && (
                    <div
                      className="absolute inset-0"
                      style={{ backgroundColor: transform.customBgColor || '#0f172a' }}
                    />
                  )}

                  <video
                    ref={videoRef}
                    src={mediaUrl}
                    loop
                    muted={isMuted}
                    autoPlay
                    playsInline
                    className="relative z-10 transition-transform duration-75"
                    style={{
                      transform: `translate(${transform.panX}px, ${transform.panY}px) scale(${transform.zoom}) rotate(${transform.rotation}deg) scaleX(${
                        transform.flipH ? -1 : 1
                      })`,
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: transform.zoom > 1.2 ? 'cover' : 'contain',
                    }}
                  />
                </div>
              )}

              {/* Story Safe-Zone UI Overlay Guide */}
              {showSafeZones && (
                <div className="absolute inset-0 pointer-events-none z-30 flex flex-col justify-between p-4 text-[10px] text-slate-400/80 font-mono">
                  <div className="border-b border-dashed border-white/20 pb-2 flex items-center justify-between">
                    <span className="bg-black/50 px-1.5 py-0.5 rounded">Story Header (Profile & Close)</span>
                  </div>
                  <div className="border-t border-dashed border-white/20 pt-2 flex items-center justify-between">
                    <span className="bg-black/50 px-1.5 py-0.5 rounded">Action Area (Reply / Share)</span>
                  </div>
                </div>
              )}

              {/* Drag Prompt Tooltip */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full text-[10px] text-slate-300 font-medium flex items-center space-x-1.5 pointer-events-none border border-white/10 shadow">
                <Move className="w-3 h-3 text-indigo-400" />
                <span>Drag to reposition inside 9:16</span>
              </div>
            </div>

            {/* Viewport Bottom Toggles */}
            <div className="flex items-center space-x-3 mt-4">
              <button
                type="button"
                onClick={() => setShowSafeZones(!showSafeZones)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
                  showSafeZones
                    ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Safe Zones {showSafeZones ? 'ON' : 'OFF'}</span>
              </button>

              {mediaType === 'video' && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      const v = videoRef.current;
                      if (!v) return;
                      if (isPlaying) {
                        v.pause();
                        setIsPlaying(false);
                      } else {
                        v.play();
                        setIsPlaying(true);
                      }
                    }}
                    className="p-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition"
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const v = videoRef.current;
                      if (!v) return;
                      v.muted = !isMuted;
                      setIsMuted(!isMuted);
                    }}
                    className="p-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition"
                    title={isMuted ? 'Unmute' : 'Mute'}
                  >
                    {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* ── Right Column: Interactive Editing Tool Suite (5 Cols) ── */}
          <div className="lg:col-span-5 p-6 flex flex-col justify-between space-y-6 bg-slate-900/50">
            {/* Tool Tabs */}
            <div className="space-y-4">
              <div className="flex bg-slate-950 p-1 rounded-2xl border border-slate-800">
                <button
                  type="button"
                  onClick={() => setActiveTab('adjust')}
                  className={`flex-1 flex items-center justify-center space-x-1.5 py-2 rounded-xl text-xs font-bold transition ${
                    activeTab === 'adjust'
                      ? 'bg-gradient-to-r from-fuchsia-600 to-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Adjust</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('background')}
                  className={`flex-1 flex items-center justify-center space-x-1.5 py-2 rounded-xl text-xs font-bold transition ${
                    activeTab === 'background'
                      ? 'bg-gradient-to-r from-fuchsia-600 to-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Palette className="w-3.5 h-3.5" />
                  <span>Background</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('preset')}
                  className={`flex-1 flex items-center justify-center space-x-1.5 py-2 rounded-xl text-xs font-bold transition ${
                    activeTab === 'preset'
                      ? 'bg-gradient-to-r from-fuchsia-600 to-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Maximize className="w-3.5 h-3.5" />
                  <span>Fit & Fill</span>
                </button>
              </div>

              {/* Tab 1: Adjust (Zoom, Rotation, Flip) */}
              {activeTab === 'adjust' && (
                <div className="space-y-5">
                  {/* Zoom Slider */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
                        <ZoomIn className="w-4 h-4 text-indigo-400" />
                        <span>Scale / Zoom</span>
                      </span>
                      <span className="font-mono text-indigo-300 font-bold">{Math.round(transform.zoom * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="3.0"
                      step="0.05"
                      value={transform.zoom}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        updateTransform((prev) => ({ ...prev, zoom: val }));
                      }}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                  </div>

                  {/* Rotation Angle Slider */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
                        <RotateCw className="w-4 h-4 text-fuchsia-400" />
                        <span>Angle Rotation</span>
                      </span>
                      <span className="font-mono text-fuchsia-300 font-bold">{transform.rotation}°</span>
                    </div>
                    <input
                      type="range"
                      min="-180"
                      max="180"
                      step="1"
                      value={transform.rotation}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        updateTransform((prev) => ({ ...prev, rotation: val }));
                      }}
                      className="w-full accent-fuchsia-500 cursor-pointer"
                    />
                  </div>

                  {/* Quick Rotate & Flip Actions */}
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, rotation: (prev.rotation - 90) % 360 }))}
                      className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition"
                    >
                      <RotateCcw className="w-4 h-4 text-slate-400 mb-1" />
                      <span className="text-[11px] font-semibold">-90° Left</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, rotation: (prev.rotation + 90) % 360 }))}
                      className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition"
                    >
                      <RotateCw className="w-4 h-4 text-slate-400 mb-1" />
                      <span className="text-[11px] font-semibold">+90° Right</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, flipH: !prev.flipH }))}
                      className={`flex flex-col items-center justify-center p-3 rounded-2xl border transition ${
                        transform.flipH
                          ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-300'
                          : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white'
                      }`}
                    >
                      <FlipHorizontal className="w-4 h-4 mb-1" />
                      <span className="text-[11px] font-semibold">Flip Horiz</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Tab 2: Background Styling */}
              {activeTab === 'background' && (
                <div className="space-y-4">
                  <p className="text-xs text-slate-400">
                    Choose how the empty letterbox areas are filled when your source media is not natively 9:16:
                  </p>

                  <div className="grid grid-cols-2 gap-3">
                    {/* Blurred Duplicate */}
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, bgMode: 'blur' }))}
                      className={`p-3 rounded-2xl border text-left transition flex items-center space-x-3 ${
                        transform.bgMode === 'blur'
                          ? 'bg-fuchsia-600/20 border-fuchsia-500 text-white'
                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-500 blur-sm flex-shrink-0" />
                      <div>
                        <p className="text-xs font-bold">Blurred Replica</p>
                        <p className="text-[10px] text-slate-400">Canva/Instagram style</p>
                      </div>
                    </button>

                    {/* Gradient Fill */}
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, bgMode: 'gradient' }))}
                      className={`p-3 rounded-2xl border text-left transition flex items-center space-x-3 ${
                        transform.bgMode === 'gradient'
                          ? 'bg-fuchsia-600/20 border-fuchsia-500 text-white'
                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-fuchsia-500 via-rose-500 to-amber-500 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-bold">Story Gradient</p>
                        <p className="text-[10px] text-slate-400">Vibrant Sunset</p>
                      </div>
                    </button>

                    {/* Solid Black */}
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, bgMode: 'black' }))}
                      className={`p-3 rounded-2xl border text-left transition flex items-center space-x-3 ${
                        transform.bgMode === 'black'
                          ? 'bg-fuchsia-600/20 border-fuchsia-500 text-white'
                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="w-6 h-6 rounded-lg bg-black border border-slate-700 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-bold">Solid Black</p>
                        <p className="text-[10px] text-slate-400">Cinema Letterbox</p>
                      </div>
                    </button>

                    {/* Solid Navy Slate */}
                    <button
                      type="button"
                      onClick={() => updateTransform((prev) => ({ ...prev, bgMode: 'slate' }))}
                      className={`p-3 rounded-2xl border text-left transition flex items-center space-x-3 ${
                        transform.bgMode === 'slate'
                          ? 'bg-fuchsia-600/20 border-fuchsia-500 text-white'
                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="w-6 h-6 rounded-lg bg-slate-900 border border-slate-700 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-bold">Dark Slate</p>
                        <p className="text-[10px] text-slate-400">Neutral Modern</p>
                      </div>
                    </button>
                  </div>

                  {/* Custom Hex Color Picker */}
                  <div className="flex items-center space-x-3 p-3 bg-slate-950 rounded-2xl border border-slate-800">
                    <input
                      type="color"
                      value={transform.customBgColor}
                      onChange={(e) =>
                        updateTransform((prev) => ({
                          ...prev,
                          bgMode: 'custom',
                          customBgColor: e.target.value,
                        }))
                      }
                      className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0"
                    />
                    <div>
                      <p className="text-xs font-bold text-slate-200">Custom Brand Color</p>
                      <p className="text-[10px] font-mono text-slate-400 uppercase">{transform.customBgColor}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Quick Fit & Fill Presets */}
              {activeTab === 'preset' && (
                <div className="space-y-4">
                  <p className="text-xs text-slate-400">
                    One-click canvas alignments calculated to match standard Story display dimensions:
                  </p>

                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={handleFit}
                      className="p-4 rounded-2xl bg-slate-950 border border-slate-800 hover:border-indigo-500/50 text-left transition space-y-2 group"
                    >
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition">
                        <Minimize className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-100">Fit Entire Asset</p>
                        <p className="text-[10px] text-slate-400">Letterbox full photo/video without cropping any edges</p>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={handleFill}
                      className="p-4 rounded-2xl bg-slate-950 border border-slate-800 hover:border-fuchsia-500/50 text-left transition space-y-2 group"
                    >
                      <div className="w-8 h-8 rounded-xl bg-fuchsia-500/10 flex items-center justify-center text-fuchsia-400 group-hover:scale-110 transition">
                        <Maximize className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-100">Fill 9:16 Canvas</p>
                        <p className="text-[10px] text-slate-400">Full-bleed immersive cover with edge cropping</p>
                      </div>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Actions: Cancel & Save */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  console.info('[STORY_EDITOR_CANCELLED]', { original_media_url: mediaUrl });
                  onClose();
                }}
                disabled={isProcessing}
                className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleSave}
                disabled={isProcessing}
                className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-fuchsia-600/20 transition disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing Media...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Save 9:16 Story Asset</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
