'use client';

import React, { useState } from 'react';
import {
  Facebook,
  Instagram,
  Play,
  Pause,
  Edit2,
  Trash2,
  Loader2,
  MessageSquare,
  Mail,
  Zap,
  CheckCircle2,
  Image as ImageIcon,
  MoreVertical,
  ShieldCheck,
  Sparkles
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Automation, SocialAccount } from '@/lib/types';
import { apiClient } from '@/lib/api';

interface AutomationCardProps {
  automation: Automation;
  account?: SocialAccount;
  onEdit: (automation: Automation) => void;
  onDelete: (automation: Automation) => void;
  onStatusChange: (updated: Automation) => void;
}

export default function AutomationCard({
  automation,
  account,
  onEdit,
  onDelete,
  onStatusChange,
}: AutomationCardProps) {
  const [isTogglingStatus, setIsTogglingStatus] = useState(false);

  const isFb = automation.platform === 'facebook';
  const isActive = automation.status === 'ACTIVE';
  const isPaused = automation.status === 'PAUSED';
  const isDraft = automation.status === 'DRAFT';

  // Trigger Details
  const isKeyword = automation.trigger_type === 'KEYWORD';
  const keywords = automation.trigger_config?.keywords || [];

  // Action Details
  const pubReply = automation.action_config?.public_reply;
  const privMsg = automation.action_config?.private_message;

  // Handle Activate / Pause Status Transition
  const handleToggleStatus = async () => {
    setIsTogglingStatus(true);
    try {
      if (isActive) {
        // Pause
        const res = await apiClient.post<Automation>(`/automations/${automation.id}/pause`);
        toast.success(`Automation "${automation.name}" paused`);
        onStatusChange(res.data);
      } else {
        // Activate (from DRAFT or PAUSED)
        const res = await apiClient.post<Automation>(`/automations/${automation.id}/activate`);
        toast.success(`Automation "${automation.name}" activated!`);
        onStatusChange(res.data);
      }
    } catch (err: any) {
      console.error('Status transition error:', err);
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Failed to update automation status.';
      toast.error(msg);
    } finally {
      setIsTogglingStatus(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-5 shadow-md hover:border-slate-700/80 transition flex flex-col justify-between space-y-4">
      {/* 1. Header: Name, Platform & Status Badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm ${
              isFb ? 'bg-blue-600' : 'bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600'
            }`}
          >
            {isFb ? <Facebook className="w-5 h-5 fill-current" /> : <Instagram className="w-5 h-5" />}
          </div>

          <div className="min-w-0">
            <h3 className="font-bold text-sm text-slate-100 truncate">{automation.name}</h3>
            <p className="text-[11px] text-slate-400 truncate">
              {account?.account_name || (isFb ? 'Facebook Page' : 'Instagram Account')} ·{' '}
              <span className="font-mono text-slate-500">ID: {automation.social_account_id}</span>
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex-shrink-0">
          {isActive && (
            <span className="px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 text-[10px] font-bold flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>ACTIVE</span>
            </span>
          )}
          {isPaused && (
            <span className="px-2.5 py-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/80 text-[10px] font-bold flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              <span>PAUSED</span>
            </span>
          )}
          {isDraft && (
            <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 text-[10px] font-bold">
              DRAFT
            </span>
          )}
        </div>
      </div>

      {/* 2. Target Post Info */}
      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center space-x-3">
        <div className="w-9 h-9 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 flex-shrink-0">
          <ImageIcon className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">
            Target Post
          </span>
          <p className="text-xs text-slate-300 truncate font-mono">
            {automation.external_post_id
              ? `External ID: ${automation.external_post_id}`
              : automation.internal_post_id
              ? `Post #${automation.internal_post_id}`
              : 'Specific Post'}
          </p>
        </div>
      </div>

      {/* 3. Trigger & Action Details */}
      <div className="space-y-2 text-xs">
        {/* Trigger Summary */}
        <div className="space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider flex items-center space-x-1">
            <Zap className="w-3 h-3 text-indigo-400" />
            <span>Trigger</span>
          </span>
          <div className="text-slate-300 text-xs">
            {isKeyword ? (
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-slate-400">Keyword:</span>
                {keywords.map((kw, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[11px] font-mono font-semibold"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-slate-300">Any incoming comment</span>
            )}
          </div>
        </div>

        {/* Actions Summary */}
        <div className="space-y-1 pt-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider flex items-center space-x-1">
            <MessageSquare className="w-3 h-3 text-emerald-400" />
            <span>Actions Configured</span>
          </span>
          <div className="space-y-1 text-[11px]">
            <div className="flex items-center space-x-2">
              <span
                className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[9px] font-bold ${
                  pubReply?.enabled
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-slate-800 text-slate-600'
                }`}
              >
                {pubReply?.enabled ? '✓' : '✕'}
              </span>
              <span className={pubReply?.enabled ? 'text-slate-200' : 'text-slate-500'}>
                Public reply {pubReply?.enabled ? `(${pubReply.variations?.length || 0} variations)` : 'disabled'}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <span
                className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[9px] font-bold ${
                  privMsg?.enabled
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-slate-800 text-slate-600'
                }`}
              >
                {privMsg?.enabled ? '✓' : '✕'}
              </span>
              <span className={privMsg?.enabled ? 'text-slate-200' : 'text-slate-500'}>
                Private message {privMsg?.enabled ? 'enabled' : 'disabled'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Footer Controls */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
        {/* Activate / Pause Toggle Button */}
        <button
          type="button"
          onClick={handleToggleStatus}
          disabled={isTogglingStatus}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 ${
            isActive
              ? 'bg-amber-950/70 hover:bg-amber-900 border border-amber-800 text-amber-300'
              : 'bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-800 text-emerald-300'
          } disabled:opacity-50`}
        >
          {isTogglingStatus ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : isActive ? (
            <Pause className="w-3.5 h-3.5" />
          ) : (
            <Play className="w-3.5 h-3.5" />
          )}
          <span>{isActive ? 'Pause' : 'Activate'}</span>
        </button>

        {/* Edit & Delete Buttons */}
        <div className="flex items-center space-x-1">
          <button
            type="button"
            onClick={() => onEdit(automation)}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            title="Edit Automation"
          >
            <Edit2 className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => onDelete(automation)}
            className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
            title="Delete Automation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
