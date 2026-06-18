import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell, { ScreenHeader } from './components/Shell';

export default function QuickTag() {
  const navigate = useNavigate();
  const {
    lang,
    familyMembers,
    narratorId,
    narratorName,
    tags,
    customTags,
    toggleTag,
    addCustomTag,
    submitTags,
  } = useCapture();
  const [showOtherInput, setShowOtherInput] = useState(false);
  const [otherName, setOtherName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const taggableMembers = familyMembers.filter((m) => m.id !== narratorId);

  function handleAddOther() {
    const name = otherName.trim();
    if (!name) return;
    addCustomTag(name);
    setOtherName('');
    setShowOtherInput(false);
  }

  async function handleNext() {
    setSubmitting(true);
    try {
      await submitTags();
    } catch {
      /* tags are optional; proceed regardless */
    }
    navigate('../confirm');
  }

  function handleSkip() {
    navigate('../confirm');
  }

  return (
    <Shell>
      <ScreenHeader title={t(lang, 'tagTitle')} onBack={() => navigate(-1)} />
      <div className="screen-content">
        <div className="title-md" style={{ textAlign: 'left', marginBottom: 20 }}>
          {t(lang, 'whoAbout')}
        </div>

        {narratorName && (
          <>
            <div className="section-label">{t(lang, 'preselected')}</div>
            <div className="preselected-chip">
              <span className="check">✓</span>
              {narratorName}
            </div>
          </>
        )}

        <div className="section-label">{t(lang, 'members')}</div>
        <div className="chips">
          {taggableMembers.map((m) => {
            const label = (lang === 'kh' && m.name_kh) || m.name_en;
            const selected = !!tags[m.id];
            return (
              <button
                key={m.id}
                type="button"
                data-lang={lang}
                className={`chip${selected ? ' selected' : ''}${m.is_deceased ? ' deceased' : ''}`}
                onClick={() => toggleTag(m.id)}
              >
                <span>{label}</span>
                {m.is_deceased && <span className="dagger">†</span>}
              </button>
            );
          })}
          {customTags.map((name) => (
            <span key={name} className="chip selected" data-lang={lang}>
              {name}
            </span>
          ))}
          {!showOtherInput && (
            <button type="button" className="chip-someone-else" onClick={() => setShowOtherInput(true)}>
              {t(lang, 'someoneElse')}
            </button>
          )}
        </div>

        {showOtherInput && (
          <div className="someone-else-input">
            <input
              type="text"
              placeholder={t(lang, 'someoneElsePlaceholder')}
              value={otherName}
              onChange={(e) => setOtherName(e.target.value)}
              autoFocus
            />
            <button type="button" onClick={handleAddOther}>
              {t(lang, 'addPerson')}
            </button>
          </div>
        )}

        <div className="subtle">{t(lang, 'tagTip')}</div>

        <div className="actions">
          <button type="button" className="btn-primary" disabled={submitting} onClick={handleNext}>
            {t(lang, 'next')}
          </button>
          <button type="button" className="btn-secondary" onClick={handleSkip}>
            {t(lang, 'skip')}
          </button>
        </div>
      </div>
    </Shell>
  );
}
