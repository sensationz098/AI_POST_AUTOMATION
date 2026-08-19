'use client';

import React from 'react';
import Link from 'next/link';
import { Bot, ArrowRight, ShieldCheck } from 'lucide-react';

export const PublicNavbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-40 bg-[var(--bg-primary)] border-b border-[var(--border-color)] px-4 sm:px-8 py-3.5 flex items-center justify-between text-xs font-sans transition-colors duration-150">
      <Link href="/" className="flex items-center space-x-2 text-[var(--text-primary)] hover:opacity-90 transition">
        <div className="w-8 h-8 rounded-md bg-[var(--accent-color)] flex items-center justify-center text-white font-bold shadow-sm">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="font-extrabold text-sm tracking-tight text-[var(--text-primary)]">Sensationz</span>
          <span className="text-[10px] text-[var(--text-secondary)] font-medium -mt-1">Publishing Platform</span>
        </div>
      </Link>

      <div className="flex items-center space-x-3">
        <Link
          href="/privacy-policy"
          className="hidden sm:flex items-center space-x-1 px-2.5 py-1.5 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-[var(--success-color)]" />
          <span>Privacy</span>
        </Link>
        <Link
          href="/login"
          className="btn-secondary text-xs py-1.5 px-3"
        >
          Sign In
        </Link>
        <Link
          href="/studio"
          className="btn-primary text-xs py-1.5 px-3.5 space-x-1.5"
        >
          <span>Go to Studio</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </header>
  );
};
