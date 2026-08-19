import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { PublicNavbar } from '@/components/PublicNavbar';
import { Footer } from '@/components/Footer';
import {
  Trash2,
  ShieldCheck,
  CheckCircle2,
  Mail,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'User Data Deletion Instructions | Sensationz',
  description:
    'Step-by-step instructions for requesting user data deletion, account removal, and revoking Meta / Facebook Graph API permissions for Sensationz.',
};

export default function DataDeletionPage() {
  const lastUpdated = 'August 19, 2026';

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col font-sans select-none transition-colors duration-150">
      <PublicNavbar />

      {/* Header Banner */}
      <section className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] py-12 px-4 sm:px-8">
        <div className="max-w-4xl mx-auto space-y-3 text-left">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--danger-color)] text-xs font-semibold">
            <Trash2 className="w-4 h-4 text-[var(--danger-color)]" />
            <span>Meta Developer Policy & User Privacy Compliance</span>
          </div>

          <h1 className="text-3xl font-extrabold text-[var(--text-primary)] tracking-tight">
            User Data Deletion Instructions
          </h1>

          <p className="text-[var(--text-secondary)] text-xs sm:text-sm max-w-2xl leading-relaxed">
            According to Meta Platform Rules and Data Privacy Standards, users have full control over their account data. Below are the step-by-step instructions on how to request data erasure or revoke <span className="text-[var(--text-primary)] font-semibold">Sensationz</span> permissions.
          </p>

          <p className="text-xs text-[var(--text-tertiary)] pt-1">
            Last Updated: <strong className="text-[var(--text-primary)]">{lastUpdated}</strong>
          </p>
        </div>
      </section>

      {/* Body Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-8 py-10 space-y-8 text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed">
        {/* Method 1 */}
        <section className="pub-card p-6 space-y-4">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center font-bold text-[var(--accent-color)] text-sm">
              1
            </div>
            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">Method 1: Instant Disconnection via In-App Dashboard</h3>
              <p className="text-[var(--text-secondary)] text-xs">Disconnect individual Facebook Pages or Instagram accounts immediately.</p>
            </div>
          </div>

          <ol className="list-decimal list-inside space-y-2 text-[var(--text-secondary)] pl-2">
            <li>Sign in to your <strong className="text-[var(--text-primary)]">Sensationz</strong> account.</li>
            <li>Navigate to the <Link href="/meta-connect" className="text-[var(--accent-color)] font-semibold underline">Meta Connect Page</Link>.</li>
            <li>Locate your connected Facebook Page or Instagram Business account.</li>
            <li>Click the <strong className="text-[var(--danger-color)]">&quot;Disconnect&quot;</strong> button next to the target account.</li>
            <li>Our system will immediately delete all stored access tokens and associated authorization credentials from our active database.</li>
          </ol>
        </section>

        {/* Method 2 */}
        <section className="pub-card p-6 space-y-4">
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center font-bold text-[var(--accent-color)] text-sm">
              2
            </div>
            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">Method 2: Submit Email Account Erasure Request</h3>
              <p className="text-[var(--text-secondary)] text-xs">Request complete permanent account and data deletion from our servers.</p>
            </div>
          </div>

          <div className="p-4 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] space-y-2 text-xs">
            <p className="font-bold text-[var(--text-primary)]">Email Request Details:</p>
            <p><strong className="text-[var(--text-tertiary)]">Send To:</strong> <code className="font-mono text-[var(--accent-color)]">support@sensationz.ai</code></p>
            <p><strong className="text-[var(--text-tertiary)]">Subject Line:</strong> <code className="font-mono text-[var(--accent-color)]">User Data Deletion Request</code></p>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
