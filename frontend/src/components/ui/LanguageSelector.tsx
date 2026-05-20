import { useTranslation } from 'react-i18next'

export function LanguageSelector() {
  const { i18n } = useTranslation()
  const current = i18n.language

  function setLang(lang: string) {
    void i18n.changeLanguage(lang)
    try {
      localStorage.setItem('autoflowops_lang', lang)
    } catch {
      // ignore
    }
  }

  return (
    <div className="flex items-center gap-1">
      {(['en', 'pt-BR'] as const).map((lang, idx) => (
        <span key={lang} className="flex items-center gap-1">
          {idx > 0 && <span className="text-gray-300 text-xs">·</span>}
          <button
            onClick={() => setLang(lang)}
            className={`text-xs transition-colors ${
              current === lang || (lang === 'pt-BR' && current.startsWith('pt'))
                ? 'font-semibold text-gray-800'
                : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            {lang === 'en' ? 'EN' : 'PT'}
          </button>
        </span>
      ))}
    </div>
  )
}
