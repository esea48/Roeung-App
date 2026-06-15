import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell, { ScreenHeader } from './components/Shell';
import { LiveWave } from './components/Waveform';
import { formatDuration } from './format';
import { useMediaRecorder } from './useMediaRecorder';

const MAX_SEC = 60 * 60;

export default function Recording() {
  const navigate = useNavigate();
  const { lang, setAudio, deleteRecording } = useCapture();
  const recorder = useMediaRecorder();
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    recorder.start();
  }, [recorder]);

  useEffect(() => {
    if (recorder.isRecording && recorder.elapsedSec >= MAX_SEC) {
      handleStop();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recorder.elapsedSec, recorder.isRecording]);

  async function handleStop() {
    const result = await recorder.stop();
    if (result) {
      setAudio(result);
      navigate('../tag');
    }
  }

  async function handleDiscard() {
    recorder.discard();
    try {
      await deleteRecording();
    } catch {
      /* story may already be gone */
    }
    navigate('../');
  }

  if (recorder.error) {
    return (
      <Shell>
        <ScreenHeader title={t(lang, 'recording')} onBack={() => navigate('../consent')} />
        <div className="screen-content">
          <div className="error-banner">{t(lang, 'micError')}</div>
          <div className="actions">
            <button type="button" className="btn-primary" onClick={() => recorder.start()}>
              {t(lang, 'next')}
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate('../')}>
              {t(lang, 'cancel')}
            </button>
          </div>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <ScreenHeader title={t(lang, 'recording')} onBack={() => navigate('../consent')} />
      <div className="record-stage">
        <div className="record-timer">{formatDuration(recorder.elapsedSec)}</div>
        <div className="record-status">
          <span className="rec-dot" />
          <span>
            {t(lang, 'recording')} · {t(lang, 'maxMin')}
          </span>
        </div>
        <LiveWave />
        <button type="button" className="stop-btn" onClick={handleStop} aria-label={t(lang, 'tapStop')}>
          <span />
        </button>
        <div className="stop-label">{t(lang, 'tapStop')}</div>
      </div>
      <div className="screen-content" style={{ flex: '0 0 auto', paddingTop: 0 }}>
        <div className="discard-row">
          <button type="button" className="discard-link" onClick={handleDiscard}>
            {t(lang, 'discard')}
          </button>
        </div>
      </div>
    </Shell>
  );
}
