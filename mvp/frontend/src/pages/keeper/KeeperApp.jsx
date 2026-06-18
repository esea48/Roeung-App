import { useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { KeeperProvider, useKeeper } from './KeeperContext';
import KeeperLogin from './KeeperLogin';
import KeeperQueue from './KeeperQueue';
import KeeperPublished from './KeeperPublished';
import KeeperArchive from './KeeperArchive';
import KeeperChapters from './KeeperChapters';
import KeeperFamilyTree from './KeeperFamilyTree';
import StoryReview from './StoryReview';
import BookApp from '../book/BookApp';
import { createKeeperNavConfig, isActive } from '../../components/navConfig.js';
import './keeper.css';

// ── Sidebar ───────────────────────────────────────────────────────────────────

const SIDEBAR_ICONS = { queue: '📥', flagged: '⚠', published: '✓', archive: '🗄', book: '📖', tree: '🌳', members: '👤', chapters: '🗂' };

function Sidebar({ onNav }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, stats, loadStats, familyAccessToken } = useKeeper();

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  function nav(path) {
    navigate(path);
    onNav?.();
  }

  const navItems = createKeeperNavConfig(stats);
  const reviewItems = navItems.filter((i) => i.section === 'review');
  const contentItems = navItems.filter((i) => i.section === 'content');

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Keeper';
  const email = user?.email || '';

  function renderItem(item) {
    return (
      <button
        key={item.id}
        type="button"
        className={`sidebar-item ${isActive(location, item) ? 'active' : ''}`}
        onClick={() => nav(item.route)}
      >
        <span className="sidebar-item-icon">{SIDEBAR_ICONS[item.id]}</span>
        <span className="sidebar-item-label">{item.labelEn}</span>
        {item.badge > 0 && (
          <span className={`sidebar-badge sidebar-badge-${item.badgeType}`}>
            {item.badge}
          </span>
        )}
      </button>
    );
  }

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
        {reviewItems.map(renderItem)}
      </nav>

      <div className="sidebar-divider" />

      {/* Content section */}
      <div className="sidebar-section-label">Content</div>
      <nav className="sidebar-nav">
        {contentItems.map(renderItem)}
      </nav>

      {/* Record a story */}
      {familyAccessToken && (
        <>
          <div className="sidebar-divider" />
          <nav className="sidebar-nav">
            <button
              type="button"
              className="sidebar-item"
              onClick={() => nav(`/f/${familyAccessToken}/capture`)}
            >
              <span className="sidebar-item-icon">🎙</span>
              <span className="sidebar-item-label">Record a story</span>
            </button>
          </nav>
        </>
      )}

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

// ── Keeper book wrapper ───────────────────────────────────────────────────────

function KeeperBookWrapper() {
  const { token } = useKeeper();
  return <BookApp keeperToken={token} />;
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
          <Route path="published" element={<KeeperPublished />} />
          <Route path="archive" element={<KeeperArchive />} />
          <Route path="book/*" element={<KeeperBookWrapper />} />
          <Route path="members" element={<KeeperFamilyTree />} />
          <Route path="chapters" element={<KeeperChapters />} />
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
