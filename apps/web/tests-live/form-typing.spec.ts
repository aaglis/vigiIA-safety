import { expect, test } from '@playwright/test'

// Regressão real: o effect de foco do Modal dependia de `onClose` (arrow inline, nova a
// cada render), então cada tecla re-rodava o effect e jogava o foco no botão Fechar —
// só a primeira letra entrava. Este teste falha se isso voltar.
test('campos do modal aceitam texto continuo sem perder o foco', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })

  await page.getByRole('button', { name: /^Novo/ }).first().click()
  await page.getByRole('menuitem').first().click()

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  const input = dialog.locator('input').first()
  await input.click()

  const texto = 'Planta Sorocaba'
  await page.keyboard.type(texto, { delay: 60 })
  await expect(input).toHaveValue(texto)
  expect(await input.evaluate((el) => el === document.activeElement)).toBe(true)
  console.log(`[form] digitado "${texto}" e o campo manteve foco`)
})
