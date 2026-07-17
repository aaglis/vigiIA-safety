import { expect, test } from '@playwright/test'

// O modal de zona é o de conteúdo mais alto (editor de polígono + campos). Se ele passar
// da viewport, os botões de salvar somem da tela — foi o bug reportado.
test('modal com muito conteudo cabe na tela e rola por dentro', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 620 })
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })

  await page.getByRole('button', { name: /^Novo/ }).first().click()
  await page.getByRole('menuitem', { name: /zona/i }).or(page.getByRole('button', { name: /Nova zona/i })).first().click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()

  const viewport = page.viewportSize()!
  const box = (await dialog.boundingBox())!
  expect(box.height).toBeLessThanOrEqual(viewport.height)
  expect(box.y).toBeGreaterThanOrEqual(-1)
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1)

  // O botão de salvar tem que estar alcançável dentro do modal.
  const submit = dialog.getByRole('button', { name: /Criar|Salvar/i }).last()
  await submit.scrollIntoViewIfNeeded()
  await expect(submit).toBeInViewport()
  console.log(`[modal] altura ${Math.round(box.height)}px em viewport de ${viewport.height}px`)
})
