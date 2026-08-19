import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { PublicNavbar } from '@/components/PublicNavbar';
import { Footer } from '@/components/Footer';
import {
  ShieldCheck,
  KeyRound,
  Trash2,
  Lock,
  Database,
  Share2,
  Clock,
  UserCheck,
  AlertCircle,
  Mail,
  ExternalLink,
  ChevronRight,
  Layers,
  CheckCircle2,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'Privacy Policy | Sensationz - Meta Graph API Publishing Platform',
  description:
    'Official Privacy Policy for Sensationz. Learn how we securely handle Meta Graph API credentials, Facebook Page data, Instagram Business accounts, and access token security.',
};

export default function PrivacyPolicyPage() {
  const lastUpdated = 'August 19, 2026';

  const sections = [
    { id: 'information-collected', title: '1. Information We Collect' },
    { id: 'how-we-use-info', title: '2. How We Use Information' },
    { id: 'meta-data-compliance', title: '3. Meta / Facebook & Instagram Data Compliance' },
    { id: 'token-security', title: '4. Access Token Security & Credential Protection' },
    { id: 'data-sharing', title: '5. Data Sharing & Third-Party Disclosures' },
    { id: 'data-retention', title: '6. Data Retention Policies' },
    { id: 'data-deletion', title: '7. User Data Deletion Instructions' },
    { id: 'security-measures', title: '8. Security Safeguards' },
    { id: 'third-party-services', title: '9. Third-Party Services' },
    { id: 'user-rights', title: '10. Your Rights & Choices' },
    { id: 'childrens-privacy', title: "11. Children's Privacy" },
    { id: 'changes-to-policy', title: '12. Changes to This Privacy Policy' },
    { id: 'contact-us', title: '13. Contact Information' },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col font-sans select-none transition-colors duration-150">
      <PublicNavbar />

      {/* Header Banner */}
      <section className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] py-12 px-4 sm:px-8">
        <div className="max-w-5xl mx-auto space-y-3 text-left">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--accent-color)] text-xs font-semibold">
            <ShieldCheck className="w-4 h-4 text-[var(--success-color)]" />
            <span>Legal Compliance & Meta API Transparency</span>
          </div>

          <h1 className="text-3xl font-extrabold text-[var(--text-primary)] tracking-tight">
            Privacy Policy
          </h1>

          <p className="text-[var(--text-secondary)] text-xs sm:text-sm max-w-2xl leading-relaxed">
            This Privacy Policy explains how <span className="text-[var(--text-primary)] font-semibold">Sensationz</span> (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) collects, uses, protects, and handles your information when you authorize our application to connect and publish content across your Facebook Pages and Instagram Professional accounts using Meta Graph APIs.
          </p>

          <div className="pt-2 flex items-center space-x-2 text-xs text-[var(--text-tertiary)]">
            <Clock className="w-3.5 h-3.5 text-[var(--accent-color)]" />
            <span>Last Updated: <strong className="text-[var(--text-primary)]">{lastUpdated}</strong></span>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-10 grid grid-cols-1 lg:grid-cols-4 gap-8">
        <aside className="hidden lg:block lg:col-span-1 space-y-4 sticky top-20 self-start">
          <div className="pub-card p-4 space-y-3">
            <h3 className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center space-x-1.5">
              <Layers className="w-4 h-4 text-[var(--accent-color)]" />
              <span>Table of Contents</span>
            </h3>
            <nav className="space-y-1 text-[11px]">
              {sections.map((sec) => (
                <a
                  key={sec.id}
                  href={`#${sec.id}`}
                  className="block px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--accent-color)] hover:bg-[var(--bg-tertiary)] transition truncate"
                >
                  {sec.title}
                </a>
              ))}
            </nav>
          </div>
        </aside>

        <div className="lg:col-span-3 space-y-8 text-xs sm:text-sm leading-relaxed text-[var(--text-secondary)]">
          <section id="information-collected" className="space-y-3 pt-2 border-t border-[var(--border-color)]">
            <div className="flex items-center space-x-2 text-[var(--accent-color)] font-bold text-base">
              <Database className="w-5 h-5" />
              <h2>1. Information We Collect</h2>
            </div>
            <p>
              When you use <strong className="text-[var(--text-primary)]">Sensationz</strong>, we collect information that you explicitly provide to us, as well as data authorized through Meta Graph APIs.
            </p>
            <div className="pub-card p-4 space-y-3 text-xs">
              <h4 className="font-bold text-[var(--text-primary)]">A. Account & Profile Information</h4>
              <ul className="list-disc list-inside space-y-1 text-[var(--text-secondary)] pl-2">
                <li><strong className="text-[var(--text-primary)]">User ID:</strong> Your full name, email address, and encrypted account credentials.</li>
                <li><strong className="text-[var(--text-primary)]">Brand Profiles:</strong> Brand names, tone of voice preferences, target audience specifications, and brand colors.</li>
              </ul>
            </div>
          </section>

          <section id="meta-data-compliance" className="space-y-3 pt-6 border-t border-[var(--border-color)]">
            <div className="flex items-center space-x-2 text-[var(--accent-color)] font-bold text-base">
              <ShieldCheck className="w-5 h-5 text-[var(--success-color)]" />
              <h2>3. Meta / Facebook & Instagram Data Compliance</h2>
            </div>
            <p>In compliance with Meta Platform Terms and Developer Policies:</p>
            <div className="pub-card p-4 space-y-2 text-xs">
              <div className="flex items-start space-x-2">
                <span className="text-[var(--success-color)] font-bold">✓</span>
                <p><strong className="text-[var(--text-primary)]">Strictly No Selling of Data:</strong> We do NOT sell, license, rent, or monetize Facebook or Instagram user data or access tokens.</p>
              </div>
            </div>
          </section>

          <section id="contact-us" className="space-y-3 pt-6 border-t border-[var(--border-color)]">
            <div className="flex items-center space-x-2 text-[var(--accent-color)] font-bold text-base">
              <Mail className="w-5 h-5" />
              <h2>13. Contact Information</h2>
            </div>
            <div className="pub-card p-4 space-y-2 text-xs font-mono text-[var(--text-secondary)]">
              <p><strong className="text-[var(--text-primary)]">Application Name:</strong> Sensationz</p>
              <p><strong className="text-[var(--text-primary)]">Support Email:</strong> support@sensationz.ai</p>
            </div>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
