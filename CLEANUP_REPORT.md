# Cleanup Report

Data: 2026-06-28

## Escopo

Esta limpeza foi conduzida com a regra de preservar funcionamento acima de reduzir tamanho. Foram removidos apenas arquivos gerados automaticamente e sem referencia direta no codigo do projeto.

Pastas analisadas com foco em limpeza segura:

- `apps/api/app`
- `apps/api/tests`
- `apps/web/tsconfig.tsbuildinfo`

Pastas mantidas fora da limpeza automatica:

- `.venv`, `.venv-1` e `apps/api/.venv`: ambientes virtuais. Nao removidos por poderem ser usados pelo terminal atual.
- `apps/api/storage`: contem usuarios, sessoes, historico, datasets, dashboards e outputs de conversao. Nao removido.
- `apps/web/.next`: build atual do Next.js. Nao removido nesta etapa de limpeza documental para evitar deixar o frontend sem build local.
- Arquivos de teste manuais na raiz: mantidos por falta de certeza absoluta de desuso.

## Arquivos removidos

Removidos apenas caches gerados automaticamente:

- `apps/api/app/**/__pycache__`
  - Motivo: cache Python gerado automaticamente.
- `apps/api/app/**/*.pyc`
  - Motivo: bytecode Python gerado automaticamente.
- `apps/api/tests/**/__pycache__`
  - Motivo: cache Python gerado automaticamente por testes.
- `apps/api/tests/**/*.pyc`
  - Motivo: bytecode Python gerado automaticamente por testes.
- `apps/web/tsconfig.tsbuildinfo`
  - Motivo: cache incremental do TypeScript, recriavel pelo build.

## Arquivos mantidos

- `apps/api/storage/**`: mantido porque contem dados reais, historico, usuarios, sessoes, uploads, dashboards e downloads.
- `apps/api/polaryix_api.egg-info/**`: mantido por ser metadata de instalacao/editable package; pode ser recriado, mas nao foi removido nesta etapa por estar dentro do pacote Python.
- `apps/web/.next/**`: mantido para preservar build atual.
- `.venv/**`, `.venv-1/**`, `apps/api/.venv/**`: mantidos por serem ambientes de execucao locais.
- `test_upload.py`, `test_multi_upload.py`, `test_profiler.py`, `check_session.py`, `verify_session.py`: mantidos por parecerem scripts manuais de validacao e nao haver certeza de desuso.
- `Novo(a) Documento de Texto.txt`: mantido por ser arquivo criado pelo usuario.

## Candidatos seguros identificados e removidos

- `apps/api/app/**/__pycache__`
- `apps/api/app/**/*.pyc`
- `apps/api/tests/**/__pycache__`
- `apps/api/tests/**/*.pyc`
- `apps/web/tsconfig.tsbuildinfo`

Motivo: caches Python e cache incremental TypeScript. Sao gerados automaticamente e nao sao importados nem referenciados pelo sistema.

## Espaco liberado

- Arquivos removidos: 69.
- Diretorios de cache removidos: 31.
- Espaco recuperado: 365057 bytes, aproximadamente 356 KB.

## Melhorias realizadas

- Criado `DOCUMENTATION.md` com visao geral, arquitetura, stack, estrutura, fluxos, premium, auth, API, fila, historico, limpeza automatica, variaveis e TODO.
- Criado este relatorio para registrar decisoes de limpeza.
- Removidos caches Python e cache incremental TypeScript sem tocar em storage, rotas, frontend ativo, backend ativo ou configuracoes.

## Validacoes apos limpeza

Executado:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest apps.api.tests.unit.test_premium_history apps.api.tests.unit.test_converter_compatibility
npm run build:clean
```

Resultado:

- 17 testes backend passaram.
- Build limpo do frontend passou.
- Checagem final nao encontrou `__pycache__`, `.pyc`, `.pyo` ou `tsconfig.tsbuildinfo` nos alvos limpos.
