import { apiFetch } from './client'
import type { WebhookEventRead, WebhookRead } from '../types'

export function getWebhooks(): Promise<WebhookRead[]> {
  return apiFetch<WebhookRead[]>('/api/webhooks')
}

export function getWebhookEvents(webhookId: string): Promise<WebhookEventRead[]> {
  return apiFetch<WebhookEventRead[]>(`/api/webhooks/${webhookId}/events`)
}
