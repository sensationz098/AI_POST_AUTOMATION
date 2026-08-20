'use client';

import React from 'react';
import Link from 'next/link';
import { Sparkles, ShieldCheck, FileText, Trash2, Mail, ExternalLink } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[#05080E] border-t border-slate-800/80 text-slate-400 text-xs py-10 px-4 sm:px-8 font-sans">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Brand Column */}
        <div className="space-y-3 md:col-span-1">
          <div className="flex items-center space-x-2 text-slate-100">
            <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-extrabold text-sm text-white">SocialAI Pro</span>
          </div>
          <p className="text-slate-400 text-[11px] leading-relaxed">
            Enterprise-grade social media automation for Facebook Pages & Instagram Business accounts powered by official Meta Graph API.
          </p>
          <div className="flex items-center space-x-2 text-[10px] text-emerald-400 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Meta API Approved Workflow</span>
          </div>
        </div>

        {/* Legal Links */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">Legal & Compliance</h4>
          <ul className="space-y-1.5 text-[11px]">
            <li>
              <Link href="/privacy-policy" className="hover:text-indigo-400 transition flex items-center space-x-1">
                <ShieldCheck className="w-3 h-3 text-indigo-400" />
                <span>Privacy Policy</span>
              </Link>
            </li>
            <li>
              <Link href="/data-deletion" className="hover:text-indigo-400 transition flex items-center space-x-1">
                <Trash2 className="w-3 h-3 text-rose-400" />
                <span>Data Deletion Instructions</span>
              </Link>
            </li>
            <li>
              <Link href="/terms" className="hover:text-indigo-400 transition flex items-center space-x-1">
                <FileText className="w-3 h-3 text-cyan-400" />
                <span>Terms of Service</span>
              </Link>
            </li>
          </ul>
        </div>

        {/* Platform Links */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">Platform & Tools</h4>
          <ul className="space-y-1.5 text-[11px]">
            <li>
              <Link href="/studio" className="hover:text-indigo-400 transition">
                AI Content Studio
              </Link>
            </li>
            <li>
              <Link href="/meta-connect" className="hover:text-indigo-400 transition">
                Meta OAuth Connect
              </Link>
            </li>
            <li>
              <Link href="/posts" className="hover:text-indigo-400 transition">
                Post Scheduler & History
              </Link>
            </li>
            <li>
              <Link href="/dashboard" className="hover:text-indigo-400 transition">
                Analytics Dashboard
              </Link>
            </li>
          </ul>
        </div>

        {/* Support & Contact */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">Support & Help</h4>
          <p className="text-[11px] text-slate-400">
            For privacy inquiries, data deletion requests, or support:
          </p>
          <a
            href="mailto:support@socialaipro.com"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-indigo-300 font-mono text-[11px] hover:border-indigo-500 transition"
          >
            <Mail className="w-3.5 h-3.5 text-indigo-400" />
            <span>support@socialaipro.com</span>
          </a>
        </div>
      </div>

      {/* Bottom Copyright */}
      <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-slate-800/60 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500">
        <p>© {new Date().getFullYear()} SocialAI Pro ([YOUR_COMPANY_NAME]). All rights reserved.</p>
        <p className="mt-2 sm:mt-0">Meta, Facebook, and Instagram are registered trademarks of Meta Platforms, Inc.</p>
      </div>
    </footer>
  );
};
