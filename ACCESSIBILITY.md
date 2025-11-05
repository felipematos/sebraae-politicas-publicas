# Guia de Acessibilidade e Contraste

## Regras de Contraste de Texto

Para garantir legibilidade adequada e conformidade com WCAG 2.1, siga estas regras:

### ✅ Fundos Claros (Branco, Gray-50, etc)

**SEMPRE use text-gray-700 ou mais escuro:**
- ✅ `text-gray-700` - Mínimo recomendado
- ✅ `text-gray-800` - Melhor contraste
- ✅ `text-gray-900` - Máximo contraste
- ✅ `text-black` - Contraste absoluto

**NUNCA use cores claras:**
- ❌ `text-gray-100`, `text-gray-200`, `text-gray-300`
- ❌ `text-white`
- ❌ Sem classe de cor (herda cor clara)

### ✅ Fundos Escuros (Gray-800, Gray-900, Black)

**SEMPRE use text-gray-300 ou mais claro:**
- ✅ `text-white` - Máximo contraste
- ✅ `text-gray-100` - Ótimo contraste
- ✅ `text-gray-200` - Bom contraste
- ✅ `text-gray-300` - Mínimo recomendado

### ✅ Fundos Coloridos

**Para fundos azuis/roxos:**
- Em `bg-blue-50`, `bg-indigo-50`: use `text-blue-900`, `text-indigo-900`
- Em `bg-blue-900`, `bg-indigo-900`: use `text-blue-50`, `text-white`

**Para fundos amarelos/âmbar:**
- Em `bg-yellow-50`, `bg-amber-50`: use `text-yellow-800`, `text-amber-800`
- Em `bg-yellow-800`: use `text-yellow-50`, `text-white`

## Checklist de Componentes

### Modais
```html
<!-- ✅ CORRETO -->
<div class="bg-white rounded-lg p-6">
    <h3 class="text-xl font-bold text-gray-700">Título</h3>
    <p class="text-sm text-gray-600">Descrição</p>
    <span class="text-sm text-gray-700">Label</span>
</div>

<!-- ❌ INCORRETO -->
<div class="bg-white rounded-lg p-6">
    <span class="text-sm">Sem classe de cor!</span>
</div>
```

### Checkboxes e Radio Buttons
```html
<!-- ✅ CORRETO -->
<label class="flex items-center space-x-2 cursor-pointer">
    <input type="checkbox" class="form-checkbox">
    <span class="text-sm text-gray-700">Label com contraste</span>
</label>

<!-- ❌ INCORRETO -->
<label class="flex items-center space-x-2 cursor-pointer">
    <input type="checkbox" class="form-checkbox">
    <span class="text-sm">Label sem cor</span>
</label>
```

### Inputs e Selects
```html
<!-- ✅ CORRETO -->
<select class="text-gray-900">
    <option value="1" class="text-gray-900">Opção 1</option>
</select>

<!-- ❌ INCORRETO -->
<select>
    <option value="1">Opção sem cor</option>
</select>
```

## Ferramentas de Verificação

### Comando para encontrar spans sem cor
```bash
# Procurar por spans que podem ter problema de contraste
grep -n 'class="text-sm"[^>]*>' static/index.html
grep -n '<span class="[^"]*">[A-Z]' static/index.html | grep -v 'text-gray-[6-9]' | grep -v 'text-black'
```

### Teste Visual
1. Abra o navegador em modo de alto contraste
2. Use extensões como "WAVE" ou "axe DevTools"
3. Teste com zoom em 200%

## Comentários no Código

Adicione comentários em seções críticas:

```html
<!-- ⚠️ ACCESSIBILITY RULE: All text on white backgrounds MUST use text-gray-700 or darker -->
<div class="bg-white">
    <!-- Seu conteúdo aqui -->
</div>
```

## Commits Relacionados

- `cbed335` - fix: Adicionar text-gray-700 a todos os textos de checkbox no modal de Filtros de Fontes
- `de21825` - fix: Melhorar contraste de texto nos labels de filtros

## Referências

- [WCAG 2.1 - Contraste](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [Tailwind CSS - Text Color](https://tailwindcss.com/docs/text-color)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
