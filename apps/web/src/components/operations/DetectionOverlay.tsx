export interface DetectedBox {
  category: string
  confidence: number
  bbox: [number, number, number, number]
}

export interface DetectedViolation {
  event_type: string
  zone_id: string | null
  confidence: number
  bbox: [number, number, number, number]
}

export interface FrameAnalysis {
  camera_id: string
  timestamp: string
  boxes: DetectedBox[]
  violations: DetectedViolation[]
}

const VIOLATION_STYLE: Record<string, { color: string; label: string }> = {
  restricted_intrusion: { color: '#E1614A', label: 'Área restrita' },
  ppe_violation: { color: '#C98A2B', label: 'Sem capacete' },
}
const OK_COLOR = '#2F7D57'

const overlaps = (a: readonly number[], b: readonly number[]) =>
  Math.max(a[0], b[0]) < Math.min(a[2], b[2]) && Math.max(a[1], b[1]) < Math.min(a[3], b[3])

/**
 * Desenha o que a CV está vendo por cima do vídeo. Coordenadas chegam normalizadas [0..1]
 * do worker, então isto alinha em qualquer tamanho de player, inclusive em tela cheia,
 * sem saber a resolução da câmera.
 *
 * Formas ficam no SVG (que estica junto com o vídeo, como devem); os rótulos ficam FORA
 * dele, como divs posicionados por %, senão o `preserveAspectRatio="none"` esticaria o
 * texto junto com o quadro.
 */
export function DetectionOverlay({ analysis, zonePolygons = [] }: { analysis: FrameAnalysis | null; zonePolygons?: { points: [number, number][]; zoneType: string }[] }) {
  if (!analysis) return null

  const persons = analysis.boxes.filter((box) => box.category === 'person')
  const violationFor = (box: DetectedBox) => analysis.violations.find((violation) => overlaps(violation.bbox, box.bbox))

  return (
    <div className="pointer-events-none absolute inset-0" data-testid="detection-overlay">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        {zonePolygons.map((zone, index) => (
          <polygon
            key={`zone-${index}`}
            points={zone.points.map(([x, y]) => `${x * 100},${y * 100}`).join(' ')}
            fill={zone.zoneType === 'ppe' ? 'rgba(201,138,43,0.14)' : 'rgba(225,97,74,0.14)'}
            stroke={zone.zoneType === 'ppe' ? '#C98A2B' : '#E1614A'}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {persons.map((box, index) => {
          const violation = violationFor(box)
          const [x1, y1, x2, y2] = box.bbox
          return (
            <rect
              key={`box-${index}`}
              x={x1 * 100}
              y={y1 * 100}
              width={Math.max(0, x2 - x1) * 100}
              height={Math.max(0, y2 - y1) * 100}
              fill={violation ? 'rgba(225,97,74,0.14)' : 'none'}
              stroke={violation ? VIOLATION_STYLE[violation.event_type]?.color ?? '#E1614A' : OK_COLOR}
              strokeWidth={violation ? 3 : 2}
              vectorEffect="non-scaling-stroke"
              style={{ transition: 'x 220ms linear, y 220ms linear, width 220ms linear, height 220ms linear' }}
            />
          )
        })}
      </svg>

      {persons.map((box, index) => {
        const violation = violationFor(box)
        const color = violation ? VIOLATION_STYLE[violation.event_type]?.color ?? '#E1614A' : OK_COLOR
        const label = violation ? VIOLATION_STYLE[violation.event_type]?.label ?? violation.event_type : 'Pessoa'
        const [x1, y1] = box.bbox
        return (
          <span
            key={`label-${index}`}
            className="absolute -translate-y-full whitespace-nowrap rounded-[3px] px-1.5 py-0.5 font-mono-ui text-[10px] font-semibold uppercase tracking-wide text-white"
            style={{ left: `${x1 * 100}%`, top: `${Math.max(y1 * 100, 2)}%`, background: color, transition: 'left 220ms linear, top 220ms linear' }}
          >
            {label} {Math.round((violation?.confidence ?? box.confidence) * 100)}%
          </span>
        )
      })}
    </div>
  )
}
