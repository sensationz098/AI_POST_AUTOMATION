'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Bot, Mail, Lock, User, Shield, ArrowRight, AlertCircle } from 'lucide-react';
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
      await apiClient.post('/auth/register', {
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
      });

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
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex items-center justify-center p-4 font-sans select-none transition-colors duration-150">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--accent-color)] text-xs font-semibold">
            <Bot className="w-4 h-4 text-[var(--accent-color)]" />
            <span>Sensationz Platform</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Create Account
          </h1>
          <p className="text-xs text-[var(--text-secondary)]">
            Set up your user account to access the publishing studio
          </p>
        </div>

        {/* Form Container */}
        <div className="pub-card p-6 space-y-5">
          {error && (
            <div className="p-3 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--danger-color)] text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-[var(--danger-color)] shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Full Name
              </label>
              <div className="relative flex items-center">
                <User className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3.5 pointer-events-none z-10" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  className="input-field w-full !pl-10"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Email Address
              </label>
              <div className="relative flex items-center">
                <Mail className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3.5 pointer-events-none z-10" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                  className="input-field w-full !pl-10"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Password
              </label>
              <div className="relative flex items-center">
                <Lock className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3.5 pointer-events-none z-10" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 chars (e.g. Pass123!)"
                  className="input-field w-full !pl-10"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Account Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('Admin')}
                  className={`py-2 px-3 rounded border text-xs font-semibold flex items-center justify-center space-x-1.5 transition ${
                    role === 'Admin'
                      ? 'bg-[var(--accent-color)] text-white border-transparent'
                      : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)]'
                  }`}
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>Admin</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('Editor')}
                  className={`py-2 px-3 rounded border text-xs font-semibold flex items-center justify-center space-x-1.5 transition ${
                    role === 'Editor'
                      ? 'bg-[var(--accent-color)] text-white border-transparent'
                      : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)]'
                  }`}
                >
                  <User className="w-3.5 h-3.5" />
                  <span>Editor</span>
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full text-xs py-2.5 space-x-2"
            >
              {isLoading ? (
                <span>Registering Account...</span>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center text-xs text-[var(--text-secondary)] border-t border-[var(--border-color)]">
            <span>Already have an account? </span>
            <Link href="/login" className="font-semibold text-[var(--accent-color)] hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
