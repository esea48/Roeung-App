import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKeeper } from './KeeperContext';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'kh', label: 'KH' },
  { key: 'en', label: 'EN' },
];

function formatRelative(isoString) {
  if (!isoString) return '';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return 'Yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(isoString).toLocaleDateString();
}

export default function KeeperPublished() {
  const navigate = useNavigate();
  const { publishedStories, publishedLoading, publishedError, loadPublished } = useKeeper();
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState('newest');

  useEffect(() => {
    loadPublished({ filter: filter || undefined, sort });
  }, [filter, sort]); // eslint-disable-line react-hooks/exhaustive-deps

  function openStory(storyId) {
    navigate(`/keeper/story/${storyId}`, { state: { from: 'published' } });
  }

  const count = publishedStories.length;

  return (
    <>
      <div className="queue-header">
        <div className="queue-title">Published</div>
        <div className="queue-sub">
          {publishedLoading
            ? 'Loading…'
            : publishedError
            ? 'Failed to load'
            : `${count} published ${count === 1 ? 'story' : 'stories'}`}
        </div>
      </div>

      <div className="queue-toolbar">
        <div className="queue-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              className={`filter-chip ${filter === f.key ? 'active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <select
          className="sort-select"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>

      <div className="queue-list">
        {publishedError && (
          <div className="keeper-error" style={{ alignItems: 'flex-start', padding: '12px 0' }}>
            {publishedError}
          </div>
        )}

        {!publishedLoading && !publishedError && publishedStories.length === 0 && (
          <div className="queue-empty">
            <div className="queue-empty-icon">📖</div>
            No published stories yet.
          </div>
        )}

        {publishedStories.map((story) => (
          <div
            key={story.id}
            className="story-card"
            onClick={() => openStory(story.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') openStory(story.id);
            }}
          >
            <div className="story-card-body">
              <div className="story-card-title">
                {story.title_en || story.title_kh || 'Untitled story'}
              </div>
              <div className="story-card-meta">
                {story.narrator_name_raw}
                {' · '}
                Published {formatRelative(story.published_at)}
              </div>
            </div>

            <div className="story-card-badges">
              {story.translation_flagged && (
                <span className="badge badge-warn">⚠ Translation</span>
              )}
              <span className="badge badge-published">Published</span>
              <span className="badge badge-lang">
                {(story.language_detected || 'KH').toUpperCase()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
