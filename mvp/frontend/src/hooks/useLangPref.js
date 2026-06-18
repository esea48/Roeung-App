import { useState } from 'react';

const STORAGE_KEY = 'roeung_lang';

/**
 * Language preference shared across all surfaces via localStorage.
 * Returns [lang, setLang] where lang is 'en' | 'kh'.
 */
export function useLangPref() {
  const [lang, setLangState] = useState(
    () => localStorage.getItem(STORAGE_KEY) || 'en'
  );

  function setLang(v) {
    setLangState(v);
    localStorage.setItem(STORAGE_KEY, v);
  }

  return [lang, setLang];
}
