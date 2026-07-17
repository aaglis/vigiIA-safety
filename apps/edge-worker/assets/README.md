# Vídeos de amostra do edge worker (dev)

Coloque aqui um vídeo curto que faça o papel de câmera em localhost.

- `sample-ppe.mp4` — clipe com pessoas com/sem capacete e alguém entrando numa área
  restrita. O seed aponta `camera-demo-01.stream_identifier` para `/assets/sample-ppe.mp4`
  (via `DEMO_CAMERA_STREAM` no compose), e o worker abre esse vídeo com OpenCV.

Em produção o mesmo caminho de código abre uma câmera RTSP ao vivo — só o
`stream_identifier` muda (de um arquivo para `rtsp://…`).

Os vídeos não são versionados (podem ser grandes / ter imagem de pessoas — LGPD).
