'use client';

import React from 'react';
import Link from 'next/link';
import { Bot, ShieldCheck, FileText, Trash2, Mail } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[var(--bg-secondary)] border-t border-[var(--border-color)] text-[var(--text-secondary)] text-xs py-10 px-4 sm:px-8 font-sans transition-colors duration-150">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Brand Column */}
        <div className="space-y-3 md:col-span-1">
          <div className="flex items-center space-x-2 text-[var(--text-primary)]">
            <div className="w-6 h-6 rounded bg-[var(--accent-color)] flex items-center justify-center">
              <Bot className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-extrabold text-sm text-[var(--text-primary)]">Sensationz</span>
          </div>
          <p className="text-[var(--text-secondary)] text-[11px] leading-relaxed">
            Minimal, professional AI publishing and social media automation platform for Facebook & Instagram management via Meta Graph API.
          </p>
          <div className="flex items-center space-x-2 text-[10px] text-[var(--success-color)] font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Meta Graph API Verified</span>
          </div>
        </div>

        {/* Legal Links */}
        <div className="space-y-2">
          <h4 className="font-bold text-[var(--text-primary)] text-xs uppercase tracking-wider">Legal & Compliance</h4>
          <ul className="space-y-1.5 text-[11px]">
            <li>
              <Link href="/privacy-policy" className="hover:text-[var(--accent-color)] transition flex items-center space-x-1">
                <ShieldCheck className="w-3 h-3 text-[var(--accent-color)]" />
                <span>Privacy Policy</span>
              </Link>
            </li>
            <li>
              <Link href="/data-deletion" className="hover:text-[var(--accent-color)] transition flex items-center space-x-1">
                <Trash2 className="w-3 h-3 text-[var(--danger-color)]" />
                <span>Data Deletion Instructions</span>
              </Link>
            </li>
            <li>
              <Link href="/terms" className="hover:text-[var(--accent-color)] transition flex items-center space-x-1">
                <FileText className="w-3 h-3 text-[var(--info-color)]" />
                <span>Terms of Service</span>
              </Link>
            </li>
          </ul>
        </div>

        {/* Platform Links */}
        <div className="space-y-2">
          <h4 className="font-bold text-[var(--text-primary)] text-xs uppercase tracking-wider">Platform & Tools</h4>
          <ul className="space-y-1.5 text-[11px]">
            <li>
              <Link href="/studio" className="hover:text-[var(--accent-color)] transition">
                AI Content Studio
              </Link>
            </li>
            <li>
              <Link href="/meta-connect" className="hover:text-[var(--accent-color)] transition">
                Meta OAuth Connect
              </Link>
            </li>
            <li>
              <Link href="/posts" className="hover:text-[var(--accent-color)] transition">
                Post Scheduler & History
              </Link>
            </li>
            <li>
              <Link href="/dashboard" className="hover:text-[var(--accent-color)] transition">
                Analytics Dashboard
              </Link>
            </li>
          </ul>
        </div>

        {/* Support & Contact */}
        <div className="space-y-2">
          <h4 className="font-bold text-[var(--text-primary)] text-xs uppercase tracking-wider">Support & Help</h4>
          <p className="text-[11px] text-[var(--text-secondary)]">
            For privacy inquiries, data deletion requests, or support:
          </p>
          <a
            href="mailto:support@sensationz.ai"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--accent-color)] font-mono text-[11px] hover:border-[var(--accent-color)] transition"
          >
            <Mail className="w-3.5 h-3.5 text-[var(--accent-color)]" />
            <span>support@sensationz.ai</span>
          </a>
        </div>
      </div>

      {/* Bottom Copyright */}
      <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-[var(--border-color)] flex flex-col sm:flex-row items-center justify-between text-[11px] text-[var(--text-tertiary)]">
        <p>© {new Date().getFullYear()} Sensationz. All rights reserved.</p>
        <p className="mt-2 sm:mt-0">Meta, Facebook, and Instagram are registered trademarks of Meta Platforms, Inc.</p>
      </div>
    </footer>
  );
};
