import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell, { ScreenHeader } from './components/Shell';
import { MiniPlayerWave } from './components/Waveform';
import { formatDuration } from './format';

export default function Confirm() {
  const navigate = useNavigate();
  const { lang, audio, narratorName, tags, customTags, familyMembers, sendToKeepers, deleteRecording } =
    useCapture();
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sending, setSending] = useState(false);
  const [sendProgress, setSendProgress] = useState(0);
  const [error, setError] = useState(null);
  const [showDelete, setShowDelete] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    if (!audio?.blob) return;
    const url = URL.createObjectURL(audio.blob);
    const el = audioRef.current;
    el.src = url;
    return () => {
      el.pause();
      el.src = '';
      URL.revokeObjectURL(url);
    };
  }, [audio]);

  function togglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
    } else {
      el.play();
    }
  }

  function handleTimeUpdate() {
    const el = audioRef.current;
    if (!el || !el.duration) return;
    setProgress(el.currentTime / el.duration);
  }

  const selectedNames = [
    ...familyMembers.filter((m) => tags[m.id]).map((m) => (lang === 'kh' && m.name_kh) || m.name_en),
    ...customTags,
  ];

  async function handleSend() {
    setSending(true);
    setError(null);
    try {
      await sendToKeepers(setSendProgress);
      navigate('../sent');
    } catch {
      setError(t(lang, 'sendError'));
      setSending(false);
    }
  }

  async function handleDelete() {
    try {
      await deleteRecording();
    } catch {
      /* story may already be gone */
    }
    navigate('../');
  }

  const durationVal = formatDuration(audio?.durationSec);

  return (
    <Shell>
      <ScreenHeader title={t(lang, 'confirmTitle')} onBack={() => navigate('../tag')} />
      <div className="screen-content">
        <div className="subtle" style={{ marginBottom: 14 }}>
          {t(lang, 'confirmSub')}
        </div>

        <audio ref={audioRef} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onTimeUpdate={handleTimeUpdate} />

        <div className="mini-player">
          <button type="button" className="mini-play" onClick={togglePlay} aria-label={t(lang, 'tapStop')}>
            {playing ? '❙❙' : '▶'}
          </button>
          <div style={{ flex: 1 }}>
            <MiniPlayerWave progress={progress} />
          </div>
          <span className="mini-time">{durationVal}</span>
        </div>

        <div className="summary-row">
          <span className="summary-label">{t(lang, 'duration')}</span>
          <span className="summary-val">{durationVal}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">{t(lang, 'capturedBy')}</span>
          <span className="summary-val">{narratorName}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">{t(lang, 'peopleTagged')}</span>
          <span className="summary-val">{selectedNames.length ? selectedNames.join(', ') : t(lang, 'noTags')}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">{t(lang, 'consentLogged')}</span>
          <span className="summary-val summary-consent">✓</span>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="actions">
          <button type="button" className="btn-primary" disabled={sending} onClick={handleSend}>
            {sending ? `${t(lang, 'uploading')} ${Math.round(sendProgress * 100)}%` : t(lang, 'sendKeepers')}
          </button>
          <button type="button" className="btn-danger" onClick={() => setShowDelete(true)}>
            {t(lang, 'deleteRec')}
          </button>
        </div>
      </div>

      {showDelete && (
        <div className="delete-overlay">
          <div className="delete-icon">⌫</div>
          <div className="delete-title">{t(lang, 'delTitle')}</div>
          <div className="delete-body">{t(lang, 'delBody')}</div>
          <button type="button" className="btn-danger-solid" onClick={handleDelete}>
            {t(lang, 'yesDelete')}
          </button>
          <button type="button" className="btn-secondary" onClick={() => setShowDelete(false)}>
            {t(lang, 'keepIt')}
          </button>
        </div>
      )}
    </Shell>
  );
}
