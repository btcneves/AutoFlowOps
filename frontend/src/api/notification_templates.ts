import { apiFetch } from './client'
import type { NotificationTemplatePayload, NotificationTemplateRead } from '../types'

export function getNotificationTemplates(): Promise<NotificationTemplateRead[]> {
  return apiFetch<NotificationTemplateRead[]>('/api/notification-templates')
}

export function createNotificationTemplate(
  payload: NotificationTemplatePayload
): Promise<NotificationTemplateRead> {
  return apiFetch<NotificationTemplateRead>('/api/notification-templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateNotificationTemplate({
  id,
  payload,
}: {
  id: string
  payload: Partial<NotificationTemplatePayload>
}): Promise<NotificationTemplateRead> {
  return apiFetch<NotificationTemplateRead>(`/api/notification-templates/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteNotificationTemplate(id: string): Promise<void> {
  return apiFetch<void>(`/api/notification-templates/${id}`, { method: 'DELETE' })
}
