import { z } from 'zod'

/**
 * Regras dos formulários de Operações num lugar só.
 *
 * Isto NÃO é segurança: a autoridade é o backend (pydantic `extra="forbid"`,
 * `validate_stream_identifier` por ambiente, RBAC e CSRF). Um POST direto na API pula
 * este arquivo inteiro. O que ganhamos aqui é dizer ao usuário o que está errado no
 * campo certo, antes de gastar um round-trip, e derivar o payload do schema.
 */

const status = z.enum(['active', 'inactive', 'suspended'])

export const siteFormSchema = z.object({
  name: z.string().trim().min(2, 'Informe o nome da unidade (mínimo 2 caracteres).').max(120, 'Nome muito longo.'),
  address: z.string().trim().max(200, 'Endereço muito longo.').optional().or(z.literal('')),
  status,
})

// Espelha `LIVE_STREAM_SOURCE_TYPES` do backend: câmera é sempre um stream ao vivo.
// Em dev a API ainda aceita arquivo, mas o formulário ensina o formato de produção.
const STREAM_URL = /^(rtsp|rtmp):\/\/[^\s/]+(\/[^\s]*)?$/i

export const cameraFormSchema = z.object({
  site_id: z.string().min(1, 'Escolha a unidade.'),
  name: z.string().trim().min(2, 'Informe o nome da câmera (mínimo 2 caracteres).').max(120, 'Nome muito longo.'),
  stream_identifier: z.string().superRefine((value, ctx) => {
    const url = (value ?? '').trim()
    if (!url) {
      ctx.addIssue({ code: 'custom', message: 'Informe a URL do stream.' })
      return
    }
    if (!STREAM_URL.test(url)) {
      ctx.addIssue({ code: 'custom', message: 'Use uma URL de câmera ao vivo, como rtsp://10.0.0.20:554/live.' })
    }
  }),
  status,
})

export const zoneFormSchema = z.object({
  site_id: z.string().min(1, 'Escolha a unidade.'),
  camera_id: z.string().min(1, 'Escolha a câmera desta zona.'),
  // Sem nome, o operador vê o id cru ("zone-demo-01") no alerta e na lista.
  name: z.string().trim().min(2, 'Dê um nome à área, como ela é conhecida na planta.').max(120, 'Nome muito longo.'),
  zone_type: z.enum(['restricted', 'ppe', 'access']),
  status,
  // O worker usa coordenadas normalizadas [0..1]; menos de 3 pontos não fecha uma área.
  polygon: z
    .array(z.tuple([z.number().min(0).max(1), z.number().min(0).max(1)]))
    .refine((points) => points.length === 0 || points.length >= 3, { message: 'Marque ao menos 3 pontos para fechar a área.' }),
})

export const edgeWorkerFormSchema = z.object({
  site_id: z.string().min(1, 'Escolha a unidade.'),
  name: z.string().trim().min(2, 'Informe o nome do worker.').max(120, 'Nome muito longo.'),
  allowed_camera_ids: z.array(z.string()).min(1, 'Selecione ao menos uma câmera para o worker.'),
})

export const workerConfigFormSchema = z.object({
  client_id: z.string().trim().min(1, 'Informe o client_id.'),
  api_key: z.string().trim().min(1, 'Informe a api_key.'),
})

export type SiteFormValues = z.infer<typeof siteFormSchema>
export type CameraFormValues = z.infer<typeof cameraFormSchema>
export type ZoneFormValues = z.infer<typeof zoneFormSchema>
export type EdgeWorkerFormValues = z.infer<typeof edgeWorkerFormSchema>
export type WorkerConfigFormValues = z.infer<typeof workerConfigFormSchema>
