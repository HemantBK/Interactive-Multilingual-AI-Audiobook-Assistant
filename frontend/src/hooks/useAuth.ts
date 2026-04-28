/**
 * React hook for Supabase auth state + sign-in/out actions.
 * Notifies the backend's audit_log on fresh sign-ins and sign-outs (best-effort).
 * Day 22: identifies the user in PostHog on SIGNED_IN; resets on SIGNED_OUT.
 */

import { useCallback, useEffect, useState } from 'react';
import type { Session, User } from '@supabase/supabase-js';

import { supabase } from '../lib/supabase';
import { identify, reset, track } from '../lib/analytics';
import { notifyAuthEvent } from '../services/api';

export interface AuthHook {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signInWithEmail: (email: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthHook {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    void supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
      if (data.session?.user) {
        identify(data.session.user.id);
      }
    });

    const { data: listener } = supabase.auth.onAuthStateChange((event, newSession) => {
      if (!mounted) return;
      setSession(newSession);
      setUser(newSession?.user ?? null);
      if (event === 'SIGNED_IN' && newSession?.access_token) {
        void notifyAuthEvent('login', newSession.access_token);
        if (newSession.user) {
          identify(newSession.user.id);
          track('auth.signed_in', {
            method: newSession.user.app_metadata?.provider ?? 'email',
          });
        }
      }
      if (event === 'SIGNED_OUT') {
        track('auth.signed_out');
        reset();
      }
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const signInWithEmail = useCallback(async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) throw error;
  }, []);

  const signInWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    const token = session?.access_token;
    if (token) {
      void notifyAuthEvent('logout', token);
    }
    await supabase.auth.signOut();
  }, [session]);

  return { user, session, loading, signInWithEmail, signInWithGoogle, signOut };
}
