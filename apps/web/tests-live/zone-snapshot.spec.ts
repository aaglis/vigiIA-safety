import { expect, test } from '@playwright/test'

// O editor de zona tem que conseguir um frame da câmera AO VIVO. Antes só existia frame
// se a câmera já tivesse gerado incidente com evidência — justamente o que não acontece
// numa câmera recém-cadastrada, que é quando se desenha a zona.
test('editor de zona pega frame da camera ao vivo (sem depender de incidente)', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })

  await page.getByTestId('site-card-site-demo').click()
  await expect(page).toHaveURL(/\/sites\/site-demo$/)

  await page.getByRole('button', { name: /^Novo/ }).first().click()
  await page.getByRole('menuitem', { name: /zona/i }).first().click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()

  // O fundo do editor é uma imagem real da câmera, não a grade vazia.
  const frame = dialog.getByAltText('Frame da câmera')
  await expect(frame).toBeVisible({ timeout: 30000 })
  const box = await frame.boundingBox()
  expect(box!.width).toBeGreaterThan(0)
  const src = await frame.getAttribute('src')
  console.log(`[zona] frame carregado: ${src?.slice(0, 24)}... (${Math.round(box!.width)}x${Math.round(box!.height)}px)`)
})
