import { useEffect } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { BookProvider, useBook } from './BookContext';
import BookHome from './BookHome';
import BookChapter from './BookChapter';
import BookStory from './BookStory';
import './book.css';

function BookNav() {
  const { accessToken, lang, setLang } = useBook();
  const location = useLocation();

  // Parse breadcrumb from location state set by child pages
  const crumb = location.state?.crumb;

  return (
    <nav className="book-nav">
      <div className="book-nav-inner">
        <Link to={`/f/${accessToken}/book`} className="book-nav-logo">
          <span className="book-nav-logo-mark">❧</span>
          The Sea Family
        </Link>
        {crumb && (
          <div className="book-nav-breadcrumb" aria-label="breadcrumb">
            {crumb}
          </div>
        )}
        <div className="book-nav-spacer" />
        <div className="book-lang-toggle">
          <button
            type="button"
            className={lang === 'en' ? 'active' : ''}
            onClick={() => setLang('en')}
          >
            EN
          </button>
          <button
            type="button"
            className={`kh ${lang === 'kh' ? 'active' : ''}`}
            onClick={() => setLang('kh')}
          >
            ខ្មែរ
          </button>
        </div>
      </div>
    </nav>
  );
}

function BookRoutes() {
  const { loadBook } = useBook();

  useEffect(() => {
    loadBook();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <BookNav />
      <Routes>
        <Route index element={<BookHome />} />
        <Route path="chapter/:chapterId" element={<BookChapter />} />
        <Route path="story/:storyId" element={<BookStory />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </>
  );
}

export default function BookApp() {
  const { accessToken } = useParams();
  return (
    <div className="book">
      <BookProvider accessToken={accessToken}>
        <BookRoutes />
      </BookProvider>
    </div>
  );
}
