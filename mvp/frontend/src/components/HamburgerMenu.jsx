import { useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { isActive } from './navConfig.js';
import './HamburgerMenu.css';

/**
 * Slide-in navigation panel shared by Book and Capture surfaces.
 *
 * Props:
 *   items      — array from createFamilyNavConfig(accessToken)
 *   lang       — 'en' | 'kh'
 *   setLang    — (lang) => void
 *   onClose    — () => void
 *   triggerRef — ref to the button that opened the menu (for focus-return)
 */
export default function HamburgerMenu({ items, lang, setLang, onClose, triggerRef }) {
  const navigate = useNavigate();
  const location = useLocation();
  const panelRef = useRef(null);

  // Focus trap + Esc to close
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    const focusable = panel.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first?.focus();

    function onKeyDown(e) {
      if (e.key === 'Escape') {
        onClose();
        triggerRef?.current?.focus();
        return;
      }
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose, triggerRef]);

  function handleItemClick(item) {
    navigate(item.route);
    onClose();
  }

  return (
    <>
      <div
        className="ham-scrim"
        onClick={() => {
          onClose();
          triggerRef?.current?.focus();
        }}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        className="ham-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
      >
        <div className="ham-header">
          <div className="ham-logo">
            <span className="ham-logo-mark">❧</span>
            The Sea Family
          </div>
          <button
            type="button"
            className="ham-close"
            onClick={() => {
              onClose();
              triggerRef?.current?.focus();
            }}
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <nav className="ham-nav">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`ham-item${isActive(location, item) ? ' active' : ''}`}
              onClick={() => handleItemClick(item)}
            >
              <span className="ham-item-label">
                {lang === 'kh' ? item.labelKh : item.labelEn}
              </span>
              {item.badge > 0 && (
                <span className={`ham-badge ham-badge-${item.badgeType}`}>
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="ham-footer">
          <div className="ham-lang-toggle">
            <button
              type="button"
              className={lang === 'en' ? 'active' : ''}
              onClick={() => setLang('en')}
            >
              EN
            </button>
            <button
              type="button"
              className={`kh ${lang === 'kh' ? 'active' : ''}`}
              onClick={() => setLang('kh')}
            >
              ខ្មែរ
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
