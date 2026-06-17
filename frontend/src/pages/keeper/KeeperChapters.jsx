import { useEffect, useState } from 'react';
import { useKeeper } from './KeeperContext';
import { createChapter, deleteChapter } from '../../api/keeperClient';

export default function KeeperChapters() {
  const { token, chapters, loadChapters } = useKeeper();
  const [toast, setToast] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(null);
  const [showAddRow, setShowAddRow] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [addInProgress, setAddInProgress] = useState(false);

  useEffect(() => {
    loadChapters();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function showToast(message) {
    setToast(message);
    setTimeout(() => setToast(null), 3500);
  }

  async function handleAdd(e) {
    e.preventDefault();
    const title = newTitle.trim();
    if (!title) return;
    setAddInProgress(true);
    try {
      await createChapter(token, title);
      setNewTitle('');
      setShowAddRow(false);
      await loadChapters();
      showToast(`Chapter "${title}" added.`);
    } catch (err) {
      showToast(`Failed to add chapter: ${err.message}`);
    } finally {
      setAddInProgress(false);
    }
  }

  async function handleDelete(chapter) {
    setActionInProgress(chapter.id);
    try {
      await deleteChapter(token, chapter.id);
      setConfirmDeleteId(null);
      await loadChapters();
      showToast(`"${chapter.title_en}" deleted. Stories moved to Uncategorised.`);
    } catch (err) {
      showToast(`Failed to delete: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  }

  return (
    <>
      {toast && <div className="archive-toast">{toast}</div>}

      <div className="queue-header">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
          <div className="queue-title">Chapters</div>
          <button
            type="button"
            className="btn-archive-action btn-restore"
            style={{ fontSize: '12px', padding: '4px 10px' }}
            onClick={() => { setShowAddRow(true); setConfirmDeleteId(null); }}
          >
            + Add chapter
          </button>
        </div>
        <div className="queue-sub" style={{ marginTop: '4px' }}>
          {chapters.length} {chapters.length === 1 ? 'chapter' : 'chapters'}
        </div>
      </div>

      <div className="queue-list">
        {chapters.map((chapter) => {
          const isBusy = actionInProgress === chapter.id;
          const isConfirming = confirmDeleteId === chapter.id;

          return (
            <div key={chapter.id} className="story-card archive-card">
              <div className="story-card-body">
                <div className="story-card-title">{chapter.title_en}</div>
                {chapter.title_kh && (
                  <div className="story-card-meta" style={{ fontFamily: 'var(--font-kh)' }}>
                    {chapter.title_kh}
                  </div>
                )}
              </div>

              <div className="archive-card-actions">
                {isConfirming ? (
                  <div className="archive-confirm">
                    <span className="archive-confirm-text">
                      Delete "{chapter.title_en}"? Stories will become uncategorised.
                    </span>
                    <button
                      type="button"
                      className="btn-archive-action btn-delete-confirm"
                      onClick={() => handleDelete(chapter)}
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
                  <button
                    type="button"
                    className="btn-archive-action btn-delete-story"
                    onClick={() => { setConfirmDeleteId(chapter.id); setShowAddRow(false); }}
                    disabled={isBusy}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {showAddRow && (
          <form className="story-card archive-card" onSubmit={handleAdd}>
            <div className="story-card-body" style={{ flex: 1 }}>
              <input
                type="text"
                className="chapter-title-input"
                placeholder="Chapter title (English)"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                autoFocus
                disabled={addInProgress}
              />
            </div>
            <div className="archive-card-actions">
              <button
                type="submit"
                className="btn-archive-action btn-restore"
                disabled={addInProgress || !newTitle.trim()}
              >
                Save
              </button>
              <button
                type="button"
                className="btn-archive-action btn-cancel"
                onClick={() => { setShowAddRow(false); setNewTitle(''); }}
                disabled={addInProgress}
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {chapters.length === 0 && !showAddRow && (
          <div className="queue-empty">
            <div className="queue-empty-icon">🗂</div>
            No chapters yet.
          </div>
        )}
      </div>
    </>
  );
}
