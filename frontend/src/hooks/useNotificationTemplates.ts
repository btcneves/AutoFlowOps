import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createNotificationTemplate,
  deleteNotificationTemplate,
  getNotificationTemplates,
  updateNotificationTemplate,
} from '../api/notification_templates'

export function useNotificationTemplates() {
  return useQuery({
    queryKey: ['notification-templates'],
    queryFn: getNotificationTemplates,
  })
}

export function useCreateNotificationTemplate() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: createNotificationTemplate,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-templates'] }),
  })
}

export function useUpdateNotificationTemplate() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: updateNotificationTemplate,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-templates'] }),
  })
}

export function useDeleteNotificationTemplate() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: deleteNotificationTemplate,
    onSuccess: () => client.invalidateQueries({ queryKey: ['notification-templates'] }),
  })
}
