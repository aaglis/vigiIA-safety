import { expect, test, type Page } from '@playwright/test'
import { expectEdgeConfigRedacted } from './edge-config-assertions'
import { expectDemoModeNotActive } from './demo-mode-assertions'
import { expectEdgeSecretNotRendered } from './edge-secret-assertions'
import { expectOperationalSiteVisible } from './operations-assertions'
import { expectPlatformAdminControls } from './platform-admin-assertions'
import { expectRetentionPurgeControls } from './retention-purge-assertions'
import { expectSignedEvidenceUrlNotRendered } from './security-assertions'

const now = '2026-07-14T21:00:00.000Z'
const signedEvidenceUrl = 'https://signed.example.invalid/evidence/inc-1/file-1?X-Amz-Signature=redacted-test-signature'
const edgeWorkerSecret = 'edge-secret-test-1'

const organization = { id: 'org-demo', name: 'VigIA Demo', slug: 'vigia-demo' }
const meResponse = {
  user: { id: 'user-dev', email: 'admin@vigia.local', full_name: 'VigIA Admin', platform_role: 'platform_admin' },
  memberships: [{ organization, role: 'org_owner', permissions: ['view_dashboard', 'org.members.manage', 'org.members.invite', 'org.roles.manage', 'audit.read', 'workers.register'], active: true }],
  active_organization: organization,
  active_permissions: ['view_dashboard', 'org.members.manage', 'org.members.invite', 'org.roles.manage', 'audit.read', 'workers.register'],
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

type MockIncident = Omit<typeof incident, 'acknowledged_at' | 'resolved_at' | 'dismissed_at' | 'status'> & {
  status: 'open' | 'acknowledged' | 'resolved' | 'dismissed'
  acknowledged_at: string | null
  resolved_at: string | null
  dismissed_at: string | null
}

type MockInvite = {
  id: string
  organization_id: string
  email: string
  role: string
  invited_by_user_id: string
  status: 'pending' | 'accepted' | 'expired' | 'revoked'
  expires_at: string
  created_at: string
  updated_at: string
  accepted_at: string | null
  revoked_at: string | null
  accepted_by_user_id: string | null
}

const operationCatalog = {
  organization_id: organization.id,
  sites: [{ id: 'site-demo', organization_id: organization.id, name: 'Site Demo', address: 'Unidade piloto', status: 'active', cameras: [], zones: [], safety_rules: [], required_ppe: [] }],
  cameras: [{ id: 'camera-demo-01', organization_id: organization.id, site_id: 'site-demo', name: 'Câmera Demo 01', stream_identifier: 'rtsp://demo/camera-01', status: 'active' }],
  zones: [{ id: 'zone-demo-01', organization_id: organization.id, site_id: 'site-demo', camera_id: 'camera-demo-01', zone_type: 'ppe', status: 'active' }],
  safety_rules: [{ id: 'rule-demo-01', organization_id: organization.id, site_id: 'site-demo', zone_id: 'zone-demo-01', name: 'Capacete obrigatório', status: 'active', metadata: {} }],
  required_ppe: [{ id: 'ppe-demo-01', organization_id: organization.id, rule_id: 'rule-demo-01', site_id: 'site-demo', zone_id: 'zone-demo-01', item: 'capacete', status: 'active' }],
}

let retentionPolicy = { organization_id: organization.id, metadata_days: 365, snapshot_days: 90, clip_days: 30, audit_log_days: 365, updated_at: now }

const platformOrganizations = {
  items: [
    { id: 'plat-org-1', name: 'Plataforma Alpha', legal_name: 'Plataforma Alpha LTDA', tax_id: '00.000.000/0001-00', slug: 'alpha', status: 'active' },
    { id: 'plat-org-2', name: 'Plataforma Beta', legal_name: 'Plataforma Beta SA', tax_id: '11.111.111/0001-11', slug: 'beta', status: 'suspended' },
  ],
}

const members = [
  { user: { id: 'user-dev', email: 'admin@vigia.local', full_name: 'VigIA Admin' }, organization, role: 'org_owner', permissions: ['view_dashboard', 'org.members.manage', 'org.members.invite', 'org.roles.manage'], active: true },
  { user: { id: 'user-2', email: 'supervisor@vigia.local', full_name: 'Supervisor' }, organization, role: 'manager', permissions: ['view_dashboard'], active: true },
]

async function expectAuthenticatedPageHeader(page: Page, title: string) {
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
}

async function mockPilotApi(page: Page) {
  let loggedIn = false
  let currentIncident: MockIncident = { ...incident, status: 'open' }
  let signedDownloadUrlRequests = 0
  const incidentListQueries: string[] = []
  const invites: MockInvite[] = [{ id: 'invite-1', organization_id: organization.id, email: 'auditor@vigia.local', role: 'manager', invited_by_user_id: 'user-dev', status: 'pending', expires_at: '2026-07-21T21:00:00.000Z', created_at: now, updated_at: now, accepted_at: null, revoked_at: null, accepted_by_user_id: null }]
  const edgeWorkers: Array<{ id: string; organization_id: string; site_id: string; name: string; client_id: string; allowed_camera_ids: string[]; api_key_suffix: string | null }> = []

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
    if (path === '/organizations/org-demo/invites' && method === 'GET') return json({ items: invites })
    if (path === '/organizations/org-demo/members' && method === 'GET') return json({ items: members })
    if (path === '/organizations/org-demo/members/user-2' && method === 'PATCH') {
      const body = JSON.parse(request.postData() ?? '{}')
      members[1] = { ...members[1], role: body.role ?? members[1].role, active: body.active ?? members[1].active }
      return json({ member: members[1] })
    }
    if (path === '/organizations/org-demo/members/user-2' && method === 'DELETE') {
      members[1] = { ...members[1], active: false }
      return json({ member: members[1] })
    }
    if (path === '/organizations/org-demo/invites' && method === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}')
      invites.push({ id: `invite-${invites.length + 1}`, organization_id: organization.id, email: body.email, role: body.role, invited_by_user_id: 'user-dev', status: 'pending', expires_at: '2026-07-21T21:00:00.000Z', created_at: now, updated_at: now, accepted_at: null, revoked_at: null, accepted_by_user_id: null })
      return json({ invite: invites[invites.length - 1], token: 'redacted-test-token' })
    }
    if (path === '/organizations/org-demo/invites/invite-1:resend' && method === 'POST') return json({ token: 'redacted-test-token' })
    if (path === '/organizations/org-demo/invites/invite-1:revoke' && method === 'POST') {
      invites[0] = { ...invites[0], status: 'revoked', revoked_at: now, updated_at: now }
      return json({ invite: invites[0] })
    }
    if (path === '/organizations/org-demo/evidence/retention' && method === 'GET') return json(retentionPolicy)
    if (path === '/organizations/org-demo/evidence/purge-preview' && method === 'GET') return json({ items: [{ incident_id: 'inc-1', file_id: 'file-1', object_key: 'evidence/inc-1/file-1.json' }], page_info: { limit: 25, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/evidence/audit-logs' && method === 'GET') return json({ items: [{ id: 'eaudit-1', organization_id: organization.id, actor_user_id: 'user-dev', action: 'download_url.created', incident_id: 'inc-1', file_id: 'file-1', created_at: now, metadata: { source: 'e2e', note: 'audit log' } }], page_info: { limit: 50, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/evidence/retention' && method === 'PUT') {
      const body = JSON.parse(request.postData() ?? '{}')
      retentionPolicy = { organization_id: organization.id, metadata_days: body.metadata_days, snapshot_days: body.snapshot_days, clip_days: body.clip_days, audit_log_days: body.audit_log_days, updated_at: now }
      return json(retentionPolicy)
    }
    if (path === '/organizations/org-demo/evidence/purge' && method === 'POST') return json({ organization_id: organization.id, purged: ['file-1'], count: 1 })
    if (path === '/health' && method === 'GET') return json({ status: 'ok', dependencies: { database: { ok: true, configured: true }, redis: { ok: true, configured: true }, minio: { ok: true, configured: true } } })
    if (path === '/readiness' && method === 'GET') return json({ status: 'ok', dependencies: { database: { ok: true, configured: true }, redis: { ok: true, configured: true }, minio: { ok: true, configured: true } } })
    if (path === '/platform/organizations' && method === 'GET') return json(platformOrganizations)
    if (path === '/organizations/org-demo/operations/catalog' && method === 'GET') return json(operationCatalog)
    if (path === '/organizations/org-demo/edge-workers' && method === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}')
      const worker = {
        id: `edge-worker-${edgeWorkers.length + 1}`,
        organization_id: organization.id,
        site_id: body.site_id,
        name: body.name,
        client_id: `edge-client-${edgeWorkers.length + 1}`,
        allowed_camera_ids: Array.isArray(body.allowed_camera_ids) ? body.allowed_camera_ids : [],
        api_key_suffix: '1a2b3c',
      }
      edgeWorkers.push(worker)
      return json({ worker, api_key: edgeWorkerSecret })
    }
    if (path === '/edge-workers/me/config' && method === 'GET') {
      const clientId = request.headers()['x-edge-client-id']
      const apiKey = request.headers()['x-edge-api-key']
      if (clientId !== 'edge-client-1' || apiKey !== edgeWorkerSecret) return json({ detail: 'invalid edge credentials' }, 401)
      return json({ worker: edgeWorkers[0], capabilities: ['detections.read', 'evidence.upload'], allowed_camera_ids: edgeWorkers[0]?.allowed_camera_ids ?? [] })
    }
    if (path === '/organizations/org-demo/operations/sites' && method === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}')
      const site = { id: `site-${operationCatalog.sites.length + 1}`, organization_id: organization.id, name: body.name, address: body.address ?? null, status: body.status ?? 'active', cameras: [], zones: [], safety_rules: [], required_ppe: [] }
      operationCatalog.sites.push(site)
      return json({ site })
    }
    if (path === '/platform/organizations' && method === 'GET') return json(platformOrganizations)
    if (path === '/platform/organizations' && method === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}')
      const org = { id: `plat-org-${platformOrganizations.items.length + 1}`, name: body.name, legal_name: body.legal_name, tax_id: body.tax_id, slug: body.name.toLowerCase().replace(/\s+/g, '-'), status: 'active' }
      platformOrganizations.items.push(org)
      return json({ organization: org })
    }
    if (path === '/platform/organizations/plat-org-1/suspend' && method === 'POST') {
      platformOrganizations.items[0] = { ...platformOrganizations.items[0], status: 'suspended' }
      return json({ organization: platformOrganizations.items[0] })
    }
    if (path === '/platform/organizations/plat-org-2/reactivate' && method === 'POST') {
      platformOrganizations.items[1] = { ...platformOrganizations.items[1], status: 'active' }
      return json({ organization: platformOrganizations.items[1] })
    }
    if (path === '/organizations/org-demo/incidents' && method === 'GET') {
      incidentListQueries.push(url.searchParams.toString())
      const matches = (!url.searchParams.get('status') || url.searchParams.get('status') === currentIncident.status)
        && (!url.searchParams.get('severity') || url.searchParams.get('severity') === currentIncident.severity)
        && (!url.searchParams.get('site_id') || url.searchParams.get('site_id') === currentIncident.site_id)
        && (!url.searchParams.get('camera_id') || url.searchParams.get('camera_id') === currentIncident.camera_id)
        && (!url.searchParams.get('zone_id') || url.searchParams.get('zone_id') === currentIncident.zone_id)
      const items = matches ? [currentIncident] : []
      return json({ items, page_info: { limit: 50, offset: 0, total: items.length, has_next: false } })
    }
    if (path === '/organizations/org-demo/incidents/inc-1' && method === 'GET') return json(currentIncident)
    if (path === '/organizations/org-demo/incidents/inc-1/audit-log' && method === 'GET') return json({ items: [{ id: 'audit-1', organization_id: organization.id, incident_id: incident.id, action: 'created', from_status: null, to_status: 'open', actor: 'system', created_at: now, metadata: {} }], page_info: { limit: 50, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/evidence' && method === 'GET') return json({ items: [{ file_id: 'file-1', organization_id: organization.id, incident_id: incident.id, object_key: 'evidence/inc-1/file-1.json', media_type: 'application/json', size: 128, source: 'edge_worker', uploaded_by: 'worker-demo-01', kind: 'metadata', created_at: now, deleted_at: null, metadata: { camera_id: 'camera-demo-01', zone_id: 'zone-demo-01', site_id: 'site-demo', sha256: 'abc123', model_version: 'e2e-mock' } }], page_info: { limit: 50, offset: 0, total: 1, has_next: false } })
    if (path === '/organizations/org-demo/incidents/inc-1/evidence/file-1:download-url' && method === 'POST') {
      signedDownloadUrlRequests += 1
      return json({ bucket: 'evidence-dev', object_key: 'evidence/inc-1/file-1.json', download_url: signedEvidenceUrl, expires_at: '2026-07-14T22:00:00.000Z' })
    }
    if (path === '/organizations/org-demo/incidents/inc-1:acknowledge' && method === 'POST') {
      currentIncident = { ...currentIncident, status: 'acknowledged', acknowledged_at: now, updated_at: now }
      return json(currentIncident)
    }

    return json({ detail: `Unhandled E2E route: ${method} ${path}` }, 404)
  })

  return {
    getIncidentListQueries: () => [...incidentListQueries],
    getSignedDownloadUrlRequests: () => signedDownloadUrlRequests,
  }
}

test('login, triage incident and open evidence only on demand', async ({ page }) => {
  const api = await mockPilotApi(page)

  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()

  await page.getByRole('button', { name: 'Entrar com demo' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Visão geral' })).toBeVisible()
  await expect(page.getByText('Capacete ausente em zona de risco').first()).toBeVisible()

  await page.getByRole('button', { name: /Incidentes/ }).first().click()
  await expect(page).toHaveURL(/\/dashboard\/incidents$/)
  await expect(page.getByRole('heading', { name: 'Central de incidentes' })).toBeVisible()
  await expect(page.getByText('LINHA DO TEMPO')).toBeVisible()
  await expect(page.getByText('Incidente criado')).toBeVisible()
  await expect(page.getByText('Aberto').first()).toBeVisible()
  await expect(page.getByText('Alta · Aberto')).toBeVisible()

  const filters = page.locator('select')
  await filters.nth(0).selectOption('medium')
  await expect(page).toHaveURL(/severity=medium/)
  await expect(page.getByText('Nenhum incidente corresponde aos filtros.')).toBeVisible()
  expect(api.getIncidentListQueries().some((query) => query.includes('severity=medium'))).toBe(true)
  await page.getByRole('button', { name: 'Limpar' }).click()
  await expect(page).toHaveURL(/\/dashboard\/incidents$/)
  await expect(page.getByText('Capacete ausente em zona de risco').first()).toBeVisible()

  await filters.nth(2).selectOption('camera-demo-01')
  await filters.nth(3).selectOption('zone-demo-01')
  await filters.nth(4).selectOption('custom')
  await expect(page).toHaveURL(/camera_id=camera-demo-01/)
  await expect(page).toHaveURL(/zone_id=zone-demo-01/)
  await expect(page).toHaveURL(/period=custom/)
  await expect(page.locator('input[type="date"]')).toHaveCount(2)
  await page.getByRole('button', { name: 'Limpar' }).click()

  await expect(page.getByText('Abrir evidências').first()).toBeVisible()
  await expectSignedEvidenceUrlNotRendered(page, signedEvidenceUrl)
  expect(api.getSignedDownloadUrlRequests()).toBe(0)

  await page.getByRole('button', { name: /Abrir evidências/ }).click()
  await expect(page).toHaveURL(/\/dashboard\/evidence$/)
  await expect(page.getByText('Conteúdo privado e auditável.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Preparar acesso seguro' }).first().click()
  await expect(page.getByText('Evidência aberta')).toBeVisible()
  await expect(page.locator(`a[href="${signedEvidenceUrl}"]`)).toHaveCount(1)
  expect(api.getSignedDownloadUrlRequests()).toBe(1)

  await page.getByRole('button', { name: /Incidentes/ }).first().click()
  await page.getByRole('button', { name: 'Reconhecer incidente' }).click()
  await expect(page.getByText('Reconhecido').first()).toBeVisible()
})

test('live login failures stay as errors and do not trigger demo takeover', async ({ page }) => {
  await page.route('**/api/v1/auth/login', async (route) => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'backend down' }) }))
  await page.route('**/api/v1/auth/me', async (route) => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'not authenticated' }) }))

  await page.goto('/login')
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByText('backend down')).toBeVisible()
  await expect(page.getByText('Capacete ausente em zona de risco')).toHaveCount(0)
  await expectDemoModeNotActive(page)
})

test('authenticated dashboard routes are navigable from the sidebar', async ({ page }) => {
  await mockPilotApi(page)

  await page.goto('/login')
  await page.getByRole('button', { name: 'Entrar com demo' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)

  const routes = [
    { label: 'Dashboard', path: '/dashboard', heading: 'Visão geral' },
    { label: 'Incidentes', path: '/dashboard/incidents', heading: 'Central de incidentes' },
    { label: 'Evidências', path: '/dashboard/evidence', heading: 'Evidências do incidente' },
    { label: 'Operações/Câmeras', path: '/dashboard/operations', heading: 'Operações e câmeras' },
    { label: 'Organizações', path: '/dashboard/organizations', heading: 'Tenants e vínculos' },
    { label: 'Usuários', path: '/dashboard/users', heading: 'Convites, vínculos e acesso' },
    { label: 'Auditoria', path: '/dashboard/audit', heading: 'Trilha de ações' },
    { label: 'Configurações', path: '/dashboard/settings', heading: 'Configurações' },
  ]

  for (const route of routes) {
    await page.getByRole('button', { name: new RegExp(`^${route.label}`) }).first().click()
    await expect(page).toHaveURL(new RegExp(`${route.path.replace('/', '\\/')}$`))
    await expectAuthenticatedPageHeader(page, route.heading)
    if (route.path === '/dashboard/audit') await expect(page.getByText('AUDITORIA', { exact: true })).toBeVisible()
    if (route.path === '/dashboard/audit') await expect(page.getByText('download_url.created')).toBeVisible()
    if (route.path === '/dashboard/settings') await expect(page.getByText('90 dias snapshots · 30 dias clips')).toBeVisible()
    if (route.path === '/dashboard/settings') await expect(page.getByText('Saúde da API')).toBeVisible()
    if (route.path === '/dashboard/settings') await expect(page.getByText('Pronto para tráfego')).toBeVisible()
    if (route.path === '/dashboard/settings') await expect(page.getByText('1 item(ns) seriam afetados')).toBeVisible()
    if (route.path === '/dashboard/settings') await expectRetentionPurgeControls(page)
    if (route.path === '/dashboard/organizations') await expect(page.getByText('Organizações da plataforma')).toBeVisible()
    if (route.path === '/dashboard/organizations') await expectPlatformAdminControls(page)

    if (route.path === '/dashboard/operations') {
      await page.getByRole('button', { name: '+ Nova unidade' }).click()
      const siteDialog = page.getByRole('dialog', { name: 'Cadastro de unidade' })
      await expect(siteDialog).toBeVisible()
      await expect(siteDialog.getByText('Salva o cadastro na API real e atualiza a lista.').first()).toBeVisible()

      // O formulário valida no cliente (zod): submeter vazio mostra o erro no campo e
      // não chama a API.
      const saveSiteButton = siteDialog.getByRole('button', { name: 'Criar unidade' })
      await saveSiteButton.click()
      await expect(siteDialog.getByText('Informe o nome da unidade (mínimo 2 caracteres).')).toBeVisible()
      await expect(siteDialog).toHaveCount(1)

      await siteDialog.getByRole('textbox', { name: 'Nome da unidade' }).fill('Pátio Norte')
      await saveSiteButton.scrollIntoViewIfNeeded()
      await saveSiteButton.click()
      await expect(siteDialog).toHaveCount(0)
      await expectOperationalSiteVisible(page, 'Pátio Norte')

      // Câmeras/zonas/workers vivem na página do site (rota com id), não na lista.
      await page.getByTestId('site-card-site-demo').click()
      await expect(page).toHaveURL(/\/dashboard\/operations\/sites\/site-demo$/)

      await page.getByRole('button', { name: 'Registrar worker' }).click()
      const edgeDialog = page.getByRole('dialog', { name: 'Registro seguro de edge worker' })
      await expect(edgeDialog).toBeVisible()
      await edgeDialog.getByRole('textbox', { name: 'Nome do worker' }).fill('Gateway Pátio Norte')
      await expect(edgeDialog.getByRole('button', { name: 'Registrar credencial' })).toBeEnabled()
      await edgeDialog.getByRole('button', { name: 'Registrar credencial' }).click()
      await expect(edgeDialog.getByText(edgeWorkerSecret, { exact: true })).toBeVisible()
      await edgeDialog.getByRole('button', { name: 'Fechar' }).first().click()
      await expect(edgeDialog).toHaveCount(0)
      await expectEdgeSecretNotRendered(page, edgeWorkerSecret)
      // o worker recém-registrado passa a aparecer vinculado à sua câmera na tabela
      await expect(page.getByText('edge-client-1', { exact: true }).first()).toBeVisible()

      await page.getByRole('button', { name: 'Registrar worker' }).click()
      await expect(page.getByRole('dialog', { name: 'Registro seguro de edge worker' })).toBeVisible()
      await expectEdgeSecretNotRendered(page, edgeWorkerSecret)
      await edgeDialog.getByRole('button', { name: 'Fechar' }).dispatchEvent('click')

      await page.getByRole('button', { name: /^Workers/ }).first().click()
      await page.locator('button', { hasText: 'Checar configuração' }).first().click({ force: true })
      const configDialog = page.getByRole('dialog', { name: 'Checagem segura de configuração' })
      await expect(configDialog).toBeVisible()
      await configDialog.getByRole('textbox', { name: 'client_id' }).fill('edge-client-1')
      await configDialog.getByRole('textbox', { name: 'api_key' }).fill(edgeWorkerSecret)
      await configDialog.getByRole('button', { name: 'Checar' }).click()
      await expectEdgeConfigRedacted(configDialog, 'edge-client-1')
      await expect(configDialog.getByText(edgeWorkerSecret, { exact: true })).toHaveCount(0)
      await configDialog.getByRole('button', { name: 'Fechar' }).last().click()
      await expectEdgeSecretNotRendered(page, edgeWorkerSecret)
    }
  }

  await page.getByRole('button', { name: /^Organizações/ }).first().click()
  await page.getByRole('button', { name: 'Nova organização' }).click()
  await expect(page.getByRole('heading', { name: 'Nova organização' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Nome', exact: true }).fill('Plataforma Gama')
  await page.getByRole('textbox', { name: 'Razão social', exact: true }).fill('Plataforma Gama LTDA')
  await page.getByRole('textbox', { name: 'Tax ID', exact: true }).fill('22.222.222/0001-22')
  await page.getByRole('button', { name: 'Criar organização' }).click()
  await expect(page.getByText('Plataforma Gama', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Suspender', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: /Confirmação de suspensão/ })).toBeVisible()
  await page.getByRole('textbox', { name: 'Confirmação' }).fill('alpha')
  await page.getByRole('button', { name: 'Suspender' }).last().click()
  // 'Plataforma Beta' já vem suspensa do mock, então checar o texto solto acha 2 e não
  // prova nada: escopa na linha da org que o teste acabou de suspender.
  const alphaRow = page.locator('div.grid').filter({ hasText: 'Plataforma Alpha' }).last()
  await expect(alphaRow.getByText('suspended', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: /^Usuários/ }).first().click()
  await expect(page.getByText('supervisor@vigia.local').first()).toBeVisible()
  await page.getByRole('button', { name: /Supervisor.*supervisor@vigia.local/ }).click()
  const editAccessButton = page.getByRole('button', { name: 'Editar acesso' })
  await expect(editAccessButton).toBeEnabled()
  await editAccessButton.dispatchEvent('click')
  const editDialog = page.getByRole('dialog', { name: 'Editar acesso' })
  await expect(editDialog).toBeVisible()
  await editDialog.getByRole('combobox').nth(1).selectOption('inactive')
  await editDialog.getByRole('button', { name: 'Salvar mudanças' }).click()
  await expect(page.getByText('Acesso atualizado no backend.')).toBeVisible()
  await page.getByRole('button', { name: 'Convidar usuário' }).click()
  await expect(page.getByText('Cria um convite real no backend da organização ativa.')).toBeVisible()
  await expect(page.getByRole('textbox', { name: /E-mail/ })).toBeVisible()
  await page.getByRole('textbox', { name: /E-mail/ }).fill('novo@vigia.local')
  await page.getByRole('button', { name: 'Enviar convite' }).click()
  await expect(page.getByText('Convite criado no backend. O token não é exibido na interface por segurança.')).toBeVisible()
  await page.getByRole('button', { name: 'Fechar', exact: true }).click()
  await expect(page.getByText('Cria um convite real no backend da organização ativa.')).toHaveCount(0)
})
