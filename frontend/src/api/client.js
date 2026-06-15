// Thin fetch wrapper for the `/f/{access_token}/...` family-member API
// (CLAUDE.md "Auth Model (Two-Tier)"). The dev server proxies `/f` to the
// FastAPI backend (see vite.config.js).

const BASE = '';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
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

export function getFamilyMembers(accessToken) {
  return request(`/f/${accessToken}/family-members`);
}

export function getBook(accessToken) {
  return request(`/f/${accessToken}/book`);
}

export function createStory(accessToken, payload) {
  return request(`/f/${accessToken}/stories`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function uploadStoryAudio(accessToken, storyId, file, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/f/${accessToken}/stories/${storyId}/audio`);
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response ? JSON.parse(xhr.response) : null);
      } else {
        let detail = xhr.statusText;
        try {
          detail = JSON.parse(xhr.response).detail || detail;
        } catch {
          // ignore parse errors, fall back to statusText
        }
        reject(new Error(detail));
      }
    };
    xhr.onerror = () => reject(new Error('Network error'));
    xhr.send(form);
  });
}

export function createStoryTags(accessToken, storyId, tags) {
  return request(`/f/${accessToken}/stories/${storyId}/tags`, {
    method: 'POST',
    body: JSON.stringify({ tags }),
  });
}

export function deleteStory(accessToken, storyId) {
  return request(`/f/${accessToken}/stories/${storyId}`, {
    method: 'DELETE',
  });
}
