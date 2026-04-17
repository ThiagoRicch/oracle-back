# Setup de Cron Externo (Render Free)

Este projeto suporta dois modos de agendamento:

1. `ENABLE_INTERNAL_SCHEDULER=true`: usa APScheduler dentro da API.
2. `ENABLE_INTERNAL_SCHEDULER=false`: recomendado no Render Free, usando cron externo para chamar endpoints internos.

## Endpoints internos

- `POST /internal/jobs/daily`
- `POST /internal/jobs/monthly`
- `POST /internal/jobs/weather`

## Autenticacao

Defina `INTERNAL_CRON_SECRET` no ambiente da API e envie um dos headers abaixo:

- `X-Internal-Secret: <INTERNAL_CRON_SECRET>`
- `Authorization: Bearer <INTERNAL_CRON_SECRET>`

## Exemplo de chamadas

```bash
curl -X POST "https://SEU-BACKEND.onrender.com/internal/jobs/daily" \
  -H "X-Internal-Secret: SEU_SEGREDO"

curl -X POST "https://SEU-BACKEND.onrender.com/internal/jobs/monthly" \
  -H "X-Internal-Secret: SEU_SEGREDO"

curl -X POST "https://SEU-BACKEND.onrender.com/internal/jobs/weather" \
  -H "X-Internal-Secret: SEU_SEGREDO"
```

## Frequencias sugeridas no cron

- `daily`: a cada minuto (o proprio backend decide enviar apenas no horario local 23:50 por continente)
- `monthly`: a cada minuto (envio apenas no ultimo dia do mes, 23:50 local)
- `weather`: a cada 30 minutos

## Idempotencia persistente

A idempotencia agora usa a tabela `report_dispatch_log` no Supabase.

Execute o SQL em `sql/report_dispatch_log.sql` no SQL Editor do Supabase antes de ativar os jobs.
