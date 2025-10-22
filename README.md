# 📊 Sebrae Nacional - Ecossistema de Inovação

Este projeto é patrocinado pelo **Sebrae Nacional** e tem o objetivo de identificar falhas de mercado no ecossistema de inovação do Brasil e propor políticas públicas que possam atacar essas falhas e reduzí-las, melhorando o ecossistema e corrigindo essas imperfeições.

## 🎯 Objetivo

O projeto visa **mapear sistematicamente** as principais falhas de mercado no ecossistema brasileiro de inovação e desenvolver **políticas públicas efetivas** para solucioná-las, contribuindo para um ambiente mais favorável ao empreendedorismo e inovação.

## 🚀 Metodologia

Esse mapeamento ocorrerá por meio de pesquisas bibliográficas e em fontes confiáveis na internet, entrevista com especialistas e membros do ecossistema de inovação no Brasil além de análises embasadas na vasta experiência dos autores nesta temática.

## 📋 Etapas do Projeto

O projeto está estruturado em **5 etapas** principais:

### 1️⃣ Levantamento de Falhas de Mercado  (Realizado)
- ✅ **Concluído** - Base de dados com **50 falhas** identificadas
- 📊 **7 pilares** de categorização
- 🔍 **Banco SQLite** (`falhas_mercado_v1.db`)

### 2️⃣ Pesquisa de Políticas Públicas (Em andamento)
- 🌍 **Pesquisa global** de boas práticas
- 📚 **Estudos de caso** internacionais
- 💡 **Soluções comprovadas** para cada tipo de falha

### 3️⃣ Priorização das Falhas
- 📈 **Critérios de relevância** definidos
- ⚖️ **Análise de impacto** no ecossistema
- 🎯 **Seleção das falhas mais críticas**

### 4️⃣ Desenvolvimento de Propostas
- 📝 **Políticas públicas detalhadas**
- 🇧🇷 **Adaptação ao contexto brasileiro**
- 🎨 **Soluções customizadas** para cada falha

### 5️⃣ Plano de Advocacy
- 🗣️ **Estratégias de comunicação**
- 🤝 **Parcerias institucionais**
- 📢 **Promoção da implementação**

## 🏛️ Os 7 Pilares do Ecossistema

As falhas de mercado estão organizadas em **7 pilares estratégicos**:

| Pilar | Foco | Descrição |
|-------|------|-----------|
| **1. Talento** | Recursos Humanos | Formação, atração e retenção de talentos |
| **2. Densidade** | Concentração | Polos de inovação e networking |
| **3. Impacto e Diversidade** | Inclusão | Diversidade e impacto social |
| **4. Acesso a Mercado** | Comercial | Barreiras de entrada e expansão |
| **5. Cultura** | Comportamental | Cultura empreendedora e inovação |
| **6. Regulação** | Legal | Marco regulatório e burocracia |
| **7. Capital** | Financeiro | Financiamento e investimento |

## 🏗️ Base de Dados

### Estrutura Atual
- **Arquivo:** `falhas_mercado_v1.db`
- **Formato:** SQLite 3.x
- **Status:** Não versionado (sem Git)

### Schema da Tabela
```sql
CREATE TABLE falhas_mercado (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    pilar TEXT NOT NULL,
    descricao TEXT NOT NULL,
    dica_busca TEXT NOT NULL
);
```
## Tecnologias Utilizadas
- Phyton 3.x
- SQLite 3.x
- Jina AI
- Perplexity AI
- Tavily API
- Serper API
- Claude Code
- Claude Chat
- Kibo UI components (based on Shadcn)
- Tailwind CSS 


## 🚀 Como Usar

### Pré-requisitos
- Python 3.x instalado
- SQLite 3.x instalado
- Variáveis de ambiente configuradas (`.env`)

### Comandos Úteis

```bash
# Ver todas as falhas
sqlite3 falhas_mercado_v1.db "SELECT * FROM falhas_mercado;"

# Filtrar por pilar
sqlite3 falhas_mercado_v1.db "SELECT * FROM falhas_mercado WHERE pilar = '1. Talento';"

# Contar registros
sqlite3 falhas_mercado_v1.db "SELECT COUNT(*) FROM falhas_mercado;"

# Exportar para CSV
sqlite3 falhas_mercado_v1.db -header -csv "SELECT * FROM falhas_mercado;" > falhas.csv
```

## ⚙️ Configuração

## 📊 Estatísticas do Projeto

- 📋 **50+ falhas de mercado** identificadas
- 🏛️ **7 pilares** de categorização
- 🌍 **Pesquisa global** de soluções
- 🇧🇷 **Foco no contexto brasileiro**

## 🎯 Impacto Esperado

- 🔍 **Identificação sistemática** de problemas
- 💡 **Propostas de soluções** baseadas em evidências
- 🤝 **Melhoria do ecossistema** de inovação
- 📈 **Aumento da competitividade** brasileira

## ⚠️ Notas Importantes

- 📊 **Base de dados ativa** - em constante desenvolvimento
- 🔑 **Credenciais sensíveis** - arquivo `.env` protegido
- 🏷️ **Nomenclatura padronizada** - pilares e falhas numerados

---

**Projeto:** Sebrae Nacional - Ecossistema de Inovação
**Status:** Em desenvolvimento (2025)
**Mantenedor:** Sebrae Nacional
**Realizador** ABGI em parceria com 10K DIGITAL
**Cooderador Técnico:** Felipe Matos

