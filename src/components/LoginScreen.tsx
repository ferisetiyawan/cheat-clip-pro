import React, { useState } from 'react';
import { useLanguage } from '../locales';
import { login } from '../utils/auth';

interface LoginScreenProps {
  onSuccess: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onSuccess }) => {
  const { t } = useLanguage();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);

    const result = await login(username.trim(), password);
    if (result.ok) {
      onSuccess();
    } else {
      setError(result.error === 'invalid' ? t.auth.invalidCredentials : t.auth.connectionError);
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        background: 'radial-gradient(1200px 600px at 50% -10%, rgba(99,102,241,0.18), transparent 60%), var(--bg-primary, #070b16)',
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          maxWidth: '400px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.1rem',
          padding: '2rem',
          borderRadius: '16px',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span style={{ fontSize: '1.8rem' }}>⚡</span>
          <div>
            <h1
              className="text-gradient"
              style={{ margin: 0, fontSize: '1.35rem', fontWeight: 800, letterSpacing: '0.02em' }}
            >
              CHEAT CLIP PRO
            </h1>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary, #9aa4b2)' }}>
              {t.auth.subtitle}
            </p>
          </div>
        </div>

        {error && (
          <div
            role="alert"
            style={{
              padding: '0.6rem 0.85rem',
              borderRadius: '8px',
              fontSize: '0.82rem',
              color: '#fca5a5',
              background: 'rgba(239,68,68,0.12)',
              border: '1px solid rgba(239,68,68,0.35)',
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary, #9aa4b2)' }}>
            {t.auth.username}
          </label>
          <input
            type="text"
            autoComplete="username"
            autoFocus
            className="form-input"
            placeholder={t.auth.usernamePlaceholder}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={submitting}
            style={{ height: '42px' }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: 'var(--text-secondary, #9aa4b2)',
            }}
          >
            <span>{t.auth.password}</span>
            <span
              onClick={() => setShowPassword((v) => !v)}
              style={{ cursor: 'pointer', color: 'var(--primary, #818cf8)', fontWeight: 500 }}
            >
              {showPassword ? t.form.hideKey : t.form.showKey}
            </span>
          </label>
          <input
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            className="form-input"
            placeholder={t.auth.passwordPlaceholder}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={submitting}
            style={{ height: '42px' }}
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !username.trim() || !password}
          style={{
            marginTop: '0.35rem',
            height: '44px',
            borderRadius: '10px',
            border: 'none',
            cursor: submitting ? 'wait' : 'pointer',
            fontWeight: 700,
            fontSize: '0.9rem',
            color: '#fff',
            background: 'linear-gradient(135deg, #6366f1, #0ea5e9)',
            opacity: submitting || !username.trim() || !password ? 0.6 : 1,
            transition: 'opacity 0.2s ease',
          }}
        >
          {submitting ? t.auth.signingIn : t.auth.signIn}
        </button>
      </form>
    </div>
  );
};
