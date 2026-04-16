---
name: docs
description: Search and read EnergyPlus documentation for any object type, field, or concept. Use when you need to understand how an EnergyPlus object works, what fields are available, or how a feature should be configured.
argument-hint: "[search-query]"
---

# EnergyPlus Documentation Search

Look up: $ARGUMENTS

## Steps

1. **Quick reference** — If the query is an object type name, read the `idfkit://docs/{object_type}` resource to get direct URLs to:
   - I/O Reference (field-level documentation)
   - Engineering Reference (algorithms and theory)
   - docs.idfkit.com search results

2. **Search** — Use `search_docs` with the query to find relevant documentation sections:
   - Returns section titles, text excerpts, relevance scores, and doc URLs
   - Filter by `tags` to target specific doc sets (e.g., "io-ref", "engineering-ref")

3. **Read details** — For the most relevant results, use `get_doc_section` with the `location` from the search results to read the full section content

4. **Present findings** — Summarize the key information:
   - What the object/feature does
   - Required vs optional fields
   - Typical values and ranges
   - Related objects and cross-references
   - Links to full documentation on docs.idfkit.com

5. **Schema complement** — If relevant, also use `describe_object_type` to show the concrete field schema alongside the documentation
