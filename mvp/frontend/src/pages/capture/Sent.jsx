import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell from './components/Shell';

export default function Sent() {
  const navigate = useNavigate();
  const { lang, reset } = useCapture();

  function backHome() {
    reset();
    navigate('../');
  }

  return (
    <Shell>
      <div className="sent-screen">
        <div className="sent-icon">❧</div>
        <div className="sent-title">{t(lang, 'sentTitle')}</div>
        <div className="sent-body">{t(lang, 'sentBody')}</div>
        <div className="sent-est">{t(lang, 'reviewTime')}</div>
        <div className="sent-actions">
          <button type="button" className="btn-primary" onClick={backHome}>
            {t(lang, 'recordAnother')}
          </button>
          <button type="button" className="btn-secondary" onClick={backHome}>
            {t(lang, 'backHome')}
          </button>
        </div>
      </div>
    </Shell>
  );
}
