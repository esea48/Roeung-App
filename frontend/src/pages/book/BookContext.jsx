import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { getBook } from '../../api/client';

const BookCtx = createContext(null);

export function BookProvider({ accessToken, children }) {
  const [lang, setLang] = useState('en');
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadBook = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBook(accessToken);
      setBook(data);
    } catch (err) {
      setError(err.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  const value = useMemo(
    () => ({ accessToken, lang, setLang, book, loading, error, loadBook }),
    [accessToken, lang, book, loading, error, loadBook]
  );

  return <BookCtx.Provider value={value}>{children}</BookCtx.Provider>;
}

export function useBook() {
  const ctx = useContext(BookCtx);
  if (!ctx) throw new Error('useBook must be used within a BookProvider');
  return ctx;
}
