'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Sparkles, Mail, Lock, User, Shield, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import { apiClient } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'Admin' | 'Editor'>('Admin');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // 1. Register User
      await apiClient.post('/auth/register', {
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
      });

      // 2. Auto-login after registration
      const loginRes = await apiClient.post('/auth/login', {
        email: email.trim(),
        password,
      });

      if (loginRes.data?.access_token) {
        localStorage.setItem('social_ai_token', loginRes.data.access_token);
        if (loginRes.data?.user_id) {
          localStorage.setItem('social_ai_user', JSON.stringify({
            id: loginRes.data.user_id,
            email: loginRes.data.email,
            full_name: loginRes.data.full_name,
            role: loginRes.data.role,
          }));
        }
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${loginRes.data.access_token}`;
        router.push('/studio');
      } else {
        router.push('/login');
      }
    } catch (err: any) {
      console.error('Registration error:', err);
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg || 'Invalid input').join(', '));
      } else {
        setError('Registration failed. Please ensure password is at least 8 characters with numbers & special symbols.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070A11] text-slate-100 flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Ambient Glows */}
      <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-indigo-600/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-[400px] h-[400px] bg-cyan-600/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md z-10 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-950/80 border border-indigo-700/50 text-indigo-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>SocialAI Registration</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Create Account
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Set up your user account to access the AI Social Media Platform
          </p>
        </div>

        {/* Form Container */}
        <div className="bg-[#0D1322]/80 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800/80 text-rose-200 text-xs flex items-start space-x-2 animate-in fade-in duration-150">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>
            </div>

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
                  placeholder="john@example.com"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 chars (e.g. Pass123!)"
                  className="w-full bg-[#070B14] border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">
                Account Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('Admin')}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center space-x-1.5 transition ${
                    role === 'Admin'
                      ? 'bg-indigo-600/30 border-indigo-500 text-white'
                      : 'bg-[#070B14] border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Shield className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Admin</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('Editor')}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center space-x-1.5 transition ${
                    role === 'Editor'
                      ? 'bg-indigo-600/30 border-indigo-500 text-white'
                      : 'bg-[#070B14] border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <User className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Editor</span>
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold text-xs shadow-lg shadow-indigo-600/25 transition flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isLoading ? (
                <span>Registering Account...</span>
              ) : (
                <>
                  <span>Create Account & Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/60">
            <span>Already have an account? </span>
            <Link href="/login" className="font-semibold text-indigo-400 hover:text-indigo-300 transition">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
