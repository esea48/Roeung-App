import { useNavigate } from 'react-router-dom';
import { useCapture } from './CaptureContext';
import { t } from './i18n';
import Shell from './components/Shell';
import { StaticWave } from './components/Waveform';
import { relativeTime } from './format';

export default function Home() {
  const navigate = useNavigate();
  const { lang, setPath, audioLang, setAudioLang, recentStories, loadingFamily } = useCapture();

  function choose(path) {
    setPath(path);
    navigate('consent');
  }

  return (
    <Shell>
      <div className="screen-content">
        <div className="title-lg">{t(lang, 'homeHeading')}</div>

        <div className="audio-lang-picker">
          <div className="section-label">{t(lang, 'audioLangLabel')}</div>
          <div className="audio-lang-options">
            <button
              type="button"
              className={`audio-lang-btn${audioLang === 'kh' ? ' active' : ''}`}
              onClick={() => setAudioLang('kh')}
            >
              {t(lang, 'audioLangKh')}
            </button>
            <button
              type="button"
              className={`audio-lang-btn${audioLang === 'en' ? ' active' : ''}`}
              onClick={() => setAudioLang('en')}
            >
              {t(lang, 'audioLangEn')}
            </button>
          </div>
        </div>

        <div className="home-options">
          <button type="button" className="home-card" onClick={() => choose('record')}>
            <div className="home-card-icon record">
              <span className="dot" />
            </div>
            <div>
              <div className="home-card-title">{t(lang, 'recordTitle')}</div>
              <div className="home-card-kh">{t(lang, 'recordKh')}</div>
            </div>
            <div className="home-card-sub">{t(lang, 'recordSub')}</div>
          </button>
          <button type="button" className="home-card" onClick={() => choose('upload')}>
            <div className="home-card-icon upload">↑</div>
            <div>
              <div className="home-card-title">{t(lang, 'uploadTitle')}</div>
              <div className="home-card-kh">{t(lang, 'uploadKh')}</div>
            </div>
            <div className="home-card-sub">{t(lang, 'uploadSub')}</div>
          </button>
        </div>

        {!loadingFamily && recentStories.length > 0 && (
          <div style={{ marginTop: 28 }}>
            <div className="section-label">{t(lang, 'recentlyAdded')}</div>
            {recentStories.slice(0, 5).map((story) => (
              <div className="recent-story" key={story.id}>
                <div className="recent-story-title">
                  {(lang === 'kh' && story.title_kh) || story.title_en || '—'}
                </div>
                <div className="recent-story-meta">
                  <span className="recent-story-name">{story.narrator_name_raw}</span>
                  <div style={{ flex: 1 }}>
                    <StaticWave count={20} />
                  </div>
                  <span className="recent-story-tag">
                    {relativeTime(story.published_at, lang)} · {story.title_kh ? 'KH' : 'EN'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
