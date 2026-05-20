import { useQuery } from '@tanstack/react-query'
import { getWebhookEvents, getWebhooks } from '../api/webhooks'
import type { WebhookEventRead, WebhookRead } from '../types'

export function useWebhooks() {
  return useQuery<WebhookRead[]>({
    queryKey: ['webhooks'],
    queryFn: getWebhooks,
    refetchInterval: 30_000,
  })
}

export function useWebhookEvents(webhookId: string) {
  return useQuery<WebhookEventRead[]>({
    queryKey: ['webhook-events', webhookId],
    queryFn: () => getWebhookEvents(webhookId),
    refetchInterval: 15_000,
  })
}
