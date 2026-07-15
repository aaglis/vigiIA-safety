import { expect, test, type Page } from '@playwright/test'

const now = '2026-07-14T21:00:00.000Z'
const signedEvidenceUrl = 'https://signed.example.invalid/evidence/inc-1/file-1?X-Amz-Signature=redacted-test-signature'

const organization = { id: 'org-demo', name: 'VigIA Demo', slug: 'vigia-demo' }
const meResponse = {
  user: { id: 'user-dev', email: 'admin@vigia.local', full_name: 'VigIA Admin' },
  memberships: [{ organization, role: 'org_owner', permissions: ['view_dashboard'], active: true }],
  active_organization: organization,
  active_permissions: ['view_dashboard'],
}

const incident = {
  id: 'inc-1',
  organization_id: organization.id,
  site_id: 'site-demo',
  detection_event_id: 'event-1',
  camera_id: 'camera-demo-01',
  zone_id: 'zone-demo-01',
  worker_id: 'worker-demo-01',
  event_type: 'ppe_missing',
  severity: 'high',
  summary: 'Capacete ausente em zona de risco',
  confidence: 0.92,
  metadata: { model_version: 'e2e-mock', camera_id: 'camera-demo-01', zone_id: 'zone-demo-01', site_id: 'site-demo' },
  status: 'open',
  created_at: now,
  updated_at: now,
  acknowledged_at: null,
  resolved_at: null,
  dismissed_at: null,
}

const operationCatalog = {
  organization_id: organization.id,
  sites: [{ id: 'site-demo', organization_id: organization.id, name: 'Site Demo', address: 'Unidade piloto', status: 'active', cameras: [], zones: [], safety_rules: [], required_ppe: [] }],
  cameras: [{ id: 'camera-demo-01', organization_id: organization.id, site_id: 'site-demo', name: 'Câmera Demo 01', stream_identifier: 'rtsp://demo/camera-01', status: 'active' }],
  zones: [{ id: 'zone-demo-01', organization_id: organization.id, site_id: 'site-demo', camera_id: 'camera-demo-01', zone_type: 'ppe', status: 'active' }],
  safety_rules: [{ id: 'rule-demo-01', organization_id: organization.id, site_id: 'site-demo', zone_id: 'zone-demo-01', name: 'Capacete obrigatório', status: 'active', metadata: {} }],
  required_ppe: [{ id: 'ppe-demo-01', organization_id: organization.id, rule_id: 'rule-demo-01', site_id: 'site-demo', zone_id: 'zone-demo-01', item: 'capacete', status: 'active' }],
}

async function mockPilotApi(page: Page) {
  let loggedIn = false
  let currentIncident = { ...incident }

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace('/api/v1', '')
    const method = request.method()

    const json = (body: unknown, status = 200, headers: Record<string, string> = {}) => route.fulfill({ status, contentType: 'application/json', headers, body: JSON.stringify(body) })

    if (path === '/auth/me' && method === 'GET') return loggedIn ? json(meResponse) : json({ detail: 'not authenticated' }, 401)
    if (path === '/auth/login' && method === 'POST') {
      loggedIn = true
      return json({ tokens: { access_token: 'access-token-test', refresh_token: 'refresh-token-test', access_token_expires_in: 900 }, me: meResponse, user: 'user-dev' }, 200, { 'set-cookie': 'csrf_token=csrf-test; Path=/; SameSite=Lax' })
    }
    if (path === '/organizations/org-demo/operations/catalog' && method === 'GET') return json(operationCatalog)
    if (path === '/organizations/org-demo/incidents' && method === 'GET') return json({ items: [currentIncident], page_info: { limit: 50, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/incidents/inc-1' && method === 'GET') return json(currentIncident)
    if (path === '/organizations/org-demo/incidents/inc-1/audit-log' && method === 'GET') return json({ items: [{ id: 'audit-1', organization_id: organization.id, incident_id: incident.id, action: 'created', from_status: null, to_status: 'open', actor: 'system', created_at: now, metadata: {} }], page_info: { limit: 50, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/evidence' && method === 'GET') return json({ items: [{ file_id: 'file-1', organization_id: organization.id, incident_id: incident.id, object_key: 'evidence/inc-1/file-1.json', media_type: 'application/json', size: 128, source: 'edge_worker', uploaded_by: 'worker-demo-01', kind: 'metadata', created_at: now, deleted_at: null, metadata: { camera_id: 'camera-demo-01', zone_id: 'zone-demo-01', site_id: 'site-demo', sha256: 'abc123', model_version: 'e2e-mock' } }], page_info: { limit: 50, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/incidents/inc-1/evidence/file-1:download-url' && method === 'POST') return json({ bucket: 'evidence-dev', object_key: 'evidence/inc-1/file-1.json', download_url: signedEvidenceUrl, expires_at: '2026-07-14T22:00:00.000Z' })
    if (path === '/organizations/org-demo/incidents/inc-1:acknowledge' && method === 'POST') {
      currentIncident = { ...currentIncident, status: 'acknowledged', acknowledged_at: now, updated_at: now }
      return json(currentIncident)
    }

    return json({ detail: `Unhandled E2E route: ${method} ${path}` }, 404)
  })
}

test('login, triage incident and open evidence only on demand', async ({ page }) => {
  await mockPilotApi(page)

  await page.goto('/')
  await page.getByRole('button', { name: 'Abrir login' }).first().click()
  await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()

  await page.getByRole('button', { name: 'Entrar com demo' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard conectado à API' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Lista operacional' })).toBeVisible()
  await expect(page.getByText('Capacete ausente em zona de risco').first()).toBeVisible()

  await expect(page.getByText('Abrir evidência segura').first()).toBeVisible()
  await expect(page.locator(`a[href="${signedEvidenceUrl}"]`)).toHaveCount(0)
  await expect(page.getByText(signedEvidenceUrl)).toHaveCount(0)
  await expect(page.getByText('X-Amz-Signature')).toHaveCount(0)

  await page.getByRole('button', { name: 'Abrir evidência segura' }).click()
  await expect(page.getByText('Evidência aberta com segurança')).toBeVisible()
  await expect(page.locator(`a[href="${signedEvidenceUrl}"]`)).toHaveCount(1)

  await page.getByRole('button', { name: 'Reconhecer' }).click()
  await expect(page.getByRole('button', { name: /Capacete ausente em zona de risco Reconhecido/ })).toBeVisible()
})
