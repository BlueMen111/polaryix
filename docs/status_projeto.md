# Polaryix — Estado Atual do Projeto

## Objetivo

Polaryix é um SaaS para análise segura de datasets enviados pelos usuários.

Formatos planejados:

- CSV
- XLS
- XLSX
- JSON
- TXT
- Parquet

O sistema deverá detectar tipos de colunas, datas, moedas, porcentagens, localidades, relacionamentos, duplicatas, inconsistências, valores ausentes e sugestões de limpeza.

Também deverá gerar KPIs, gráficos, dashboards, insights, estatísticas e relatórios.

---

## Stack definida

Backend:

- Python
- FastAPI
- Pydantic
- Pandas
- Polars
- DuckDB

Planejado:

- PostgreSQL
- SQLAlchemy
- Alembic
- Redis
- Celery
- Docker
- Nginx
- GitHub Actions

Frontend planejado:

- Next.js
- React
- TypeScript
- Plotly
- Apache ECharts

---

## Estrutura criada

A estrutura inicial foi criada dentro de:

```text
D:\Python\polaryix

---

## Fase 3 implementada

A Fase 3 adicionou detecção semântica inicial de tipos de coluna.

Arquivo criado:

```text
apps/api/app/data_processing/profiling/column_type_detector.py