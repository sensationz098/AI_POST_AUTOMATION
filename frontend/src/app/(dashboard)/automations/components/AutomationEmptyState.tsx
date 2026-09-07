'use client';

import React from 'react';
import { Bot, MessageSquare, Zap, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';

interface AutomationEmptyStateProps {
  onCreateClick: () => void;
}

export default function AutomationEmptyState({ onCreateClick }: AutomationEmptyStateProps) {
  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-3xl p-8 md:p-12 text-center max-w-4xl mx-auto shadow-xl relative overflow-hidden backdrop-blur-sm">
      {/* Decorative background glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-2xl mx-auto space-y-6">
        {/* Icon & Badge */}
        <div className="flex flex-col items-center space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/25 ring-4 ring-indigo-500/10">
            <Bot className="w-8 h-8" />
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            Social Automation Engine
          </span>
        </div>

        {/* Headings */}
        <div className="space-y-2">
          <h3 className="text-2xl md:text-3xl font-bold text-slate-100 tracking-tight">
            Turn comments into conversations
          </h3>
          <p className="text-sm md:text-base text-slate-400 max-w-lg mx-auto">
            Create an automation that responds to comments and sends a private message to interested people automatically.
          </p>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-left pt-2">
          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <Zap className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold text-slate-200">Keyword Triggers</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Match words like "price", "link", or "details" to trigger immediate responses.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <MessageSquare className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold text-slate-200">Public Replies</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Rotate multiple public replies to keep comments natural and conversational.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold text-slate-200">Private DMs</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Deliver direct messages with resource links, pricing, or custom offers.
            </p>
          </div>
        </div>

        {/* CTA Button */}
        <div className="pt-4 flex justify-center">
          <button
            type="button"
            onClick={onCreateClick}
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition shadow-lg shadow-indigo-600/30 flex items-center space-x-2 group focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <span>Create your first automation</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
}
