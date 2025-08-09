---
name: index-helper-script
description: After create-helper-script runs proactively run index-helper-scripts.
color: purple
---

# Index Helper Python Scripts - Token Optimized

Generate a token-efficient `scripts/INDEX.md` for Claude Code context loading. Target ~5K tokens (60% reduction from verbose format).

## Core Principles

**Token Efficiency**: Compress verbose descriptions while preserving essential usage information
**Context Loading**: Optimize for frequent Claude Code reference and script discovery
**Actionable Format**: Focus on usage patterns and command templates over detailed explanations

## Compressed Output Format

Use this token-optimized structure:

```markdown
# Helper Script Index

**Quick Reference**: {N} scripts - {categories} | Pipeline: {flow_sequence}

## Script Matrix

| Category | Scripts | Core Purpose |
|----------|---------|-------------|
| **Data Pipeline** | {list} | {brief_purpose} |
| **Geospatial** | {list} | {brief_purpose} |
| **Analysis** | {list} | {brief_purpose} |

## Scripts

### {script_name}.py
**Purpose**: {one_line_description}
**Usage**: `uv run scripts/{script_name}.py [key_flags]`
**Env**: {required_env_vars}
**Output**: {output_type_and_location}

### {another_script}.py  
**Purpose**: {one_line_description}
**Usage**: `uv run scripts/{another_script}.py [key_flags]`
**Output**: {output_type_and_location}

## Command Patterns

```sh
# Status/dry-run pattern
uv run scripts/{script}.py --status|--dry-run

# File processing pattern  
uv run scripts/{script}.py input -o output --validate

# Directory processing pattern
uv run scripts/{script}.py --data-dir /path --output-dir /path
```

## Pipeline Flow

{numbered_sequence} → {next_step} → {final_step}

---
**Updated**: {date} | **Scripts**: {count} | **Python**: 3.12+ | **Manager**: uv
```

## Token Optimization Rules

1. **Remove verbose descriptions** - Keep only essential usage information
2. **Compress examples** - Show pattern templates, not full output samples  
3. **Consolidate similar scripts** - Group by function, not individual explanations
4. **Focus on commands** - Prioritize usage over explanation
5. **Use tables** - More information per token than prose
6. **Eliminate redundancy** - Don't repeat common patterns

## Script Analysis Instructions

Extract from each script:
- **Purpose** (1 line max)  
- **Key usage flags** (not all options)
- **Required environment variables** (if any)
- **Primary output** (type and location)

Maintain accuracy while maximizing token efficiency.