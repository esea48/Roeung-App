// API client for /keeper/... routes — JWT auth via Supabase Bearer token.
// The dev server proxies /keeper/(queue|stories|family-members|chapters|stats)
// to the FastAPI backend. See vite.config.js.

const BASE = '';

async function request(path, options = {}, token) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }

  if (res.status === 204) return null;
  return res.json();
}

// Authenticate directly against the Supabase REST auth API.
// Requires VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.
export async function loginWithSupabase(email, password) {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !anonKey) {
    throw new Error('VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set');
  }

  const res = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: anonKey },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error_description || err.msg || 'Login failed');
  }

  return res.json(); // { access_token, refresh_token, expires_in, user: {...} }
}

// Queue & stats
export const getQueue = (token, params = {}) =>
  request(`/keeper/queue?${new URLSearchParams(params)}`, {}, token);

export const getKeeperStats = (token) =>
  request('/keeper/stats', {}, token);

export const getPublishedStories = (token, params = {}) =>
  request(`/keeper/published?${new URLSearchParams(params)}`, {}, token);

export const getArchivedStories = (token, params = {}) =>
  request(`/keeper/archived?${new URLSearchParams(params)}`, {}, token);

// Story detail + lock lifecycle
export const getStory = (token, storyId) =>
  request(`/keeper/stories/${storyId}`, {}, token);

export const lockStory = (token, storyId) =>
  request(`/keeper/stories/${storyId}/lock`, { method: 'POST' }, token);

// Heartbeat ping. On tab close, call with release=true using fetch+keepalive
// (sendBeacon cannot carry Authorization headers, so keepalive fetch is used
// instead — same fire-and-forget guarantee, with auth support).
export const pingStory = (token, storyId, release = false) =>
  request(
    `/keeper/stories/${storyId}/ping${release ? '?release=true' : ''}`,
    { method: 'POST' },
    token
  );

export const pingStoryBeacon = (token, storyId) => {
  const url = `/keeper/stories/${storyId}/ping?release=true`;
  fetch(url, {
    method: 'POST',
    keepalive: true,
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => {});
};

// Story mutations
export const updateStory = (token, storyId, payload) =>
  request(`/keeper/stories/${storyId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }, token);

export const updateSegment = (token, storyId, segmentType, segmentId, editedText) =>
  request(`/keeper/stories/${storyId}/${segmentType}/${segmentId}`, {
    method: 'PATCH',
    body: JSON.stringify({ edited_text: editedText }),
  }, token);

export const publishStory = (token, storyId, payload) =>
  request(`/keeper/stories/${storyId}/publish`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, token);

export const archiveStory = (token, storyId) =>
  request(`/keeper/stories/${storyId}/archive`, { method: 'POST' }, token);

export const unpublishStory = (token, storyId) =>
  request(`/keeper/stories/${storyId}/unpublish`, { method: 'POST' }, token);

export const deleteStory = (token, storyId) =>
  request(`/keeper/stories/${storyId}`, { method: 'DELETE' }, token);

export const restoreStory = (token, storyId) =>
  request(`/keeper/stories/${storyId}/restore`, { method: 'POST' }, token);

// People mentions
export const linkMention = (token, storyId, mentionId, familyMemberId) =>
  request(`/keeper/stories/${storyId}/people-mentions/${mentionId}/link`, {
    method: 'POST',
    body: JSON.stringify({ family_member_id: familyMemberId }),
  }, token);

export const dismissMention = (token, storyId, mentionId) =>
  request(`/keeper/stories/${storyId}/people-mentions/${mentionId}/dismiss`, {
    method: 'POST',
  }, token);

export const getFamilyToken = (token) =>
  request('/keeper/family-token', {}, token);

// Reference data
export const getFamilyMembers = (token) =>
  request('/keeper/family-members', {}, token);

export const getChapters = (token) =>
  request('/keeper/chapters', {}, token);

export const createChapter = (token, titleEn) =>
  request('/keeper/chapters', {
    method: 'POST',
    body: JSON.stringify({ title_en: titleEn }),
  }, token);

export const deleteChapter = (token, chapterId) =>
  request(`/keeper/chapters/${chapterId}`, { method: 'DELETE' }, token);
