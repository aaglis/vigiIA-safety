import type { EvidenceItem } from '../../api/evidence'
import { Icon } from '../ui/icons'
import { formatBytes, formatClock, formatTimestamp, readMetadataValue } from '../../utils/formatters'

function getEvidenceLabel(evidence: EvidenceItem) {
  return evidence.kind === 'clip' ? 'Vídeo' : evidence.kind === 'metadata' ? 'Metadado' : 'Snapshot'
}

function evidenceFileName(item: EvidenceItem) {
  return item.object_key.split('/').filter(Boolean).pop() || item.file_id
}

function evidenceFileIcon(kind: string) {
  return kind === 'clip' ? 'video' : kind === 'metadata' ? 'file-text' : 'image'
}

export function EvidenceExplorer({
  evidenceItems,
  selectedEvidence,
  evidenceLoading,
  evidenceError,
  evidenceDownloadUrl,
  evidenceDownloadLoading,
  evidenceDownloadError,
  onSelectEvidence,
  onOpenEvidence,
  onRetry,
}: {
  incident: unknown
  organizationName: string | null
  evidenceItems: EvidenceItem[]
  selectedEvidence: EvidenceItem | null
  evidenceLoading: boolean
  evidenceError: string | null
  evidenceDownloadUrl: string | null
  evidenceDownloadLoading: boolean
  evidenceDownloadError: string | null
  onSelectEvidence: (fileId: string) => void
  onOpenEvidence: () => void
  onRetry: () => void
}) {
  const metadata = selectedEvidence?.metadata ?? {}
  const contentType = selectedEvidence?.media_type ?? readMetadataValue(metadata, 'content_type') ?? '—'
  const sha256 = readMetadataValue(metadata, 'sha256')
  const kindLabel = selectedEvidence ? getEvidenceLabel(selectedEvidence) : 'Evidência'
  const hasImagePreview = Boolean(evidenceDownloadUrl && selectedEvidence?.media_type.startsWith('image/'))
  const released = Boolean(evidenceDownloadUrl)

  return (
    <div className="grid gap-3.5 xl:grid-cols-[300px_minmax(0,1fr)]">
      {/* FILE LIST */}
      <div className="flex flex-col overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)]">
        <div className="flex items-center justify-between border-b border-[color:var(--divider)] px-4 py-3">
          <span className="font-display text-[14px] font-bold text-[var(--ink)]">Arquivos</span>
          <span className="font-mono-ui text-[11px] text-[var(--label)]">{evidenceItems.length} {evidenceItems.length === 1 ? 'item' : 'itens'}</span>
        </div>
        <div className="flex-1 overflow-auto p-2">
          {evidenceLoading ? (
            <p className="px-2 py-6 text-[13px] text-[var(--muted)]">Carregando evidências…</p>
          ) : evidenceItems.length === 0 ? (
            <p className="px-2 py-6 text-[13px] leading-6 text-[var(--muted)]">Sem evidência anexada a este incidente. A triagem segue por contexto e auditoria.</p>
          ) : (
            evidenceItems.map((item) => {
              const active = selectedEvidence?.file_id === item.file_id
              return (
                <button
                  key={item.file_id}
                  type="button"
                  onClick={() => onSelectEvidence(item.file_id)}
                  className={`mb-1.5 flex w-full gap-[11px] rounded-[9px] p-[11px] text-left transition ${active ? 'border border-[#EAD8CD] bg-[#F9EEE7]' : 'border border-transparent hover:bg-[rgba(32,27,24,0.03)]'}`}
                >
                  <span className="relative grid h-11 w-11 flex-none place-items-center rounded-lg border border-[color:var(--line)] bg-[var(--divider)]">
                    <Icon name={evidenceFileIcon(item.kind)} size={20} className="text-[var(--muted-2)]" />
                    {item.kind === 'snapshot' ? (
                      <span className="absolute -bottom-1 -right-1 grid h-4 w-4 place-items-center rounded-[5px] bg-[var(--ink)]">
                        <Icon name="lock" size={9} className="text-[var(--paper)]" />
                      </span>
                    ) : null}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-semibold text-[var(--ink)]">{evidenceFileName(item)}</span>
                    <span className="mt-0.5 block truncate font-mono-ui text-[10px] text-[var(--nav-label)]">{item.media_type} · {formatBytes(item.size)}</span>
                    <span className="mt-[5px] flex items-center gap-1.5">
                      <span className="rounded-[5px] bg-[var(--divider)] px-1.5 py-px text-[10px] font-medium text-[#7c756c]">{item.kind}</span>
                      <span className="font-mono-ui text-[10px] text-[#b0a99e]">{formatClock(item.created_at)}</span>
                    </span>
                  </span>
                </button>
              )
            })
          )}
        </div>
        {evidenceError ? (
          <div className="border-t border-[color:var(--divider)] px-4 py-3 text-[12px] text-[#9e4120]">
            <p>{evidenceError}</p>
            <button type="button" onClick={onRetry} className="mt-1 font-medium underline decoration-[rgba(158,65,32,0.4)] underline-offset-2">Tentar de novo</button>
          </div>
        ) : null}
      </div>

      {/* PREVIEW + METADATA */}
      <div className="grid gap-3.5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="flex min-h-[420px] flex-col overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)]">
          <div className="flex items-center justify-between border-b border-[color:var(--divider)] px-[18px] py-3">
            <span className="truncate font-display text-[14px] font-bold text-[var(--ink)]">{selectedEvidence ? evidenceFileName(selectedEvidence) : 'Nenhum arquivo'}</span>
            <span className="inline-flex flex-none items-center gap-1.5 rounded-md px-2.5 py-[3px] text-[11px] font-medium" style={released ? { background: '#E4EFE9', color: '#1F6B4A' } : { background: '#EEEAE3', color: '#7C756C' }}>
              <Icon name={released ? 'check' : 'lock'} size={11} />
              {released ? 'Liberado' : 'Protegido'}
            </span>
          </div>
          {hasImagePreview ? (
            <div className="flex flex-1 flex-col gap-3 p-4">
              <img src={evidenceDownloadUrl ?? ''} alt={selectedEvidence?.object_key ?? ''} className="w-full flex-1 rounded-lg border border-[color:var(--line)] bg-black object-contain" />
              <a href={evidenceDownloadUrl ?? ''} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 self-end text-[13px] font-medium text-[var(--accent)] hover:opacity-80">Abrir em nova aba <Icon name="arrow-right" size={13} /></a>
            </div>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center px-10 py-10 text-center" style={{ backgroundImage: 'repeating-linear-gradient(45deg,#F2EEE7 0,#F2EEE7 12px,#F5F1EA 12px,#F5F1EA 24px)' }}>
              <div className="mb-5 grid h-[60px] w-[60px] place-items-center rounded-[15px] border border-[color:var(--line)] bg-[var(--card)] shadow-[0_8px_20px_-12px_rgba(24,16,12,0.3)]">
                <Icon name="lock" size={26} className="text-[var(--muted-2)]" />
              </div>
              <p className="mb-2 font-display text-[18px] font-bold text-[var(--ink)]">{released ? 'Evidência aberta' : 'Pré-visualização protegida'}</p>
              <p className="mb-[22px] max-w-[320px] text-[13px] leading-[1.55] text-[var(--muted)]">
                {released ? 'Acesso seguro preparado. O conteúdo pode ser aberto em nova aba e o acesso já foi registrado na auditoria.' : 'O conteúdo é privado. Ao preparar o acesso seguro, uma permissão temporária é criada e registrada na auditoria.'}
              </p>
              {evidenceDownloadError ? <p className="mb-3 max-w-[320px] text-[12px] text-[#9e4120]">{evidenceDownloadError}</p> : null}
              {released ? (
                <a href={evidenceDownloadUrl ?? ''} target="_blank" rel="noreferrer" className="flex h-[42px] items-center gap-2.5 rounded-[9px] bg-[var(--ink)] px-[22px] text-sm font-semibold text-[var(--paper)] transition hover:bg-[var(--ink-soft)]">
                  <Icon name="link" size={16} />
                  Abrir em nova aba
                </a>
              ) : (
                <button type="button" onClick={onOpenEvidence} disabled={evidenceDownloadLoading || !selectedEvidence} className="flex h-[42px] items-center gap-2.5 rounded-[9px] bg-[var(--ink)] px-[22px] text-sm font-semibold text-[var(--paper)] transition hover:bg-[var(--ink-soft)] disabled:cursor-not-allowed disabled:opacity-50">
                  <Icon name="link" size={16} />
                  {evidenceDownloadLoading ? 'Preparando…' : 'Preparar acesso seguro'}
                </button>
              )}
              <span className="mt-3 font-mono-ui text-[11px] text-[var(--nav-label)]">Expira em 5 min · uso único</span>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3.5">
          <div className="flex-1 overflow-auto rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[17px] py-4">
            <p className="mb-3.5 font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">METADADOS TÉCNICOS</p>
            <div className="flex flex-col gap-3.5">
              <div>
                <p className="mb-1 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--nav-label)]">TIPO</p>
                <p className="text-[13px] text-[var(--ink)]">{kindLabel}</p>
              </div>
              <div>
                <p className="mb-1 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--nav-label)]">CONTENT-TYPE</p>
                <p className="font-mono-ui text-[12px] text-[var(--ink)]">{contentType}</p>
              </div>
              <div>
                <p className="mb-1 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--nav-label)]">OBJECT KEY</p>
                <div className="rounded-[7px] border border-[color:var(--border)] bg-[var(--paper)] px-2.5 py-[7px]">
                  <p className="truncate font-mono-ui text-[11px] text-[var(--muted)]">{selectedEvidence?.object_key ?? '—'}</p>
                </div>
              </div>
              <div>
                <p className="mb-1 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--nav-label)]">HASH SHA-256</p>
                <div className="rounded-[7px] bg-[var(--ink)] px-2.5 py-[9px]">
                  <p className="break-all font-mono-ui text-[11px] leading-[1.5] text-[#c9c1b7]">{sha256 ?? '—'}</p>
                </div>
                {sha256 ? <p className="mt-[5px] flex items-center gap-1.5 text-[11px] text-[var(--accent-2)]"><Icon name="check" size={11} /> Integridade verificada</p> : null}
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-3.5">
                <div>
                  <p className="mb-1 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--nav-label)]">ENVIADO POR</p>
                  <p className="truncate text-[13px] text-[var(--ink)]">{selectedEvidence?.uploaded_by ?? '—'}</p>
                </div>
                <div>
                  <p className="mb-1 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--nav-label)]">CRIADO EM</p>
                  <p className="text-[13px] text-[var(--ink)]">{formatTimestamp(selectedEvidence?.created_at ?? null)}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-4 py-3.5">
            <div className="mb-2 flex items-center gap-2">
              <Icon name="link" size={14} className="text-[var(--muted-2)]" />
              <span className="text-[13px] font-semibold text-[var(--ink)]">Acesso à mídia</span>
            </div>
            <p className="mb-3 text-[12px] leading-[1.5] text-[var(--muted-2)]">{released ? 'Acesso seguro ativo. Expira em 5 minutos.' : 'Nenhum acesso ativo. Prepare um acesso seguro para visualizar ou baixar — válido por 5 minutos.'}</p>
            <button type="button" onClick={onOpenEvidence} disabled={evidenceDownloadLoading || !selectedEvidence} className="h-[38px] w-full rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] text-[13px] font-semibold text-[var(--ink)] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50">
              {evidenceDownloadLoading ? 'Preparando…' : released ? 'Abrir evidência' : 'Preparar acesso seguro'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
