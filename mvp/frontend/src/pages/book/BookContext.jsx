import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  getBook,
  getChapterStories,
  getKeeperBook,
  getKeeperChapterStories,
  getKeeperStoryDetail,
  getKeeperUncategorisedStories,
  getStoryDetail,
  getUncategorisedStories,
} from '../../api/client';
import { useLangPref } from '../../hooks/useLangPref';

const BookCtx = createContext(null);

export function BookProvider({ accessToken, keeperToken, children }) {
  const [lang, setLang] = useLangPref();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isKeeper = !!keeperToken;
  const basePath = isKeeper ? '/keeper/book' : `/f/${accessToken}/book`;

  const loadBook = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = isKeeper ? await getKeeperBook(keeperToken) : await getBook(accessToken);
      setBook(data);
    } catch (err) {
      setError(err.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [isKeeper, keeperToken, accessToken]);

  const fetchChapterStories = useCallback(
    (chapterId, sort) =>
      isKeeper
        ? getKeeperChapterStories(keeperToken, chapterId, sort)
        : getChapterStories(accessToken, chapterId, sort),
    [isKeeper, keeperToken, accessToken],
  );

  const fetchUncategorisedStories = useCallback(
    (sort) =>
      isKeeper
        ? getKeeperUncategorisedStories(keeperToken, sort)
        : getUncategorisedStories(accessToken, sort),
    [isKeeper, keeperToken, accessToken],
  );

  const fetchStoryDetail = useCallback(
    (storyId) =>
      isKeeper
        ? getKeeperStoryDetail(keeperToken, storyId)
        : getStoryDetail(accessToken, storyId),
    [isKeeper, keeperToken, accessToken],
  );

  const value = useMemo(
    () => ({
      accessToken,
      keeperToken,
      isKeeper,
      basePath,
      lang,
      setLang,
      book,
      loading,
      error,
      loadBook,
      fetchChapterStories,
      fetchUncategorisedStories,
      fetchStoryDetail,
    }),
    [
      accessToken,
      keeperToken,
      isKeeper,
      basePath,
      lang,
      book,
      loading,
      error,
      loadBook,
      fetchChapterStories,
      fetchUncategorisedStories,
      fetchStoryDetail,
    ],
  );

  return <BookCtx.Provider value={value}>{children}</BookCtx.Provider>;
}

export function useBook() {
  const ctx = useContext(BookCtx);
  if (!ctx) throw new Error('useBook must be used within a BookProvider');
  return ctx;
}
