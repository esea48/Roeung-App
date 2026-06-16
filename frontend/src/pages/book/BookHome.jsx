import { useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useBook } from './BookContext';

const WAVE_PATTERN = [10, 16, 8, 20, 14, 24, 18, 22, 12, 26, 8, 28, 16, 10, 22, 14, 26, 8, 18, 14];
const PLAYED = '#a3623e';
const UNPLAYED = '#cdbfab';

function MiniWave({ count = 22, progress = 0.32 }) {
  return (
    <div
      className="book-player-wave-bars"
      style={{ height: 18, gap: 2 }}
      aria-hidden="true"
    >
      {Array.from({ length: count }, (_, i) => {
        const h = Math.max(2, Math.round(WAVE_PATTERN[i % WAVE_PATTERN.length] * (18 / 28)));
        return (
          <div
            key={i}
            className="book-player-wave-bar"
            style={{
              width: 2.5,
              height: h,
              background: i / count < progress ? PLAYED : UNPLAYED,
            }}
          />
        );
      })}
    </div>
  );
}

function fmtDuration(seconds) {
  if (!seconds) return null;
  const m = Math.round(seconds / 60);
  return `${m} min`;
}

function fmtPublishedDate(isoDate) {
  if (!isoDate) return null;
  const d = new Date(isoDate);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function BookHome() {
  const { basePath, lang, book, loading, error } = useBook();
  const navigate = useNavigate();
  const pageRef = useRef(null);

  // Set breadcrumb to nothing (home = root)
  useEffect(() => {
    if (pageRef.current) {
      window.history.replaceState({ ...window.history.state, crumb: null }, '');
    }
  }, []);

  if (loading) return <div className="book-spinner">Loading…</div>;
  if (error) return <div className="book-page"><div className="book-error">{error}</div></div>;
  if (!book) return null;

  const { chapters = [], recent_stories = [] } = book;

  const goToChapter = (chapterId) => {
    navigate(`${basePath}/chapter/${chapterId}`, {
      state: { crumb: null },
    });
  };

  const goToUncategorised = () => {
    navigate(`${basePath}/chapter/uncategorised`, {
      state: { crumb: null },
    });
  };

  const goToStory = (storyId, storyTitle) => {
    navigate(`${basePath}/story/${storyId}`, {
      state: {
        crumb: `⟩ ${storyTitle || 'Story'}`,
        storyIds: recent_stories.map((s) => s.id),
        fromHome: true,
      },
    });
  };

  const hasUncategorised = recent_stories.some((s) => !s.chapter_id);

  return (
    <div ref={pageRef}>
      {/* Masthead */}
      <div className="book-masthead">
        <div className="book-masthead-text">
          <div className="book-masthead-ornament">❧</div>
          <div className="book-masthead-title">The Sea Family</div>
          <div className="book-masthead-rule" />
          <div className="book-masthead-kh">ក្រុមគ្រួសាររបស់យើង</div>
          <div className="book-masthead-sub">
            {lang === 'en'
              ? 'Voices, memories, and stories — kept for the generations after us.'
              : 'សំឡេង ការចងចាំ និងរឿងរ៉ាវ — ដែលបានរក្សាទុកសម្រាប់មនុស្សជំនាន់ក្រោយ។'}
          </div>
        </div>
        <div className="book-masthead-photo" aria-hidden="true">
          <span className="book-masthead-photo-label">family photograph</span>
        </div>
      </div>

      <div className="book-page">
        {/* Recently added */}
        {recent_stories.length > 0 && (
          <section className="book-section">
            <div className="book-section-label">
              {lang === 'en' ? 'Recently added' : 'បន្ថែមថ្មីៗ'}
            </div>
            <div className="book-recent-scroll">
              {recent_stories.map((story) => {
                const title = (lang === 'kh' && story.title_kh) ? story.title_kh : (story.title_en || 'Untitled');
                const dur = fmtDuration(story.duration_seconds);
                return (
                  <div
                    key={story.id}
                    className="book-story-card-mini"
                    onClick={() => goToStory(story.id, title)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && goToStory(story.id, title)}
                  >
                    <div className="book-story-card-mini-title">{title}</div>
                    <div className="book-story-card-mini-wave">
                      <MiniWave progress={0.3} />
                    </div>
                    <div className="book-story-card-mini-meta">
                      {story.narrator_name_raw}
                      {dur && ` · ${dur}`}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Chapters */}
        <section className="book-section" style={{ marginTop: 28 }}>
          <div className="book-section-label">
            {lang === 'en' ? 'Chapters' : 'ជំពូក'}
          </div>
          {chapters.map((chapter) => {
            const name = (lang === 'kh' && chapter.title_kh) ? chapter.title_kh : chapter.title_en;
            return (
              <div
                key={chapter.id}
                className="book-chapter-row"
                onClick={() => goToChapter(chapter.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && goToChapter(chapter.id)}
              >
                <span
                  className="book-chapter-dot"
                  style={{ background: '#a3623e' }}
                />
                <div className="book-chapter-row-main">
                  <div className="book-chapter-row-name">{name}</div>
                </div>
                <div className="book-chapter-row-arrow">→</div>
              </div>
            );
          })}

          {/* Uncategorised shelf — only shown if relevant */}
          {hasUncategorised && (
            <div
              className="book-chapter-row muted"
              onClick={goToUncategorised}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && goToUncategorised()}
            >
              <span
                className="book-chapter-dot"
                style={{ background: '#c7bda9' }}
              />
              <div className="book-chapter-row-main">
                <div className="book-chapter-row-name">
                  {lang === 'en' ? 'Uncategorised' : 'មិនទាន់ចាត់ថ្នាក់'}
                </div>
                <div className="book-chapter-row-note">
                  {lang === 'en' ? 'not yet assigned to a chapter' : 'មិនទាន់ដាក់ក្នុងជំពូក'}
                </div>
              </div>
              <div className="book-chapter-row-arrow">→</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
