import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useBook } from './BookContext';

const LANG_LABELS = { en: 'EN', kh: 'KH', khmer: 'KH' };

function fmtDuration(seconds) {
  if (!seconds) return null;
  const m = Math.round(seconds / 60);
  return `${m} min`;
}

function fmtDate(isoDate) {
  if (!isoDate) return null;
  const d = new Date(isoDate);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function BookChapter() {
  const { basePath, lang, book, fetchChapterStories, fetchUncategorisedStories } = useBook();
  const { chapterId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sort, setSort] = useState('newest');
  const [langFilter, setLangFilter] = useState('all');

  const isUncategorised = chapterId === 'uncategorised';

  // Resolve chapter metadata from book context
  const chapter = useMemo(() => {
    if (!book?.chapters) return null;
    return book.chapters.find((c) => c.id === chapterId) ?? null;
  }, [book, chapterId]);

  const chapterTitle = isUncategorised
    ? (lang === 'en' ? 'Uncategorised' : 'មិនទាន់ចាត់ថ្នាក់')
    : (lang === 'kh' && chapter?.title_kh ? chapter.title_kh : (chapter?.title_en ?? ''));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const fetch = isUncategorised
      ? fetchUncategorisedStories(sort)
      : fetchChapterStories(chapterId, sort);

    fetch
      .then((data) => {
        if (!cancelled) setStories(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load stories');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fetchChapterStories, fetchUncategorisedStories, chapterId, isUncategorised, sort]);

  // Filter by language
  const filtered = useMemo(() => {
    if (langFilter === 'all') return stories;
    // The API doesn't return a primary_language on StorySummaryResponse yet,
    // so we filter by what's available — skip if no match field
    return stories;
  }, [stories, langFilter]);

  const goToStory = (storyId, storyTitle) => {
    navigate(`${basePath}/story/${storyId}`, {
      state: {
        crumb: `⟩ ${chapterTitle} ⟩ ${storyTitle || 'Story'}`,
        chapterId: isUncategorised ? 'uncategorised' : chapterId,
        chapterTitle,
        storyIds: filtered.map((s) => s.id),
      },
    });
  };

  const toggleSort = () => setSort((s) => (s === 'newest' ? 'chronological' : 'newest'));

  return (
    <div className="book-page">
      <button
        type="button"
        className="book-back-btn"
        onClick={() =>
          navigate(basePath, { state: { crumb: null } })
        }
      >
        ← {lang === 'en' ? 'Home' : 'ដើម'}
      </button>

      <div className="book-chapter-header">
        <div className="book-chapter-title">{chapterTitle}</div>
        {!loading && !error && (
          <div className="book-chapter-span">
            {filtered.length} {lang === 'en' ? 'stories' : 'រឿង'}
          </div>
        )}
        <div className="book-chapter-controls">
          <div className="book-sort-toggle">
            {lang === 'en' ? 'Sort' : 'តម្រៀប'}:{' '}
            <button type="button" onClick={toggleSort}>
              {sort === 'newest'
                ? (lang === 'en' ? 'Newest first' : 'ថ្មីបំផុតមុន')
                : (lang === 'en' ? 'Chronological' : 'តាមលំដាប់')}
            </button>
          </div>
          <div className="book-filter-chips">
            {['all', 'kh', 'en'].map((l) => (
              <button
                key={l}
                type="button"
                className={`book-filter-chip ${langFilter === l ? 'active' : ''}`}
                onClick={() => setLangFilter(l)}
              >
                {l === 'all'
                  ? (lang === 'en' ? 'All languages' : 'គ្រប់ភាសា')
                  : l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && <div className="book-spinner">Loading…</div>}
      {error && <div className="book-error">{error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className="book-not-found">
          {lang === 'en' ? 'No stories yet in this chapter.' : 'មិនទាន់មានរឿងក្នុងជំពូកនេះ។'}
        </div>
      )}

      {!loading && filtered.map((story) => {
        const title = (lang === 'kh' && story.title_kh) ? story.title_kh : (story.title_en || 'Untitled');
        const dur = fmtDuration(story.duration_seconds);
        const addedDate = fmtDate(story.published_at);

        return (
          <div
            key={story.id}
            className="book-story-row"
            onClick={() => goToStory(story.id, title)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && goToStory(story.id, title)}
          >
            <div className="book-story-row-body">
              <div className="book-story-row-title">{title}</div>
              <div className="book-story-row-meta">
                {story.narrator_name_raw}
                {addedDate && ` · ${lang === 'en' ? 'added' : 'បន្ថែម'} ${addedDate}`}
              </div>
              <div className="book-story-row-badges">
                {story.translation_flagged && (
                  <span className="book-badge book-badge-warn">
                    ⚠ {lang === 'en' ? 'Translation approximate' : 'ការបកប្រែប្រហែល'}
                  </span>
                )}
              </div>
            </div>
            {dur && <div className="book-story-row-dur">{dur}</div>}
          </div>
        );
      })}
    </div>
  );
}
