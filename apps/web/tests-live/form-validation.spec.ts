import { expect, test } from '@playwright/test'

// A validação do cliente NÃO é segurança (o backend é a autoridade: pydantic extra=forbid,
// validate_stream_identifier, RBAC, CSRF). Ela existe para dizer o que está errado no campo
// certo, sem gastar um round-trip. Este teste prova que ela faz isso e não chama a API.
test('formulario invalido mostra erro no campo e nao chama a API', async ({ page }) => {
  const chamadas: string[] = []
  page.on('request', (r) => {
    if (r.method() === 'POST' && r.url().includes('/operations/cameras')) chamadas.push(r.url())
  })

  await page.goto('/dashboard')
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })

  await page.getByRole('button', { name: /^Novo/ }).first().click()
  await page.getByRole('menuitem', { name: /câmera/i }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()

  // URL de câmera inválida (não é rtsp/rtmp) + nome vazio
  await dialog.getByLabel('URL do stream').fill('nao-e-uma-url')
  await dialog.getByRole('button', { name: /Criar câmera/ }).click()

  await expect(dialog.getByText(/Use uma URL de câmera ao vivo/)).toBeVisible()
  await expect(dialog.getByText(/Informe o nome da câmera/)).toBeVisible()
  expect(chamadas).toHaveLength(0)
  console.log(`[validacao] erro mostrado no campo | POSTs para a API: ${chamadas.length}`)
})
