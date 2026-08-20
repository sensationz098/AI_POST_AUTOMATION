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
  Sparkles,
  Layers,
  CheckCircle2,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'Privacy Policy | SocialAI Pro - Meta Graph API Automation Platform',
  description:
    'Official Privacy Policy for SocialAI Pro. Learn how we securely handle Meta Graph API credentials, Facebook Page data, Instagram Business accounts, and access token security.',
};

export default function PrivacyPolicyPage() {
  const lastUpdated = 'August 12, 2026';

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
    <div className="min-h-screen bg-[#070A11] text-slate-200 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      <PublicNavbar />

      {/* Header Banner */}
      <section className="relative bg-gradient-to-b from-[#0D1322] to-[#070A11] border-b border-slate-800/80 py-12 sm:py-16 px-4 sm:px-8 overflow-hidden">
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-5xl mx-auto space-y-4 text-center sm:text-left relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-950/80 border border-indigo-700/60 text-indigo-300 text-xs font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Legal Compliance & Meta API Transparency</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Privacy Policy
          </h1>

          <p className="text-slate-400 text-xs sm:text-sm max-w-2xl leading-relaxed">
            This Privacy Policy explains how <span className="text-slate-200 font-semibold">SocialAI Pro</span> (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) collects, uses, protects, and handles your information when you authorize our application to connect and publish content across your Facebook Pages and Instagram Professional accounts using Meta Graph APIs.
          </p>

          <div className="pt-2 flex items-center space-x-2 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span>Last Updated: <strong className="text-slate-200">{lastUpdated}</strong></span>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-10 sm:py-14 grid grid-cols-1 lg:grid-cols-4 gap-10">
        
        {/* Quick Navigation Sidebar (Desktop) */}
        <aside className="hidden lg:block lg:col-span-1 space-y-4 sticky top-20 self-start">
          <div className="bg-[#0D1322] border border-slate-800 rounded-xl p-4 space-y-3">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Table of Contents</span>
            </h3>
            <nav className="space-y-1 text-[11px]">
              {sections.map((sec) => (
                <a
                  key={sec.id}
                  href={`#${sec.id}`}
                  className="block px-2.5 py-1.5 rounded text-slate-400 hover:text-indigo-300 hover:bg-slate-800/60 transition truncate"
                >
                  {sec.title}
                </a>
              ))}
            </nav>
          </div>

          <div className="bg-indigo-950/40 border border-indigo-800/50 rounded-xl p-4 space-y-2 text-xs">
            <div className="flex items-center space-x-2 text-indigo-300 font-bold">
              <Trash2 className="w-4 h-4 text-rose-400" />
              <span>Data Deletion Request</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Need to request deletion of your account or revoking Meta permissions?
            </p>
            <Link
              href="/data-deletion"
              className="inline-flex items-center space-x-1 text-[11px] text-indigo-400 font-semibold hover:text-indigo-300 transition"
            >
              <span>View Deletion Page</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </aside>

        {/* Legal Policy Document Body */}
        <div className="lg:col-span-3 space-y-10 text-xs sm:text-sm leading-relaxed text-slate-300">

          {/* Placeholders Notice Alert */}
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold">Production Configuration Notice for Application Administrator:</p>
              <p className="text-amber-300/90 text-[11px]">
                Placeholder fields marked as <code className="bg-amber-900/60 px-1 py-0.5 rounded text-amber-100 font-mono">[YOUR_COMPANY_NAME]</code>, <code className="bg-amber-900/60 px-1 py-0.5 rounded text-amber-100 font-mono">support@socialaipro.com</code>, and <code className="bg-amber-900/60 px-1 py-0.5 rounded text-amber-100 font-mono">https://mydomain.com</code> can be updated prior to Meta Live Mode App Review.
              </p>
            </div>
          </div>

          {/* Section 1 */}
          <section id="information-collected" className="space-y-3 pt-2 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <Database className="w-5 h-5" />
              <h2>1. Information We Collect</h2>
            </div>
            <p>
              When you register for and use <strong className="text-slate-100">SocialAI Pro</strong>, we collect information that you explicitly provide to us, as well as data authorized through third-party platform integrations (specifically Meta / Facebook & Instagram Graph APIs).
            </p>
            <div className="bg-[#0D1322] border border-slate-800 rounded-xl p-4 space-y-3 text-xs">
              <h4 className="font-bold text-slate-100">A. Account & Profile Information</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-400 pl-2">
                <li><strong className="text-slate-200">User Identification:</strong> Your full name, email address, and encrypted account password.</li>
                <li><strong className="text-slate-200">Brand Profiles:</strong> Brand names, target audience descriptions, tone of voice preferences, brand color tokens, and logo asset URLs.</li>
              </ul>

              <h4 className="font-bold text-slate-100 pt-2">B. Authorized Meta / Facebook & Instagram Account Data</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-400 pl-2">
                <li><strong className="text-slate-200">Facebook Page Information:</strong> Authorized Facebook Page IDs, Page names, and Page profile picture URLs.</li>
                <li><strong className="text-slate-200">Instagram Professional Account Information:</strong> Instagram Business / Creator Account IDs, usernames, and profile picture URLs.</li>
                <li><strong className="text-slate-200">Authentication Credentials:</strong> User access tokens and Page access tokens issued by Meta OAuth 2.0 authorization.</li>
              </ul>

              <h4 className="font-bold text-slate-100 pt-2">C. User Content & Publishing Media</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-400 pl-2">
                <li><strong className="text-slate-200">Post Copy & Metadata:</strong> Captions, titles, hashtags, call-to-action (CTA) text, SEO keywords, and scheduling dates/times.</li>
                <li><strong className="text-slate-200">Visual Assets:</strong> Images and media uploaded by you or generated via integrated AI services for publication.</li>
              </ul>

              <h4 className="font-bold text-slate-100 pt-2">D. Technical & Security Logs</h4>
              <ul className="list-disc list-inside space-y-1 text-slate-400 pl-2">
                <li>IP addresses, browser type, operating system details, and system audit logs recording publishing actions for security compliance.</li>
              </ul>
            </div>
            <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-800/40 text-xs text-indigo-300 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>We access only the specific Meta scopes and permissions that you explicitly authorize during the Meta OAuth consent prompt.</span>
            </div>
          </section>

          {/* Section 2 */}
          <section id="how-we-use-info" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <UserCheck className="w-5 h-5" />
              <h2>2. How We Use Information</h2>
            </div>
            <p>We use the information we collect strictly to provide, maintain, and operate the core services of SocialAI Pro, including:</p>
            <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-300">
              <li>Authenticating your user session and managing account security.</li>
              <li>Connecting your authorized Facebook Pages and Instagram Professional accounts via Meta Graph API.</li>
              <li>Creating, scheduling, and automatically publishing authorized photo, text, and graphic posts on your behalf.</li>
              <li>Providing multi-tenant brand profile management and AI-assisted content drafting.</li>
              <li>Fetching post engagement metrics (likes, comments, reach) to display performance insights on your private dashboard.</li>
              <li>Maintaining audit trails to verify authorized publishing actions and prevent fraud.</li>
              <li>Responding to customer support inquiries and resolving technical issues.</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section id="meta-data-compliance" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h2>3. Meta / Facebook & Instagram Data Compliance</h2>
            </div>
            <p>
              SocialAI Pro integrates directly with Meta Graph APIs. In compliance with Meta Platform Terms and Developer Policies:
            </p>
            <div className="space-y-2 bg-[#0D1322] border border-slate-800 rounded-xl p-4 text-xs">
              <div className="flex items-start space-x-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <p><strong className="text-slate-100">Strictly No Selling of Data:</strong> We do NOT sell, license, rent, or monetize Facebook or Instagram user data, Page data, access tokens, or account information to any third parties, data brokers, or advertisers.</p>
              </div>
              <div className="flex items-start space-x-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <p><strong className="text-slate-100">Explicit Permission Usage:</strong> We request and use Meta permissions (such as <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300 font-mono">pages_manage_posts</code>, <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300 font-mono">instagram_content_publish</code>, <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300 font-mono">pages_show_list</code>) exclusively to perform user-instructed actions within our application.</p>
              </div>
              <div className="flex items-start space-x-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <p><strong className="text-slate-100">Revocation Rights:</strong> You can disconnect your Facebook Pages or Instagram accounts at any time within SocialAI Pro or by removing our application in your <a href="https://www.facebook.com/settings?tab=business_tools" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline hover:text-indigo-300">Facebook Business Integrations Settings</a>.</p>
              </div>
            </div>
          </section>

          {/* Section 4 */}
          <section id="token-security" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <KeyRound className="w-5 h-5 text-indigo-400" />
              <h2>4. Access Token Security & Credential Protection</h2>
            </div>
            <p>
              OAuth access tokens allow our background processes to execute scheduled publishing requests. We treat all access tokens as highly sensitive credentials:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-300">
              <li><strong className="text-slate-100">Server-Side Storage Only:</strong> Long-lived Meta access tokens are stored in secure server databases and are never exposed in client-side JavaScript or public API responses.</li>
              <li><strong className="text-slate-100">Restricted Execution Scope:</strong> Tokens are used solely to execute automated background API calls for posts that you explicitly create and schedule.</li>
              <li><strong className="text-slate-100">Token Revocation Cleanup:</strong> When you disconnect a social account or delete your profile, all corresponding access tokens are immediately purged from our active databases.</li>
            </ul>
          </section>

          {/* Section 5 */}
          <section id="data-sharing" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <Share2 className="w-5 h-5" />
              <h2>5. Data Sharing & Third-Party Disclosures</h2>
            </div>
            <p>We do not sell personal data. We share information only under the following limited circumstances:</p>
            <div className="bg-[#0D1322] border border-slate-800 rounded-xl p-4 space-y-2 text-xs">
              <p><strong className="text-slate-100">1. Meta Platforms, Inc. (Facebook & Instagram):</strong> To publish your authorized posts, we transmit post copy, media URLs, and authentication tokens directly to official Meta Graph API endpoints.</p>
              <p><strong className="text-slate-100">2. Essential Service Providers:</strong> We utilize trusted infrastructure vendors (such as cloud hosting, database providers, and media storage services) necessary to host and run our application under strict confidentiality obligations.</p>
              <p><strong className="text-slate-100">3. Legal Requirements:</strong> We may disclose information if required by applicable law, regulation, subpoena, or lawful government request to protect the rights, security, and safety of our platform and users.</p>
            </div>
          </section>

          {/* Section 6 */}
          <section id="data-retention" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <Clock className="w-5 h-5" />
              <h2>6. Data Retention Policies</h2>
            </div>
            <p>
              We retain personal data and connected account credentials only for as long as your account remains active or as needed to provide social media publishing services.
            </p>
            <p>
              If you disconnect a social media account, we immediately erase associated access tokens. If you close your SocialAI Pro account, all stored profile data, credentials, and scheduled posts are permanently deleted within 30 days, except where longer retention is strictly required for legal compliance or audit logging.
            </p>
          </section>

          {/* Section 7 */}
          <section id="data-deletion" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-rose-400 font-bold text-base sm:text-lg">
              <Trash2 className="w-5 h-5" />
              <h2>7. User Data Deletion Instructions</h2>
            </div>
            <p>
              In accordance with Meta Developer Policies and global privacy regulations, users have the right to request the complete deletion of their account data and connected Meta information.
            </p>

            <div className="bg-rose-950/30 border border-rose-900/50 rounded-xl p-4 space-y-3 text-xs">
              <h4 className="font-bold text-rose-200">How to Delete Your Data:</h4>
              <ol className="list-decimal list-inside space-y-1.5 text-slate-300 pl-1">
                <li><strong className="text-slate-100">In-App Disconnection:</strong> Navigate to the <Link href="/meta-connect" className="text-indigo-400 underline">Meta Connect Page</Link> in SocialAI Pro and click &quot;Disconnect&quot; next to any connected Facebook Page or Instagram account.</li>
                <li><strong className="text-slate-100">Account Erasure Request:</strong> Send an email from your registered address to <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono">support@socialaipro.com</code> with the subject line <code className="bg-slate-900 px-1.5 py-0.5 rounded text-indigo-300 font-mono">&quot;Data Deletion Request&quot;</code>. We will purge your account records within 7 business days.</li>
                <li><strong className="text-slate-100">Meta Permission Revocation:</strong> You may also revoke SocialAI Pro access directly via your <a href="https://www.facebook.com/settings?tab=business_tools" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline hover:text-indigo-300">Facebook Settings &gt; Business Integrations</a>.</li>
              </ol>
              <div className="pt-2">
                <Link
                  href="/data-deletion"
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-900/40 border border-rose-700/60 text-rose-200 font-semibold text-xs hover:bg-rose-900/60 transition"
                >
                  <span>Visit Dedicated Data Deletion Guide Page</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </section>

          {/* Section 8 */}
          <section id="security-measures" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <Lock className="w-5 h-5" />
              <h2>8. Security Safeguards</h2>
            </div>
            <p>
              We implement industry-standard technical and organizational security measures to safeguard your personal data and access tokens. These measures include HTTPS transport encryption, password hashing (bcrypt), token authorization middleware, and restricted database access control.
            </p>
            <p className="text-slate-400 text-xs italic">
              While we implement rigorous security safeguards, no method of electronic transmission or storage is 100% immune to all hypothetical security threats. We continuously update our security practices to protect your information.
            </p>
          </section>

          {/* Section 9 */}
          <section id="third-party-services" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <ExternalLink className="w-5 h-5" />
              <h2>9. Third-Party Services</h2>
            </div>
            <p>
              SocialAI Pro interacts with third-party services to deliver functionality. These external services maintain their own independent privacy policies:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2 text-slate-300">
              <li><a href="https://www.facebook.com/privacy/policy" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">Meta Platforms Data Policy (Facebook & Instagram)</a></li>
              <li><a href="https://openai.com/privacy" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">OpenAI Privacy Policy (AI Copy Generation)</a></li>
              <li><a href="https://cloudinary.com/privacy" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">Cloudinary Privacy Policy (Media CDN Storage)</a></li>
            </ul>
          </section>

          {/* Section 10 */}
          <section id="user-rights" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <UserCheck className="w-5 h-5" />
              <h2>10. Your Rights & Choices</h2>
            </div>
            <p>Depending on your jurisdiction, you have the right to:</p>
            <ul className="list-disc list-inside space-y-1 pl-2 text-slate-300">
              <li>Request access to the personal data we hold about you.</li>
              <li>Request correction of inaccurate or incomplete information.</li>
              <li>Request erasure of your personal data and connected credentials.</li>
              <li>Disconnect social media accounts at any time.</li>
              <li>Withdraw previously granted OAuth authorization consent.</li>
            </ul>
          </section>

          {/* Section 11 */}
          <section id="childrens-privacy" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <AlertCircle className="w-5 h-5" />
              <h2>11. Children&apos;s Privacy</h2>
            </div>
            <p>
              SocialAI Pro is a business software tool intended strictly for users aged 18 and older (or the minimum legal age required in your jurisdiction). We do not knowingly collect personal information from children under 13. If you become aware that a child has provided us with personal data, please contact us for immediate deletion.
            </p>
          </section>

          {/* Section 12 */}
          <section id="changes-to-policy" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <Clock className="w-5 h-5" />
              <h2>12. Changes to This Privacy Policy</h2>
            </div>
            <p>
              We may update this Privacy Policy periodically to reflect improvements to our application or changes in legal requirements. Material updates will be posted on this page with an updated &quot;Last Updated&quot; revision date. Continued use of our application after changes indicates acceptance of the updated policy.
            </p>
          </section>

          {/* Section 13 */}
          <section id="contact-us" className="space-y-3 pt-6 border-t border-slate-800/80">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold text-base sm:text-lg">
              <Mail className="w-5 h-5 text-indigo-400" />
              <h2>13. Contact Information</h2>
            </div>
            <p>
              If you have any questions, concerns, or privacy inquiries regarding this policy or our data practices, please contact us at:
            </p>
            <div className="bg-[#0D1322] border border-slate-800 rounded-xl p-4 space-y-2 text-xs font-mono text-slate-300">
              <p><strong className="text-slate-400">Application Name:</strong> SocialAI Pro</p>
              <p><strong className="text-slate-400">Company Name:</strong> Sensationz</p>
              <p><strong className="text-slate-400">Support Email:</strong> support@socialaipro.com</p>
              <p><strong className="text-slate-400">Application Website:</strong> https://mydomain.com</p>
              <p><strong className="text-slate-400">Data Protection Officer:</strong> Privacy & Compliance Team</p>
            </div>
          </section>

        </div>
      </main>

      <Footer />
    </div>
  );
}
