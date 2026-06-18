import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell, { ScreenHeader } from './components/Shell';

const OTHER = 'other';

export default function Consent() {
  const navigate = useNavigate();
  const { lang, path, narratorId, narratorName, familyMembers, setNarrator, agreeConsent } = useCapture();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isOther = narratorId === null;

  function handleSelect(e) {
    const value = e.target.value;
    if (value === OTHER) {
      setNarrator(null, '');
      return;
    }
    const member = familyMembers.find((m) => m.id === value);
    setNarrator(member.id, member.name_en);
  }

  async function handleAgree() {
    setSubmitting(true);
    setError(null);
    try {
      await agreeConsent();
      navigate(path === 'record' ? '../record' : '../upload');
    } catch {
      setError(t(lang, 'sendError'));
      setSubmitting(false);
    }
  }

  const consentBody =
    path === 'record'
      ? t(lang, 'consentBodyRecordTemplate', { name: narratorName || '…' })
      : t(lang, 'consentBodyUpload');

  return (
    <Shell>
      <ScreenHeader title={t(lang, 'consentTitle')} onBack={() => navigate('../')} />
      <div className="screen-content">
        <div className="consent-icon">
          <span />
        </div>
        <div className="title-md" style={{ marginBottom: 18 }}>
          {t(lang, 'consentLead')}
        </div>

        <div className="narrator-field">
          <label>{t(lang, 'narratorLabel')}</label>
          <select className="narrator-select" value={isOther ? OTHER : narratorId} onChange={handleSelect}>
            {familyMembers.map((m) => (
              <option key={m.id} value={m.id}>
                {(lang === 'kh' && m.name_kh) || m.name_en}
                {m.is_deceased ? ' †' : ''}
              </option>
            ))}
            <option value={OTHER}>{t(lang, 'someoneElse')}</option>
          </select>
          {isOther && (
            <input
              className="narrator-input"
              style={{ marginTop: 8 }}
              type="text"
              placeholder={t(lang, 'narratorPlaceholder')}
              value={narratorName}
              onChange={(e) => setNarrator(null, e.target.value)}
            />
          )}
        </div>

        <div className="consent-box" data-lang={lang}>
          {consentBody}
        </div>
        <div className="consent-meta">{t(lang, 'consentMeta')}</div>

        {error && <div className="error-banner">{error}</div>}

        <div className="actions">
          <button
            type="button"
            className="btn-primary"
            disabled={!narratorName.trim() || submitting}
            onClick={handleAgree}
          >
            {t(lang, 'yesAgreed')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate('../')}>
            {t(lang, 'cancel')}
          </button>
        </div>
      </div>
    </Shell>
  );
}
