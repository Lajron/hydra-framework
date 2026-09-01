"""Starter-page text for a new `project-wiki/<slug>` surface."""

from __future__ import annotations


def wiki_home_page_text(title: str) -> str:
    return f"""# {title}

Status: draft

This is the human-facing wiki area for `{title}`. Use it for teammate-readable product, module, feature, system, and operations docs.

## Scope

- Product systems and modules
- Feature behavior and workflows
- Operational notes that teammates need
- Links to source code, existing docs, task records, and validation evidence

## Source Policy

AI may draft or update pages here, but durable claims must link to verified code, existing project docs, accepted rules, task records, or other source material.

`.hydra-framework/` remains the AI/automation layer. Teammates should be able to understand product systems from this wiki area without browsing `.hydra-framework/`.

## Start Here

- [[sources]]
"""


def wiki_sources_page_text(title: str) -> str:
    return f"""# {title} Sources

Track source material used to create or update this wiki area. Keep live source-of-truth state with its owner and link it from here.

## Existing Project Docs

- To be identified.

## Code Roots

- To be identified.

## Rules And Task Records

- To be identified.
"""
