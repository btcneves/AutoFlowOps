import { useTranslation } from 'react-i18next'
import type { WSStatus } from '../../hooks/useWebSocket'

interface Props {
  status: WSStatus
}

export function LiveIndicator({ status }: Props) {
  const { t } = useTranslation()

  if (status === 'open') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-green-600">
        <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        {t('liveIndicator.live')}
      </span>
    )
  }
  if (status === 'connecting') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
        <span className="h-2 w-2 rounded-full bg-gray-400" />
        {t('liveIndicator.connecting')}
      </span>
    )
  }
  return null
}
