import { useEffect, useState } from 'react';
import { useKeeper } from './KeeperContext';
import { deleteStory, restoreStory } from '../../api/keeperClient';

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

export default function KeeperArchive() {
  const { token, archivedStories, archivedLoading, archivedError, loadArchived } = useKeeper();
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState('newest');
  const [toast, setToast] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(null);

  useEffect(() => {
    loadArchived({ filter: filter || undefined, sort });
  }, [filter, sort]); // eslint-disable-line react-hooks/exhaustive-deps

  function showToast(message) {
    setToast(message);
    setTimeout(() => setToast(null), 3500);
  }

  async function handleRestore(story) {
    setActionInProgress(story.id);
    try {
      await restoreStory(token, story.id);
      showToast(`'${story.title_en || story.title_kh || 'Story'}' has been restored.`);
      loadArchived({ filter: filter || undefined, sort });
    } catch (err) {
      showToast(`Failed to restore: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleDelete(story) {
    setActionInProgress(story.id);
    try {
      await deleteStory(token, story.id);
      setConfirmDeleteId(null);
      showToast(`'${story.title_en || story.title_kh || 'Story'}' has been deleted.`);
      loadArchived({ filter: filter || undefined, sort });
    } catch (err) {
      showToast(`Failed to delete: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  }

  const count = archivedStories.length;

  return (
    <>
      {toast && (
        <div className="archive-toast">{toast}</div>
      )}

      <div className="queue-header">
        <div className="queue-title">Archive</div>
        <div className="queue-sub archive-keeper-note">Visible to Keepers only</div>
        <div className="queue-sub" style={{ marginTop: '2px' }}>
          {archivedLoading
            ? 'Loading…'
            : archivedError
            ? 'Failed to load'
            : `${count} archived ${count === 1 ? 'story' : 'stories'}`}
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
        {archivedError && (
          <div className="keeper-error" style={{ alignItems: 'flex-start', padding: '12px 0' }}>
            {archivedError}
          </div>
        )}

        {!archivedLoading && !archivedError && archivedStories.length === 0 && (
          <div className="queue-empty">
            <div className="queue-empty-icon">🗄</div>
            Archive is empty.
          </div>
        )}

        {archivedStories.map((story) => {
          const title = story.title_en || story.title_kh || 'Untitled story';
          const isBusy = actionInProgress === story.id;
          const isConfirming = confirmDeleteId === story.id;

          return (
            <div key={story.id} className="story-card archive-card">
              <div className="story-card-body">
                <div className="story-card-title">{title}</div>
                <div className="story-card-meta">
                  {story.narrator_name_raw}
                  {' · '}
                  Archived {formatRelative(story.archived_at)}
                </div>
              </div>

              <div className="archive-card-actions">
                {isConfirming ? (
                  <div className="archive-confirm">
                    <span className="archive-confirm-text">
                      Permanently delete "{title}"?
                    </span>
                    <button
                      type="button"
                      className="btn-archive-action btn-delete-confirm"
                      onClick={() => handleDelete(story)}
                      disabled={isBusy}
                    >
                      Delete
                    </button>
                    <button
                      type="button"
                      className="btn-archive-action btn-cancel"
                      onClick={() => setConfirmDeleteId(null)}
                      disabled={isBusy}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      className="btn-archive-action btn-restore"
                      onClick={() => handleRestore(story)}
                      disabled={isBusy}
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      className="btn-archive-action btn-delete-story"
                      onClick={() => setConfirmDeleteId(story.id)}
                      disabled={isBusy}
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
