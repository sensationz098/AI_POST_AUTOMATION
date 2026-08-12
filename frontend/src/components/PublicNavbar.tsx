'use client';

import React from 'react';
import Link from 'next/link';
import { Sparkles, ArrowRight, ShieldCheck } from 'lucide-react';

export const PublicNavbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-40 bg-[#070A11]/90 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-8 py-3.5 flex items-center justify-between text-xs font-sans">
      <Link href="/" className="flex items-center space-x-2 text-slate-100 hover:opacity-90 transition">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-md shadow-indigo-500/20">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="font-extrabold text-sm tracking-tight text-white">SocialAI Pro</span>
          <span className="text-[10px] text-indigo-400 font-medium -mt-1">Meta Graph Automation</span>
        </div>
      </Link>

      <div className="flex items-center space-x-3">
        <Link
          href="/privacy-policy"
          className="hidden sm:flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Privacy</span>
        </Link>
        <Link
          href="/login"
          className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 font-semibold transition"
        >
          Sign In
        </Link>
        <Link
          href="/studio"
          className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold transition shadow-sm flex items-center space-x-1.5"
        >
          <span>Go to Studio</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </header>
  );
};
