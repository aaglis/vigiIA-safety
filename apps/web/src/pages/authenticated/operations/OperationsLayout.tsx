import { useEffect, useId, useMemo, useState, type ChangeEvent, type ReactNode } from 'react'
import { Outlet, useParams } from '@tanstack/react-router'
import type { OperationEntityStatus, OperationZoneType } from '../../../api/operations'
import type { JsonValue } from '../../../api/types'
import { Button, Modal, SelectField, TextField } from '../../../components/ui/dashboard'
import { FormActions } from '../../../components/ui/brand'
import { Icon } from '../../../components/ui/icons'
import { SiteForm } from './forms/SiteForm'
import { CameraForm } from './forms/CameraForm'
import { ZoneForm } from './forms/ZoneForm'
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
  const [draftOpen, setDraftOpen] = useState(false)
  const [draftKind, setDraftKind] = useState<DraftKind>('site')
  const [edgeWorkerOpen, setEdgeWorkerOpen] = useState(false)
  const [edgeWorkerSiteId, setEdgeWorkerSiteId] = useState(sites[0]?.id ?? '')
  const [edgeWorkerName, setEdgeWorkerName] = useState('')
  const [edgeWorkerAllowedCameraIds, setEdgeWorkerAllowedCameraIds] = useState<string[]>([])
  const [edgeWorkerSaving, setEdgeWorkerSaving] = useState(false)
  const [edgeWorkerError, setEdgeWorkerError] = useState<string | null>(null)
  const [edgeWorkerResult, setEdgeWorkerResult] = useState<RegisterEdgeWorkerResponse | null>(null)
  const [lastEdgeWorker, setLastEdgeWorker] = useState<EdgeWorker | null>(null)
  const [secretCopied, setSecretCopied] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
  const [configClientId, setConfigClientId] = useState('')
  const [configApiKey, setConfigApiKey] = useState('')
  const [configSaving, setConfigSaving] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [configResult, setConfigResult] = useState<EdgeWorkerConfig | null>(null)
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




  // Cada form tem seus próprios defaultValues e é montado do zero ao abrir o modal —
  // não há mais estado de rascunho para limpar aqui.
  const openDraft = (kind: DraftKind) => {
    setNewMenuOpen(false)
    setDraftKind(kind)
    setDraftOpen(true)
  }

  const openEdgeWorkerRegistration = () => {
    const nextSiteId = activeSite?.id ?? sites[0]?.id ?? ''
    setEdgeWorkerSiteId(nextSiteId)
    setEdgeWorkerAllowedCameraIds(operationCameras.filter((camera) => camera.site_id === nextSiteId).map((camera) => camera.id))
    setEdgeWorkerName('')
    setEdgeWorkerError(null)
    setEdgeWorkerResult(null)
    setSecretCopied(false)
    setEdgeWorkerOpen(true)
  }

  const closeEdgeWorkerRegistration = () => {
    setEdgeWorkerOpen(false)
    setEdgeWorkerError(null)
    setEdgeWorkerResult(null)
    setEdgeWorkerName('')
    setSecretCopied(false)
  }

  useEffect(() => {
    if (!edgeWorkerOpen) return
    setEdgeWorkerAllowedCameraIds(operationCameras.filter((camera) => camera.site_id === edgeWorkerSiteId).map((camera) => camera.id))
  }, [edgeWorkerOpen, edgeWorkerSiteId, operationCameras])

  useEffect(() => () => {
    setEdgeWorkerResult(null)
    setSecretCopied(false)
    setConfigApiKey('')
    setConfigResult(null)
  }, [])

  useEffect(() => {
    if (!configOpen) return
    setConfigError(null)
  }, [configOpen])

  const submitEdgeWorkerRegistration = async () => {
    if (!canRegisterEdgeWorker) return
    if (!edgeWorkerName.trim() || !edgeWorkerSiteId) return
    setEdgeWorkerSaving(true)
    setEdgeWorkerError(null)
    try {
      const result = await onRegisterEdgeWorker({ site_id: edgeWorkerSiteId, name: edgeWorkerName.trim(), allowed_camera_ids: edgeWorkerAllowedCameraIds })
      setEdgeWorkerResult(result)
      setLastEdgeWorker(result.worker)
      setSecretCopied(false)
    } catch (error) {
      setEdgeWorkerError(error instanceof Error ? error.message : 'Não foi possível registrar o edge worker.')
    } finally {
      setEdgeWorkerSaving(false)
    }
  }

  const copyEdgeWorkerSecret = async () => {
    if (!edgeWorkerResult?.api_key) return
    try {
      await navigator.clipboard.writeText(edgeWorkerResult.api_key)
      setSecretCopied(true)
    } catch {
      setEdgeWorkerError('Não foi possível copiar automaticamente. Selecione a chave e copie manualmente.')
    }
  }

  const openConfigCheck = () => {
    setConfigClientId(lastEdgeWorker?.client_id ?? '')
    setConfigApiKey('')
    setConfigError(null)
    setConfigResult(null)
    setConfigOpen(true)
  }

  const closeConfigCheck = () => {
    setConfigOpen(false)
    setConfigApiKey('')
    setConfigError(null)
    setConfigResult(null)
  }

  const submitConfigCheck = async () => {
    if (!configClientId.trim() || !configApiKey.trim()) return
    setConfigSaving(true)
    setConfigError(null)
    try {
      const result = await onCheckEdgeWorkerConfig({ client_id: configClientId.trim(), api_key: configApiKey })
      setConfigResult(result)
      setConfigApiKey('')
    } catch (error) {
      setConfigError(error instanceof Error ? error.message : 'Não foi possível validar a configuração do worker.')
    } finally {
      setConfigSaving(false)
    }
  }

  const draftTitle = draftKind === 'site' ? 'Cadastro de unidade' : draftKind === 'camera' ? 'Cadastro de câmera' : 'Cadastro de zona'
  const draftHintText = 'Salva o cadastro na API real e atualiza a lista.'
  const edgeWorkerSite = sites.find((site) => site.id === edgeWorkerSiteId) ?? null
  const edgeWorkerSiteCameras = operationCameras.filter((camera) => camera.site_id === edgeWorkerSiteId)

  // No nível de Operações o badge vale para a organização: existe site ativo com câmera ativa.
  const readyToDetect = sites.some((site) => site.status === 'active' && operationCameras.some((camera) => camera.site_id === site.id && camera.status === 'active'))

  const layoutValue = useMemo(
    () => ({ openDraft, lastEdgeWorker, openEdgeWorkerRegistration, openConfigCheck, canRegisterEdgeWorker }),
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

      <Modal open={edgeWorkerOpen} onClose={closeEdgeWorkerRegistration} title="Registro seguro de edge worker" description="A chave é exibida uma única vez. Copie agora e guarde em um secret manager ou variável de ambiente.">
        {edgeWorkerResult ? (
          <div className="space-y-5">
            <div className="rounded-[12px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-sm leading-6 text-[#5a4a2a]">
              <span className="font-semibold text-[#3f3212]">Chave gerada com sucesso.</span> Não será possível recuperá-la depois que você fechar este painel. Não cole em chat, logs ou tickets públicos.
            </div>

            <div className="rounded-[16px] border border-[rgba(32,27,24,0.9)] bg-[rgba(32,27,24,0.96)] px-4 py-4 text-[var(--paper)] shadow-[0_16px_38px_rgba(32,27,24,0.2)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-mono-ui text-[10px] tracking-[0.16em] text-[#b7afa5]">API KEY · VISUALIZAÇÃO ÚNICA</p>
                  <p className="mt-1 text-sm text-[#d7cec4]">Copie agora e mova para o secret manager do worker.</p>
                </div>
                <Button variant="secondary" size="sm" onClick={copyEdgeWorkerSecret} className="border-transparent bg-[rgba(255,255,255,0.08)] text-[var(--paper)] hover:bg-[rgba(255,255,255,0.14)]">
                  <Icon name="copy" size={14} /> {secretCopied ? 'Copiada' : 'Copiar chave'}
                </Button>
              </div>
              <code className="mt-4 block break-all rounded-[12px] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.04)] px-3.5 py-3 font-mono-ui text-[13px] leading-6 text-[#f5f3ef]">{edgeWorkerResult.api_key}</code>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
                <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">WORKER</p>
                <p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{edgeWorkerResult.worker.name}</p>
                <p className="mt-1 truncate text-xs text-[var(--muted-2)]">{edgeWorkerResult.worker.id}</p>
              </div>
              <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
                <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">CLIENT ID</p>
                <p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{edgeWorkerResult.worker.client_id}</p>
                <p className="mt-1 text-xs text-[var(--muted-2)]">Use este valor nas chamadas X-Edge-Client-Id.</p>
              </div>
              <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5">
                <p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">CÂMERAS</p>
                <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{edgeWorkerResult.worker.allowed_camera_ids.length} liberadas</p>
                <p className="mt-1 text-xs text-[var(--muted-2)]">Escopo mínimo para o edge worker.</p>
              </div>
            </div>

            <FormActions
              primaryLabel="Fechar"
              secondaryLabel="Copiar chave"
              onPrimary={closeEdgeWorkerRegistration}
              onSecondary={copyEdgeWorkerSecret}
              primaryHint="A chave some ao fechar. Guarde em secret manager e nunca em texto aberto."
              primaryDisabled={false}
            />
          </div>
        ) : (
          <div className="space-y-5">
            <SelectField label="Unidade" value={edgeWorkerSiteId} onChange={(event) => setEdgeWorkerSiteId(event.target.value)} helperText="A credencial nasce ligada ao site escolhido.">
              <option value="">Selecione uma unidade</option>
              {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
            </SelectField>

            <TextField label="Nome do worker" value={edgeWorkerName} onChange={(event) => setEdgeWorkerName(event.target.value)} placeholder="Ex.: Gateway Pátio Sul" helperText="Nome humano para identificar a credencial nas operações." />

            <div className="rounded-[16px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-display text-[17px] font-bold text-[var(--ink)]">Câmeras permitidas</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--muted)]">Selecione só as câmeras que esse worker pode consumir. O escopo vai junto da chave.</p>
                </div>
                <span className="rounded-[5px] bg-[#F3E9D6] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em] text-[#946416]">SENSÍVEL</span>
              </div>
              {edgeWorkerSiteCameras.length > 0 ? (
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {edgeWorkerSiteCameras.map((camera) => {
                    const checked = edgeWorkerAllowedCameraIds.includes(camera.id)
                    return (
                      <label key={camera.id} className={`flex items-center gap-3 rounded-[12px] border px-3 py-3 text-sm transition ${checked ? 'border-[rgba(193,85,43,0.28)] bg-[rgba(193,85,43,0.05)]' : 'border-[color:var(--line)] bg-[var(--paper)] hover:bg-white'}`}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(event) => {
                            setEdgeWorkerAllowedCameraIds((current) => event.target.checked ? Array.from(new Set([...current, camera.id])) : current.filter((id) => id !== camera.id))
                          }}
                          className="h-4 w-4 rounded border-[color:var(--line)] text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(193,85,43,0.16)]"
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-[var(--ink)]">{camera.name}</span>
                          <span className="block truncate text-xs text-[var(--muted-2)]">{edgeWorkerSite?.name ?? camera.site_id} · {camera.stream_identifier}</span>
                        </span>
                      </label>
                    )
                  })}
                </div>
              ) : (
                <p className="mt-4 rounded-[12px] border border-dashed border-[color:var(--line)] px-4 py-4 text-sm text-[var(--muted)]">Esse site ainda não tem câmeras. Cadastre uma câmera antes de registrar o worker.</p>
              )}
            </div>

            {edgeWorkerError ? <div className="rounded-[12px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">{edgeWorkerError}</div> : null}

            <div className="rounded-[12px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-sm leading-6 text-[#5a4a2a]">
              <span className="font-semibold text-[#3f3212]">Chave sensível:</span> copie uma vez, guarde em secret manager e não compartilhe em chat, log ou print.
            </div>

            <FormActions
              primaryLabel={edgeWorkerSaving ? 'Registrando…' : 'Registrar credencial'}
              secondaryLabel="Cancelar"
              onPrimary={submitEdgeWorkerRegistration}
              onSecondary={closeEdgeWorkerRegistration}
              primaryDisabled={!canRegisterEdgeWorker || edgeWorkerSaving || !edgeWorkerSiteId || !edgeWorkerName.trim() || edgeWorkerSiteCameras.length === 0 || edgeWorkerAllowedCameraIds.length === 0}
              primaryHint={canRegisterEdgeWorker ? 'A API devolve a chave uma única vez; o painel já prepara o copy-paste seguro.' : 'A permissão workers.register é necessária para abrir este fluxo.'}
            />

            <div className="rounded-[16px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-display text-[17px] font-bold text-[var(--ink)]">Verificação de configuração</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--muted)]">Valide client_id + api_key sem persistir segredos. O retorno fica redigido.</p>
                </div>
                <Button variant="secondary" size="sm" onClick={openConfigCheck} disabled={!canRegisterEdgeWorker} title={canRegisterEdgeWorker ? 'Abrir checagem segura' : 'Pendente da permissão workers.register'}>
                  <Icon name="lock" size={15} /> Checar configuração
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>

      <Modal open={configOpen} onClose={closeConfigCheck} title="Checagem segura de configuração" description="A api_key é usada apenas na chamada e não é renderizada de volta.">
        <div className="space-y-5">
          <TextField label="client_id" value={configClientId} onChange={(event) => setConfigClientId(event.target.value)} placeholder="edge-client-123" helperText="Informe o client_id do worker." />
          <TextField label="api_key" type="password" value={configApiKey} onChange={(event) => setConfigApiKey(event.target.value)} placeholder="••••••••" helperText="Usada só na checagem; não é persistida." />
          <div className="rounded-[12px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-sm leading-6 text-[#5a4a2a]">Nunca cole a chave em chat, logs ou tickets. Se funcionar, a tela mostra apenas metadados seguros.</div>
          {configError ? <div className="rounded-[12px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">{configError}</div> : null}
          {configResult ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5"><p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">WORKER</p><p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{configResult.worker.name}</p><p className="mt-1 truncate text-xs text-[var(--muted-2)]">{configResult.worker.id}</p></div>
              <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5"><p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">CLIENT ID</p><p className="mt-2 truncate text-sm font-semibold text-[var(--ink)]">{configResult.worker.client_id}</p><p className="mt-1 text-xs text-[var(--muted-2)]">api_key omitida.</p></div>
              <div className="rounded-[14px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.72)] px-4 py-3.5"><p className="font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">ESCOPO</p><p className="mt-2 text-sm font-semibold text-[var(--ink)]">{configResult.allowed_camera_ids.length} câmeras</p><p className="mt-1 text-xs text-[var(--muted-2)]">capabilities: {configResult.capabilities.join(' · ')}</p></div>
            </div>
          ) : null}
          <FormActions primaryLabel={configSaving ? 'Checando…' : 'Checar'} secondaryLabel="Fechar" onPrimary={submitConfigCheck} onSecondary={closeConfigCheck} primaryDisabled={configSaving || !configClientId.trim() || !configApiKey.trim()} primaryHint="Ao concluir, a chave é limpa da tela e nunca reexibida." />
        </div>
      </Modal>

      <Modal open={draftOpen} onClose={() => setDraftOpen(false)} title={draftTitle} description={draftHintText}>
        <div className="space-y-5">
          <SelectField label="Tipo de cadastro" value={draftKind} onChange={(event) => setDraftKind(event.target.value as DraftKind)} helperText="Escolha o recurso que você quer cadastrar.">
            <option value="site">Unidade</option>
            <option value="camera">Câmera</option>
            <option value="zone">Zona</option>
          </SelectField>

          {/* Um form por tipo, cada um com seu schema: o formulário remonta ao trocar o
              tipo, então não sobra valor de um cadastro no outro. */}
          {draftKind === 'site' ? (
            <SiteForm
              onCancel={() => setDraftOpen(false)}
              onSubmit={async (values) => {
                await onCreateSite({ name: values.name, address: values.address || null, status: values.status })
                setDraftOpen(false)
              }}
            />
          ) : null}

          {draftKind === 'camera' ? (
            <CameraForm
              sites={sites}
              defaultSiteId={activeSite?.id}
              onCancel={() => setDraftOpen(false)}
              onSubmit={async (values) => {
                await onCreateCamera(values)
                setDraftOpen(false)
              }}
            />
          ) : null}

          {draftKind === 'zone' ? (
            <ZoneForm
              sites={sites}
              cameras={operationCameras}
              defaultSiteId={activeSite?.id}
              onLoadCameraFrame={onLoadCameraFrame}
              onCancel={() => setDraftOpen(false)}
              onSubmit={async (values) => {
                // Polígono em coords normalizadas [0..1] — mesma convenção do worker.
                const polygon: Record<string, JsonValue> = values.polygon.length >= 3 ? { type: 'polygon', points: values.polygon } : {}
                await onCreateZone({ site_id: values.site_id, camera_id: values.camera_id, zone_type: values.zone_type, status: values.status, polygon_json: polygon })
                setDraftOpen(false)
              }}
            />
          ) : null}
        </div>
      </Modal>

    </div>
    </OperationsLayoutProvider>
  )
}
