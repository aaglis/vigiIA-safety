import { expect, test } from '@playwright/test'

// Editar era impossível pela tela: a API já tinha PATCH e a UI só criava. Zona com
// polígono errado não tinha conserto. Este teste cobre o caminho inteiro.
test('editar zona: abre com o desenho salvo e persiste a mudanca', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })
  await page.getByTestId('site-card-site-demo').click()
  await page.getByRole('button', { name: /^Zonas/ }).first().click()

  await page.getByTestId('zone-edit-zone-demo-01').click()
  // O título do modal é rotulado por aria-labelledby, não é um heading.
  const dialog = page.getByRole('dialog', { name: 'Editar zona' })
  await expect(dialog).toBeVisible()

  // O nome salvo veio preenchido (não é um form em branco). Não fixa o valor: o teste
  // roda repetidas vezes e precisa partir do que estiver lá.
  const nome = dialog.getByLabel('Nome da área')
  const nomeOriginal = await nome.inputValue()
  expect(nomeOriginal.length).toBeGreaterThan(0)

  // O polígono salvo voltou para o editor: 4 pontos arrastáveis.
  const pontos = dialog.getByRole('button', { name: /^Ponto \d/ })
  await expect(pontos).toHaveCount(4)

  const nomeNovo = `Corredor da Fiação ${Date.now()}`
  await nome.fill(nomeNovo)
  await dialog.getByRole('button', { name: 'Salvar zona' }).click()
  await expect(dialog).toHaveCount(0)

  // Persistiu de verdade: sobrevive a um reload.
  await expect(page.getByText(nomeNovo)).toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: /^Zonas/ }).first().click()
  await expect(page.getByText(nomeNovo)).toBeVisible()

  // Devolve a zona ao nome original: o teste não pode deixar rastro no ambiente.
  await page.getByTestId('zone-edit-zone-demo-01').click()
  const dialog2 = page.getByRole('dialog', { name: 'Editar zona' })
  await dialog2.getByLabel('Nome da área').fill(nomeOriginal)
  await dialog2.getByRole('button', { name: 'Salvar zona' }).click()
  await expect(dialog2).toHaveCount(0)
  console.log(`[edicao] zona editada com poligono salvo (4 pontos), persistida e restaurada para "${nomeOriginal}"`)
})
