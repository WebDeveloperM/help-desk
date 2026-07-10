import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import ruCommon from './locales/ru/common.json';
import ruTickets from './locales/ru/tickets.json';
import ruDepartments from './locales/ru/departments.json';
import ruDashboard from './locales/ru/dashboard.json';
import ruReports from './locales/ru/reports.json';
import ruSettings from './locales/ru/settings.json';
import ruAuth from './locales/ru/auth.json';
import ruErrors from './locales/ru/errors.json';
import ruNotifications from './locales/ru/notifications.json';

import uzCommon from './locales/uz/common.json';
import uzTickets from './locales/uz/tickets.json';
import uzDepartments from './locales/uz/departments.json';
import uzDashboard from './locales/uz/dashboard.json';
import uzReports from './locales/uz/reports.json';
import uzSettings from './locales/uz/settings.json';
import uzAuth from './locales/uz/auth.json';
import uzErrors from './locales/uz/errors.json';
import uzNotifications from './locales/uz/notifications.json';

export const SUPPORTED_LANGUAGES = ['ru', 'uz'] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'ru';
export const LANGUAGE_STORAGE_KEY = 'helpdesk.language';

export const LANGUAGE_LABELS: Record<SupportedLanguage, string> = {
  ru: 'Русский',
  uz: "O'zbekcha",
};

export const LANGUAGE_SHORT_LABELS: Record<SupportedLanguage, string> = {
  ru: 'RU',
  uz: "O'z",
};

export const LANGUAGE_HTML_LANG: Record<SupportedLanguage, string> = {
  ru: 'ru',
  uz: 'uz-Latn',
};

export const isSupportedLanguage = (value: string | null | undefined): value is SupportedLanguage =>
  !!value && (SUPPORTED_LANGUAGES as readonly string[]).includes(value);

const resources = {
  ru: {
    common: ruCommon,
    tickets: ruTickets,
    departments: ruDepartments,
    dashboard: ruDashboard,
    reports: ruReports,
    settings: ruSettings,
    auth: ruAuth,
    errors: ruErrors,
    notifications: ruNotifications,
  },
  uz: {
    common: uzCommon,
    tickets: uzTickets,
    departments: uzDepartments,
    dashboard: uzDashboard,
    reports: uzReports,
    settings: uzSettings,
    auth: uzAuth,
    errors: uzErrors,
    notifications: uzNotifications,
  },
} as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
    nonExplicitSupportedLngs: true,
    load: 'languageOnly',
    ns: ['common', 'tickets', 'departments', 'dashboard', 'reports', 'settings', 'auth', 'errors', 'notifications'],
    defaultNS: 'common',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ['localStorage'],
    },
    returnNull: false,
  });

const syncHtmlLang = (lng: string): void => {
  const normalized = lng.split('-')[0];
  if (isSupportedLanguage(normalized)) {
    document.documentElement.lang = LANGUAGE_HTML_LANG[normalized];
  } else {
    document.documentElement.lang = LANGUAGE_HTML_LANG[DEFAULT_LANGUAGE];
  }
};

syncHtmlLang(i18n.language || DEFAULT_LANGUAGE);
i18n.on('languageChanged', syncHtmlLang);

export default i18n;
