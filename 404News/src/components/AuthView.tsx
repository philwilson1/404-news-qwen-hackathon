import { useState } from 'react';
import { Mail, Lock, User, Loader2 } from 'lucide-react';
import { signInWithEmail, signUpWithEmail, signInWithGoogle } from '../lib/supabase';

export default function AuthView() {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleEmailAuth = async () => {
    if (!email.trim() || !password.trim()) {
      setError('Enter both email and password.');
      return;
    }
    if (mode === 'signup' && !fullName.trim()) {
      setError('Please enter your full name.');
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);

    const result = mode === 'signin'
      ? await signInWithEmail(email.trim(), password)
      : await signUpWithEmail(email.trim(), password, fullName.trim());

    setLoading(false);

    if (result.error) {
      setError(result.error);
      return;
    }

    if (mode === 'signup') {
      setMessage('Account created! Logging you in...');
    }
  };

  const handleGoogle = async () => {
    setLoading(true);
    setError(null);
    const result = await signInWithGoogle();
    setLoading(false);
    if (result.error) setError(result.error);
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-zinc-950">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-sky-400 to-blue-600 shadow-lg shadow-sky-500/30 mb-3">
            <span className="text-white font-bold text-xl">4</span>
          </div>
          <h1 className="text-white font-bold text-2xl">404 News</h1>
          <p className="text-zinc-500 text-sm mt-1">
            {mode === 'signin' ? 'Sign in to continue' : 'Create your account'}
          </p>
        </div>

        <div className="space-y-3">
          {mode === 'signup' && (
            <div className="relative">
              <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Full Name"
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 pl-10 pr-3 text-white text-sm placeholder:text-zinc-600 outline-none focus:border-sky-500"
              />
            </div>
          )}

          <div className="relative">
            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 pl-10 pr-3 text-white text-sm placeholder:text-zinc-600 outline-none focus:border-sky-500"
            />
          </div>

          <div className="relative">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleEmailAuth()}
              placeholder="Password"
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 pl-10 pr-3 text-white text-sm placeholder:text-zinc-600 outline-none focus:border-sky-500"
            />
          </div>

          {error && <p className="text-rose-400 text-xs px-1">{error}</p>}
          {message && <p className="text-emerald-400 text-xs px-1">{message}</p>}

          <button
            onClick={handleEmailAuth}
            disabled={loading}
            className="w-full bg-sky-500 hover:bg-sky-400 transition-colors text-white font-semibold text-sm rounded-xl py-3 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {mode === 'signin' ? 'Sign In' : 'Sign Up'}
          </button>

          <div className="flex items-center gap-3 py-1">
            <div className="flex-1 h-px bg-zinc-800" />
            <span className="text-zinc-600 text-xs">or</span>
            <div className="flex-1 h-px bg-zinc-800" />
          </div>

          <button
            onClick={handleGoogle}
            disabled={loading}
            className="w-full bg-white hover:bg-zinc-100 transition-colors text-zinc-900 font-semibold text-sm rounded-xl py-3 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <svg width="16" height="16" viewBox="0 0 48 48">
              <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 3l6-6C34.5 5.1 29.5 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21 21-9.4 21-21c0-1.4-.1-2.7-.4-3.5z"/>
              <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.9 18.9 13 24 13c3.1 0 5.8 1.1 8 3l6-6C34.5 5.1 29.5 3 24 3 16.3 3 9.7 7.3 6.3 14.7z"/>
              <path fill="#4CAF50" d="M24 45c5.4 0 10.3-1.8 14.1-4.9l-6.5-5.5c-2 1.5-4.6 2.4-7.6 2.4-5.3 0-9.7-3.4-11.3-8.1l-6.5 5C9.6 40.6 16.2 45 24 45z"/>
              <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.1 4.1-3.8 5.6l6.5 5.5C41.5 36 45 30.5 45 24c0-1.4-.1-2.7-.4-3.5z"/>
            </svg>
            Continue with Google
          </button>
        </div>

        <p className="text-center text-zinc-500 text-xs mt-6">
          {mode === 'signin' ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(null); setMessage(null); }}
            className="text-sky-400 font-medium"
          >
            {mode === 'signin' ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  );
}