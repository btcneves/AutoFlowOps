import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import ptBr from './locales/pt-br.json'

function getSavedLang(): string {
  try {
    return localStorage.getItem('autoflowops_lang') ?? 'en'
  } catch {
    return 'en'
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    'pt-BR': { translation: ptBr },
  },
  lng: getSavedLang(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  initAsync: false,
})

export default i18n
