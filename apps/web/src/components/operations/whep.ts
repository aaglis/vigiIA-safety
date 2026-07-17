/**
 * WHEP: o vídeo vem do edge (MediaMTX na planta) DIRETO para o navegador via WebRTC.
 * O cloud só emite o ticket de curta duração e nunca vê o frame.
 * Ver docs/architecture/live-video.md.
 */
export async function connectWhep(whepUrl: string, pc: RTCPeerConnection): Promise<void> {
  pc.addTransceiver('video', { direction: 'recvonly' })
  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  await new Promise<void>((resolve) => {
    if (pc.iceGatheringState === 'complete') return resolve()
    const check = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', check)
        resolve()
      }
    }
    pc.addEventListener('icegatheringstatechange', check)
    setTimeout(resolve, 1500)
  })
  const response = await fetch(whepUrl, { method: 'POST', headers: { 'Content-Type': 'application/sdp' }, body: pc.localDescription?.sdp ?? '' })
  if (!response.ok) throw new Error(`whep ${response.status}`)
  await pc.setRemoteDescription({ type: 'answer', sdp: await response.text() })
}

/**
 * Congela um frame da câmera ao vivo, sem servidor no meio: conecta, espera a imagem
 * chegar, desenha num canvas e devolve como data URL. É assim que o editor de zona
 * consegue um fundo mesmo numa câmera recém-cadastrada, que nunca gerou incidente —
 * e o frame não trafega pelo nosso cloud.
 */
export async function captureLiveFrame(whepUrl: string, timeoutMs = 12000): Promise<string | null> {
  const pc = new RTCPeerConnection({ iceServers: [] })
  const video = document.createElement('video')
  video.muted = true
  video.playsInline = true
  try {
    const frameReady = new Promise<HTMLVideoElement>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('timeout ao capturar frame')), timeoutMs)
      pc.ontrack = (event) => {
        if (!event.streams[0]) return
        video.srcObject = event.streams[0]
        void video.play().catch(() => undefined)
        const onData = () => {
          if (video.videoWidth === 0) return
          clearTimeout(timer)
          video.removeEventListener('loadeddata', onData)
          resolve(video)
        }
        video.addEventListener('loadeddata', onData)
        // Alguns navegadores só expõem dimensão depois do primeiro frame pintado.
        video.addEventListener('timeupdate', onData)
      }
    })
    await connectWhep(whepUrl, pc)
    const ready = await frameReady
    const canvas = document.createElement('canvas')
    canvas.width = ready.videoWidth
    canvas.height = ready.videoHeight
    const context = canvas.getContext('2d')
    if (!context) return null
    context.drawImage(ready, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.85)
  } catch {
    return null
  } finally {
    video.srcObject = null
    pc.close()
  }
}
