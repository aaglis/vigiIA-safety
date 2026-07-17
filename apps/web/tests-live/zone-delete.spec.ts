import { expect, test } from '@playwright/test'

// Excluir zona com histórico é barrado (409): o incidente guarda o zone_id e a auditoria
// ficaria órfã. O usuário precisa entender o motivo, não ver um erro cru.
test('excluir zona com incidentes explica por que nao pode', async ({ page }) => {
  page.on('dialog', (d) => void d.accept())
  await page.goto('/dashboard')
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })
  await page.getByTestId('site-card-site-demo').click()
  await page.getByRole('button', { name: /^Zonas/ }).first().click()

  await page.getByTestId('zone-delete-zone-demo-01').click()

  await expect(page.getByText(/já gerou incidentes e não pode ser excluída/)).toBeVisible()
  // A zona continua lá: nada foi apagado.
  await expect(page.getByTestId('zone-delete-zone-demo-01')).toBeVisible()
  console.log('[exclusao] zona com historico protegida, motivo explicado ao usuario')
})
