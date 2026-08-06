import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'SocialAI Pro - Facebook & Instagram AI Automation Platform',
  description: 'Production-Ready AI Content Generation & Social Media Automation Platform for Facebook & Instagram Meta Graph API.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0B0F17] text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
