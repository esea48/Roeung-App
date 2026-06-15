import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell, { ScreenHeader } from './components/Shell';

const ACCEPTED_TYPES = ['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/m4a', 'audio/wav', 'audio/x-wav'];
const ACCEPTED_EXTENSIONS = ['mp3', 'm4a', 'wav'];
const MAX_SIZE_BYTES = 500 * 1024 * 1024;

function isAcceptedFile(file) {
  const ext = file.name.split('.').pop()?.toLowerCase();
  return ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(ext);
}

function formatBytes(bytes) {
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

function readDuration(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.src = url;
    audio.addEventListener('loadedmetadata', () => {
      resolve(Number.isFinite(audio.duration) ? audio.duration : 0);
      URL.revokeObjectURL(url);
    });
    audio.addEventListener('error', () => {
      resolve(0);
      URL.revokeObjectURL(url);
    });
  });
}

export default function Upload() {
  const navigate = useNavigate();
  const { lang, setAudio } = useCapture();
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  async function handleFile(selected) {
    if (!selected) return;
    if (!isAcceptedFile(selected)) {
      setError(t(lang, 'fileTypeError'));
      return;
    }
    if (selected.size > MAX_SIZE_BYTES) {
      setError(t(lang, 'fileSizeError'));
      return;
    }
    setError(null);
    const durationSec = await readDuration(selected);
    setFile({ blob: selected, name: selected.name, size: selected.size, durationSec });
  }

  function handleContinue() {
    if (!file) return;
    setAudio({ blob: file.blob, durationSec: file.durationSec });
    navigate('../tag');
  }

  return (
    <Shell>
      <ScreenHeader title={t(lang, 'uploadHead')} onBack={() => navigate('../consent')} />
      <div className="screen-content">
        <div
          className={`upload-zone${dragOver ? ' dragover' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFile(e.dataTransfer.files?.[0]);
          }}
        >
          <div className="upload-zone-icon">↑</div>
          <div className="upload-zone-title">{t(lang, 'chooseFile')}</div>
          <div className="upload-zone-sub">{t(lang, 'fileLimit')}</div>
          <div className="upload-zone-browse">{t(lang, 'orBrowse')}</div>
          <input
            ref={inputRef}
            type="file"
            accept="audio/*,.mp3,.m4a,.wav"
            style={{ display: 'none' }}
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
        </div>

        {error && <div className="error-banner">{error}</div>}

        {file && (
          <div className="file-row">
            <div className="file-icon">
              <span />
            </div>
            <div className="file-info">
              <div className="file-name">{file.name}</div>
              <div className="file-meta">{formatBytes(file.size)}</div>
            </div>
            <button type="button" className="file-change" onClick={() => inputRef.current?.click()}>
              {t(lang, 'change')}
            </button>
          </div>
        )}

        <div className="actions">
          <button type="button" className="btn-primary" disabled={!file} onClick={handleContinue}>
            {t(lang, 'continueBtn')}
          </button>
        </div>
      </div>
    </Shell>
  );
}
