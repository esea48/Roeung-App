import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  createStory,
  createStoryTags,
  deleteStory,
  getBook,
  getFamilyMembers,
  uploadStoryAudio,
} from '../../api/client';

const CaptureCtx = createContext(null);

const initialState = {
  lang: 'en',
  path: 'record', // 'record' | 'upload'
  audioLang: 'kh', // 'kh' | 'en' — language of the audio, set by recorder at capture
  narratorId: null,
  narratorName: '',
  familyMembers: [],
  recentStories: [],
  loadingFamily: true,
  storyId: null,
  consentedAt: null,
  audio: null, // { blob, durationSec }
  tags: {}, // familyMemberId -> bool
  customTags: [], // free-text names from "+ Someone else"
};

export function CaptureProvider({ accessToken, children }) {
  const [state, setState] = useState(initialState);

  const setLang = useCallback((lang) => setState((s) => ({ ...s, lang })), []);
  const setPath = useCallback((path) => setState((s) => ({ ...s, path })), []);
  const setAudioLang = useCallback((audioLang) => setState((s) => ({ ...s, audioLang })), []);
  const setNarrator = useCallback(
    (narratorId, narratorName) => setState((s) => ({ ...s, narratorId, narratorName })),
    []
  );

  const loadFamilyData = useCallback(async () => {
    setState((s) => ({ ...s, loadingFamily: true }));
    try {
      const [members, book] = await Promise.all([
        getFamilyMembers(accessToken),
        getBook(accessToken),
      ]);
      setState((s) => ({
        ...s,
        familyMembers: members,
        recentStories: book.recent_stories,
        loadingFamily: false,
        narratorId: s.narratorId ?? members[0]?.id ?? null,
        narratorName: s.narratorName || members[0]?.name_en || '',
      }));
    } catch {
      setState((s) => ({ ...s, loadingFamily: false }));
    }
  }, [accessToken]);

  const agreeConsent = useCallback(async () => {
    const consentedAt = new Date();
    const story = await createStory(accessToken, {
      capture_method: state.path === 'record' ? 'recorded' : 'uploaded',
      narrator_id: state.narratorId,
      narrator_name_raw: state.narratorName || 'Unknown',
      consent_wording_key: state.path === 'record' ? 'v1_recorded' : 'v1_uploaded',
      consented_at: consentedAt.toISOString(),
      audio_language: state.audioLang,
    });
    setState((s) => ({
      ...s,
      storyId: story.id,
      consentedAt,
      tags: state.narratorId ? { [state.narratorId]: true } : {},
    }));
    return story;
  }, [accessToken, state.path, state.narratorId, state.narratorName]);

  const setAudio = useCallback((audio) => setState((s) => ({ ...s, audio })), []);

  const toggleTag = useCallback(
    (memberId) => setState((s) => ({ ...s, tags: { ...s.tags, [memberId]: !s.tags[memberId] } })),
    []
  );

  const addCustomTag = useCallback(
    (name) => setState((s) => (s.customTags.includes(name) ? s : { ...s, customTags: [...s.customTags, name] })),
    []
  );

  const submitTags = useCallback(async () => {
    const tags = [
      ...Object.entries(state.tags)
        .filter(([id, sel]) => sel && id !== state.narratorId)
        .map(([family_member_id]) => ({ family_member_id })),
      ...state.customTags.map((name_raw) => ({ name_raw })),
    ];
    if (tags.length === 0) return [];
    return createStoryTags(accessToken, state.storyId, tags);
  }, [accessToken, state.storyId, state.tags, state.narratorId, state.customTags]);

  const sendToKeepers = useCallback(
    (onProgress) => uploadStoryAudio(accessToken, state.storyId, state.audio.blob, onProgress),
    [accessToken, state.storyId, state.audio]
  );

  const deleteRecording = useCallback(
    () => deleteStory(accessToken, state.storyId),
    [accessToken, state.storyId]
  );

  const reset = useCallback(() => {
    setState((s) => ({
      ...initialState,
      lang: s.lang,
      familyMembers: s.familyMembers,
      recentStories: s.recentStories,
      loadingFamily: false,
      narratorId: s.familyMembers[0]?.id ?? null,
      narratorName: s.familyMembers[0]?.name_en || '',
    }));
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      accessToken,
      setLang,
      setPath,
      setAudioLang,
      setNarrator,
      loadFamilyData,
      agreeConsent,
      setAudio,
      toggleTag,
      addCustomTag,
      submitTags,
      sendToKeepers,
      deleteRecording,
      reset,
    }),
    [
      state,
      accessToken,
      setLang,
      setPath,
      setAudioLang,
      setNarrator,
      loadFamilyData,
      agreeConsent,
      setAudio,
      toggleTag,
      addCustomTag,
      submitTags,
      sendToKeepers,
      deleteRecording,
      reset,
    ]
  );

  return <CaptureCtx.Provider value={value}>{children}</CaptureCtx.Provider>;
}

export function useCapture() {
  const ctx = useContext(CaptureCtx);
  if (!ctx) throw new Error('useCapture must be used within a CaptureProvider');
  return ctx;
}
