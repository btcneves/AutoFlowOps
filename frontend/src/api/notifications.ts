import { apiFetch } from './client'
import type {
  NotificationChannelPayload,
  NotificationChannelRead,
  NotificationChannelUpdatePayload,
  NotificationDeliveryRead,
  NotificationTestResult,
} from '../types'

export function getNotificationChannels(): Promise<NotificationChannelRead[]> {
  return apiFetch<NotificationChannelRead[]>('/api/notification-channels')
}

export function createNotificationChannel(
  payload: NotificationChannelPayload
): Promise<NotificationChannelRead> {
  return apiFetch<NotificationChannelRead>('/api/notification-channels', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateNotificationChannel({
  id,
  payload,
}: {
  id: string
  payload: NotificationChannelUpdatePayload
}): Promise<NotificationChannelRead> {
  return apiFetch<NotificationChannelRead>(`/api/notification-channels/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteNotificationChannel(id: string): Promise<void> {
  return apiFetch<void>(`/api/notification-channels/${id}`, { method: 'DELETE' })
}

export function activateNotificationChannel(id: string): Promise<NotificationChannelRead> {
  return apiFetch<NotificationChannelRead>(`/api/notification-channels/${id}/activate`, {
    method: 'PATCH',
  })
}

export function deactivateNotificationChannel(id: string): Promise<NotificationChannelRead> {
  return apiFetch<NotificationChannelRead>(`/api/notification-channels/${id}/deactivate`, {
    method: 'PATCH',
  })
}

export function testNotificationChannel(id: string): Promise<NotificationTestResult> {
  return apiFetch<NotificationTestResult>(`/api/notification-channels/${id}/test`, {
    method: 'POST',
  })
}

export function getNotificationDeliveries(): Promise<NotificationDeliveryRead[]> {
  return apiFetch<NotificationDeliveryRead[]>('/api/notification-channels/deliveries')
}
