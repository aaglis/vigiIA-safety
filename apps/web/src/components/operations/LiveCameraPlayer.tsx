import { useEffect, useRef, useState } from 'react'
import { apiBaseUrl } from '../../api/client'
import { Icon } from '../ui/icons'
import { DetectionOverlay, type FrameAnalysis } from './DetectionOverlay'
import { connectWhep } from './whep'

// Sem análise nova por este tempo, o overlay some: melhor nenhuma caixa do que caixa
// fantasma parada sobre um vídeo que continua andando.
const ANALYSIS_TTL_MS = 3000

function detectionsSocketUrl(organizationId: string, cameraId: string, token: string): string {
  const base = apiBaseUrl.startsWith('http') ? apiBaseUrl : `${window.location.origin}${apiBaseUrl}`
  const url = new URL(`${base}/organizations/${encodeURIComponent(organizationId)}/operations/cameras/${encodeURIComponent(cameraId)}/detections`)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', token)
  return url.toString()
}

type PlayerState = 'idle' | 'connecting' | 'live' | 'unavailable' | 'error'

export function LiveCameraPlayer({
  cameraId,
  cameraName,
  organizationId,
  zonePolygons,
  onRequestTicket,
}: {
  cameraId: string
  cameraName: string
  organizationId?: string
  zonePolygons?: { points: [number, number][]; zoneType: string }[]
  onRequestTicket: (cameraId: string) => Promise<{ whep_url: string; token?: string } | null>
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [state, setState] = useState<PlayerState>('idle')
  const [detail, setDetail] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<FrameAnalysis | null>(null)

  const ticketTokenRef = useRef<string | null>(null)

  useEffect(() => {
    let pc: RTCPeerConnection | null = null
    let cancelled = false

    const start = async () => {
      setState('connecting')
      setDetail(null)
      try {
        const ticket = await onRequestTicket(cameraId)
        if (cancelled) return
        if (!ticket) {
          setState('unavailable')
          return
        }
        ticketTokenRef.current = ticket.token ?? null
        pc = new RTCPeerConnection({ iceServers: [] })
        pc.ontrack = (event) => {
          if (videoRef.current && event.streams[0]) videoRef.current.srcObject = event.streams[0]
        }
        pc.onconnectionstatechange = () => {
          if (cancelled || !pc) return
          if (pc.connectionState === 'connected') setState('live')
          if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
            setState('error')
            setDetail('conexão com a câmera caiu')
          }
        }
        await connectWhep(ticket.whep_url, pc)
      } catch (error) {
        if (cancelled) return
        setState('error')
        setDetail(error instanceof Error ? error.message : 'falha ao conectar')
      }
    }

    void start()
    return () => {
      cancelled = true
      pc?.close()
    }
  }, [cameraId, onRequestTicket])

  useEffect(() => {
    const token = ticketTokenRef.current
    if (state !== 'live' || !organizationId || !token) return
    let socket: WebSocket | null = null
    let expiry: ReturnType<typeof setTimeout> | undefined
    try {
      socket = new WebSocket(detectionsSocketUrl(organizationId, cameraId, token))
    } catch {
      return
    }
    socket.onmessage = (event) => {
      try {
        setAnalysis(JSON.parse(event.data) as FrameAnalysis)
        clearTimeout(expiry)
        expiry = setTimeout(() => setAnalysis(null), ANALYSIS_TTL_MS)
      } catch {
        /* frame malformado não derruba o player */
      }
    }
    return () => {
      clearTimeout(expiry)
      socket?.close()
      setAnalysis(null)
    }
  }, [cameraId, organizationId, state])

  return (
    <div className="space-y-2">
      <div className="relative aspect-video w-full overflow-hidden rounded-[10px] border border-[#E2DDD4] bg-[#201B18]">
        <video ref={videoRef} autoPlay muted playsInline data-testid="live-video" className="h-full w-full object-contain" />
        {state === 'live' ? <DetectionOverlay analysis={analysis} zonePolygons={zonePolygons} /> : null}
        {state !== 'live' ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-[#EDE9E1] px-6 text-center">
            <Icon name={state === 'error' || state === 'unavailable' ? 'alert-triangle' : 'video'} size={18} className="text-[#A9A398]" />
            <p className="text-[13px] font-medium text-[var(--ink)]">
              {state === 'connecting' ? 'Conectando à câmera…' : state === 'unavailable' ? 'Câmera sem transmissão ao vivo' : state === 'error' ? 'Não foi possível exibir a câmera' : 'Câmera parada'}
            </p>
            <p className="max-w-[300px] text-[12px] leading-5 text-[#8E887B]">
              {state === 'unavailable'
                ? 'Esta câmera está cadastrada como arquivo de vídeo. Só fontes RTSP transmitem ao vivo.'
                : state === 'error'
                  ? `${cameraName} está offline ou inacessível a partir do seu navegador${detail ? ` (${detail})` : ''}.`
                  : 'O vídeo vai direto do equipamento da planta para o seu navegador.'}
            </p>
          </div>
        ) : null}
        {state === 'live' ? (
          <span data-testid="live-badge" className="absolute left-2 top-2 flex items-center gap-1.5 rounded-[6px] bg-[rgba(32,27,24,0.72)] px-2 py-1 font-mono-ui text-[10px] font-semibold uppercase tracking-wider text-white">
            <span className="h-1.5 w-1.5 rounded-full bg-[#E1614A]" />
            ao vivo
          </span>
        ) : null}
      </div>
      <p className="text-[12px] leading-5 text-[var(--label)]">
        Transmissão direta do edge — o vídeo não passa pelos nossos servidores.
        {state === 'live' && analysis ? ` Visão computacional analisando: ${analysis.boxes.filter((box) => box.category === 'person').length} pessoa(s) no quadro.` : ''}
      </p>
    </div>
  )
}
