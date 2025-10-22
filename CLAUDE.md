# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Sebrae Nacional** research project focused on identifying market failures in Brazil's innovation ecosystem and proposing public policies to address them. The project is implemented by ABGI in partnership with 10K DIGITAL.

**Current Status:** Phase 2 (Policy Research) - IN PROGRESS
- Phase 1 (Market Failures Identification): COMPLETED - 50 failures mapped
- Phases 3-5 (Prioritization, Proposals, Advocacy): PLANNED

**Project Language:** Portuguese (Brazilian)
**Documentation Language:** Portuguese
**Database Language:** Portuguese

## Architecture

This is a **database-driven research project** with minimal backend implementation:

- **Data Layer:** SQLite database (`falhas_mercado_v1.db`) containing 50 market failures
- **Backend:** Python 3.x (planned, not yet implemented)
- **Frontend:** Planned using Kibo UI (Shadcn-based) + Tailwind CSS
- **APIs:** Jina AI (web scraping/extraction) and Perplexity AI (research)

**Key Insight:** 52% of identified failures are in the "Regulação" (Regulation) pillar, indicating bureaucracy and legal framework are the most critical barriers.

## The 7 Strategic Pillars

All market failures are categorized into these pillars:

1. **Talento** - Talent/Human Resources (training, attraction, retention)
2. **Densidade** - Density/Concentration (innovation hubs, networking)
3. **Impacto e Diversidade** - Impact & Diversity (social impact, inclusion)
4. **Acesso a Mercado** - Market Access (entry barriers, expansion)
5. **Cultura** - Culture (entrepreneurial culture, innovation mindset)
6. **Regulação** - Regulation (legal framework, bureaucracy) - **26 failures (52%)**
7. **Capital** - Capital (financing, investment)

## Database Structure

**File:** `falhas_mercado_v1.db` (SQLite 3.x, not versioned)

**Schema:**
```sql
CREATE TABLE falhas_mercado (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,        -- Failure title
    pilar TEXT NOT NULL,          -- Pillar (e.g., "1. Talento")
    descricao TEXT NOT NULL,      -- Detailed description
    dica_busca TEXT NOT NULL      -- Search tips for research
);
```

## Essential Commands

### Database Operations
```bash
# View all market failures
sqlite3 falhas_mercado_v1.db "SELECT * FROM falhas_mercado;"

# Filter by pillar (e.g., Regulation)
sqlite3 falhas_mercado_v1.db "SELECT * FROM falhas_mercado WHERE pilar = '6. Regulação';"

# Count failures by pillar
sqlite3 falhas_mercado_v1.db "SELECT pilar, COUNT(*) as total FROM falhas_mercado GROUP BY pilar ORDER BY total DESC;"

# Export to CSV
sqlite3 falhas_mercado_v1.db -header -csv "SELECT * FROM falhas_mercado;" > falhas.csv

# Search by keyword in title or description
sqlite3 falhas_mercado_v1.db "SELECT * FROM falhas_mercado WHERE titulo LIKE '%keyword%' OR descricao LIKE '%keyword%';"
```

### Git Operations
```bash
# Remote repository
git remote -v  # https://github.com/felipematos/sebraae-politicas-publicas.git

# Standard workflow
git status
git add .
git commit -m "message"
git push origin main
```

## Important File Locations

**Protected Files (Not Versioned):**
- `.env` - Contains `JINA_API_KEY` and `PERPLEXITY_API_KEY`
- `falhas_mercado_v1.db` - Main database (156 KB, 50 records)

**Versioned Files:**
- `README.md` - Comprehensive project documentation in Portuguese
- `.gitignore` - Protects `.env`, `*.db`, IDE files, OS files

## Development Guidelines

### Working with Data
- The database is the **source of truth** for market failures
- All queries should be in Portuguese
- When adding new failures, ensure proper pillar categorization
- The `dica_busca` field provides research guidance for each failure

### Research Workflow (Phase 2)
1. Query specific failures from the database
2. Use `dica_busca` field to guide research
3. Leverage Jina AI for web content extraction
4. Use Perplexity AI for global policy analysis
5. Document findings systematically

### Code Style
- Use Portuguese for variable names, comments, and documentation when working with domain-specific content
- Follow Brazilian Portuguese conventions (e.g., "Regulação" not "Regulacion")
- Keep pillar naming consistent: "1. Talento", "2. Densidade", etc.

### API Integration
- Jina AI: Web scraping and content extraction
- Perplexity AI: Research and policy analysis
- API keys stored in `.env` file (never commit)

## Project Phases Reference

1. **Levantamento** (Data Collection) - ✅ COMPLETED
2. **Pesquisa** (Policy Research) - 🔄 IN PROGRESS
3. **Priorização** (Prioritization) - ⏳ PLANNED
4. **Propostas** (Policy Proposals) - ⏳ PLANNED
5. **Advocacy** (Implementation Strategy) - ⏳ PLANNED

## Common Tasks

### Query Failures by Pillar
```bash
# Regulation (highest count - 26 failures)
sqlite3 falhas_mercado_v1.db "SELECT id, titulo FROM falhas_mercado WHERE pilar = '6. Regulação';"

# Capital (5 failures)
sqlite3 falhas_mercado_v1.db "SELECT id, titulo FROM falhas_mercado WHERE pilar = '7. Capital';"
```

### Get Failure Details
```bash
# By ID
sqlite3 falhas_mercado_v1.db "SELECT * FROM falhas_mercado WHERE id = 1;"

# With formatted output
sqlite3 -column -header falhas_mercado_v1.db "SELECT id, titulo, pilar FROM falhas_mercado LIMIT 10;"
```

### Generate Statistics
```bash
# Distribution by pillar
sqlite3 -column -header falhas_mercado_v1.db "SELECT pilar, COUNT(*) as total FROM falhas_mercado GROUP BY pilar ORDER BY total DESC;"

# Total count
sqlite3 falhas_mercado_v1.db "SELECT COUNT(*) as total_falhas FROM falhas_mercado;"
```

## Technical Stack Notes

**Current:**
- SQLite 3.x (active)
- Git/GitHub (active)
- External APIs: Jina AI, Perplexity AI (configured)

**Planned:**
- Python 3.x backend
- Kibo UI components (Shadcn-based)
- Tailwind CSS
- Testing framework (recommend pytest)

## Repository Information

- **GitHub:** https://github.com/felipematos/sebraae-politicas-publicas.git
- **Branch:** main
- **Owner:** felipematos
- **Team:** 10K-Digital (felipematos@gmail.com)

## Project Metadata

- **Sponsor:** Sebrae Nacional
- **Implementation:** ABGI + 10K DIGITAL
- **Technical Coordinator:** Felipe Matos
- **Year:** 2025
- **Focus:** Brazilian innovation ecosystem
