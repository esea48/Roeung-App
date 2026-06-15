import { useCapture } from '../CaptureContext';
import LangToggle from './LangToggle';
import '../capture.css';

export default function Shell({ children }) {
  const { lang } = useCapture();
  return (
    <div className="capture" data-lang={lang}>
      <div className="capture-bar">
        <div className="capture-logo">
          <span className="capture-logo-en">Roeung</span>
          <span className="capture-logo-kh">រឿង</span>
        </div>
        <LangToggle />
      </div>
      <div className="capture-body">
        <div className="capture-card">{children}</div>
      </div>
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
