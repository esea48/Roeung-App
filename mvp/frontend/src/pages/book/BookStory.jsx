import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useBook } from './BookContext';

/* ── Waveform ─────────────────────────────────────────────── */

const WAVE_PAT = [10, 16, 8, 20, 14, 24, 18, 22, 12, 26, 8, 28, 16, 10, 22, 14, 26, 8, 18, 14, 20, 12, 24, 10, 18, 22];
const PLAYED = '#a3623e';
const UNPLAYED = '#cdbfab';

function PlayerWave({ count, barW, gap, maxH, progress, onSeek }) {
  const totalW = count * (barW + gap) - gap;

  const handleClick = (e) => {
    if (!onSeek) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onSeek(frac);
  };

  return (
    <div
      className="book-player-wave-bars"
      style={{ height: maxH, gap, cursor: onSeek ? 'pointer' : 'default', maxWidth: totalW }}
      onClick={handleClick}
      aria-hidden="true"
    >
      {Array.from({ length: count }, (_, i) => {
        const h = Math.max(2, Math.round(WAVE_PAT[i % WAVE_PAT.length] * (maxH / 28)));
        return (
          <div
            key={i}
            className="book-player-wave-bar"
            style={{
              width: barW,
              height: h,
              background: i / count < progress ? PLAYED : UNPLAYED,
            }}
          />
        );
      })}
    </div>
  );
}

/* ── Helpers ─────────────────────────────────────────────── */

function fmtTime(sec) {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${m}:${ss.toString().padStart(2, '0')}`;
}

function PersonChip({ tag, lang }) {
  const name = (lang === 'kh' && tag.name_kh) ? tag.name_kh : (tag.name_en || tag.name_raw);
  return (
    <span className="book-person-chip">
      {name}
      {tag.is_deceased && <span className="book-person-dagger">†</span>}
    </span>
  );
}

/* ── Main component ──────────────────────────────────────── */

const SPEEDS = [0.75, 1, 1.25];

export default function BookStory() {
  const { basePath, lang, fetchStoryDetail } = useBook();
  const { storyId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  // Navigation context from the chapter page
  const { storyIds = [], chapterId, chapterTitle, crumb } = location.state ?? {};

  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Audio + listen-mode state
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speedIdx, setSpeedIdx] = useState(1); // index into SPEEDS
  const [activeIdx, setActiveIdx] = useState(-1);
  const [transcriptTab, setTranscriptTab] = useState('en'); // independent EN/KH toggle

  // Load story
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setActiveIdx(-1);

    fetchStoryDetail(storyId)
      .then((data) => {
        if (!cancelled) setStory(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Story not found');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fetchStoryDetail, storyId]);

  // Pair transcript_segments with translation_segments by segment_index
  const sentences = useMemo(() => {
    if (!story) return [];
    const { transcript_segments, translation_segments } = story;

    // Index translations: { `${segment_index}:${target_language}` → segment }
    const tIdx = {};
    for (const t of translation_segments) {
      tIdx[`${t.segment_index}:${t.target_language}`] = t;
    }

    return transcript_segments.map((seg) => {
      const origLang = seg.language; // 'en' or 'kh'
      const otherLang = origLang === 'en' ? 'kh' : 'en';
      const transl = tIdx[`${seg.segment_index}:${otherLang}`];

      const enText = origLang === 'en' ? seg.text : (transl?.text ?? '');
      const khText = origLang === 'kh' ? seg.text : (transl?.text ?? '');

      return {
        idx: seg.segment_index,
        enText,
        khText,
        startMs: seg.start_ms,
        endMs: seg.end_ms,
        culturalFlag: transl?.cultural_flag ?? false,
      };
    });
  }, [story]);

  // Attach audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => {
      const t = audio.currentTime;
      setCurrentTime(t);
      // Find which sentence is active
      const ms = t * 1000;
      const idx = sentences.findIndex((s) => ms >= s.startMs && ms < s.endMs);
      setActiveIdx(idx);
    };

    const onLoadedMetadata = () => setDuration(audio.duration || 0);
    const onEnded = () => {
      setPlaying(false);
      setActiveIdx(-1);
    };
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
    };
  }, [sentences]);

  // Sync playback speed to audio element
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = SPEEDS[speedIdx];
    }
  }, [speedIdx]);

  // Scroll active sentence into view
  const activeRef = useRef(null);
  useEffect(() => {
    if (activeRef.current && playing) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeIdx, playing]);

  // ── Handlers ──

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
  };

  const cycleSpeed = () => setSpeedIdx((i) => (i + 1) % SPEEDS.length);

  const seekToFraction = (frac) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    audio.currentTime = frac * duration;
  };

  const seekToSentence = (idx) => {
    const s = sentences[idx];
    if (!s) return;
    const audio = audioRef.current;
    if (audio) {
      audio.currentTime = s.startMs / 1000;
      setActiveIdx(idx);
    }
  };

  // ── Prev / Next story navigation ──

  const currentIdx = storyIds.indexOf(storyId);
  const prevId = currentIdx > 0 ? storyIds[currentIdx - 1] : null;
  const nextId = currentIdx < storyIds.length - 1 ? storyIds[currentIdx + 1] : null;

  const goToStory = (id) => {
    navigate(`${basePath}/story/${id}`, {
      state: {
        crumb,
        storyIds,
        chapterId,
        chapterTitle,
      },
    });
  };

  // ── Render ──

  if (loading) return <div className="book-spinner">Loading…</div>;
  if (error) return (
    <div className="book-page">
      <button
        type="button"
        className="book-back-btn"
        onClick={() => navigate(-1)}
      >
        ← Back
      </button>
      <div className="book-error">{error}</div>
    </div>
  );
  if (!story) return null;

  const title = (lang === 'kh' && story.title_kh) ? story.title_kh : (story.title_en || 'Untitled');
  const progress = duration > 0 ? currentTime / duration : 0;
  const hasAudio = !!story.audio_url;

  const navLabel = storyIds.length > 0 && currentIdx >= 0
    ? `${currentIdx + 1} / ${storyIds.length}${chapterTitle ? ` · ${chapterTitle}` : ''}`
    : null;

  return (
    <>
      {/* Hidden audio element */}
      {hasAudio && (
        <audio ref={audioRef} src={story.audio_url} preload="metadata" />
      )}

      <div className="book-page book-story-page">
        <button
          type="button"
          className="book-back-btn"
          onClick={() => navigate(-1)}
        >
          ←{' '}
          {chapterTitle || (lang === 'en' ? 'Back' : 'ត្រឡប់')}
        </button>

        {/* Story header */}
        <div className="book-story-header">
          <h1 className="book-story-title">{title}</h1>
          <div className="book-story-narrator">
            {lang === 'en' ? 'Narrated by' : 'និទានដោយ'}{' '}
            <strong>{story.narrator_name_raw}</strong>
            {story.duration_seconds && (
              <> · {Math.round(story.duration_seconds / 60)} min</>
            )}
          </div>
        </div>

        {/* Audio player — inline, above the translation flag */}
        <div className="book-player-track">
          <button
            type="button"
            className={`book-player-play${playing ? ' playing' : ''}`}
            onClick={togglePlay}
            disabled={!hasAudio}
            aria-label={playing ? 'Pause' : 'Play'}
          >
            {playing ? '❚❚' : '▶'}
          </button>

          <div className="book-player-wave">
            <PlayerWave
              count={52}
              barW={3}
              gap={2}
              maxH={28}
              progress={progress}
              onSeek={hasAudio ? seekToFraction : null}
            />
          </div>

          <span className="book-player-time">
            {fmtTime(currentTime)}
            {duration > 0 && ` / ${fmtTime(duration)}`}
          </span>

          <button
            type="button"
            className="book-player-speed"
            onClick={cycleSpeed}
            aria-label={`Playback speed: ${SPEEDS[speedIdx]}×`}
          >
            {SPEEDS[speedIdx]}×
          </button>
        </div>

        {/* Translation flag — appears below player */}
        {story.translation_flagged && (
          <div className="book-flag-banner">
            <span className="book-flag-icon">⚠</span>
            <span>
              {lang === 'en'
                ? 'This translation may not capture all the nuances of the original Khmer.'
                : 'ការបកប្រែនេះអាចមិនបង្ហាញអត្ថន័យពេញលេញនៃខ្មែរដើមឡើយ។'}
            </span>
          </div>
        )}

        {/* Bilingual transcript */}
        <div className="book-transcript">
          <div className="book-transcript-header">
            <div className="book-transcript-label">
              {transcriptTab === 'en' ? 'English — translation' : 'ភាសាខ្មែរ — ដើម'}
            </div>
            <div className="book-transcript-toggle">
              <button
                type="button"
                className={transcriptTab === 'en' ? 'active' : ''}
                onClick={() => setTranscriptTab('en')}
              >
                English
              </button>
              <button
                type="button"
                className={`kh ${transcriptTab === 'kh' ? 'active' : ''}`}
                onClick={() => setTranscriptTab('kh')}
              >
                ភាសាខ្មែរ
              </button>
            </div>
          </div>

          {sentences.length === 0 ? (
            <div style={{ color: 'var(--faint)', font: '400 14px var(--font-sans)' }}>
              {lang === 'en' ? 'Transcript not yet available.' : 'អត្ថបទមិនទាន់មាន។'}
            </div>
          ) : (
            <div
              className={transcriptTab === 'en' ? 'book-transcript-body-en' : 'book-transcript-body-kh'}
            >
              {sentences.map((s, i) => {
                const text = transcriptTab === 'en' ? s.enText : s.khText;
                if (!text) return null;
                const isActive = i === activeIdx;
                return (
                  <span
                    key={s.idx}
                    ref={isActive ? activeRef : null}
                    className={`book-sentence${isActive ? ' active' : ''}`}
                    onClick={() => seekToSentence(i)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && seekToSentence(i)}
                    title={lang === 'en' ? 'Click to jump to this sentence' : 'ចុចដើម្បីលោតទៅប្រយោគនេះ'}
                  >
                    {text}{' '}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        {/* People in this story */}
        {story.tags?.length > 0 && (
          <div className="book-people">
            <div className="book-people-label">
              {lang === 'en' ? 'People in this story' : 'មនុស្សនៅក្នុងរឿងនេះ'}
            </div>
            <div className="book-people-chips">
              {story.tags.map((tag) => (
                <PersonChip key={tag.id} tag={tag} lang={lang} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Prev / Next navigation */}
      <div className="book-story-nav">
        <button
          type="button"
          className="book-story-nav-btn"
          onClick={() => prevId && goToStory(prevId)}
          disabled={!prevId}
        >
          ← {lang === 'en' ? 'Prev story' : 'រឿងមុន'}
        </button>

        {navLabel && (
          <span className="book-story-nav-pos">{navLabel}</span>
        )}

        <button
          type="button"
          className="book-story-nav-btn"
          onClick={() => nextId && goToStory(nextId)}
          disabled={!nextId}
        >
          {lang === 'en' ? 'Next story' : 'រឿងបន្ទាប់'} →
        </button>
      </div>
    </>
  );
}
