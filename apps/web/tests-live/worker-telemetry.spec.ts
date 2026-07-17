import { expect, test } from '@playwright/test'

// A telemetria do heartbeat era descartada pela API: latência, fila e regras inativas
// existiam no worker e não chegavam a ninguém. Este teste exige que cheguem à tela.
test('aba Workers mostra a telemetria real do heartbeat', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })
  await page.getByTestId('site-card-site-demo').click()
  await page.getByRole('button', { name: /^Workers/ }).first().click()

  // O worker do seed aparece sem ter sido registrado nesta sessão (inventário real).
  const telemetria = page.getByTestId('worker-telemetry-edge-worker-demo')
  await expect(telemetria).toBeVisible({ timeout: 20000 })
  await expect(page.getByText('dev-client-id')).toBeVisible()
  await expect(page.getByText('Online').first()).toBeVisible()

  const texto = await telemetria.innerText()
  expect(texto).toMatch(/ms/)
  console.log(`[telemetria] ${texto.replace(/\n/g, ' ')}`)
})
