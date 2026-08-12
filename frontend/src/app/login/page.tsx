'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Sparkles, Mail, Lock, ArrowRight, CheckCircle2, ShieldCheck, KeyRound, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fill default test admin credentials
  const fillTestCredentials = () => {
    setEmail('testadmin@socialai.com');
    setPassword('TestAdmin123!');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const res = await apiClient.post('/auth/login', {
        email: email.trim(),
        password,
      });

      if (res.data?.access_token) {
        // Save JWT token to localStorage
        localStorage.setItem('social_ai_token', res.data.access_token);
        if (res.data?.user_id) {
          localStorage.setItem('social_ai_user', JSON.stringify({
            id: res.data.user_id,
            email: res.data.email,
            full_name: res.data.full_name,
            role: res.data.role,
          }));
        }

        // Set default Authorization header for subsequent API calls
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;

        // Redirect to main studio page
        router.push('/studio');
      } else {
        setError('Authentication response did not return an access token.');
      }
    } catch (err: any) {
      console.error('Login error:', err);
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg || 'Invalid input').join(', '));
      } else {
        setError('Failed to connect to authentication server. Please check backend status.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070A11] text-slate-100 flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Background Decorative Ambient Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-cyan-600/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md z-10 space-y-6">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-950/80 border border-indigo-700/50 text-indigo-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>SocialAI Pro Automation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Welcome Back
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Sign in to manage multi-brand AI workflows & Meta Graph publishing
          </p>
        </div>

        {/* Card Container */}
        <div className="bg-[#0D1322]/80 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
          {/* Quick 1-Click Test Credentials Box */}
          <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-800/40 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-300">
                <KeyRound className="w-4 h-4 text-indigo-400" />
                <span>Test Credentials Ready</span>
              </div>
              <button
                type="button"
                onClick={fillTestCredentials}
                className="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] transition shadow-sm flex items-center space-x-1"
              >
                <span>1-Click Fill</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="text-[11px] text-slate-400 font-mono space-y-0.5 pt-1 border-t border-indigo-900/50">
              <p><span className="text-slate-500">Email:</span> testadmin@socialai.com</p>
              <p><span className="text-slate-500">Pass:</span> TestAdmin123!</p>
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800/80 text-rose-200 text-xs flex items-start space-x-2 animate-in fade-in duration-150">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@socialai.com"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-slate-300">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold text-xs shadow-lg shadow-indigo-600/25 transition flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isLoading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Footer Link */}
          <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/60">
            <span>Don't have an account yet? </span>
            <Link href="/register" className="font-semibold text-indigo-400 hover:text-indigo-300 transition">
              Create New Account
            </Link>
          </div>
        </div>

        {/* Security Badge */}
        <div className="flex items-center justify-center space-x-2 text-[11px] text-slate-500">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Encrypted JWT Token & Role-Based Security</span>
        </div>
      </div>
    </div>
  );
}
