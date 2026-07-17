import { expect, test } from '@playwright/test'

// Só passa se o vídeo REALMENTE chegar do edge: exige frames decodificados no <video>.
test('camera ao vivo transmite do edge para o navegador via WebRTC', async ({ page }) => {
  await page.goto('/dashboard')
  // O clique é repetido até pegar: o dashboard re-renderiza ao carregar dados e engole o primeiro.
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })
  await expect(page.getByRole('heading', { name: 'Operações e câmeras' })).toBeVisible()

  await page.getByTestId('site-card-site-demo').click()
  await expect(page).toHaveURL(/\/sites\/site-demo$/)
  await page.getByTestId('camera-open-camera-demo-01').click()
  await expect(page).toHaveURL(/\/cameras\/camera-demo-01$/)
  await expect(page.getByTestId('live-badge')).toBeVisible({ timeout: 20000 })

  const size = await page.getByTestId('live-video').evaluate(
    (el) => new Promise<{ w: number; h: number }>((resolve) => {
      const video = el as HTMLVideoElement
      const read = () => resolve({ w: video.videoWidth, h: video.videoHeight })
      if (video.videoWidth > 0) return read()
      video.addEventListener('loadeddata', read, { once: true })
      setTimeout(read, 10000)
    }),
  )
  expect(size.w).toBeGreaterThan(0)
  expect(size.h).toBeGreaterThan(0)

  // Vídeo tem que ANDAR, não só conectar: currentTime avança entre duas leituras.
  const video = page.getByTestId('live-video')
  const t0 = await video.evaluate((el) => (el as HTMLVideoElement).currentTime)
  await page.waitForTimeout(1500)
  const t1 = await video.evaluate((el) => (el as HTMLVideoElement).currentTime)
  expect(t1).toBeGreaterThan(t0)
  console.log(`[live] ${size.w}x${size.h} | currentTime ${t0.toFixed(2)}s -> ${t1.toFixed(2)}s`)
  await page.getByTestId('live-video').scrollIntoViewIfNeeded()
  await page.waitForTimeout(400)
  await page.screenshot({ path: 'test-results/live-camera-evidence.png' })
})
