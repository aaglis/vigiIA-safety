import { expect, test } from '@playwright/test'

// Trocar a URL da câmera troca a imagem, mas as zonas continuam nas mesmas coordenadas —
// passam a marcar outro lugar. O usuário precisa ser avisado antes de salvar.
test('editar camera avisa sobre as zonas desenhadas sobre ela', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })
  await page.getByTestId('site-card-site-demo').click()

  await page.getByTestId('camera-edit-camera-demo-01').click()
  const dialog = page.getByRole('dialog', { name: 'Editar câmera' })
  await expect(dialog).toBeVisible()

  await expect(dialog.getByText(/zonas desenhadas sobre a imagem desta câmera/)).toBeVisible()
  await expect(dialog.getByText(/o desenho continua nas mesmas coordenadas/)).toBeVisible()
  // A URL atual veio preenchida (é edição, não cadastro em branco).
  await expect(dialog.getByLabel('URL do stream')).toHaveValue(/^rtsp:\/\//)
  console.log('[camera] aviso das zonas exibido ao editar a URL')
})
