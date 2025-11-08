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

### Claude Code Best Practices

#### UI/UX Guidelines
- **NEVER** create UI elements with insufficient text contrast
- Always ensure readable contrast ratios between text color and background color
- Follow WCAG accessibility guidelines (minimum 4.5:1 for normal text, 3:1 for large text)
- Test color combinations before implementing

#### Documentation Maintenance
- **ALWAYS** update README.md when making significant changes to:
  - Project structure
  - Dependencies or technical stack
  - API integrations
  - Database schema
  - Key features or workflows
- Keep CLAUDE.md updated with new patterns, commands, or guidelines discovered during development
- Document architectural decisions and their rationale

#### Testing & Verification
- **ALWAYS** test changes before considering them complete, especially for:
  - Large or complex modifications
  - Changes affecting multiple files or components
  - Database migrations or schema changes
  - API integrations
  - UI/UX modifications
- Verify that changes don't break existing functionality
- Run relevant test commands or manual verification steps
- Check console for errors after making frontend changes

#### Error Resolution Strategy
- When encountering errors, **ALWAYS**:
  - Review recent changes made in the current session
  - Consider how recent modifications might have caused the issue
  - Check if new dependencies or configurations are missing
  - Verify file paths and references are still valid
- Maintain context awareness of the change history during debugging
- Document solutions to non-obvious errors for future reference

#### LLM Model Selection
- **ALWAYS** use the intelligent model manager system (`app/llm/gerenciador_modelos.py`) when calling LLMs
- The system automatically selects appropriate models based on:
  - Task requirements (context length, capabilities)
  - Cost optimization (prices from OpenRouter API)
  - Model availability and performance characteristics
- Data source: `app/llm/modelos_openrouter.json` (contains pricing and features)
- Use `chamador_llm_inteligente.py` for smart model routing
- Never hardcode model selection - let the manager choose optimally

#### HTML Structure & Div Balance (CRITICAL)

**Problem Recognition:**
The application uses Alpine.js v3.15.1 for reactivity. When div tags are improperly balanced (missing or extra closing `</div>` tags), it causes:
- All modals/sections to display simultaneously
- Alpine.js failing to bind to the `#app` element
- Header and main content becoming children of modal elements instead of `#app`
- Page rendering only partial content (usually just a modal's content)

**Symptoms:**
- Console shows: `[Alpine] #app bound: false`
- Visual: All screens/dialogs appear opened at once
- DOM Inspector: `header` and `main` are children of a modal div instead of `#app`
- Stats may or may not load depending on how broken the structure is

**Root Causes:**
1. **Extra closing divs** between modals (orphaned `</div>` tags)
2. **Missing closing divs** for modal structures (especially 2-layer modals with outer + inner divs)
3. **Premature container closures** (e.g., closing a container before all its children are closed)

**Diagnostic Commands:**
```bash
# Check overall div balance
python3 -c "
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()
total_open = content.count('<div')
total_close = content.count('</div>')
print(f'<div: {total_open}, </div>: {total_close}, Balance: {total_open - total_close}')
"

# Find where balance goes negative (extra closing divs)
python3 << 'EOF'
with open('static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

balance = 0
for i, line in enumerate(lines, 1):
    balance += line.count('<div') - line.count('</div>')
    if balance < 0:
        print(f"Line {i}: balance = {balance} | {line.strip()[:80]}")
        if i <= 5:  # Show first 5 instances
            continue
        else:
            break
EOF
```

**Prevention Guidelines:**
1. **NEVER manually edit modal structures** - they are complex nested structures
2. **ALWAYS verify div balance** after ANY changes to `static/index.html`
3. **Use git history** when structure is broken - check recent commits that fixed similar issues
4. **Understand modal structure**: Most modals have 2 layers:
   - Outer div: `class="fixed inset-0 bg-black bg-opacity-50..."` (backdrop)
   - Inner div: `class="bg-white rounded-lg..."` (content)
   - Both need proper closing tags
5. **Check git log first** before attempting manual fixes:
   ```bash
   git log --oneline --all -20 --grep="div\|layout\|Alpine"
   ```

**Recovery Strategy:**
1. Check git history for recent fixes: `git log --oneline -20`
2. If similar issue was fixed before, restore from that commit:
   ```bash
   git show <commit-hash>:static/index.html > static/index.html.temp
   # Review the temp file
   cp static/index.html.temp static/index.html
   ```
3. Test with Playwright/browser to verify the fix works
4. Only attempt manual fixes if no working commit exists

**Testing After Changes:**
Always use Playwright or Chrome DevTools to verify:
```javascript
// Check if Alpine bound correctly
const app = document.querySelector('#app');
console.log('Alpine bound:', app?.__x !== undefined);

// Check DOM structure
const header = document.querySelector('header');
const main = document.querySelector('main');
console.log('Header parent:', header?.parentElement?.id || header?.parentElement?.tagName);
console.log('Main parent:', main?.parentElement?.id || main?.parentElement?.tagName);
// Both should be 'app' or 'DIV' (inside #app), NOT a modal ID
```

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
