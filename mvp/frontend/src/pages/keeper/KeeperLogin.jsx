import { useState } from 'react';
import { useKeeper } from './KeeperContext';

export default function KeeperLogin() {
  const { login } = useKeeper();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="keeper-login">
      <div className="login-card">
        <div className="login-logo">
          <span className="login-logo-mark">❧</span>
          <span className="login-logo-name">The Sea Family</span>
          <span className="login-logo-sub">Keeper Review</span>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}

          <div className="login-field">
            <label className="login-label" htmlFor="keeper-email">
              Email
            </label>
            <input
              id="keeper-email"
              className="login-input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="login-field">
            <label className="login-label" htmlFor="keeper-password">
              Password
            </label>
            <input
              id="keeper-password"
              className="login-input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}
