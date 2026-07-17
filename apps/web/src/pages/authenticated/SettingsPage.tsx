import { useEffect, useState } from 'react'
import { PageHeader } from '../../components/ui/dashboard'
import { Button, FormActions, TextField } from '../../components/ui/brand'
import { Icon } from '../../components/ui/icons'
import { useEvidenceAdminMutations, useEvidencePurgePreview, useEvidenceRetention, useHealth, useReadiness } from '../../queries/platform'

function SettingsField({
  label,
  value,
  readOnly,
  caret,
}: {
  label: string
  value: string
  readOnly?: boolean
  caret?: boolean
}) {
  return (
    <div>
      <p className="mb-[7px] text-[13px] font-medium text-[#403933]">
        {label}{readOnly ? <span className="font-normal text-[var(--nav-label)]"> (somente leitura)</span> : null}
      </p>
      <div className={`flex h-11 items-center justify-between rounded-[9px] border px-3.5 text-sm ${readOnly ? 'border-[color:var(--line)] bg-[#F2EEE7] text-[var(--muted-2)]' : 'border-[#DCD7CC] bg-[var(--card)] text-[var(--ink)]'}`}>
        <span className="truncate">{value}</span>
        {caret ? <Icon name="chevron-down" size={15} className="flex-none text-[var(--nav-label)]" /> : null}
      </div>
    </div>
  )
}

function PrivacyGuarantee({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[9px] border border-[#CFE6DA] bg-[#E7F1EB] px-3.5 py-3">
      <Icon name="shield" size={18} className="flex-none text-[#2F7D57]" />
      <div className="flex-1">
        <p className="text-[13px] font-semibold text-[#1F5540]">{title}</p>
        <p className="text-xs text-[#4E7A64]">{desc}</p>
      </div>
      <span className="relative h-[22px] w-[38px] flex-none rounded-full bg-[#2F7D57]"><span className="absolute right-0.5 top-0.5 h-[18px] w-[18px] rounded-full bg-white" /></span>
    </div>
  )
}

function FutureToggle({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[9px] border border-[color:var(--border)] px-3.5 py-3">
      <Icon name="bell" size={16} className="flex-none text-[var(--muted-2)]" />
      <span className="flex-1 text-[13px] font-medium text-[var(--muted)]">{label}</span>
      <span className="relative h-[22px] w-[38px] flex-none rounded-full bg-[var(--line)]"><span className="absolute left-0.5 top-0.5 h-[18px] w-[18px] rounded-full bg-[var(--card)]" /></span>
    </div>
  )
}

function PendingSave({ note }: { note: string }) {
  return (
    <div className="mt-5 flex items-center justify-between gap-3 border-t border-[color:var(--divider)] pt-4">
      <span className="font-mono-ui text-[11px] text-[var(--nav-label)]">{note}</span>
      <button type="button" disabled title="Pendente de API" className="h-[38px] cursor-not-allowed rounded-[9px] bg-[#E4C3B4] px-[18px] text-sm font-semibold text-white">Salvar</button>
    </div>
  )
}

function NumberInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label className="block space-y-2"><span className="text-[13px] font-medium text-[#403933]">{label}</span><input type="number" min={1} value={value} onChange={(e) => onChange(Number(e.target.value || 0))} className="h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)]" /></label>
}

export function SettingsPage({
  userName,
  userEmail,
  organizationName,
  organizationId,
  activePermissions,
  liveLabel,
}: {
  userName: string
  userEmail: string
  organizationName: string
  organizationId: string | null
  activePermissions: string[]
  liveLabel: string
}) {
  const sectionNav = ['Perfil & preferências', 'Retenção & LGPD', 'Notificações & integrações', 'Segurança da sessão']
  const canReadRetention = activePermissions.includes('audit.read')
  const isLive = liveLabel === 'Conectado à API'
  const canManageEvidence = canReadRetention && isLive
  const retentionQuery = useEvidenceRetention(organizationId, canReadRetention)
  const purgePreviewQuery = useEvidencePurgePreview(organizationId, canReadRetention)
  const adminMutations = useEvidenceAdminMutations(organizationId)
  const healthQuery = useHealth(isLive)
  const readinessQuery = useReadiness(isLive)
  const retention = retentionQuery.data
  const evidenceRetentionValue = retention ? `${retention.snapshot_days} dias snapshots · ${retention.clip_days} dias clips` : canReadRetention ? 'Carregando política…' : 'Permissão audit.read necessária'
  const auditRetentionValue = retention ? `${retention.audit_log_days} dias` : canReadRetention ? 'Carregando política…' : 'Permissão audit.read necessária'
  const dependencyTone = (ok: boolean) => ({ label: ok ? 'OK' : 'Falha', bg: ok ? '#E7F1EB' : '#F6E4DC', color: ok ? '#2F7D57' : '#B14A22' })
  const previewItems = purgePreviewQuery.data?.items ?? []
  const [metadataDays, setMetadataDays] = useState(365)
  const [snapshotDays, setSnapshotDays] = useState(90)
  const [clipDays, setClipDays] = useState(30)
  const [auditDays, setAuditDays] = useState(365)
  const [retentionFeedback, setRetentionFeedback] = useState<string | null>(null)
  const [retentionError, setRetentionError] = useState<string | null>(null)
  const [purgeReason, setPurgeReason] = useState('')
  const [purgeConfirmText, setPurgeConfirmText] = useState('')
  const [purgeFeedback, setPurgeFeedback] = useState<string | null>(null)
  const [purgeError, setPurgeError] = useState<string | null>(null)

  useEffect(() => {
    if (!retention) return
    setMetadataDays(retention.metadata_days)
    setSnapshotDays(retention.snapshot_days)
    setClipDays(retention.clip_days)
    setAuditDays(retention.audit_log_days)
  }, [retention])

  const purgeEnabled = canManageEvidence && purgeReason.trim().length >= 4 && purgeConfirmText.trim().toUpperCase() === 'PURGAR'

  const submitRetention = async () => {
    setRetentionFeedback(null)
    setRetentionError(null)
    try {
      await adminMutations.updateRetention.mutateAsync({ metadata_days: metadataDays, snapshot_days: snapshotDays, clip_days: clipDays, audit_log_days: auditDays, reason: 'Atualização de política pela UI' })
      setRetentionFeedback('Política de retenção atualizada.')
    } catch (error) {
      setRetentionError(error instanceof Error ? error.message : 'Não foi possível atualizar a retenção.')
    }
  }

  const submitPurge = async () => {
    setPurgeFeedback(null)
    setPurgeError(null)
    try {
      await purgePreviewQuery.refetch()
      await adminMutations.purgeExpired.mutateAsync({ confirm: true, reason: purgeReason.trim() })
      setPurgeFeedback('Purge executado com sucesso.')
      setPurgeReason('')
      setPurgeConfirmText('')
      await Promise.all([purgePreviewQuery.refetch(), retentionQuery.refetch()])
    } catch (error) {
      setPurgeError(error instanceof Error ? error.message : 'Não foi possível executar o purge.')
    }
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        eyebrow="PREFERÊNCIAS"
        title="Configurações"
        description="Preferências da conta e da organização, com ênfase em retenção e privacidade."
      />

      <div className="grid gap-5 xl:grid-cols-[224px_minmax(0,1fr)]">
        <nav className="hidden flex-col gap-[3px] self-start xl:flex">
          {sectionNav.map((item, index) => (
            <span key={item} className={`rounded-lg px-3 py-2.5 text-sm ${index === 0 ? 'bg-[var(--nav-active-bg)] font-semibold text-[var(--nav-active-text)]' : 'text-[var(--nav-text)]'}`}>{item}</span>
          ))}
        </nav>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
            <h3 className="mb-[18px] font-display text-[17px] font-bold text-[var(--ink)]">Perfil &amp; preferências</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <SettingsField label="Nome" value={userName} />
              <SettingsField label="E-mail" value={userEmail} readOnly />
              <SettingsField label="Idioma" value="Português (Brasil)" caret />
              <SettingsField label="Organização padrão" value={organizationName} caret />
            </div>
            <div className="mt-4">
              <p className="mb-2.5 text-[13px] font-medium text-[#403933]">Tema</p>
              <div className="flex gap-2.5">
                <span className="flex items-center gap-2 rounded-[9px] border-[1.5px] border-[var(--accent)] bg-[#F9EEE7] px-3.5 py-2 text-[13px] font-semibold text-[var(--nav-active-text)]"><span className="h-3 w-3 rounded-[3px] border border-[#DCD7CC] bg-[var(--paper)]" />Claro</span>
                <span className="flex items-center gap-2 rounded-[9px] border border-[#DCD7CC] bg-[var(--card)] px-3.5 py-2 text-[13px] text-[var(--muted)]"><span className="h-3 w-3 rounded-[3px] bg-[var(--ink)]" />Escuro</span>
              </div>
            </div>
            <PendingSave note="Idioma e tema salvam localmente · nome pendente de API" />
          </div>

          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
            <h3 className="mb-1 font-display text-[17px] font-bold text-[var(--ink)]">Saúde da API</h3>
            <p className="mb-[18px] text-[13px] text-[var(--muted-2)]">{isLive ? 'Status real da API conectado nesta sessão.' : 'Status omitido fora do modo conectado.'}</p>
            {!isLive ? (
              <div className="rounded-[9px] border border-dashed border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3 text-[13px] text-[var(--muted)]">{liveLabel}</div>
            ) : healthQuery.isLoading || readinessQuery.isLoading ? (
              <div className="rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3 text-[13px] text-[var(--muted)]">Carregando saúde da API…</div>
            ) : healthQuery.isError || readinessQuery.isError ? (
              <div className="rounded-[9px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-3.5 py-3 text-[13px] leading-6 text-[#9e4120]">Não foi possível carregar /health ou /readiness.</div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-medium text-[var(--ink)]">Health</span>
                    <span className="rounded-[5px] px-2 py-0.5 text-[10px] font-semibold" style={{ background: dependencyTone(healthQuery.data?.status === 'ok').bg, color: dependencyTone(healthQuery.data?.status === 'ok').color }}>{healthQuery.data?.status ?? '—'}</span>
                  </div>
                  <div className="space-y-1 text-[13px] text-[var(--muted)]">
                    {(['database', 'redis', 'minio'] as const).map((key) => {
                      const dep = healthQuery.data?.dependencies[key]
                      return <div key={key} className="flex items-center justify-between gap-2"><span className="capitalize">{key}</span><span className={dep?.ok ? 'text-[#2F7D57]' : 'text-[#B14A22]'}>{dep?.ok ? 'ok' : 'degraded'}</span></div>
                    })}
                  </div>
                </div>
                <div className="rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-medium text-[var(--ink)]">Readiness</span>
                    <span className="rounded-[5px] px-2 py-0.5 text-[10px] font-semibold" style={{ background: dependencyTone(readinessQuery.data?.status === 'ok').bg, color: dependencyTone(readinessQuery.data?.status === 'ok').color }}>{readinessQuery.data?.status ?? '—'}</span>
                  </div>
                  <p className="text-[13px] text-[var(--muted)]">{readinessQuery.data?.status === 'ok' ? 'Pronto para tráfego' : 'Dependências com alerta'}</p>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
            <h3 className="font-display text-[17px] font-bold text-[var(--ink)]">Retenção &amp; LGPD</h3>
            <p className="mb-[18px] mt-1 text-[13px] text-[var(--muted-2)]">Períodos de retenção por organização e garantias de privacidade do produto.</p>
            {canManageEvidence ? (
              <div className="mb-[18px] grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <NumberInput label="Metadata days" value={metadataDays} onChange={setMetadataDays} />
                <NumberInput label="Snapshot days" value={snapshotDays} onChange={setSnapshotDays} />
                <NumberInput label="Clip days" value={clipDays} onChange={setClipDays} />
                <NumberInput label="Audit log days" value={auditDays} onChange={setAuditDays} />
              </div>
            ) : null}
            <div className="mb-[18px] grid gap-4 sm:grid-cols-2">
              <SettingsField label="Retenção de evidências" value={evidenceRetentionValue} readOnly={!canReadRetention} />
              <SettingsField label="Retenção do audit log" value={auditRetentionValue} readOnly={!canReadRetention} />
            </div>
            {retentionQuery.isError ? <div className="mb-[18px] rounded-[9px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-3.5 py-3 text-[13px] leading-6 text-[#9e4120]">Não foi possível carregar a política real de retenção.</div> : null}
            {retentionFeedback ? <div className="mb-[18px] rounded-[9px] border border-[#CFE6DA] bg-[#E7F1EB] px-3.5 py-3 text-[13px] leading-6 text-[#1F5540]">{retentionFeedback}</div> : null}
            {retentionError ? <div className="mb-[18px] rounded-[9px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-3.5 py-3 text-[13px] leading-6 text-[#9e4120]">{retentionError}</div> : null}
            {retention ? <div className="mb-[18px] rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3 text-[13px] leading-6 text-[var(--muted)]">Política carregada de <code>/organizations/{organizationId}/evidence/retention</code>.</div> : null}
            <div className="mb-[18px] rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3">
              <p className="text-[13px] font-semibold text-[var(--ink)]">Preview de purge</p>
               <p className="mt-1 text-[13px] leading-6 text-[var(--muted)]">Leia o preview antes de qualquer purge; a confirmação forte exige motivo e palavra-chave.</p>
              {!canReadRetention ? (
                <p className="mt-2 text-[13px] text-[var(--muted)]">Permissão audit.read necessária</p>
              ) : purgePreviewQuery.isLoading ? (
                <p className="mt-2 text-[13px] text-[var(--muted)]">Carregando preview…</p>
              ) : purgePreviewQuery.isError ? (
                <p className="mt-2 text-[13px] leading-6 text-[#9e4120]">Não foi possível carregar o preview de purge.</p>
              ) : previewItems.length > 0 ? (
                <div className="mt-2 space-y-1 text-[13px] text-[var(--muted)]">
                  <p className="font-medium text-[var(--ink)]">{purgePreviewQuery.data?.page_info?.total ?? previewItems.length} item(ns) seriam afetados</p>
                  {previewItems.slice(0, 3).map((item) => <p key={`${item.incident_id}-${item.file_id}`} className="font-mono-ui text-[11px]">{item.incident_id} · {item.file_id}</p>)}
                </div>
              ) : (
                <p className="mt-2 text-[13px] text-[var(--muted)]">Nenhum item elegível para purge no momento.</p>
              )}
            </div>
            {canManageEvidence ? (
              <div className="mb-[18px] rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3">
                <p className="text-[13px] font-semibold text-[var(--ink)]">Atualizar política</p>
                <p className="mt-1 text-[13px] text-[var(--muted)]">As mudanças usam PUT e preservam o padrão visual simples.</p>
                <FormActions primaryLabel={adminMutations.updateRetention.isPending ? 'Salvando…' : 'Salvar retenção'} secondaryLabel="Recarregar" onPrimary={submitRetention} onSecondary={() => void retentionQuery.refetch()} primaryDisabled={adminMutations.updateRetention.isPending} primaryHint="Disponível apenas com audit.read e sessão conectada." />
              </div>
            ) : null}
            <div className="mb-[18px] rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3">
              <p className="text-[13px] font-semibold text-[var(--ink)]">Purge com confirmação forte</p>
              <p className="mt-1 text-[13px] text-[var(--muted)]">Digite <span className="font-semibold">PURGAR</span> e um motivo antes de liberar a ação.</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <TextField label="Motivo" value={purgeReason} onChange={(e) => setPurgeReason(e.target.value)} placeholder="Ex.: Política expirada e revisão concluída" />
                <TextField label="Confirmação" value={purgeConfirmText} onChange={(e) => setPurgeConfirmText(e.target.value)} placeholder="PURGAR" />
              </div>
              {purgeFeedback ? <div className="mt-3 rounded-[9px] border border-[#CFE6DA] bg-[#E7F1EB] px-3.5 py-3 text-[13px] leading-6 text-[#1F5540]">{purgeFeedback}</div> : null}
              {purgeError ? <div className="mt-3 rounded-[9px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-3.5 py-3 text-[13px] leading-6 text-[#9e4120]">{purgeError}</div> : null}
              <FormActions primaryLabel={adminMutations.purgeExpired.isPending ? 'Executando…' : 'Executar purge'} secondaryLabel="Atualizar preview" onPrimary={submitPurge} onSecondary={() => void purgePreviewQuery.refetch()} primaryDisabled={!purgeEnabled || adminMutations.purgeExpired.isPending} primaryHint="O preview é revalidado antes do POST; URLs assinadas nunca são exibidas." />
            </div>
            <div className="mb-[18px]">
              <p className="mb-[7px] text-[13px] font-medium text-[#403933]">Finalidade declarada</p>
              <div className="rounded-[9px] border border-[color:var(--line)] bg-[#F2EEE7] px-3.5 py-3 text-[13px] leading-[1.5] text-[var(--muted)]">Segurança do trabalho e conformidade de EPI. Não usado para vigilância de produtividade.</div>
            </div>
            <p className="mb-2.5 font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">GARANTIAS FIXAS DO MVP</p>
            <div className="flex flex-col gap-2.5">
              <PrivacyGuarantee title="Sem reconhecimento facial" desc="Detecção de EPI e zonas, nunca identidade de pessoas." />
              <PrivacyGuarantee title="Sem vídeo contínuo" desc="Apenas snapshots/clips vinculados a incidentes." />
            </div>
            <PendingSave note={canReadRetention ? 'Retenção editável · purge com confirmação forte' : 'Retenção protegida por audit.read no backend'} />
          </div>

          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5 opacity-95">
            <div className="mb-1 flex items-center gap-2.5">
              <h3 className="font-display text-[17px] font-bold text-[var(--ink)]">Notificações &amp; integrações</h3>
              <span className="rounded-[5px] bg-[#F3E9D6] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em] text-[#946416]">FUTURO</span>
            </div>
            <p className="mb-4 text-[13px] text-[var(--muted-2)]">Alertas de incidente por canal. Ainda não disponível — em roadmap.</p>
            <div className="flex flex-col gap-2.5">
              <FutureToggle label="Alertas por e-mail" />
              <FutureToggle label="Alertas por WhatsApp" />
            </div>
          </div>

          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
            <h3 className="mb-4 font-display text-[17px] font-bold text-[var(--ink)]">Segurança da sessão</h3>
            <div className="flex items-center justify-between border-b border-[color:var(--row)] py-3">
              <div>
                <p className="text-sm text-[var(--ink)]">Expiração do token</p>
                <p className="text-xs text-[var(--muted-2)]">Access token expira em 15 min · refresh em 7 dias.</p>
              </div>
              <span className="font-mono-ui text-xs text-[var(--muted)]">15 min / 7 d</span>
            </div>
            <div className="flex items-center justify-between pb-1 pt-3.5">
              <div>
                <p className="text-sm text-[var(--ink)]">Encerrar outras sessões</p>
                <p className="text-xs text-[var(--muted-2)]">Desconecta este usuário em todos os outros dispositivos.</p>
              </div>
              <button type="button" disabled title="Pendente de API" className="h-9 cursor-not-allowed rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-3.5 text-[13px] font-medium text-[var(--nav-label)]">Encerrar (pendente)</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
