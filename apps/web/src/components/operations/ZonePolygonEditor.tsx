import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../ui/dashboard'
import { Icon } from '../ui/icons'

export type PolygonPoint = [number, number]

const ZONE_COLORS: Record<string, { stroke: string; fill: string }> = {
  restricted: { stroke: '#C1552B', fill: 'rgba(193,85,43,0.18)' },
  ppe: { stroke: '#C98A2B', fill: 'rgba(201,138,43,0.18)' },
  access: { stroke: '#2F7D57', fill: 'rgba(47,125,87,0.16)' },
}

const clamp01 = (value: number) => Math.min(1, Math.max(0, value))

/**
 * Editor de polígono em coordenadas NORMALIZADAS [0..1] — a mesma convenção que o
 * worker usa (`geometry.parse_polygon`), então o desenho independe da resolução da câmera.
 */
export function ZonePolygonEditor({
  frameUrl,
  frameLoading,
  points,
  onChange,
  zoneType,
}: {
  frameUrl: string | null
  frameLoading: boolean
  points: PolygonPoint[]
  onChange: (points: PolygonPoint[]) => void
  zoneType: string
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [dragging, setDragging] = useState<number | null>(null)
  const colors = ZONE_COLORS[zoneType] ?? ZONE_COLORS.restricted

  const toNormalized = useCallback((clientX: number, clientY: number): PolygonPoint => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect || rect.width === 0 || rect.height === 0) return [0, 0]
    return [clamp01((clientX - rect.left) / rect.width), clamp01((clientY - rect.top) / rect.height)]
  }, [])

  useEffect(() => {
    if (dragging === null) return
    const onMove = (event: MouseEvent) => {
      const next = points.slice()
      next[dragging] = toNormalized(event.clientX, event.clientY)
      onChange(next)
    }
    const onUp = () => setDragging(null)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [dragging, onChange, points, toNormalized])

  const addPoint = (event: React.MouseEvent<HTMLDivElement>) => {
    if (dragging !== null) return
    onChange([...points, toNormalized(event.clientX, event.clientY)])
  }

  const polygonPoints = points.map(([x, y]) => `${x * 100},${y * 100}`).join(' ')
  const closed = points.length >= 3

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[13px] font-medium text-[#403933]">Área monitorada</span>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => onChange(points.slice(0, -1))} disabled={points.length === 0} className="text-[12px] font-medium text-[var(--ink)] disabled:cursor-not-allowed disabled:text-[#C0BAB0] hover:underline">
            Desfazer
          </button>
          <span className="text-[#D2CCC0]">·</span>
          <button type="button" onClick={() => onChange([])} disabled={points.length === 0} className="text-[12px] font-medium text-[#B14A22] disabled:cursor-not-allowed disabled:text-[#C0BAB0] hover:underline">
            Limpar
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        onClick={addPoint}
        className="relative aspect-video w-full cursor-crosshair overflow-hidden rounded-[10px] border border-[#E2DDD4] bg-[#EDE9E1] select-none"
        style={frameUrl ? undefined : { backgroundImage: 'repeating-linear-gradient(45deg,#F2EEE7 0,#F2EEE7 11px,#EDE9E1 11px,#EDE9E1 22px)' }}
      >
        {frameUrl ? <img src={frameUrl} alt="Frame da câmera" className="pointer-events-none absolute inset-0 h-full w-full object-cover" /> : null}

        {!frameUrl ? (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 px-6 text-center">
            <Icon name="image" size={18} className="text-[#A9A398]" />
            <p className="text-[13px] font-medium text-[var(--ink)]">{frameLoading ? 'Buscando frame da câmera…' : 'Sem frame desta câmera ainda'}</p>
            {!frameLoading ? <p className="max-w-[280px] text-[12px] leading-5 text-[#8E887B]">A imagem aparece após o primeiro incidente com evidência. Você ainda pode desenhar a área usando a grade.</p> : null}
          </div>
        ) : null}

        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
          {points.length >= 2 ? (
            closed ? (
              <polygon points={polygonPoints} fill={colors.fill} stroke={colors.stroke} strokeWidth={2} vectorEffect="non-scaling-stroke" />
            ) : (
              <polyline points={polygonPoints} fill="none" stroke={colors.stroke} strokeWidth={2} vectorEffect="non-scaling-stroke" />
            )
          ) : null}
        </svg>

        {points.map(([x, y], index) => (
          <button
            key={index}
            type="button"
            onMouseDown={(event) => {
              event.stopPropagation()
              setDragging(index)
            }}
            onClick={(event) => event.stopPropagation()}
            aria-label={`Ponto ${index + 1}`}
            className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 cursor-grab rounded-full border-2 border-white shadow-[0_1px_3px_rgba(32,27,24,0.4)] active:cursor-grabbing"
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, background: colors.stroke }}
          />
        ))}
      </div>

      <p className="text-[12px] leading-5 text-[var(--label)]">
        {points.length === 0
          ? 'Clique para marcar os cantos da área. Mínimo de 3 pontos.'
          : closed
            ? `${points.length} pontos · arraste para ajustar. Só o que estiver dentro da área vira incidente.`
            : `${points.length} de 3 pontos — continue clicando para fechar a área.`}
      </p>
    </div>
  )
}
