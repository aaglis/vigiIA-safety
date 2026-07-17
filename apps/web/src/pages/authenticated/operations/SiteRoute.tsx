import { useEffect, useMemo, useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { Button } from '../../../components/ui/dashboard'
import { Icon } from '../../../components/ui/icons'
import type { EdgeWorker } from '../../../api/edgeWorkers'
import type { OperationZone } from '../../../api/operations'
import { isApiError } from '../../../api/client'
import { useOperations, useOperationsLayout } from './OperationsContext'
import { Panel, StatusDot, cameraSource, labelZoneType } from './shared'

type DetailTab = 'cameras' | 'zones' | 'rules' | 'workers' | 'tests'

function polygonPointsOf(zone: OperationZone): [number, number][] {
  const points = (zone.polygon_json as { points?: [number, number][] } | undefined)?.points
  return Array.isArray(points) ? points : []
}


/** Rota `/dashboard/operations/sites/$siteId`. */
export function SiteRoute() {
  const { siteId } = useParams({ strict: false }) as { siteId: string }
  const {
    operationSites,
    operationCameras,
    operationZones,
    operationRules,
    operationPpe,
    operationsLoading,
    operationsCatalog,
    ENTITY_STATUS_BADGE,
    ZONE_TYPE_BADGE,
    readMetadataValue,
    ruleSeverityBadge,
    onOpenCamera,
    onBackToSites,
    onDeleteZone,
  } = useOperations()
  const { openDraft, openEditSite, openEditCamera, openEditZone, lastEdgeWorker, openConfigCheck, openEdgeWorkerRegistration, canRegisterEdgeWorker } = useOperationsLayout()
  const [zonaExcluindo, setZonaExcluindo] = useState<string | null>(null)
  const [erroExclusao, setErroExclusao] = useState<{ zoneId: string; texto: string } | null>(null)

  // Excluir zona com histórico é barrado pela API (409): o incidente aponta para o
  // `zone_id` e a auditoria ficaria órfã. Traduz o motivo em vez de só falhar.
  const excluirZona = async (zone: OperationZone) => {
    const nome = zone.name || zone.id
    if (!window.confirm(`Excluir a zona "${nome}"? A visão computacional deixa de avaliar essa área.`)) return
    setErroExclusao(null)
    setZonaExcluindo(zone.id)
    try {
      await onDeleteZone(zone.id)
    } catch (error) {
      const conflito = isApiError(error) && error.status === 409
      setErroExclusao({
        zoneId: zone.id,
        texto: conflito
          ? 'Esta zona já gerou incidentes e não pode ser excluída — o histórico deixaria de fazer sentido. Marque como inativa para parar de avaliar a área.'
          : error instanceof Error ? error.message : 'Não foi possível excluir a zona.',
      })
    } finally {
      setZonaExcluindo(null)
    }
  }

  const [activeTab, setActiveTab] = useState<DetailTab>('cameras')
  const [validationCameraId, setValidationCameraId] = useState<string>('')

  const activeSite = operationSites.find((site) => site.id === siteId) ?? null
  const cameraById = useMemo(() => new Map(operationCameras.map((camera) => [camera.id, camera] as const)), [operationCameras])
  const siteCameras = activeSite ? operationCameras.filter((camera) => camera.site_id === activeSite.id) : []
  const siteZones = activeSite ? operationZones.filter((zone) => zone.site_id === activeSite.id) : []
  const siteRules = activeSite ? operationRules.filter((rule) => rule.site_id === activeSite.id || (rule.zone_id ? siteZones.some((zone) => zone.id === rule.zone_id) : false)) : []

  // Worker (registrado nesta sessão) que autoriza a câmera — única fonte real de vínculo câmera↔worker no painel.
  const workerForCamera = (cameraId: string): EdgeWorker | null =>
    lastEdgeWorker && lastEdgeWorker.allowed_camera_ids.includes(cameraId) ? lastEdgeWorker : null

  // Cenários de CV cobertos por uma câmera: zonas ancoradas nela + EPIs das regras dessas zonas.
  const scenariosForCamera = (cameraId: string) => {
    const camZones = siteZones.filter((zone) => zone.camera_id === cameraId)
    const zoneChips = camZones.map((zone) => {
      const badge = ZONE_TYPE_BADGE[zone.zone_type] ?? { label: labelZoneType(zone.zone_type), bg: '#EDE9E1', color: '#5F5951' }
      return { key: `z-${zone.id}`, label: badge.label, bg: badge.bg, color: badge.color }
    })
    const camRuleIds = siteRules.filter((rule) => rule.zone_id && camZones.some((zone) => zone.id === rule.zone_id)).map((rule) => rule.id)
    const epiItems = Array.from(new Set(operationPpe.filter((item) => camRuleIds.includes(item.rule_id)).map((item) => item.item)))
    const epiChips = epiItems.map((item, index) => ({ key: `e-${index}-${item}`, label: item, bg: '#F6E4DC', color: '#B14A22' }))
    return [...zoneChips, ...epiChips]
  }

  const validationCamera = siteCameras.find((camera) => camera.id === validationCameraId) ?? siteCameras[0] ?? null

  // Mantém a câmera de validação coerente com as câmeras deste site.
  useEffect(() => {
    if (siteCameras.length === 0) {
      if (validationCameraId) setValidationCameraId('')
      return
    }
    if (!siteCameras.some((camera) => camera.id === validationCameraId)) setValidationCameraId(siteCameras[0].id)
  }, [siteCameras, validationCameraId])

  const tabs: { key: DetailTab; label: string; count: number | null }[] = [
    { key: 'cameras', label: 'Câmeras', count: siteCameras.length },
    { key: 'zones', label: 'Zonas', count: siteZones.length },
    { key: 'rules', label: 'Regras & EPIs', count: siteRules.length },
    { key: 'workers', label: 'Workers', count: lastEdgeWorker ? 1 : null },
    { key: 'tests', label: 'Testes CV', count: null },
  ]

  const openTestForCamera = (cameraId: string) => {
    setValidationCameraId(cameraId)
    setActiveTab('tests')
  }

  if (operationsLoading && !operationsCatalog) {
    return <div className="rounded-xl border border-[#E7E3DC] bg-[var(--card)] px-4 py-8 text-sm text-[var(--muted)]">Carregando configuração operacional…</div>
  }

  if (!activeSite) {
    return (
      <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
        <p className="font-display text-xl font-bold text-[var(--ink)]">Unidade não encontrada</p>
        <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">A unidade deste endereço não existe nesta organização ou foi removida.</p>
        <div className="mt-4">
          <Button size="sm" variant="secondary" onClick={onBackToSites}>
            <Icon name="arrow-left" size={15} /> Voltar para as unidades
          </Button>
        </div>
      </div>
    )
  }

  return (
      <div className="flex min-w-0 flex-col gap-3.5">
        {/* Cabeçalho do site + abas */}
        <div className="overflow-hidden rounded-[12px] border border-[#E7E3DC] bg-[var(--card)]">
          <div className="flex items-start justify-between gap-3 px-5 pb-3.5 pt-[18px]">
            <div className="min-w-0">
              <button type="button" onClick={onBackToSites} className="mb-1.5 inline-flex items-center gap-1.5 text-[12px] font-medium text-[var(--muted)] hover:text-[var(--ink)]">
                <Icon name="arrow-left" size={13} /> Unidades
              </button>
              <div className="mb-1 flex flex-wrap items-center gap-2.5">
                <h3 className="truncate font-display text-[20px] font-bold tracking-[-0.02em] text-[var(--ink)]">{activeSite?.name ?? 'Nenhuma unidade selecionada'}</h3>
                {activeSite ? (
                  <span className="flex-none rounded-[5px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em]" style={{ background: ENTITY_STATUS_BADGE[activeSite.status].bg, color: ENTITY_STATUS_BADGE[activeSite.status].color }}>
                    {ENTITY_STATUS_BADGE[activeSite.status].label}
                  </span>
                ) : null}
              </div>
              <p className="truncate text-[13px] text-[#5F5951]">{activeSite?.address ?? 'Escolha uma unidade para ver câmeras, zonas, regras e workers vinculados.'}</p>
            </div>
            <button type="button" onClick={() => activeSite && openEditSite(activeSite)} data-testid="site-edit" className="h-[34px] flex-none rounded-[8px] border border-[#DCD7CC] bg-[var(--card)] px-3.5 text-[13px] font-medium text-[var(--ink)] transition hover:bg-white">
              Editar unidade
            </button>
          </div>
          <div className="flex gap-0.5 overflow-x-auto border-t border-[#EDE9E1] px-3">
            {tabs.map((tab) => {
              const active = activeTab === tab.key
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={`relative whitespace-nowrap px-3.5 py-3 text-[13px] transition ${active ? 'font-semibold text-[#B14A22]' : 'text-[#5F5951] hover:text-[var(--ink)]'}`}
                >
                  {tab.label}
                  {tab.count !== null ? <span className="ml-1.5 font-mono-ui font-normal text-[#A9A398]">{tab.count}</span> : null}
                  {active ? <span className="absolute inset-x-2 bottom-0 h-0.5 rounded-[2px] bg-[var(--accent)]" /> : null}
                </button>
              )
            })}
          </div>
        </div>

        {/* CÂMERAS */}
        {activeTab === 'cameras' ? (
          <Panel
            title="Câmeras da unidade"
            action={<button type="button" onClick={() => openDraft('camera')} className="text-[12px] font-medium text-[#B14A22] hover:underline">+ Nova câmera</button>}
          >
            {siteCameras.length === 0 ? (
              <p className="px-[18px] py-8 text-sm text-[var(--muted)]">Nenhuma câmera vinculada a este site. Use “Nova câmera” para conectar a primeira fonte.</p>
            ) : (
              <div className="min-w-0 overflow-x-auto">
                <div className="min-w-[720px]">
                  <div className="grid grid-cols-[1.5fr_1.1fr_1fr_1.6fr_0.9fr] gap-3 border-b border-[#EDE9E1] px-[18px] py-2.5 font-mono-ui text-[10px] tracking-[0.08em] text-[#A9A398]">
                    <span>CÂMERA / FONTE</span>
                    <span>WORKER</span>
                    <span>STATUS</span>
                    <span>CENÁRIOS CV</span>
                    <span className="text-right">VALIDAÇÃO</span>
                  </div>
                  {siteCameras.map((camera) => {
                    const source = cameraSource(camera.stream_identifier)
                    const worker = workerForCamera(camera.id)
                    const scenarios = scenariosForCamera(camera.id)
                    const statusInfo = camera.status === 'suspended'
                      ? { color: '#C1552B', text: 'Suspensa', textColor: '#B14A22' }
                      : camera.status === 'inactive'
                        ? { color: '#C0BAB0', text: 'Inativa', textColor: '#8E887B' }
                        : worker
                          ? { color: '#2F7D57', text: 'Ativa', textColor: '#1F6B4A' }
                          : { color: '#C98A2B', text: 'Sem worker', textColor: '#946416' }
                    const canTest = camera.status !== 'inactive'
                    return (
                      <div key={camera.id} className="border-b border-[#F0EDE6] last:border-b-0">
                        <div className="grid grid-cols-[1.5fr_1.1fr_1fr_1.6fr_0.9fr] items-center gap-3 px-[18px] py-3">
                        <div className="min-w-0">
                          <button
                            type="button"
                            onClick={() => activeSite && onOpenCamera(activeSite.id, camera.id)}
                            data-testid={`camera-open-${camera.id}`}
                            className="block max-w-full truncate text-left text-[13px] font-medium text-[var(--ink)] hover:text-[var(--accent)] hover:underline"
                          >
                            {camera.name}
                          </button>
                          <div className="mt-1 flex items-center gap-1.5">
                            <span className="flex-none rounded-[4px] px-1.5 py-px text-[9px] font-semibold tracking-[0.04em]" style={{ background: source.bg, color: source.color }}>{source.label}</span>
                            <span className="truncate font-mono-ui text-[10px] text-[#A9A398]">{camera.stream_identifier}</span>
                          </div>
                        </div>
                        {worker ? (
                          <span className="truncate font-mono-ui text-[12px] text-[#5F5951]">{worker.client_id}</span>
                        ) : camera.status === 'active' ? (
                          <span className="flex items-center gap-1.5 font-mono-ui text-[12px] text-[#B14A22]"><Icon name="alert-triangle" size={12} /> sem worker</span>
                        ) : (
                          <span className="font-mono-ui text-[12px] text-[#A9A398]">—</span>
                        )}
                        <span className="flex items-center gap-1.5 text-[11px]" style={{ color: statusInfo.textColor }}>
                          <StatusDot color={statusInfo.color} /> {statusInfo.text}
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {scenarios.length === 0 ? (
                            <span className="text-[11px] text-[#A9A398]">Sem zona vinculada</span>
                          ) : (
                            <>
                              {scenarios.slice(0, 3).map((chip) => (
                                <span key={chip.key} className="rounded-full px-[7px] py-px text-[10px]" style={{ background: chip.bg, color: chip.color }}>{chip.label}</span>
                              ))}
                              {scenarios.length > 3 ? <span className="rounded-full bg-[#EDE9E1] px-[7px] py-px text-[10px] text-[#5F5951]">+{scenarios.length - 3}</span> : null}
                            </>
                          )}
                        </div>
                        <div className="flex items-center justify-end gap-2.5 text-right">
                          <button
                            type="button"
                            onClick={() => activeSite && onOpenCamera(activeSite.id, camera.id)}
                            data-testid={`live-toggle-${camera.id}`}
                            className="text-[12px] font-semibold text-[var(--ink)] hover:underline"
                          >
                            Ao vivo
                          </button>
                          <button
                            type="button"
                            onClick={() => openEditCamera(camera)}
                            data-testid={`camera-edit-${camera.id}`}
                            className="text-[12px] font-medium text-[var(--muted)] hover:text-[var(--ink)] hover:underline"
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            onClick={() => canTest && openTestForCamera(camera.id)}
                            disabled={!canTest}
                            className={`text-[12px] font-semibold ${canTest ? 'text-[#B14A22] hover:underline' : 'cursor-not-allowed text-[#C0BAB0]'}`}
                          >
                            Testar
                          </button>
                        </div>
                        </div>

                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </Panel>
        ) : null}

        {/* ZONAS */}
        {activeTab === 'zones' ? (
          <Panel
            title="Zonas da unidade"
            action={<button type="button" onClick={() => openDraft('zone')} className="text-[12px] font-medium text-[#B14A22] hover:underline">+ Nova zona</button>}
          >
            {siteZones.length === 0 ? (
              <p className="px-[18px] py-8 text-sm text-[var(--muted)]">Nenhuma zona desenhada para este site.</p>
            ) : (
              <div className="grid gap-2.5 p-[18px] md:grid-cols-2">
                {siteZones.map((zone) => {
                  const statusBadge = ENTITY_STATUS_BADGE[zone.status]
                  const typeBadge = ZONE_TYPE_BADGE[zone.zone_type] ?? { label: labelZoneType(zone.zone_type), bg: '#EEEAE3', color: '#7C756C' }
                  const camera = cameraById.get(zone.camera_id)
                  return (
                    <div key={zone.id} className="rounded-[10px] border border-[#EDE9E1] bg-[var(--paper)] px-4 py-3.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          {/* Zona antiga pode não ter nome: cai no tipo, nunca no id cru. */}
                          <p className="truncate text-sm font-semibold text-[var(--ink)]">{zone.name || typeBadge.label}</p>
                          <p className="mt-1 truncate text-xs text-[#8E887B]">{camera?.name ?? zone.camera_id}</p>
                        </div>
                        <span className="flex-none rounded-[5px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em]" style={{ background: typeBadge.bg, color: typeBadge.color }}>{typeBadge.label}</span>
                      </div>
                      <div className="mt-2.5 flex items-center justify-between gap-3 border-t border-[#F0EDE6] pt-2.5">
                        <span className="flex items-center gap-1.5 text-[11px]" style={{ color: statusBadge.color }}>
                          <StatusDot color={statusBadge.color} /> {statusBadge.label}
                        </span>
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono-ui text-[10px] text-[#A9A398]">
                            {polygonPointsOf(zone).length >= 3 ? 'área desenhada' : 'quadro inteiro'}
                          </span>
                          <button type="button" onClick={() => openEditZone(zone)} data-testid={`zone-edit-${zone.id}`} className="text-[12px] font-medium text-[#B14A22] hover:underline">
                            Editar
                          </button>
                          <button
                            type="button"
                            onClick={() => void excluirZona(zone)}
                            disabled={zonaExcluindo === zone.id}
                            data-testid={`zone-delete-${zone.id}`}
                            className="text-[12px] font-medium text-[var(--muted-2)] hover:text-[#9e4120] hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {zonaExcluindo === zone.id ? 'Excluindo…' : 'Excluir'}
                          </button>
                        </div>
                      </div>
                      {erroExclusao?.zoneId === zone.id ? (
                        <p className="mt-2.5 rounded-[8px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.06)] px-3 py-2 text-[12px] leading-5 text-[#9e4120]">
                          {erroExclusao.texto}
                        </p>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            )}
          </Panel>
        ) : null}

        {/* REGRAS & EPIs */}
        {activeTab === 'rules' ? (
          <Panel title="Regras & EPIs da unidade">
            {siteRules.length === 0 ? (
              <p className="px-[18px] py-8 text-sm text-[var(--muted)]">Nenhuma regra associada ao site selecionado.</p>
            ) : (
              <div className="grid gap-2.5 p-[18px] md:grid-cols-2 xl:grid-cols-3">
                {siteRules.map((rule) => {
                  const severity = ruleSeverityBadge(readMetadataValue(rule.metadata, 'severity'))
                  const ppeItems = operationPpe.filter((item) => item.rule_id === rule.id)
                  return (
                    <div key={rule.id} className="rounded-[10px] border border-[#EDE9E1] bg-[var(--paper)] px-4 py-3.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-[var(--ink)]">{rule.name}</p>
                          <p className="mt-1 truncate text-xs text-[#8E887B]">{rule.zone_id ? `Zona: ${rule.zone_id}` : 'Regra em nível de site'}</p>
                        </div>
                        <span className="flex-none rounded-[5px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em]" style={{ background: severity.bg, color: severity.color }}>
                          {severity.label}
                        </span>
                      </div>
                      {ppeItems.length > 0 ? (
                        <div className="mt-2.5 flex flex-wrap gap-1.5">
                          {ppeItems.map((item) => (
                            <span key={item.id} className="rounded-full bg-[#F6E4DC] px-2 py-0.5 text-[10px] text-[#B14A22]">{item.item}</span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            )}
          </Panel>
        ) : null}

        {/* WORKERS */}
        {activeTab === 'workers' ? (
          <Panel
            title={<span>Edge workers {lastEdgeWorker ? <span className="font-mono-ui text-[12px] font-normal text-[#A9A398]">1</span> : null}</span>}
            action={
              <div className="flex items-center gap-3">
                <button type="button" onClick={openConfigCheck} disabled={!canRegisterEdgeWorker} className={`text-[12px] font-medium ${canRegisterEdgeWorker ? 'text-[var(--ink)] hover:underline' : 'cursor-not-allowed text-[#C0BAB0]'}`}>Checar configuração</button>
                <span className="text-[#D2CCC0]">·</span>
                <button type="button" onClick={openEdgeWorkerRegistration} disabled={!canRegisterEdgeWorker} className={`text-[12px] font-medium ${canRegisterEdgeWorker ? 'text-[#B14A22] hover:underline' : 'cursor-not-allowed text-[#C0BAB0]'}`}>+ Registrar worker</button>
              </div>
            }
          >
            <div className="p-[18px]">
              <div className="mb-3.5 flex items-start gap-2.5 rounded-[9px] border border-[#E3D8C8] bg-[#F7F0E2] px-3.5 py-2.5">
                <Icon name="lock" size={15} className="mt-0.5 flex-none text-[#946416]" />
                <p className="text-[12px] leading-[1.5] text-[#5a4a2a]">
                  Registro e checagem usam a <span className="font-semibold text-[#3f3212]">API real</span> (a chave aparece uma única vez). O inventário completo de workers da organização depende de um endpoint de listagem ainda pendente — aqui aparece o worker registrado nesta sessão.
                </p>
              </div>
              {lastEdgeWorker ? (
                <div className="grid gap-2.5 sm:grid-cols-2">
                  <div className="rounded-[10px] border border-[#EDE9E1] bg-[var(--paper)] px-4 py-3.5">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="truncate font-mono-ui text-[13px] font-medium text-[var(--ink)]">{lastEdgeWorker.client_id}</span>
                      <span className="flex flex-none items-center gap-1.5 text-[11px] text-[#8E887B]">
                        <StatusDot color={lastEdgeWorker.last_heartbeat_at ? '#2F7D57' : '#C0BAB0'} />
                        {lastEdgeWorker.last_heartbeat_at ? 'Online' : 'Aguardando 1º heartbeat'}
                      </span>
                    </div>
                    <p className="truncate text-[12px] text-[#5F5951]">{lastEdgeWorker.name}</p>
                    <p className="mt-1 font-mono-ui text-[11px] text-[#8E887B]">{lastEdgeWorker.allowed_camera_ids.length} câmeras liberadas</p>
                    <div className="mt-2.5 flex gap-3">
                      <button type="button" onClick={openConfigCheck} className="text-[12px] text-[var(--ink)] hover:underline">Checar</button>
                    </div>
                  </div>
                  <div className="flex flex-col items-start justify-center gap-2 rounded-[10px] border border-dashed border-[#DCD7CC] bg-[var(--card)] px-4 py-3.5">
                    <p className="text-[12px] text-[#5F5951]">Provisionar outro worker para este ambiente.</p>
                    <button type="button" onClick={openEdgeWorkerRegistration} disabled={!canRegisterEdgeWorker} className={`flex items-center gap-1.5 text-[12px] font-medium ${canRegisterEdgeWorker ? 'text-[#B14A22] hover:underline' : 'cursor-not-allowed text-[#C0BAB0]'}`}>
                      <Icon name="plus" size={13} /> Registrar worker
                    </button>
                  </div>
                </div>
              ) : (
                <div className="rounded-[10px] border border-dashed border-[#DCD7CC] bg-[var(--paper)] px-5 py-7 text-center">
                  <p className="text-sm font-semibold text-[var(--ink)]">Nenhum worker registrado nesta sessão</p>
                  <p className="mx-auto mt-1.5 max-w-md text-[13px] leading-6 text-[#5F5951]">O edge worker roda junto às câmeras (RTSP), faz a detecção com YOLO e envia eventos assinados. Registre um para liberar a validação de CV.</p>
                  <div className="mt-3.5 flex justify-center">
                    <Button size="sm" onClick={openEdgeWorkerRegistration} disabled={!canRegisterEdgeWorker} title={canRegisterEdgeWorker ? 'Registrar edge worker' : 'Pendente da permissão workers.register'}>
                      <Icon name="server" size={15} /> Registrar edge worker
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </Panel>
        ) : null}

        {/* TESTES CV */}
        {activeTab === 'tests' ? (
          <Panel
            title={<span className="flex items-center gap-2"><Icon name="activity" size={15} className="text-[var(--accent)]" /> Validação de visão computacional</span>}
            action={
              <div className="flex items-center gap-2.5">
                {siteCameras.length > 0 ? (
                  <select
                    value={validationCamera?.id ?? ''}
                    onChange={(event) => setValidationCameraId(event.target.value)}
                    className="h-[34px] rounded-[8px] border border-[#E2DDD4] bg-[var(--paper)] px-2.5 text-[13px] text-[var(--ink)] outline-none focus:border-[var(--accent)]"
                  >
                    {siteCameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}
                  </select>
                ) : null}
                <button type="button" disabled title="A detecção roda no edge worker; o resultado chega via detecções assinadas." className="flex h-[34px] items-center gap-1.5 rounded-[8px] bg-[var(--accent)] px-3.5 text-[13px] font-semibold text-white opacity-50">
                  <Icon name="play" size={13} /> Rodar validação
                </button>
              </div>
            }
          >
            {validationCamera ? (
              <div className="grid gap-0 lg:grid-cols-[1.3fr_1fr_1fr]">
                {/* Frame */}
                <div className="border-b border-[#EDE9E1] p-[18px] lg:border-b-0 lg:border-r">
                  <p className="mb-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[#A9A398]">FRAME ANALISADO</p>
                  <div className="relative h-[150px] overflow-hidden rounded-[9px] border border-[#E2DDD4]" style={{ background: 'repeating-linear-gradient(45deg,#F2EEE7 0,#F2EEE7 11px,#EDE9E1 11px,#EDE9E1 22px)' }}>
                    <span className="absolute left-2 top-2 rounded-[4px] bg-[rgba(252,250,247,0.85)] px-1.5 py-0.5 font-mono-ui text-[9px] text-[#8E887B]">{validationCamera.name}</span>
                    <span className="absolute inset-0 flex items-center justify-center font-mono-ui text-[10px] text-[#A9A398]">aguardando frame do worker</span>
                  </div>
                  <p className="mt-2.5 font-mono-ui text-[10px] text-[#A9A398]">Fonte: {validationCamera.stream_identifier}</p>
                </div>
                {/* Esperado (real) */}
                <div className="border-b border-[#EDE9E1] p-[18px] lg:border-b-0 lg:border-r">
                  <p className="mb-3 font-mono-ui text-[10px] tracking-[0.1em] text-[#A9A398]">CENÁRIO ESPERADO</p>
                  {(() => {
                    const camZones = siteZones.filter((zone) => zone.camera_id === validationCamera.id)
                    const camRules = siteRules.filter((rule) => rule.zone_id && camZones.some((zone) => zone.id === rule.zone_id))
                    const epis = Array.from(new Set(operationPpe.filter((item) => camRules.some((rule) => rule.id === item.rule_id)).map((item) => item.item)))
                    return (
                      <>
                        <div className="flex flex-col gap-2.5">
                          {camRules.length === 0 && camZones.length === 0 ? (
                            <p className="text-[13px] text-[#8E887B]">Sem zonas ou regras vinculadas a esta câmera.</p>
                          ) : (
                            <>
                              {camRules.map((rule) => {
                                const severity = ruleSeverityBadge(readMetadataValue(rule.metadata, 'severity'))
                                return (
                                  <div key={rule.id} className="flex items-center gap-2.5">
                                    <StatusDot color={severity.dot} />
                                    <span className="text-[13px] text-[var(--ink)]">{rule.name}</span>
                                  </div>
                                )
                              })}
                              {camZones.map((zone) => {
                                const typeBadge = ZONE_TYPE_BADGE[zone.zone_type] ?? { label: labelZoneType(zone.zone_type), bg: '#EDE9E1', color: '#5F5951' }
                                return (
                                  <div key={zone.id} className="flex items-center gap-2.5">
                                    <span className="h-[7px] w-[7px] flex-none rounded-full border border-[#D2CCC0] bg-[#EDE9E1]" />
                                    <span className="text-[13px] text-[#5F5951]">{typeBadge.label} — {zone.id}</span>
                                  </div>
                                )
                              })}
                            </>
                          )}
                        </div>
                        <p className="mb-2.5 mt-4 font-mono-ui text-[10px] tracking-[0.1em] text-[#A9A398]">EPIs MONITORADOS</p>
                        {epis.length === 0 ? (
                          <p className="text-[12px] text-[#8E887B]">Nenhum EPI exigido nesta câmera.</p>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {epis.map((item) => <span key={item} className="rounded-full bg-[#EDE9E1] px-2.5 py-0.5 text-[11px] text-[#5F5951]">{item}</span>)}
                          </div>
                        )}
                      </>
                    )
                  })()}
                </div>
                {/* Resultado (pendente do worker) */}
                <div className="p-[18px]">
                  <p className="mb-3 font-mono-ui text-[10px] tracking-[0.1em] text-[#A9A398]">RESULTADO DETECTADO</p>
                  <div className="rounded-[10px] border border-dashed border-[#DCD7CC] bg-[var(--paper)] px-4 py-6 text-center">
                    <Icon name="activity" size={18} className="mx-auto text-[#C0BAB0]" />
                    <p className="mt-2 text-[13px] font-medium text-[var(--ink)]">Aguardando detecção</p>
                    <p className="mx-auto mt-1 max-w-[220px] text-[12px] leading-5 text-[#8E887B]">A validação executa no edge worker. Cada detecção assinada vira incidente e evidência automaticamente.</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="px-[18px] py-8 text-sm text-[var(--muted)]">Cadastre uma câmera nesta unidade para validar a detecção.</p>
            )}
          </Panel>
        ) : null}
      </div>
  )
}
