import React, { useEffect, useState } from 'react';
import { useLanguage } from '../locales';
import { fetchAuthStatus } from '../utils/auth';
import { LoginScreen } from './LoginScreen';

/**
 * Blocks the dashboard behind a login screen when the server has dashboard
 * credentials configured. Renders children directly when auth is disabled.
 */
export const AuthGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { t } = useLanguage();
  const [state, setState] = useState<'checking' | 'login' | 'ready'>('checking');

  useEffect(() => {
    let cancelled = false;
    fetchAuthStatus()
      .then((status) => {
        if (cancelled) return;
        setState(status.auth_required && !status.authenticated ? 'login' : 'ready');
      })
      .catch(() => {
        if (!cancelled) setState('ready');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === 'checking') {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-secondary, #9aa4b2)',
          fontSize: '0.9rem',
        }}
      >
        {t.auth.checking}
      </div>
    );
  }

  if (state === 'login') {
    return <LoginScreen onSuccess={() => setState('ready')} />;
  }

  return <>{children}</>;
};
