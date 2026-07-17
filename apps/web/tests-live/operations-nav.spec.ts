import { expect, test } from '@playwright/test'

test('operacoes navega site -> camera com URL propria e deep-link funciona', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(async () => {
    await page.getByRole('button', { name: /^Operações\/Câmeras/ }).first().click()
    await expect(page).toHaveURL(/\/dashboard\/operations$/, { timeout: 2000 })
  }).toPass({ timeout: 25000 })

  // nivel 1: lista de sites
  await expect(page.getByTestId('site-card-site-demo')).toBeVisible()

  // nivel 2: site tem URL propria
  await page.getByTestId('site-card-site-demo').click()
  await expect(page).toHaveURL(/\/dashboard\/operations\/sites\/site-demo$/)
  await expect(page.getByRole('heading', { name: 'Planta Demo' })).toBeVisible()

  // nivel 3: camera tem URL propria
  await page.getByTestId('camera-open-camera-demo-01').click()
  await expect(page).toHaveURL(/\/sites\/site-demo\/cameras\/camera-demo-01$/)
  await expect(page.getByTestId('live-video')).toBeVisible()

  // deep-link: recarregar na URL da camera abre a camera (antes voltava pro Dashboard)
  await page.reload()
  await expect(page).toHaveURL(/\/sites\/site-demo\/cameras\/camera-demo-01$/)
  await expect(page.getByTestId('live-video')).toBeVisible()

  // voltar do navegador respeita a hierarquia
  await page.goBack()
  await expect(page).toHaveURL(/\/dashboard\/operations\/sites\/site-demo$/)
  // link colado direto na barra de endereco (sessao ja existente) tambem abre a camera
  await page.goto('/dashboard/operations/sites/site-demo/cameras/camera-demo-01')
  await expect(page).toHaveURL(/\/sites\/site-demo\/cameras\/camera-demo-01$/)
  await expect(page.getByTestId('live-video')).toBeVisible()

  console.log('[nav] sites -> site -> camera + deep-link (reload e URL colada) + voltar: ok')
})
