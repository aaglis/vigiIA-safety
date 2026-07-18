import { describe, expect, it } from 'vitest'
import { cameraEditFormSchema, cameraFormSchema, zoneFormSchema } from '../schemas'

describe('operations schemas', () => {
  it('requires a live stream URL for camera creation', () => {
    expect(cameraFormSchema.safeParse({ site_id: 'site-1', name: 'Cam 1', stream_identifier: '', status: 'active' }).success).toBe(false)
    expect(cameraFormSchema.safeParse({ site_id: 'site-1', name: 'Cam 1', stream_identifier: 'https://example.invalid/video', status: 'active' }).success).toBe(false)
    expect(cameraFormSchema.safeParse({ site_id: 'site-1', name: 'Cam 1', stream_identifier: 'rtsp://10.0.0.20:554/live', status: 'active' }).success).toBe(true)
  })

  it('allows blank stream on edit', () => {
    expect(cameraEditFormSchema.safeParse({ site_id: 'site-1', name: 'Cam 1', stream_identifier: '', status: 'inactive' }).success).toBe(true)
  })

  it('requires an empty or closed polygon', () => {
    expect(zoneFormSchema.safeParse({ site_id: 'site-1', camera_id: 'cam-1', name: 'Zona', zone_type: 'ppe', status: 'active', polygon: [] }).success).toBe(true)
    expect(zoneFormSchema.safeParse({ site_id: 'site-1', camera_id: 'cam-1', name: 'Zona', zone_type: 'ppe', status: 'active', polygon: [[0, 0], [1, 0]] }).success).toBe(false)
    expect(zoneFormSchema.safeParse({ site_id: 'site-1', camera_id: 'cam-1', name: 'Zona', zone_type: 'ppe', status: 'active', polygon: [[0, 0], [1, 0], [1, 1]] }).success).toBe(true)
  })
})
