---
name: format-gb2760-additives
description: Formats GB2760 food additive documents to a standardized structure. Use when formatting food additive documentation, GB2760 files, or when the user asks to format/additive documents with CNS/INS codes and usage tables.
---

# Format GB2760 Food Additives

Formats GB2760 food additive documents to a consistent structure with standardized headers, CNS/INS codes, and usage tables.

## Format Structure

Each additive entry should follow this format:

```markdown
## [Chinese Name]  
[English name only, no Chinese or parentheses]  
**CNS号**：[CNS code]  
**INS号**：[INS code or —]  
**功能**：[Function]

| 食品分类号 | 食品名称 | 最大使用量 | 备注 |
|---|---|---|---|
| [Code] | [Food name] | [Usage limit] | [Note or —] |
```

## Formatting Rules

### 1. Remove Header Titles
- Remove "## 表 A.1 食品添加剂的允许使用品种、使用范围以及最大使用量或残留量"
- Remove "## 表 A.1（续）"
- Remove any table continuation headers

### 2. English Name Line
- **Only English**: Extract English name from parentheses, remove Chinese name
- **Examples**:
  - `β-胡萝卜素（beta-carotene synthetic, beta-carotene, Blakeslea trispora, beta-carotene, algal）` → `beta-carotene synthetic, beta-carotene, Blakeslea trispora, beta-carotene, algal`
  - `β-环状糊精（beta-cyclodextrin）` → `beta-cyclodextrin`
  - `L-苹果酸（L-malic acid）` → `L-malic acid`
- Keep chemical notation symbols like `(−)` in stereochemistry (e.g., `L-(−)-malic acid disodium salt`)
- Convert Greek letters to English when appropriate: `β` → `beta`, `α` → `alpha`, `γ` → `gamma`

### 3. CNS/INS/Function Order
- Always use this order: **CNS号** → **INS号** → **功能**
- Format: `**CNS号**：` (with bold and Chinese colon)
- Format: `**INS号**：` (with bold and Chinese colon)
- Format: `**功能**：` (with bold and Chinese colon)
- If INS code is missing, use `—` (em dash)

### 4. Table Format
- Header: `| 食品分类号 | 食品名称 | 最大使用量 | 备注 |`
- Separator: `|---|---|---|---|`
- Remove units from header: `最大使用量/(g/kg)` → `最大使用量`
- Add spaces after `|` in all cells for consistency
- Empty 备注 cells: use `—` (em dash)

### 5. Remove Notes Section
- Remove any "注" (notes) section at the end of the file
- Remove references to "表 A.2" or other table references in notes

## Example Transformation

**Before:**
```markdown
## 表 A.1（续）

## β-胡萝卜素  
β-胡萝卜素（beta-carotene synthetic, beta-carotene, Blakeslea trispora, beta-carotene, algal）  
INS号：160a(i), 160a(iii), 160a(iv)  
CNS号：08.010  
功能：着色剂  

| 食品分类号 | 食品名称 | 最大使用量/(g/kg) | 备注 |
|---|---|---|---|
| 01.01.03 | 调制乳 | 1.0 | |
```

**After:**
```markdown
## β-胡萝卜素  
beta-carotene synthetic, beta-carotene, Blakeslea trispora, beta-carotene, algal  
**CNS号**：08.010  
**INS号**：160a(i), 160a(iii), 160a(iv)  
**功能**：着色剂

| 食品分类号 | 食品名称 | 最大使用量 | 备注 |
|---|---|---|---|
| 01.01.03 | 调制乳 | 1.0 | — |
```

## Processing Steps

When formatting a GB2760 document:

1. **Remove headers**: Delete table continuation headers
2. **Extract English names**: For each additive, extract only the English name from parentheses
3. **Reorder fields**: Ensure CNS号 comes before INS号, both before 功能
4. **Format tables**: Standardize table headers and separators, add spaces, replace empty cells with —
5. **Remove notes**: Delete any "注" sections at the end
6. **Preserve data**: Keep all usage data rows intact, only format the structure

## Common Patterns

- Multiple INS codes: `160a(i), 160a(iii), 160a(iv)` (keep as comma-separated)
- Multiple functions: `甜味剂、乳化剂、膨松剂、稳定剂、增稠剂` (keep as comma-separated with Chinese commas)
- Usage notes: Preserve notes like "以即饮状态计，相应的固体饮料按稀释倍数增加使用量"
- Special characters: Keep chemical notation, convert Greek letters to English when appropriate
