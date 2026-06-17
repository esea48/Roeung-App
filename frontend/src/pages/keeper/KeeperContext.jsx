import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  loginWithSupabase,
  getQueue,
  getKeeperStats,
  getPublishedStories,
  getArchivedStories,
  getFamilyMembers,
  getChapters,
} from '../../api/keeperClient';

const TOKEN_KEY = 'roeung_keeper_token';
const USER_KEY = 'roeung_keeper_user';

const KeeperCtx = createContext(null);

export function KeeperProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  });

  const [queue, setQueue] = useState([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState(null);

  const [publishedStories, setPublishedStories] = useState([]);
  const [publishedLoading, setPublishedLoading] = useState(false);
  const [publishedError, setPublishedError] = useState(null);

  const [archivedStories, setArchivedStories] = useState([]);
  const [archivedLoading, setArchivedLoading] = useState(false);
  const [archivedError, setArchivedError] = useState(null);

  const [stats, setStats] = useState({ awaiting_review: 0, flagged: 0 });

  const [familyMembers, setFamilyMembers] = useState([]);
  const [chapters, setChapters] = useState([]);

  const login = useCallback(async (email, password) => {
    const data = await loginWithSupabase(email, password);
    const { access_token, user: supaUser } = data;
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(supaUser));
    setToken(access_token);
    setUser(supaUser);
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    setQueue([]);
    setPublishedStories([]);
    setArchivedStories([]);
  }, []);

  const loadQueue = useCallback(
    async (params = {}) => {
      if (!token) return;
      setQueueLoading(true);
      setQueueError(null);
      try {
        const data = await getQueue(token, params);
        setQueue(data);
      } catch (err) {
        if (err.message?.includes('401') || err.message?.toLowerCase().includes('unauthorized')) {
          logout();
        }
        setQueueError(err.message || 'Failed to load queue');
      } finally {
        setQueueLoading(false);
      }
    },
    [token, logout]
  );

  const loadPublished = useCallback(
    async (params = {}) => {
      if (!token) return;
      setPublishedLoading(true);
      setPublishedError(null);
      try {
        const data = await getPublishedStories(token, params);
        setPublishedStories(data);
      } catch (err) {
        if (err.message?.includes('401') || err.message?.toLowerCase().includes('unauthorized')) {
          logout();
        }
        setPublishedError(err.message || 'Failed to load published stories');
      } finally {
        setPublishedLoading(false);
      }
    },
    [token, logout]
  );

  const loadArchived = useCallback(
    async (params = {}) => {
      if (!token) return;
      setArchivedLoading(true);
      setArchivedError(null);
      try {
        const data = await getArchivedStories(token, params);
        setArchivedStories(data);
      } catch (err) {
        if (err.message?.includes('401') || err.message?.toLowerCase().includes('unauthorized')) {
          logout();
        }
        setArchivedError(err.message || 'Failed to load archived stories');
      } finally {
        setArchivedLoading(false);
      }
    },
    [token, logout]
  );

  const loadStats = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getKeeperStats(token);
      setStats(data);
    } catch {
      // Stats are non-critical; silently ignore
    }
  }, [token]);

  const loadFamilyMembers = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getFamilyMembers(token);
      setFamilyMembers(data);
    } catch {
      // Non-critical; used for mention linking
    }
  }, [token]);

  const loadChapters = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getChapters(token);
      setChapters(data);
    } catch {
      // Non-critical
    }
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      user,
      login,
      logout,
      queue,
      queueLoading,
      queueError,
      loadQueue,
      publishedStories,
      publishedLoading,
      publishedError,
      loadPublished,
      archivedStories,
      archivedLoading,
      archivedError,
      loadArchived,
      stats,
      loadStats,
      familyMembers,
      loadFamilyMembers,
      chapters,
      loadChapters,
    }),
    [
      token, user, login, logout,
      queue, queueLoading, queueError, loadQueue,
      publishedStories, publishedLoading, publishedError, loadPublished,
      archivedStories, archivedLoading, archivedError, loadArchived,
      stats, loadStats,
      familyMembers, loadFamilyMembers,
      chapters, loadChapters,
    ]
  );

  return <KeeperCtx.Provider value={value}>{children}</KeeperCtx.Provider>;
}

export function useKeeper() {
  const ctx = useContext(KeeperCtx);
  if (!ctx) throw new Error('useKeeper must be used within a KeeperProvider');
  return ctx;
}
