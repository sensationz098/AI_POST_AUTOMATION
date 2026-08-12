import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { PublicNavbar } from '@/components/PublicNavbar';
import { Footer } from '@/components/Footer';
import {
  Trash2,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Mail,
  ArrowRight,
  AlertCircle,
  KeyRound,
  Layers,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'User Data Deletion Instructions | SocialAI Pro',
  description:
    'Step-by-step instructions for requesting user data deletion, account removal, and revoking Meta / Facebook Graph API permissions for SocialAI Pro.',
};

export default function DataDeletionPage() {
  const lastUpdated = 'August 12, 2026';

  return (
    <div className="min-h-screen bg-[#070A11] text-slate-200 flex flex-col font-sans selection:bg-rose-500 selection:text-white">
      <PublicNavbar />

      {/* Header Banner */}
      <section className="relative bg-gradient-to-b from-[#140D19] to-[#070A11] border-b border-slate-800/80 py-12 sm:py-16 px-4 sm:px-8 overflow-hidden">
        <div className="absolute top-0 left-1/3 w-96 h-96 bg-rose-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-4xl mx-auto space-y-4 text-center sm:text-left relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-rose-950/80 border border-rose-700/60 text-rose-300 text-xs font-semibold">
            <Trash2 className="w-4 h-4 text-rose-400" />
            <span>Meta Developer Policy & User Privacy Compliance</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            User Data Deletion Instructions
          </h1>

          <p className="text-slate-400 text-xs sm:text-sm max-w-2xl leading-relaxed">
            According to Meta Platform Rules and Data Privacy Standards, users have full control over their account data. Below are the step-by-step instructions on how to request data erasure or revoke <span className="text-slate-200 font-semibold">SocialAI Pro</span> permissions.
          </p>

          <p className="text-xs text-slate-400 pt-1">
            Last Updated: <strong className="text-slate-200">{lastUpdated}</strong>
          </p>
        </div>
      </section>

      {/* Body Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-8 py-10 sm:py-14 space-y-10 text-xs sm:text-sm text-slate-300 leading-relaxed">

        {/* Method 1 */}
        <section className="bg-[#0D1322] border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-4 shadow-xl">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center font-bold text-indigo-300 text-sm">
              1
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-white">Method 1: Instant Disconnection via In-App Dashboard</h3>
              <p className="text-slate-400 text-xs">Disconnect individual Facebook Pages or Instagram accounts immediately.</p>
            </div>
          </div>

          <ol className="list-decimal list-inside space-y-2 text-slate-300 pl-2">
            <li>Sign in to your <strong className="text-slate-100">SocialAI Pro</strong> account.</li>
            <li>Navigate to the <Link href="/meta-connect" className="text-indigo-400 font-semibold underline hover:text-indigo-300">Meta Connect Page</Link>.</li>
            <li>Locate your connected Facebook Page or Instagram Business account.</li>
            <li>Click the <strong className="text-rose-400">&quot;Disconnect&quot;</strong> button next to the target account.</li>
            <li>Our system will immediately delete all stored access tokens and associated authorization credentials from our active database.</li>
          </ol>
        </section>

        {/* Method 2 */}
        <section className="bg-[#0D1322] border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-4 shadow-xl">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-cyan-600/30 border border-cyan-500/50 flex items-center justify-center font-bold text-cyan-300 text-sm">
              2
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-white">Method 2: Revoke Access via Facebook Settings</h3>
              <p className="text-slate-400 text-xs">Remove SocialAI Pro from your Facebook account settings at any time.</p>
            </div>
          </div>

          <ol className="list-decimal list-inside space-y-2 text-slate-300 pl-2">
            <li>Log in to your Facebook account.</li>
            <li>Go to <a href="https://www.facebook.com/settings?tab=business_tools" target="_blank" rel="noopener noreferrer" className="text-indigo-400 font-semibold underline hover:text-indigo-300">Facebook Settings &amp; Privacy &gt; Settings</a>.</li>
            <li>Click <strong className="text-slate-100">&quot;Business Integrations&quot;</strong> (or <strong className="text-slate-100">&quot;Apps and Websites&quot;</strong>).</li>
            <li>Find <strong className="text-slate-100">SocialAI Pro</strong> in the list of active apps.</li>
            <li>Click <strong className="text-rose-400">&quot;Remove&quot;</strong> to revoke all app permissions and access tokens.</li>
          </ol>

          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-400 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Once revoked in Facebook settings, SocialAI Pro can no longer make API calls to your accounts.</span>
          </div>
        </section>

        {/* Method 3 */}
        <section className="bg-[#0D1322] border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-4 shadow-xl">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-rose-600/30 border border-rose-500/50 flex items-center justify-center font-bold text-rose-300 text-sm">
              3
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-white">Method 3: Submit Email Account Erasure Request</h3>
              <p className="text-slate-400 text-xs">Request complete permanent account and data deletion from our servers.</p>
            </div>
          </div>

          <p>
            If you wish to permanently erase your user account, stored brand profiles, post history, and all stored tokens:
          </p>

          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 space-y-2 text-xs">
            <p className="font-bold text-rose-200">Email Request Details:</p>
            <p className="text-slate-300"><strong className="text-slate-400">Send To:</strong> <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono">support@socialaipro.com</code></p>
            <p className="text-slate-300"><strong className="text-slate-400">Subject Line:</strong> <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono">User Data Deletion Request</code></p>
            <p className="text-slate-300"><strong className="text-slate-400">Required Body Info:</strong> Please include your registered email address and full name.</p>
          </div>

          <p className="text-xs text-slate-400">
            Our compliance team will process your request and permanently erase all matching records from our databases within <strong className="text-slate-200">7 business days</strong>. You will receive a confirmation email upon completion.
          </p>
        </section>

        {/* What Gets Deleted */}
        <section className="bg-[#0D1322] border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-3">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Data Purged Upon Deletion Request</span>
          </h3>
          <ul className="list-disc list-inside space-y-1.5 text-xs text-slate-400 pl-1">
            <li>All active Facebook Page &amp; Instagram Business access tokens.</li>
            <li>Stored user profile information (email, name, hashed password).</li>
            <li>Configured brand voice profiles, color palettes, and tone tokens.</li>
            <li>Drafted, scheduled, and published post copy and image prompt history.</li>
            <li>System audit log associations.</li>
          </ul>
        </section>

      </main>

      <Footer />
    </div>
  );
}
