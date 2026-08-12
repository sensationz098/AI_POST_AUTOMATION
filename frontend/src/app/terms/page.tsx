import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { PublicNavbar } from '@/components/PublicNavbar';
import { Footer } from '@/components/Footer';
import {
  FileText,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  ExternalLink,
  Mail,
  Scale,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'Terms of Service | SocialAI Pro',
  description:
    'Terms of Service governing the use of SocialAI Pro social media automation platform and Meta Graph API integrations.',
};

export default function TermsPage() {
  const lastUpdated = 'August 12, 2026';

  return (
    <div className="min-h-screen bg-[#070A11] text-slate-200 flex flex-col font-sans selection:bg-cyan-500 selection:text-white">
      <PublicNavbar />

      {/* Header Banner */}
      <section className="relative bg-gradient-to-b from-[#0D1322] to-[#070A11] border-b border-slate-800/80 py-12 sm:py-16 px-4 sm:px-8 overflow-hidden">
        <div className="absolute top-0 right-1/3 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-4xl mx-auto space-y-4 text-center sm:text-left relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-700/60 text-cyan-300 text-xs font-semibold">
            <Scale className="w-4 h-4 text-cyan-400" />
            <span>Platform Agreement & Usage Terms</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Terms of Service
          </h1>

          <p className="text-slate-400 text-xs sm:text-sm max-w-2xl leading-relaxed">
            These Terms of Service (&quot;Terms&quot;) govern your access to and use of <span className="text-slate-200 font-semibold">SocialAI Pro</span>. By registering for or using our services, you agree to comply with these Terms and applicable third-party platform policies (including Meta Platform Terms).
          </p>

          <p className="text-xs text-slate-400 pt-1">
            Last Updated: <strong className="text-slate-200">{lastUpdated}</strong>
          </p>
        </div>
      </section>

      {/* Body Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-8 py-10 sm:py-14 space-y-8 text-xs sm:text-sm text-slate-300 leading-relaxed">

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            <span>1. Acceptance of Terms</span>
          </h2>
          <p>
            By creating an account or connecting social media profiles to SocialAI Pro, you confirm that you are at least 18 years of age (or the legal age of majority in your jurisdiction) and possess legal authority to enter into this agreement.
          </p>
        </section>

        <section className="space-y-3 pt-4 border-t border-slate-800/80">
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            <span>2. Meta Platform Compliance & Account Ownership</span>
          </h2>
          <p>
            SocialAI Pro utilizes Meta Graph APIs to access Facebook Pages and Instagram Professional accounts. You explicitly represent and warrant that:
          </p>
          <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-400">
            <li>You own or possess explicit administrative authorization to manage and publish content to connected Facebook Pages and Instagram accounts.</li>
            <li>Your use of our automation tools complies with <a href="https://developers.facebook.com/terms/" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">Meta Platform Terms</a> and Community Standards.</li>
            <li>You will not use our platform to distribute spam, unauthorized advertising, malware, or deceptive content.</li>
          </ul>
        </section>

        <section className="space-y-3 pt-4 border-t border-slate-800/80">
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            <span>3. User Content & Responsibilities</span>
          </h2>
          <p>
            You retain full ownership of all text, post copy, graphics, and images uploaded or generated using SocialAI Pro. You are solely responsible for ensuring that published content does not infringe upon any third-party intellectual property, privacy, or publicity rights.
          </p>
        </section>

        <section className="space-y-3 pt-4 border-t border-slate-800/80">
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-indigo-400" />
            <span>4. Limitation of Liability</span>
          </h2>
          <p>
            SocialAI Pro is provided on an &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; basis. We do not warrant that service will be completely uninterrupted or error-free. We shall not be liable for any indirect, incidental, or consequential damages resulting from third-party platform API outages, Meta token expirations, or account suspensions enforced by Meta Platforms, Inc.
          </p>
        </section>

        <section className="space-y-3 pt-4 border-t border-slate-800/80">
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <Mail className="w-5 h-5 text-indigo-400" />
            <span>5. Contact & Support</span>
          </h2>
          <p>
            For questions regarding these Terms of Service, please contact our support team at <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono">support@socialaipro.com</code>.
          </p>
        </section>

      </main>

      <Footer />
    </div>
  );
}
