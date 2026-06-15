import { useCapture } from '../CaptureContext';

export default function LangToggle() {
  const { lang, setLang } = useCapture();
  return (
    <div className="lang-toggle">
      <button type="button" className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>
        EN
      </button>
      <button type="button" className={`kh ${lang === 'kh' ? 'active' : ''}`} onClick={() => setLang('kh')}>
        ខ្មែរ
      </button>
    </div>
  );
}
