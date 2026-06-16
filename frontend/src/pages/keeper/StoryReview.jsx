import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useKeeper } from './KeeperContext';
import {
  getStory,
  lockStory,
  pingStory,
  pingStoryBeacon,
  updateStory,
  publishStory,
  archiveStory,
  linkMention,
  dismissMention,
} from '../../api/keeperClient';

const PING_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

// Deterministic fake waveform heights from a story id hash
function waveformHeights(seed, count = 50) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return Array.from({ length: count }, (_, i) => {
    h = (h * 1664525 + 1013904223) >>> 0;
    return 10 + (h % 22);
  });
}

function formatTime(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

// ── Audio Player ─────────────────────────────────────────────────────────────

function AudioPlayer({ audioUrl, storyId }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1);
  const bars = waveformHeights(storyId || 'default');
  const SPEEDS = [0.75, 1, 1.25];

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => setCurrentTime(audio.currentTime);
    const onMeta = () => setDuration(audio.duration);
    const onEnd = () => setPlaying(false);
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('loadedmetadata', onMeta);
    audio.addEventListener('ended', onEnd);
    return () => {
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('loadedmetadata', onMeta);
      audio.removeEventListener('ended', onEnd);
    };
  }, []);

  function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play().then(() => setPlaying(true)).catch(() => {});
    }
  }

  function cycleSpeed() {
    const audio = audioRef.current;
    const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];
    setSpeed(next);
    if (audio) audio.playbackRate = next;
  }

  function seekToBar(idx) {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    audio.currentTime = (idx / bars.length) * duration;
  }

  const playedFrac = duration ? currentTime / duration : 0;
  const playedCount = Math.round(playedFrac * bars.length);

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      <button type="button" className="audio-play-btn" onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'}>
        {playing ? (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
            <rect x="2" y="1" width="4" height="12" rx="1" />
            <rect x="8" y="1" width="4" height="12" rx="1" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
            <path d="M3 1.5l9 5.5-9 5.5z" />
          </svg>
        )}
      </button>

      <div className="audio-waveform" role="slider" aria-label="Seek audio">
        {bars.map((h, i) => (
          <div
            key={i}
            className={`waveform-bar ${i < playedCount ? 'played' : ''}`}
            style={{ height: `${h}px` }}
            onClick={() => seekToBar(i)}
          />
        ))}
      </div>

      <div className="audio-time">
        {formatTime(currentTime)} / {formatTime(duration)}
      </div>

      <button type="button" className="audio-speed" onClick={cycleSpeed} title="Playback speed">
        {speed}×
      </button>
    </div>
  );
}

// ── Full-story transcript editor ──────────────────────────────────────────────

function TranscriptEditor({ story, mobileLang, onSave }) {
  const transcriptSegments = story.transcript_segments ?? [];
  const translationSegments = story.translation_segments ?? [];

  const fullTranscript =
    story.transcript_edited ??
    transcriptSegments.map((s) => s.edited_text ?? s.original_text).join('\n\n');
  const fullTranslation =
    story.translation_edited ??
    translationSegments.map((s) => s.edited_text ?? s.original_text).join('\n\n');

  const hasLowConfidence = translationSegments.some(
    (s) => s.confidence_score !== null && s.confidence_score < 0.7
  );

  const showKh = !mobileLang || mobileLang === 'kh';
  const showEn = !mobileLang || mobileLang === 'en';

  return (
    <div className="segment-row transcript-full">
      <div className={`segment-col ${!showKh ? 'hidden-mobile' : ''}`}>
        <textarea
          className="segment-textarea lang-kh transcript-full-area"
          defaultValue={fullTranscript}
          onBlur={(e) => onSave({ transcript_edited: e.target.value })}
          placeholder="Transcript…"
        />
      </div>
      <div className={`segment-col ${!showEn ? 'hidden-mobile' : ''}`}>
        <textarea
          className={`segment-textarea transcript-full-area${hasLowConfidence ? ' warn-segment' : ''}`}
          defaultValue={fullTranslation}
          onBlur={(e) => onSave({ translation_edited: e.target.value })}
          placeholder="Translation…"
        />
        {hasLowConfidence && (
          <div className="segment-warn-note">⚠ Some segments have low confidence</div>
        )}
      </div>
    </div>
  );
}

// ── People section ────────────────────────────────────────────────────────────

function PeopleSection({ tags, mentions, familyMembers, storyId, token, onUpdate }) {
  const [addingTag, setAddingTag] = useState(false);
  const [linkingMentionId, setLinkingMentionId] = useState(null);

  async function handleRemoveTag(tagId) {
    // Optimistic: parent handles via re-load
    try {
      await fetch(`/keeper/stories/${storyId}/tags/${tagId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      onUpdate();
    } catch {
      // Silently fail — not blocking
    }
  }

  async function handleAddTag(familyMemberId) {
    if (!familyMemberId) return;
    try {
      await fetch(`/keeper/stories/${storyId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ family_member_id: familyMemberId, tagged_by: 'keeper' }),
      });
      setAddingTag(false);
      onUpdate();
    } catch {
      // Silently fail
    }
  }

  async function handleLinkMention(mentionId, familyMemberId) {
    try {
      await linkMention(token, storyId, mentionId, familyMemberId);
      setLinkingMentionId(null);
      onUpdate();
    } catch {
      // Silently fail
    }
  }

  async function handleDismissMention(mentionId) {
    try {
      await dismissMention(token, storyId, mentionId);
      onUpdate();
    } catch {
      // Silently fail
    }
  }

  const pendingMentions = mentions.filter((m) => m.resolution_status === 'pending');
  const linkedMentions = mentions.filter((m) => m.resolution_status === 'linked');

  const taggedIds = new Set(tags.map((t) => t.family_member_id).filter(Boolean));
  const untaggedMembers = familyMembers.filter((m) => !taggedIds.has(m.id));

  return (
    <>
      {/* Story tags */}
      <div className="panel-section">
        <div className="panel-label">People tagged</div>
        <div className="chips-wrap">
          {tags.map((tag) => (
            <span key={tag.id} className={`person-chip ${tag.deceased_date ? 'deceased' : ''}`}>
              {tag.name_en || tag.name_raw}
              {tag.deceased_date && ' †'}
              <button
                type="button"
                className="chip-remove"
                onClick={() => handleRemoveTag(tag.id)}
                aria-label={`Remove ${tag.name_en || tag.name_raw}`}
              >
                ×
              </button>
            </span>
          ))}

          <button
            type="button"
            className="chip-add-btn"
            onClick={() => setAddingTag((v) => !v)}
          >
            + Add
          </button>
        </div>

        {addingTag && (
          <select
            className="chip-add-select"
            defaultValue=""
            onChange={(e) => handleAddTag(e.target.value)}
          >
            <option value="" disabled>
              Select family member…
            </option>
            {untaggedMembers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name_en}
                {m.deceased_date ? ' †' : ''}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* AI people mentions */}
      {(pendingMentions.length > 0 || linkedMentions.length > 0) && (
        <div className="panel-section">
          <div className="panel-label">AI-detected mentions</div>

          {pendingMentions.map((mention) => (
            <div key={mention.id} className="mention-row">
              <span className="mention-name">
                <span className="mention-quote">"{mention.name_raw}"</span>
              </span>

              {linkingMentionId === mention.id ? (
                <select
                  className="mention-link-select"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) handleLinkMention(mention.id, e.target.value);
                  }}
                >
                  <option value="" disabled>
                    Link to…
                  </option>
                  {familyMembers.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name_en}
                      {m.deceased_date ? ' †' : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <>
                  <button
                    type="button"
                    className="mention-btn mention-btn-link"
                    onClick={() => setLinkingMentionId(mention.id)}
                  >
                    Link
                  </button>
                  <button
                    type="button"
                    className="mention-btn mention-btn-dismiss"
                    onClick={() => handleDismissMention(mention.id)}
                  >
                    Dismiss
                  </button>
                </>
              )}
            </div>
          ))}

          {linkedMentions.map((mention) => (
            <div key={mention.id} className="mention-row">
              <span className="mention-name">
                <span className="mention-quote">"{mention.name_raw}"</span>
              </span>
              <span className="mention-resolved">
                ✓ {mention.linked_family_member_name || 'Linked'}
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ── Main StoryReview component ────────────────────────────────────────────────

export default function StoryReview() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const { token, familyMembers, loadFamilyMembers, chapters, loadChapters } = useKeeper();

  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Title picker
  const [selectedSuggestionIdx, setSelectedSuggestionIdx] = useState(null);
  const [customTitleEn, setCustomTitleEn] = useState('');
  const [customTitleKh, setCustomTitleKh] = useState('');

  // Translation flag (may differ from story.translation_flagged during editing)
  const [translationFlagged, setTranslationFlagged] = useState(false);

  // Chapter assignment
  const [chapterId, setChapterId] = useState('');

  // Decision state
  const [view, setView] = useState('review'); // 'review' | 'published' | 'archived'
  const [deciding, setDeciding] = useState(false);
  const [decisionError, setDecisionError] = useState(null);

  // Mobile transcript tab
  const [mobileLang, setMobileLang] = useState('kh');

  // Heartbeat refs
  const pingIntervalRef = useRef(null);

  const loadStory = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getStory(token, storyId);
      setStory(data);
      setTranslationFlagged(data.translation_flagged ?? false);
      // Pre-select the first suggestion if no custom title exists
      if (data.title_suggestions?.length > 0 && !data.title_en) {
        setSelectedSuggestionIdx(0);
      }
    } catch (err) {
      setError(err.message || 'Failed to load story');
    } finally {
      setLoading(false);
    }
  }, [token, storyId]);

  // Lock acquisition and heartbeat setup
  useEffect(() => {
    if (!token || !storyId) return;

    let cancelled = false;

    (async () => {
      try {
        await lockStory(token, storyId);
      } catch {
        // Lock may fail if already locked by someone else — load the story anyway
      }

      if (!cancelled) {
        await loadStory();
        loadFamilyMembers();
        loadChapters();
      }
    })();

    // Heartbeat: ping every 5 minutes to keep lock alive
    pingIntervalRef.current = setInterval(() => {
      pingStory(token, storyId).catch(() => {});
    }, PING_INTERVAL_MS);

    // Release lock on page unload (tab close, navigation away)
    const handleUnload = () => pingStoryBeacon(token, storyId);
    window.addEventListener('beforeunload', handleUnload);
    // Also release when tab becomes hidden (covers mobile background, OS-level close)
    const handleVisibility = () => {
      if (document.visibilityState === 'hidden') pingStoryBeacon(token, storyId);
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      cancelled = true;
      clearInterval(pingIntervalRef.current);
      window.removeEventListener('beforeunload', handleUnload);
      document.removeEventListener('visibilitychange', handleVisibility);
      // Release lock when component unmounts (navigating back to queue)
      pingStory(token, storyId, true).catch(() => {});
    };
  }, [token, storyId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleTranscriptSave(patch) {
    try {
      await updateStory(token, storyId, patch);
    } catch {
      // Non-blocking: textarea already reflects the edit
    }
  }

  async function handleFlagToggle(on) {
    setTranslationFlagged(on);
    try {
      await updateStory(token, storyId, { translation_flagged: on });
    } catch {
      setTranslationFlagged(!on); // revert on failure
    }
  }

  function resolvedTitle() {
    if (selectedSuggestionIdx !== null && story?.title_suggestions?.length > selectedSuggestionIdx) {
      return {
        title_en: story.title_suggestions[selectedSuggestionIdx].title_en,
        title_kh: story.title_suggestions[selectedSuggestionIdx].title_kh,
      };
    }
    return { title_en: customTitleEn || undefined, title_kh: customTitleKh || undefined };
  }

  async function handlePublish(withFlag = false) {
    setDecisionError(null);
    setDeciding(true);
    try {
      const titlePayload = resolvedTitle();
      await updateStory(token, storyId, {
        ...titlePayload,
        translation_flagged: withFlag || translationFlagged,
      });
      await publishStory(token, storyId, {
        chapter_id: chapterId || null,
        translation_flagged: withFlag || translationFlagged,
      });
      setView('published');
    } catch (err) {
      setDecisionError(err.message || 'Failed to publish');
    } finally {
      setDeciding(false);
    }
  }

  async function handleArchive() {
    setDecisionError(null);
    setDeciding(true);
    try {
      await archiveStory(token, storyId);
      setView('archived');
    } catch (err) {
      setDecisionError(err.message || 'Failed to archive');
    } finally {
      setDeciding(false);
    }
  }

  // ── Published confirmation ────────────────────────────────────────────────

  if (view === 'published') {
    const finalTitle = story
      ? (story.title_en || resolvedTitle().title_en || 'Untitled story')
      : 'Story';
    return (
      <div className="published-wrap">
        <div className="published-card">
          <div className="published-icon">✓</div>
          <div className="published-title">Published to the book</div>
          <div className="published-story-title">{finalTitle}</div>
          <div className="published-actions">
            <button
              type="button"
              className="btn-back-queue"
              onClick={() => navigate('/keeper')}
            >
              Back to queue
            </button>
            <button
              type="button"
              className="btn-view-story"
              onClick={() => navigate('/keeper')}
            >
              View in book →
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (view === 'archived') {
    return (
      <div className="published-wrap">
        <div className="published-card">
          <div className="published-icon" style={{ fontSize: '22px', color: 'var(--faint)' }}>
            🗄
          </div>
          <div className="published-title">Archived privately</div>
          <div className="published-story-title">
            This story has been preserved but not published to the book.
          </div>
          <div className="published-actions">
            <button
              type="button"
              className="btn-back-queue"
              onClick={() => navigate('/keeper')}
            >
              Back to queue
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Loading / error ───────────────────────────────────────────────────────

  if (loading) {
    return <div className="keeper-loading">Loading story…</div>;
  }

  if (error) {
    return (
      <div className="keeper-error">
        <div>{error}</div>
        <button type="button" className="btn-back-queue" onClick={() => navigate('/keeper')}>
          Back to queue
        </button>
      </div>
    );
  }

  if (!story) return null;

  const isLockedByOther =
    story.lock?.keeper_name && story.lock.keeper_name !== story.current_keeper_name;

  const audioUrl = story.audio_file?.storage_url;
  const titleSuggestions = story.title_suggestions ?? [];
  const tags = story.story_tags ?? [];
  const mentions = story.ai_people_mentions ?? [];

  // ── Review UI ─────────────────────────────────────────────────────────────

  return (
    <div className="review-wrap">
      {/* Header */}
      <div className="review-header">
        <div className="review-header-left">
          <button type="button" className="review-back" onClick={() => navigate('/keeper')}>
            ← Queue
          </button>
          <div className="review-narrator">
            {story.narrator_name}
            {story.narrator_deceased && ' †'}
          </div>
          {story.narrator_name_kh && (
            <div className="review-narrator-kh">{story.narrator_name_kh}</div>
          )}
          <div className="review-meta">
            {story.language?.toUpperCase()} ·{' '}
            {story.duration_seconds
              ? `${Math.round(story.duration_seconds / 60)} min`
              : ''}
            {story.submitted_at && (
              <> · Submitted {new Date(story.submitted_at).toLocaleDateString()}</>
            )}
          </div>
        </div>

        {isLockedByOther && (
          <div className="review-lock-banner">
            🔒 {story.lock.keeper_name} is reviewing this story
          </div>
        )}
      </div>

      {/* Audio player */}
      <AudioPlayer audioUrl={audioUrl} storyId={storyId} />

      {/* Mobile lang tabs — hidden on desktop, shown via CSS @media */}
      <div className="mobile-lang-tabs-wrap">
        <div className="lang-tabs">
          <button
            type="button"
            className={`lang-tab ${mobileLang === 'kh' ? 'active' : ''}`}
            onClick={() => setMobileLang('kh')}
          >
            Transcript KH
          </button>
          <button
            type="button"
            className={`lang-tab ${mobileLang === 'en' ? 'active' : ''}`}
            onClick={() => setMobileLang('en')}
          >
            Translation EN
          </button>
        </div>
      </div>

      {/* Body: transcript + right panel */}
      <div className="review-body">
        {/* Bilingual transcript */}
        <div className="review-transcript-area">
          <div className="transcript-header">
            <div className="transcript-col-label">
              Transcript KH
              {story.translation_confidence_score !== null &&
                story.translation_confidence_score !== undefined && (
                  <span
                    style={{
                      color:
                        story.translation_confidence_score < 0.7
                          ? 'var(--warn-strong)'
                          : 'var(--faint2)',
                    }}
                  >
                    {story.translation_confidence_score < 0.7 && '⚠ '}
                    {Math.round(story.translation_confidence_score * 100)}% confidence
                  </span>
                )}
            </div>
            <div className="transcript-col-label">Translation EN</div>
          </div>

          <div className="transcript-cols">
            {(story.transcript_segments ?? []).length === 0 && !story.transcript_edited ? (
              <div style={{ color: 'var(--faint)', fontSize: '12px' }}>
                No transcript segments yet.
              </div>
            ) : (
              <TranscriptEditor
                story={story}
                mobileLang={mobileLang}
                onSave={handleTranscriptSave}
              />
            )}
          </div>
        </div>

        {/* Right panel */}
        <div className="review-sidebar-panel">
          {/* Title picker */}
          <div className="panel-section">
            <div className="panel-label">Title</div>

            {titleSuggestions.map((sug, idx) => (
              <div
                key={sug.id ?? idx}
                className={`title-option ${selectedSuggestionIdx === idx ? 'selected' : ''}`}
                aria-label={`Title option ${idx + 1}: ${sug.title_en}${sug.title_kh ? ` / ${sug.title_kh}` : ''}`}
                onClick={() => {
                  setSelectedSuggestionIdx(idx);
                  setCustomTitleEn('');
                  setCustomTitleKh('');
                }}
                role="radio"
                tabIndex={0}
                aria-checked={selectedSuggestionIdx === idx}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    setSelectedSuggestionIdx(idx);
                    setCustomTitleEn('');
                    setCustomTitleKh('');
                  }
                }}
              >
                <div className="title-radio" />
                <div className="title-option-text">
                  <div className="title-option-en">{sug.title_en}</div>
                  {sug.title_kh && (
                    <div className="title-option-kh">{sug.title_kh}</div>
                  )}
                </div>
              </div>
            ))}

            {/* Custom title */}
            <div
              className={`title-option ${selectedSuggestionIdx === null ? 'selected' : ''}`}
              aria-label="Custom title"
              onClick={() => setSelectedSuggestionIdx(null)}
              role="radio"
              tabIndex={0}
              aria-checked={selectedSuggestionIdx === null}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setSelectedSuggestionIdx(null);
              }}
            >
              <div className="title-radio" />
              <div className="title-option-text" style={{ color: 'var(--faint)' }}>
                ✎ Custom title
              </div>
            </div>

            {selectedSuggestionIdx === null && (
              <>
                <input
                  type="text"
                  className="title-custom-input"
                  placeholder="Title in English…"
                  value={customTitleEn}
                  onChange={(e) => setCustomTitleEn(e.target.value)}
                />
                <input
                  type="text"
                  className="title-custom-input title-custom-kh"
                  placeholder="ចំណងជើងជាភាសាខ្មែរ…"
                  value={customTitleKh}
                  onChange={(e) => setCustomTitleKh(e.target.value)}
                />
              </>
            )}
          </div>

          {/* People: tags + mentions */}
          <PeopleSection
            tags={tags}
            mentions={mentions}
            familyMembers={familyMembers}
            storyId={storyId}
            token={token}
            onUpdate={loadStory}
          />

          {/* Translation flag */}
          <div className="panel-section">
            <div className="panel-label">Translation quality</div>
            <div className="flag-row">
              <div className="flag-text">
                <div className="flag-label-text">⚠ Translation approximate</div>
                <div className="flag-sublabel">Shown to readers on this story</div>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={translationFlagged}
                  onChange={(e) => handleFlagToggle(e.target.checked)}
                />
                <span className="toggle-track" />
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Decision bar */}
      <div className="decision-bar">
        <span className="decision-label">Publish to:</span>
        <select
          className="chapter-select"
          value={chapterId}
          onChange={(e) => setChapterId(e.target.value)}
        >
          <option value="">Uncategorised</option>
          {chapters.map((ch) => (
            <option key={ch.id} value={ch.id}>
              {ch.title_en}
            </option>
          ))}
        </select>

        <button
          type="button"
          className="btn-publish"
          onClick={() => handlePublish(false)}
          disabled={deciding}
        >
          Publish →
        </button>

        <button
          type="button"
          className="btn-publish-flag"
          onClick={() => handlePublish(true)}
          disabled={deciding}
          title="Publish and mark translation as approximate"
        >
          Publish with ⚠ flag
        </button>

        <button
          type="button"
          className="btn-archive"
          onClick={handleArchive}
          disabled={deciding}
        >
          Archive privately
        </button>

        {decisionError && (
          <span style={{ fontSize: '11px', color: 'var(--danger)', marginLeft: '8px' }}>
            {decisionError}
          </span>
        )}
      </div>
    </div>
  );
}
