import { expect, test } from '@playwright/test'

// Exige o edge worker rodando (docker compose --profile cv up -d edge-worker):
// só passa se as caixas da CV real chegarem no navegador enquanto o vídeo roda.
test('deteccoes da CV aparecem sobre o video ao vivo', async ({ page }) => {
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

  // O overlay só renderiza quando chega análise do worker via websocket.
  await expect(page.getByTestId('detection-overlay')).toBeVisible({ timeout: 45000 })
  const boxes = await page.getByTestId('detection-overlay').locator('rect').count()
  expect(boxes).toBeGreaterThan(0)
  console.log(`[overlay] ${boxes} caixa(s) desenhada(s) sobre o video ao vivo`)
  await page.getByTestId('live-video').scrollIntoViewIfNeeded()
  await page.waitForTimeout(400)
  await page.screenshot({ path: 'test-results/overlay-evidence.png' })
})
