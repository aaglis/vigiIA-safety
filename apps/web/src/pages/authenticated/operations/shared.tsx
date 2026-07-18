import type { ReactNode } from 'react'
import type { OperationEntityStatus, OperationZoneType } from '../../../api/operations'

export function labelOperationStatus(status: OperationEntityStatus) {
  return status === 'active' ? 'Ativo' : status === 'inactive' ? 'Inativo' : 'Suspenso'
}

export function labelZoneType(zoneType: OperationZoneType) {
  return zoneType === 'access' ? 'Acesso' : zoneType === 'restricted' ? 'Restrita' : 'EPI'
}

// Deriva o tipo de fonte a partir do campo público `stream_source_type` da API.
export function cameraSource(sourceType?: string | null): { label: string; bg: string; color: string } {
  const value = (sourceType ?? '').toLowerCase()
  if (value.startsWith('rtsp')) return { label: 'RTSP', bg: '#EAF0F5', color: '#2C4C74' }
  if (value.startsWith('rtmp')) return { label: 'RTMP', bg: '#EAF0F5', color: '#2C4C74' }
  if (value === 'video') {
    return { label: 'VÍDEO TESTE', bg: '#F3E9D6', color: '#946416' }
  }
  if (value.startsWith('http')) return { label: 'HTTP', bg: '#EAF0F5', color: '#2C4C74' }
  return { label: 'FONTE', bg: '#EDE9E1', color: '#5F5951' }
}

export function Panel({ title, action, children, className = '' }: { title: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`overflow-hidden rounded-[12px] border border-[#E7E3DC] bg-[var(--card)] ${className}`}>
      <div className="flex items-center justify-between gap-3 border-b border-[#EDE9E1] px-[18px] py-[13px]">
        <span className="font-display text-[14px] font-bold text-[var(--ink)]">{title}</span>
        {action}
      </div>
      {children}
    </section>
  )
}

export function StatusDot({ color }: { color: string }) {
  return <span className="h-1.5 w-1.5 flex-none rounded-full" style={{ background: color }} />
}
