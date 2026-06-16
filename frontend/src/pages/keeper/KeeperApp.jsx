import { useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { KeeperProvider, useKeeper } from './KeeperContext';
import KeeperLogin from './KeeperLogin';
import KeeperQueue from './KeeperQueue';
import StoryReview from './StoryReview';
import './keeper.css';

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ onNav }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, stats, loadStats } = useKeeper();

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  function nav(path) {
    navigate(path);
    onNav?.();
  }

  const isQueue =
    location.pathname === '/keeper' || location.pathname === '/keeper/';
  const isStory = location.pathname.startsWith('/keeper/story/');

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Keeper';
  const email = user?.email || '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Brand */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">❧</div>
        <div className="sidebar-logo-name">The Sea Family</div>
        <div className="sidebar-logo-role">Keeper Review</div>
      </div>

      {/* Review section */}
      <div className="sidebar-section-label">Review</div>
      <nav className="sidebar-nav">
        <button
          type="button"
          className={`sidebar-item ${isQueue || isStory ? 'active' : ''}`}
          onClick={() => nav('/keeper')}
        >
          <span className="sidebar-item-icon">📥</span>
          <span className="sidebar-item-label">Queue</span>
          {stats.awaiting_review > 0 && (
            <span className="sidebar-badge sidebar-badge-neutral">{stats.awaiting_review}</span>
          )}
        </button>

        <button
          type="button"
          className={`sidebar-item ${location.search === '?filter=flagged' ? 'active' : ''}`}
          onClick={() => {
            navigate('/keeper?filter=flagged');
            onNav?.();
          }}
        >
          <span className="sidebar-item-icon">⚠</span>
          <span className="sidebar-item-label">Flagged</span>
          {stats.flagged > 0 && (
            <span className="sidebar-badge sidebar-badge-warn">{stats.flagged}</span>
          )}
        </button>
      </nav>

      <div className="sidebar-divider" />

      {/* Content section */}
      <div className="sidebar-section-label">Content</div>
      <nav className="sidebar-nav">
        <button
          type="button"
          className="sidebar-item"
          onClick={() => nav('/keeper/book')}
        >
          <span className="sidebar-item-icon">📖</span>
          <span className="sidebar-item-label">Book</span>
        </button>

        <button
          type="button"
          className="sidebar-item"
          onClick={() => nav('/keeper/members')}
        >
          <span className="sidebar-item-icon">👤</span>
          <span className="sidebar-item-label">Members</span>
        </button>

        <button
          type="button"
          className="sidebar-item"
          onClick={() => nav('/keeper/chapters')}
        >
          <span className="sidebar-item-icon">🗂</span>
          <span className="sidebar-item-label">Chapters</span>
        </button>
      </nav>

      {/* Keeper identity + logout */}
      <div className="sidebar-keeper">
        <div className="sidebar-keeper-name">{displayName}</div>
        <div className="sidebar-keeper-email">{email}</div>
        <button type="button" className="sidebar-logout" onClick={logout}>
          Sign out
        </button>
      </div>
    </div>
  );
}

// ── Placeholder pages for non-queue sections ──────────────────────────────────

function PlaceholderPage({ title }) {
  return (
    <div className="keeper-loading" style={{ flexDirection: 'column', gap: '8px' }}>
      <div style={{ fontSize: '16px', color: 'var(--faint)', fontWeight: 500 }}>{title}</div>
      <div style={{ fontSize: '12px', color: 'var(--faint2)' }}>Coming soon</div>
    </div>
  );
}

// ── Mobile hamburger + drawer ─────────────────────────────────────────────────

function MobileBar({ onOpen }) {
  return (
    <div className="keeper-mobile-bar">
      <div className="keeper-mobile-logo">
        <span>❧ </span>The Sea Family
      </div>
      <button type="button" className="keeper-hamburger" onClick={onOpen} aria-label="Open menu">
        ☰
      </button>
    </div>
  );
}

function Drawer({ open, onClose }) {
  if (!open) return null;
  return (
    <>
      <div className="keeper-drawer-backdrop" onClick={onClose} />
      <div className="keeper-drawer">
        <Sidebar onNav={onClose} />
      </div>
    </>
  );
}

// ── Shell: sidebar + main ─────────────────────────────────────────────────────

function KeeperShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="keeper">
      {/* Desktop sidebar */}
      <div className="keeper-sidebar">
        <Sidebar />
      </div>

      {/* Mobile top bar */}
      <MobileBar onOpen={() => setDrawerOpen(true)} />
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      {/* Main content */}
      <div className="keeper-main">
        <Routes>
          <Route index element={<KeeperQueue />} />
          <Route path="story/:storyId" element={<StoryReview />} />
          <Route path="book" element={<PlaceholderPage title="Book" />} />
          <Route path="members" element={<PlaceholderPage title="Family Members" />} />
          <Route path="chapters" element={<PlaceholderPage title="Chapters" />} />
          <Route path="*" element={<Navigate to="/keeper" replace />} />
        </Routes>
      </div>
    </div>
  );
}

// ── Root: auth gate ───────────────────────────────────────────────────────────

function KeeperAuthGate() {
  const { token } = useKeeper();
  if (!token) return <KeeperLogin />;
  return <KeeperShell />;
}

export default function KeeperApp() {
  return (
    <KeeperProvider>
      <KeeperAuthGate />
    </KeeperProvider>
  );
}
