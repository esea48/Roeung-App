import { useRef, useState } from 'react';
import { useCapture } from '../CaptureContext';
import LangToggle from './LangToggle';
import HamburgerMenu from '../../../components/HamburgerMenu';
import { createFamilyNavConfig } from '../../../components/navConfig';
import '../capture.css';

export default function Shell({ children }) {
  const { lang, setLang, accessToken } = useCapture();
  const [menuOpen, setMenuOpen] = useState(false);
  const hamburgerRef = useRef(null);
  const navItems = createFamilyNavConfig(accessToken);

  return (
    <div className="capture" data-lang={lang}>
      <div className="capture-bar">
        <div className="capture-logo">
          <span className="capture-logo-en">Roeung</span>
          <span className="capture-logo-kh">រឿង</span>
        </div>
        <LangToggle />
        <button
          ref={hamburgerRef}
          type="button"
          className="capture-hamburger"
          onClick={() => setMenuOpen(true)}
          aria-label="Open navigation menu"
          aria-expanded={menuOpen}
        >
          ☰
        </button>
      </div>
      <div className="capture-body">
        <div className="capture-card">{children}</div>
      </div>

      {menuOpen && (
        <HamburgerMenu
          items={navItems}
          lang={lang}
          setLang={setLang}
          onClose={() => setMenuOpen(false)}
          triggerRef={hamburgerRef}
        />
      )}
    </div>
  );
}

export function ScreenHeader({ title, onBack }) {
  return (
    <div className="screen-header">
      {onBack ? (
        <button type="button" className="screen-back" onClick={onBack} aria-label="Back">
          ←
        </button>
      ) : (
        <span />
      )}
      <div className="screen-header-title">{title}</div>
      <span style={{ width: 24 }} />
    </div>
  );
}
