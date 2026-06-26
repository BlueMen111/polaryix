# Nova Arquitetura do Polaryix — Assistente Inteligente de BI

## Visão Geral

O Polaryix foi transformado de um simples gerador de dashboards para um **Assistente Inteligente de Business Intelligence (BI)**. O foco deixou de ser o arquivo enviado e passou a ser o **problema de negócio** que o usuário deseja resolver.

---

## Fluxo Atual vs. Novo Fluxo

### ❌ Fluxo Antigo
```
Upload → Analisar CSV → Mostrar KPIs → Criar Dashboard
```

### ✅ Novo Fluxo
```
Sessão de Análise
    ↓
Upload de múltiplos arquivos
    ↓
Descrição do negócio
    ↓
Objetivo da análise
    ↓
Leitura e relacionamento dos dados
    ↓
IA interpreta o contexto
    ↓
Planejamento do Dashboard
    ↓
Construção do Dashboard
    ↓
Dashboard Inteligente
```

---

## Conceito de "Analysis Session"

Uma `Analysis Session` é uma entidade intermediária que representa todo o contexto da análise.

### Estrutura de Dados

```typescript
{
  id: string;                    // UUID único
  title: string;                 // Título da análise
  description?: string;          // Descrição do negócio em linguagem natural
  objective?: string;            // Objetivo da análise
  objective_category?: string;   // Categoria (comercial, financeiro, etc.)
  files: AnalysisSessionFile[];  // Lista de arquivos enviados
  status: AnalysisSessionStatus; // Status do processamento
  processing_steps: string[];    // Etapas concluídas
  dashboard_specification?: DashboardSpecification; // Especificação do dashboard
  dashboard_id?: string;         // ID do dashboard gerado
  created_at: datetime;
  updated_at: datetime;
  completed_at?: datetime;
}
```

### Status Possíveis

- `draft` — Criada, aguardando arquivos e descrição
- `ready` — Todas as informações fornecidas, pronta para processar
- `processing` — IA está analisando os dados
- `completed` — Dashboard gerado com sucesso
- `failed` — Erro no processamento
- `archived` — Sessão arquivada

---

## Upload de Múltiplos Arquivos

### Formatos Suportados

- `.csv` — Planilhas CSV
- `.xlsx` / `.xls` — Excel
- `.json` — JSON
- `.txt` — Texto
- `.parquet` — Parquet

### Limites

- Tamanho máximo: 100MB por arquivo
- Múltiplos arquivos por sessão
- Validação de segurança automática

### Armazenamento

1. **Quarentena** — Arquivos são salvos temporariamente para validação
2. **Validação** — Verificação de segurança (malware, extensões perigosas)
3. **Processamento** — Leitura e profiling dos dados
4. **Vinculação** — Arquivo é anexado à sessão com metadados

---

## Descrição do Negócio

A descrição em linguagem natural é uma das etapas mais importantes. Ela fornece contexto que dificilmente pode ser inferido apenas analisando os dados.

### Exemplo de Descrição

```
Esses arquivos representam uma concessionária.

• clientes.csv: Cadastro de clientes com dados demográficos
• vendas.csv: Histórico de vendas dos últimos 3 anos
• estoque.csv: Veículos disponíveis e status
• comentarios.csv: Avaliações e feedbacks dos clientes

Gostaria de entender:
• quais carros vendem mais
• ticket médio
• desempenho dos vendedores
• sazonalidade
• satisfação dos clientes
```

### Benefícios

- Contextualiza os dados
- Permite relacionamentos entre arquivos
- Direciona a IA para os indicadores corretos
- Personaliza o dashboard para o negócio

---

## Objetivo da Análise

Além da descrição, o usuário informa o objetivo principal.

### Categorias Disponíveis

- **Comercial** — Vendas, clientes, produtos
- **Financeiro** — Receita, custos, lucratividade
- **Marketing** — Campanhas, conversão, engajamento
- **RH** — Funcionários, turnover, desempenho
- **Operacional** — Processos, produtividade, eficiência
- **Logística** — Estoque, transporte, entregas
- **Atendimento** — Suporte, satisfação, tickets
- **Outro** — Outros objetivos

### Exemplos de Objetivos

- "Quero entender por que minhas vendas diminuíram"
- "Quero descobrir quais clientes são mais lucrativos"
- "Quero acompanhar indicadores financeiros mensais"
- "Quero analisar comentários negativos para melhorar o atendimento"
- "Quero construir um dashboard executivo para reuniões de diretoria"

---

## Processamento Inteligente

### Etapas do Processamento

1. **🧠 Entendendo seu negócio** — IA interpreta a descrição e objetivo
2. **📖 Lendo arquivos** — Leitura e validação de todos os arquivos
3. **🔗 Relacionando dados** — Identificação de relacionamentos entre datasets
4. **📊 Detectando indicadores** — IA sugere KPIs relevantes
5. **📋 Planejando Dashboard** — Criação da especificação estruturada
6. **🎨 Construindo gráficos** — Geração dos componentes visuais
7. **✨ Finalizando** — Preparação para exibição

### Dashboard Specification

Antes de renderizar qualquer componente visual, a IA gera uma especificação estruturada:

```json
{
  "title": "Dashboard Comercial",
  "description": "Análise de vendas e desempenho",
  "sections": [
    {
      "name": "Visão Geral",
      "widgets": [
        {
          "type": "kpi",
          "title": "Receita Total",
          "metric": "sum",
          "field": "valor_venda"
        },
        {
          "type": "kpi",
          "title": "Ticket Médio",
          "metric": "average",
          "field": "valor_venda"
        }
      ]
    },
    {
      "name": "Vendas",
      "widgets": [
        {
          "type": "line_chart",
          "title": "Evolução Mensal",
          "x": "data_venda",
          "y": "valor_venda"
        }
      ]
    }
  ]
}
```

### Benefícios

- Separação entre lógica da IA e renderização
- Facilita alterações futuras
- Permite versionamento de dashboards
- Habilita preview antes da geração

---

## API Endpoints

### Analysis Sessions

```
POST   /api/v1/analysis-sessions              Criar nova sessão
GET    /api/v1/analysis-sessions              Listar sessões
GET    /api/v1/analysis-sessions/{id}         Detalhes da sessão
PATCH  /api/v1/analysis-sessions/{id}         Atualizar sessão
DELETE /api/v1/analysis-sessions/{id}         Deletar sessão
```

### Files

```
POST   /api/v1/analysis-sessions/{id}/files  Upload de arquivo
```

### Progress

```
GET    /api/v1/analysis-sessions/{id}/progress  Progresso do processamento
```

---

## Frontend Components

### Páginas

- `/` — Landing page com proposta de valor
- `/upload` — Fluxo de criação de análise
- `/datasets` — Lista de análises
- `/datasets/[id]` — Detalhes da análise

### Componentes Principais

- **AnalysisSessionForm** — Formulário multi-etapas
  - Etapa 1: Informações do negócio
  - Etapa 2: Upload de arquivos
  - Etapa 3: Processamento
  - Etapa 4: Conclusão

- **SessionProgress** — Visualização do progresso
  - Barra de progresso
  - Etapas visuais com ícones
  - Detalhes do processamento
  - Animações e feedback visual

---

## Backend Services

### Domain Layer

- `AnalysisSession` — Entidade principal
- `AnalysisSessionFile` — Metadados de arquivo
- `DashboardSpecification` — Especificação do dashboard
- Enums: `AnalysisSessionStatus`, `AnalysisObjectiveCategory`

### Infrastructure Layer

- `AnalysisSessionsStorage` — Persistência de sessões
- `LocalStorage` — Armazenamento de arquivos
- `FileSecurity` — Validação de segurança

### Data Processing

- `DatasetReader` — Leitura de múltiplos formatos
- `DatasetProfiler` — Análise de estrutura dos dados
- (Futuro) `DataRelationMapper` — Relacionamento entre datasets

### AI Integration

- (Futuro) `BusinessContextAnalyzer` — Interpretação da descrição
- (Futuro) `DashboardSpecGenerator` — Geração de especificação
- (Futuro) `KPIRecommender` — Sugestão de indicadores

---

## Roadmap de Implementação

### ✅ Concluído

- [x] Estrutura de Analysis Session
- [x] Upload múltiplo de arquivos
- [x] Descrição do negócio
- [x] Objetivo da análise
- [x] Tela de progresso visual
- [x] UX melhorada do fluxo

### 🔄 Em Desenvolvimento

- [ ] Mecanismo de relacionamento entre datasets
- [ ] Integração com IA para interpretação de contexto
- [ ] Geração automática de Dashboard Specification
- [ ] Dashboard Builder que interpreta a especificação

### 📋 Planejado

- [ ] Preview da proposta antes de gerar
- [ ] Edição manual da especificação
- [ ] Versionamento de dashboards
- [ ] Compartilhamento de sessões
- [ ] Histórico de processamento
- [ ] Métricas de uso da IA
- [ ] Sugestões inteligentes de análises

---

## Benefícios da Nova Arquitetura

1. **Múltiplas fontes de dados** — Análise integrada de vários arquivos
2. **Contexto do negócio** — IA entende o cenário do cliente
3. **Dashboards personalizados** — Soluções relevantes para cada necessidade
4. **Relacionamento de dados** — Conexões entre diferentes fontes
5. **Experiência superior** — Fluxo intuitivo e profissional
6. **Percepção de inteligência** — Transparência no processamento
7. **Extensibilidade** — Fácil integração com modelos de IA
8. **Personalização** — Dashboards por área do negócio

---

## Visão de Longo Prazo

O objetivo final é tornar o Polaryix um **Copilot de Business Intelligence**, capaz de:

- Compreender o contexto do cliente
- Interpretar diferentes fontes de dados
- Sugerir indicadores estratégicos
- Construir dashboards personalizados
- Auxiliar na tomada de decisão baseada em dados

Nesse modelo, o upload de arquivos é apenas o ponto de partida. O verdadeiro diferencial competitivo é a capacidade de entender o negócio do cliente e transformar dados brutos em conhecimento acionável.

---

## Próximos Passos

1. Implementar `DataRelationMapper` para relacionar múltiplos datasets
2. Integrar com modelo de IA (OpenAI, Claude, etc.) para interpretação
3. Criar `DashboardSpecGenerator` para gerar especificações automáticas
4. Desenvolver `DashboardBuilder` que renderiza a especificação
5. Adicionar tela de preview e edição da proposta
6. Implementar sistema de versionamento

---

**Última atualização:** 26/06/2026
**Versão:** 1.0.0