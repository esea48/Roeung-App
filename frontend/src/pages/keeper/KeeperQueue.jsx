import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKeeper } from './KeeperContext';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'flagged', label: '⚠ Flagged' },
  { key: 'kh', label: 'KH' },
  { key: 'en', label: 'EN' },
];

function formatDuration(seconds) {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m} min`;
}

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
  return `${days} days ago`;
}

export default function KeeperQueue() {
  const navigate = useNavigate();
  const { queue, queueLoading, queueError, loadQueue } = useKeeper();
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState('newest');

  useEffect(() => {
    loadQueue({ filter: filter || undefined, sort });
  }, [filter, sort]); // eslint-disable-line react-hooks/exhaustive-deps

  function openStory(storyId) {
    navigate(`/keeper/story/${storyId}`);
  }

  const storyCount = queue.length;

  return (
    <>
      <div className="queue-header">
        <div className="queue-title">Review queue</div>
        <div className="queue-sub">
          {queueLoading
            ? 'Loading…'
            : queueError
            ? 'Failed to load'
            : `${storyCount} ${storyCount === 1 ? 'story' : 'stories'} awaiting review`}
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
        {queueError && (
          <div className="keeper-error" style={{ alignItems: 'flex-start', padding: '12px 0' }}>
            {queueError}
          </div>
        )}

        {!queueLoading && !queueError && queue.length === 0 && (
          <div className="queue-empty">
            <div className="queue-empty-icon">✓</div>
            All caught up — no stories awaiting review.
          </div>
        )}

        {queue.map((story) => {
          const isLocked = !!story.lock?.keeper_name;
          return (
            <div
              key={story.id}
              className={`story-card ${isLocked ? 'story-card-locked' : ''}`}
              onClick={() => !isLocked && openStory(story.id)}
              role={isLocked ? undefined : 'button'}
              tabIndex={isLocked ? -1 : 0}
              onKeyDown={(e) => {
                if (!isLocked && (e.key === 'Enter' || e.key === ' ')) openStory(story.id);
              }}
            >
              <div className="story-card-body">
                <div className="story-card-title">
                  {story.title_en || story.title_kh || 'Untitled story'}
                </div>
                <div className="story-card-meta">
                  {story.narrator_name}
                  {story.narrator_deceased && ' †'}
                  {' · '}
                  {formatRelative(story.submitted_at)}
                </div>
              </div>

              <div className="story-card-badges">
                <span className="story-card-dur">{formatDuration(story.duration_seconds)}</span>
                {story.translation_flagged && (
                  <span className="badge badge-warn">⚠ Translation</span>
                )}
                {isLocked ? (
                  <span className="badge badge-locked">
                    🔒 {story.lock.keeper_name} reviewing
                  </span>
                ) : null}
                <span className="badge badge-lang">
                  {(story.language || 'KH').toUpperCase()}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
