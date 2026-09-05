'use client';

import React from 'react';
import { Facebook, Instagram, Layers, MessageSquare, Check, Sparkles, MessageCircle } from 'lucide-react';

export interface AccountMetric {
  social_account_id: number;
  account_name: string;
  username?: string;
  platform: string;
  logo_url?: string;
  top_level_comment_count: number;
  reply_count: number;
  total_interaction_count: number;
  is_selected?: boolean;
}

interface AccountCommentBreakdownBarProps {
  accounts: AccountMetric[];
  selectedAccountId: string;
  onSelectAccount: (accountId: string) => void;
  totalOrganicConversations?: number;
  totalOrganicReplies?: number;
  loading?: boolean;
}

export default function AccountCommentBreakdownBar({
  accounts,
  selectedAccountId,
  onSelectAccount,
  totalOrganicConversations = 0,
  totalOrganicReplies = 0,
  loading = false,
}: AccountCommentBreakdownBarProps) {
  const isAllSelected = selectedAccountId === 'ALL';
  const totalInteractions = totalOrganicConversations + totalOrganicReplies;

  const getPlatformIcon = (platform: string, size = 'w-4 h-4') => {
    if (platform?.toLowerCase() === 'facebook') {
      return <Facebook className={`${size} text-blue-400 fill-current`} />;
    }
    if (platform?.toLowerCase() === 'instagram') {
      return <Instagram className={`${size} text-pink-400`} />;
    }
    return <Layers className={`${size} text-indigo-400`} />;
  };

  return (
    <div className="space-y-3">
      {/* Header with Title and Subtitle */}
      <div className="flex items-center justify-between px-1">
        <div>
          <h2 className="text-xs font-black tracking-wider uppercase text-slate-300 flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
            <span>COMMENTS BY ACCOUNT</span>
          </h2>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Inspect organic conversations by connected social account
          </p>
        </div>

        <span className="text-[10px] text-slate-500 font-mono hidden sm:inline-block">
          {accounts.length} Connected {accounts.length === 1 ? 'Account' : 'Accounts'}
        </span>
      </div>

      {/* Account Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {/* Card 0: All Connected Accounts Aggregate Card */}
        <div
          onClick={() => onSelectAccount('ALL')}
          className={`relative p-3.5 rounded-2xl border transition-all duration-150 cursor-pointer flex flex-col justify-between space-y-3 ${
            isAllSelected
              ? 'bg-indigo-950/40 border-indigo-500/90 shadow-md ring-1 ring-indigo-500/50'
              : 'bg-slate-900/70 border-slate-800/90 hover:border-slate-700 hover:bg-slate-800/40'
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-indigo-950/80 border border-indigo-800/70 flex items-center justify-center flex-shrink-0 shadow-inner">
                <Layers className="w-4 h-4 text-indigo-300" />
              </div>

              <div className="min-w-0">
                <h3 className="font-bold text-xs text-slate-100 truncate">
                  All Connected Accounts
                </h3>
                <span className="text-[10px] text-slate-400 font-medium">
                  Aggregated Workspace
                </span>
              </div>
            </div>

            {isAllSelected && (
              <span className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                <Check className="w-3 h-3 stroke-[3]" />
              </span>
            )}
          </div>

          <div className="pt-2 border-t border-slate-800/70 flex items-center justify-between text-xs">
            <div className="flex items-baseline space-x-1.5">
              <span className="text-sm font-extrabold text-indigo-300 font-mono">
                {loading ? '...' : totalOrganicConversations}
              </span>
              <span className="text-[10px] text-slate-400 font-semibold">Conversations</span>
            </div>

            <div className="text-[10px] text-slate-400 font-medium font-mono">
              {loading ? '...' : totalOrganicReplies} replies
            </div>
          </div>
        </div>

        {/* Dynamic Connected Account Cards */}
        {accounts.map((acc) => {
          const isSelected = String(acc.social_account_id) === String(selectedAccountId);
          const isFb = acc.platform?.toLowerCase() === 'facebook';

          return (
            <div
              key={acc.social_account_id}
              onClick={() => onSelectAccount(String(acc.social_account_id))}
              className={`relative p-3.5 rounded-2xl border transition-all duration-150 cursor-pointer flex flex-col justify-between space-y-3 ${
                isSelected
                  ? isFb
                    ? 'bg-blue-950/40 border-blue-500/90 shadow-md ring-1 ring-blue-500/50'
                    : 'bg-pink-950/30 border-pink-500/90 shadow-md ring-1 ring-pink-500/50'
                  : 'bg-slate-900/70 border-slate-800/90 hover:border-slate-700 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-inner ${
                      isFb
                        ? 'bg-blue-950/80 border border-blue-800/70'
                        : 'bg-gradient-to-tr from-amber-500/20 via-rose-500/20 to-purple-600/20 border border-pink-800/70'
                    }`}
                  >
                    {getPlatformIcon(acc.platform, 'w-4 h-4')}
                  </div>

                  <div className="min-w-0">
                    <h3 className="font-bold text-xs text-slate-100 truncate" title={acc.account_name}>
                      {acc.account_name}
                    </h3>
                    <div className="flex items-center space-x-1.5 mt-0.5">
                      <span
                        className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded border ${
                          isFb
                            ? 'bg-blue-950 text-blue-300 border-blue-800'
                            : 'bg-pink-950 text-pink-300 border-pink-800'
                        }`}
                      >
                        {acc.platform}
                      </span>
                      {acc.username && (
                        <span className="text-[10px] text-slate-400 truncate max-w-[90px]">
                          @{acc.username}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {isSelected && (
                  <span
                    className={`w-5 h-5 rounded-full text-white flex items-center justify-center flex-shrink-0 shadow-sm ${
                      isFb ? 'bg-blue-600' : 'bg-pink-600'
                    }`}
                  >
                    <Check className="w-3 h-3 stroke-[3]" />
                  </span>
                )}
              </div>

              <div className="pt-2 border-t border-slate-800/70 flex items-center justify-between text-xs">
                <div className="flex items-baseline space-x-1.5">
                  <span
                    className={`text-sm font-extrabold font-mono ${
                      isFb ? 'text-blue-300' : 'text-pink-300'
                    }`}
                  >
                    {loading ? '...' : acc.top_level_comment_count}
                  </span>
                  <span className="text-[10px] text-slate-400 font-semibold">Conversations</span>
                </div>

                <div className="text-[10px] text-slate-400 font-medium font-mono">
                  {loading ? '...' : acc.reply_count} replies
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
