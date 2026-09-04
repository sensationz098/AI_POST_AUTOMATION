'use client';

import React, { useState } from 'react';
import { Sparkles, Bot, ThumbsUp, RefreshCw, ChevronDown, ChevronUp, AlertCircle, Send } from 'lucide-react';

interface AIAssistanceProps {
  intent?: string;
  sentiment?: 'Positive' | 'Neutral' | 'Negative' | string;
  priority?: 'High' | 'Medium' | 'Low' | string;
  knowledgeUsed?: string;
  suggestedReply?: string;
  onUseSuggestedReply?: (reply: string) => void;
}

export default function AIAssistanceCard({
  intent = 'General Inquiry',
  sentiment = 'Positive',
  priority = 'Medium',
  knowledgeUsed,
  suggestedReply,
  onUseSuggestedReply,
}: AIAssistanceProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-2.5 rounded-xl border border-indigo-900/60 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950/60 overflow-hidden text-xs shadow-sm">
      {/* Header Bar */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between bg-indigo-950/60 hover:bg-indigo-900/40 transition text-slate-200"
      >
        <div className="flex items-center space-x-2">
          <Bot className="w-4 h-4 text-indigo-400" />
          <span className="font-bold text-slate-200 flex items-center space-x-1.5">
            <span>AI Co-Pilot Assistance</span>
            <span className="px-1.5 py-0.2 text-[9px] font-mono rounded bg-indigo-900/80 text-indigo-200 border border-indigo-700/80">
              RAG Ready
            </span>
          </span>
        </div>

        <div className="flex items-center space-x-2 text-[11px] text-slate-400">
          <span>{isExpanded ? 'Hide AI Details' : 'Inspect AI Analysis'}</span>
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded Body Drawer */}
      {isExpanded && (
        <div className="p-3 space-y-3 border-t border-indigo-900/40 text-slate-300">
          {/* Metadata Badges */}
          <div className="flex items-center space-x-2 flex-wrap gap-y-1 text-[10px]">
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
              Intent: <strong className="text-indigo-300">{intent}</strong>
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
              Sentiment: <strong className="text-emerald-400">{sentiment}</strong>
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
              Priority: <strong className="text-amber-300">{priority}</strong>
            </span>
          </div>

          {knowledgeUsed && (
            <div className="text-[11px] text-slate-400 bg-slate-950/60 p-2 rounded-lg border border-slate-800 font-mono">
              <span className="text-slate-500 font-semibold">Knowledge Retrieved:</span> {knowledgeUsed}
            </div>
          )}

          {/* Suggested Reply Box */}
          {suggestedReply ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-indigo-300">
                <span className="flex items-center space-x-1">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Suggested Draft Reply:</span>
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/90 border border-indigo-800/60 text-slate-100 font-sans leading-relaxed">
                {suggestedReply}
              </div>
              {onUseSuggestedReply && (
                <div className="flex items-center justify-end space-x-2 pt-1">
                  <button
                    onClick={() => onUseSuggestedReply(suggestedReply)}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition flex items-center space-x-1"
                  >
                    <Send className="w-3 h-3" />
                    <span>Use Suggested Reply</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 text-[11px] text-slate-400 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-indigo-400 flex-shrink-0" />
              <span>
                AI response generation endpoint ready. Connect knowledge base embeddings to automatically generate contextual responses.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
