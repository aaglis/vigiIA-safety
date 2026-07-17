import { useEffect, useId, useMemo, useState, type ChangeEvent, type ReactNode } from 'react'
import { Outlet, useParams } from '@tanstack/react-router'
import type { OperationCamera, OperationEntityStatus, OperationSite, OperationZone, OperationZoneType } from '../../../api/operations'
import type { JsonValue } from '../../../api/types'
import { Button, Modal, SelectField, TextField } from '../../../components/ui/dashboard'
import { FormActions } from '../../../components/ui/brand'
import { Icon } from '../../../components/ui/icons'
import { SiteModal } from './components/SiteModal'
import { EdgeWorkerModal } from './components/EdgeWorkerModal'
import { WorkerConfigModal } from './components/WorkerConfigModal'
import { CameraModal } from './components/CameraModal'
import { ZoneModal } from './components/ZoneModal'
import { OperationsLayoutProvider, useOperations } from './OperationsContext'
import { labelOperationStatus, labelZoneType } from './shared'
import type { EdgeWorker, EdgeWorkerConfig, RegisterEdgeWorkerResponse } from '../../../api/edgeWorkers'

type DraftKind = 'site' | 'camera' | 'zone'

function DescriptionField({
  label,
  helperText,
  value,
  onChange,
  placeholder,
}: {
  label: string
  helperText?: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  const id = useId()

  return (
    <label className="block space-y-2" htmlFor={id}>
      <span className="text-[13px] font-medium text-[#403933]">{label}</span>
      <textarea
        id={id}
        value={value}
        onChange={(event: ChangeEvent<HTMLTextAreaElement>) => onChange(event.target.value)}
        rows={4}
        placeholder={placeholder}
        className="w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 py-3 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)] focus-visible:outline-none"
      />
      {helperText ? <p className="text-[12px] leading-5 text-[var(--label)]">{helperText}</p> : null}
    </label>
  )
}

// Painel com título/eyebrow no padrão Paper Terracota (borda sólida, radius contido).
function DraftPreview({ kind, siteName, cameraName, zoneName }: { kind: DraftKind; siteName: string; cameraName: string; zoneName: string }) {
  const map: Record<DraftKind, string> = {
    site: `Prévia: site ${siteName || '—'} · será salvo na API real da organização ativa.`,
    camera: `Prévia: câmera ${cameraName || '—'} em ${siteName || '—'} · será salva na API real.`,
    zone: `Prévia: zona ${zoneName || '—'} em ${siteName || '—'} · será salva na API real.`,
  }

  return (
    <div className="rounded-[12px] border border-[#CFE6DA] bg-[#E7F1EB] px-4 py-3 text-sm leading-6 text-[#2C5B45]">
      {map[kind]}
    </div>
  )
}

/** Layout de `/dashboard/operations`: cabeçalho, KPIs e modais. O conteúdo de cada nível
 *  (lista de sites, site, câmera) vem das rotas filhas pelo <Outlet />. */
export function OperationsLayout() {
  const {
    operationSites,
    operationCameras,
    operationZones,
    operationRules,
    operationPpe,
    operationsLoading,
    operationsCatalog,
    activeCamerasCount,
    connectionTone,
    mode,
    readMetadataValue,
    activePermissions,
    onCreateSite,
    onCreateCamera,
    onCreateZone,
    onUpdateSite,
    onUpdateCamera,
    onUpdateZone,
    onLoadCameraFrame,
    onRegisterEdgeWorker,
    onCheckEdgeWorkerConfig,
  } = useOperations()
  // Params das rotas filhas: o layout sabe em que site o usuário está sem receber prop.
  const { siteId: routeSiteId } = useParams({ strict: false }) as { siteId?: string }
  const activeSite = operationSites.find((site) => site.id === routeSiteId) ?? null
  const siteById = useMemo(() => new Map(operationSites.map((site) => [site.id, site] as const)), [operationSites])
  const cameraById = useMemo(() => new Map(operationCameras.map((camera) => [camera.id, camera] as const)), [operationCameras])

  const sites = operationSites
  const [newMenuOpen, setNewMenuOpen] = useState(false)
  // Um alvo por tipo. `null` = fechado; `{}` = criando; `{ entity }` = editando.
  const [siteModal, setSiteModal] = useState<{ site?: OperationSite | null } | null>(null)
  const [cameraModal, setCameraModal] = useState<{ camera?: OperationCamera | null } | null>(null)
  const [zoneModal, setZoneModal] = useState<{ zone?: OperationZone | null } | null>(null)
  const [edgeWorkerOpen, setEdgeWorkerOpen] = useState(false)
  const [lastEdgeWorker, setLastEdgeWorker] = useState<EdgeWorker | null>(null)
  const [configOpen, setConfigOpen] = useState(false)
  const canRegisterEdgeWorker = activePermissions.includes('workers.register')

  const activeSitesTotal = sites.filter((site) => site.status === 'active').length
  const restrictedZonesTotal = operationZones.filter((zone) => zone.zone_type === 'restricted').length
  const ppeZonesTotal = operationZones.filter((zone) => zone.zone_type === 'ppe').length
  const highRulesTotal = operationRules.filter((rule) => (readMetadataValue(rule.metadata, 'severity') ?? '').toLowerCase() === 'high').length
  const kpis = [
    { label: 'Unidades', value: String(sites.length), note: `${activeSitesTotal} ativos`, noteColor: '#2F7D57' },
    { label: 'Câmeras ativas', value: `${activeCamerasCount}`, sub: `/${operationCameras.length}`, note: '', noteColor: '#8E887B' },
    { label: 'Zonas críticas', value: String(restrictedZonesTotal + ppeZonesTotal), note: `${operationZones.length} total`, noteColor: '#8E887B' },
    { label: 'Regras ativas', value: String(operationRules.length), note: highRulesTotal > 0 ? `${highRulesTotal} alta` : 'ok', noteColor: highRulesTotal > 0 ? '#946416' : '#2F7D57' },
    { label: 'EPIs exigidos', value: String(operationPpe.length), note: 'catálogo', noteColor: '#8E887B' },
  ]




  // Cada modal é dono do seu formulário e monta do zero ao abrir — não há estado de
  // rascunho para limpar aqui.
  const openDraft = (kind: DraftKind) => {
    setNewMenuOpen(false)
    if (kind === 'site') setSiteModal({})
    if (kind === 'camera') setCameraModal({})
    if (kind === 'zone') setZoneModal({})
  }

  const openEditSite = (site: OperationSite) => setSiteModal({ site })
  const openEditCamera = (camera: OperationCamera) => setCameraModal({ camera })
  const openEditZone = (zone: OperationZone) => setZoneModal({ zone })

  // Os modais são donos do próprio estado (chave, resultado, erros). O layout só decide
  // quem está aberto e guarda o worker recém-registrado, que a aba Workers usa.
  const openEdgeWorkerRegistration = () => {
    setNewMenuOpen(false)
    setEdgeWorkerOpen(true)
  }

  const openConfigCheck = () => setConfigOpen(true)

  // No nível de Operações o badge vale para a organização: existe unidade ativa com câmera ativa.
  const readyToDetect = sites.some((site) => site.status === 'active' && operationCameras.some((camera) => camera.site_id === site.id && camera.status === 'active'))

  const layoutValue = useMemo(
    () => ({ openDraft, openEditSite, openEditCamera, openEditZone, lastEdgeWorker, openEdgeWorkerRegistration, openConfigCheck, canRegisterEdgeWorker }),
    [lastEdgeWorker, canRegisterEdgeWorker],
  )

  return (
    <OperationsLayoutProvider value={layoutValue}>
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-[26px] font-bold leading-none tracking-[-0.025em] text-[var(--ink)]">Operações e câmeras</h2>
          <p className="mt-1.5 text-sm text-[var(--muted)]">Configure o ambiente físico e valide se a visão computacional está detectando riscos.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-[9px] border px-2.5 py-[7px] text-xs font-medium" style={{ borderColor: connectionTone.border, background: connectionTone.bg, color: connectionTone.color }}>
            <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: connectionTone.dot }} />
            {mode === 'live' ? 'Ao vivo' : 'Demonstração'}
          </span>
          {readyToDetect ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#CFE6DA] bg-[#E7F1EB] px-3 py-[7px] text-xs font-medium text-[#1F6B4A]">
              <Icon name="check-circle" size={13} /> Pronto para detectar
            </span>
          ) : null}
          <Button variant="secondary" size="sm" onClick={openEdgeWorkerRegistration} disabled={!canRegisterEdgeWorker} title={canRegisterEdgeWorker ? 'Registrar edge worker' : 'Pendente da permissão workers.register'}>
            <Icon name="server" size={15} /> Registrar worker
          </Button>
          <div className="relative">
            <Button variant="secondary" size="sm" onClick={() => setNewMenuOpen((current) => !current)} aria-haspopup="menu" aria-expanded={newMenuOpen}>
              Novo <Icon name="chevron-down" size={13} />
            </Button>
            {newMenuOpen ? (
              <>
                <div className="fixed inset-0 z-30" aria-hidden="true" onClick={() => setNewMenuOpen(false)} />
                <div role="menu" className="absolute right-0 z-40 mt-2 w-44 overflow-hidden rounded-[12px] border border-[#E7E3DC] bg-[var(--card)] py-1 shadow-[0_18px_44px_rgba(32,27,24,0.14)]">
                  {([['site', 'Nova unidade'], ['camera', 'Nova câmera'], ['zone', 'Nova zona']] as [DraftKind, string][]).map(([kind, label]) => (
                    <button key={kind} type="button" role="menuitem" onClick={() => openDraft(kind)} className="flex w-full items-center gap-2.5 px-3.5 py-2 text-left text-[13px] text-[var(--ink)] hover:bg-[rgba(32,27,24,0.04)]">
                      <Icon name="plus" size={14} className="text-[var(--nav-label)]" /> {label}
                    </button>
                  ))}
                </div>
              </>
            ) : null}
          </div>
          <Button size="sm" onClick={() => openDraft('camera')}>
            <Icon name="plus" size={15} /> Nova câmera
          </Button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2.5 rounded-[9px] border border-[#CFE6DA] bg-[#E7F1EB] px-3.5 py-2.5">
        <Icon name="check-circle" size={16} className="flex-none text-[#1F6B4A]" />
        <p className="text-[13px] leading-[1.4] text-[#2C5B45]">
          Cadastros são salvos na <span className="font-semibold text-[#1F5540]">API real da organização ativa</span>. Para validar a visão computacional, vincule câmeras a um worker e acompanhe o resultado na aba <span className="font-semibold text-[#1F5540]">Testes CV</span>.
        </p>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-5">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-[11px] border border-[#E7E3DC] bg-[var(--card)] px-4 py-3.5">
            <p className="mb-2.5 text-xs text-[#8E887B]">{kpi.label}</p>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-[26px] font-bold leading-none text-[var(--ink)]">
                {kpi.value}
                {'sub' in kpi && kpi.sub ? <span className="text-[17px] text-[#A9A398]">{kpi.sub}</span> : null}
              </span>
              {kpi.note ? <span className="font-mono-ui text-[11px]" style={{ color: kpi.noteColor }}>{kpi.note}</span> : null}
            </div>
          </div>
        ))}
      </div>

      {operationsLoading && !operationsCatalog ? (
        <div className="rounded-xl border border-[#E7E3DC] bg-[var(--card)] px-4 py-8 text-sm text-[var(--muted)]">Carregando configuração operacional…</div>
      ) : sites.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
          <p className="font-display text-xl font-bold text-[var(--ink)]">Nenhum site configurado</p>
          <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">Para preparar o piloto: cadastre um site → conecte ao menos uma câmera → desenhe as zonas → associe regras e EPIs.</p>
          <div className="mt-4">
            <Button size="sm" onClick={() => openDraft('site')}>
              <Icon name="plus" size={15} /> Cadastrar primeiro site
            </Button>
          </div>
        </div>
      ) : (
        <Outlet />
      )}

      <EdgeWorkerModal
        open={edgeWorkerOpen}
        sites={sites}
        cameras={operationCameras}
        defaultSiteId={activeSite?.id}
        onClose={() => setEdgeWorkerOpen(false)}
        onRegister={(values) => onRegisterEdgeWorker(values)}
        onRegistered={(resposta) => setLastEdgeWorker(resposta.worker)}
      />

      <WorkerConfigModal
        open={configOpen}
        onClose={() => setConfigOpen(false)}
        onCheck={(payload) => onCheckEdgeWorkerConfig(payload)}
      />

      <SiteModal
        open={siteModal !== null}
        site={siteModal?.site}
        onClose={() => setSiteModal(null)}
        onSubmit={async (values) => {
          const payload = { name: values.name, address: values.address || null, status: values.status }
          if (siteModal?.site) await onUpdateSite(siteModal.site.id, payload)
          else await onCreateSite(payload)
          setSiteModal(null)
        }}
      />

      <CameraModal
        open={cameraModal !== null}
        sites={sites}
        zones={operationZones}
        defaultSiteId={activeSite?.id}
        camera={cameraModal?.camera}
        onClose={() => setCameraModal(null)}
        onSubmit={async (values) => {
          if (cameraModal?.camera) await onUpdateCamera(cameraModal.camera.id, values)
          else await onCreateCamera(values)
          setCameraModal(null)
        }}
      />

      <ZoneModal
        open={zoneModal !== null}
        sites={sites}
        cameras={operationCameras}
        defaultSiteId={activeSite?.id}
        zone={zoneModal?.zone}
        onLoadCameraFrame={onLoadCameraFrame}
        onClose={() => setZoneModal(null)}
        onSubmit={async (values) => {
          // Polígono em coords normalizadas [0..1] — mesma convenção do worker.
          const polygon: Record<string, JsonValue> = values.polygon.length >= 3 ? { type: 'polygon', points: values.polygon } : {}
          const payload = { site_id: values.site_id, camera_id: values.camera_id, zone_type: values.zone_type, name: values.name, status: values.status, polygon_json: polygon }
          if (zoneModal?.zone) await onUpdateZone(zoneModal.zone.id, payload)
          else await onCreateZone(payload)
          setZoneModal(null)
        }}
      />

    </div>
    </OperationsLayoutProvider>
  )
}
