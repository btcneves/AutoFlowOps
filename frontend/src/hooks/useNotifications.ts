import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  activateNotificationChannel,
  createNotificationChannel,
  deactivateNotificationChannel,
  deleteNotificationChannel,
  getNotificationChannels,
  getNotificationDeliveries,
  testNotificationChannel,
  updateNotificationChannel,
} from '../api/notifications'

export function useNotificationChannels() {
  return useQuery({
    queryKey: ['notification-channels'],
    queryFn: getNotificationChannels,
    refetchInterval: 30_000,
  })
}

export function useNotificationDeliveries() {
  return useQuery({
    queryKey: ['notification-deliveries'],
    queryFn: getNotificationDeliveries,
    refetchInterval: 30_000,
  })
}

export function useCreateNotificationChannel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: createNotificationChannel,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-channels'] }),
  })
}

export function useUpdateNotificationChannel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: updateNotificationChannel,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-channels'] }),
  })
}

export function useDeleteNotificationChannel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: deleteNotificationChannel,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-channels'] }),
  })
}

export function useActivateNotificationChannel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: activateNotificationChannel,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-channels'] }),
  })
}

export function useDeactivateNotificationChannel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: deactivateNotificationChannel,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-channels'] }),
  })
}

export function useTestNotificationChannel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: testNotificationChannel,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['notification-channels'] })
      void client.invalidateQueries({ queryKey: ['notification-deliveries'] })
    },
  })
}
