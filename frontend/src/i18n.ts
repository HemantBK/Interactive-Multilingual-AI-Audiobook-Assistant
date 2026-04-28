import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import hi from './locales/hi.json';

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'hi'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'aria.lang',
      caches: ['localStorage'],
    },
  });

// Day 21 a11y: sync <html lang> with the active i18n language so screen
// readers (NVDA, VoiceOver) pronounce UI strings in the right language.
// Per-content `lang={...}` overrides this for embedded snippets in
// other languages (e.g. an English question with a Hindi answer).
if (typeof document !== 'undefined') {
  const apply = (lng: string) => {
    document.documentElement.lang = (lng || 'en').slice(0, 2);
  };
  apply(i18n.language);
  i18n.on('languageChanged', apply);
}

export default i18n;
