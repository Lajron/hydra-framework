"""wiki command decisions."""

from __future__ import annotations

from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import is_relative_to, write_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.wiki.links import validate_wiki
from hydra_engine.wiki.paths import WikiPaths
from hydra_engine.wiki.scaffold import wiki_home_page_text, wiki_sources_page_text


def command_validate_wiki(args, paths: WikiPaths) -> CommandResult:
    root = Path(args.path).resolve() if args.path else paths.project_wiki
    shown = root.relative_to(paths.root) if is_relative_to(root, paths.root) else root
    print(f"Hydra wiki docs: {shown}")
    errors = validate_wiki(root, paths.root)
    if errors:
        print("Hydra wiki docs: failed")
        for error in errors:
            print(f"- {error}")
        return CommandResult(1)
    print("Hydra wiki docs: ok")
    return CommandResult(0)


def command_wiki_scaffold(args, paths: WikiPaths) -> CommandResult:
    slug = slugify(args.project)
    title = args.title or args.project.replace("-", " ").replace("_", " ").title()
    target = paths.project_wiki / slug
    existing_files = list(target.glob("*.md")) if target.exists() else []
    if existing_files and not args.force:
        print(f"Wiki surface already exists: {target.relative_to(paths.root)}")
        return CommandResult(1)

    write_text(target / "home.md", wiki_home_page_text(title))
    write_text(target / "sources.md", wiki_sources_page_text(title))
    print(f"Created wiki surface: {target.relative_to(paths.root)}")
    print(f"- {(target / 'home.md').relative_to(paths.root)}")
    print(f"- {(target / 'sources.md').relative_to(paths.root)}")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add `validate-wiki` and `wiki scaffold`."""
    wiki_validate = subparsers.add_parser("validate-wiki", help="Validate project-wiki Markdown and Obsidian links")
    wiki_validate.add_argument("--path", help="Explicit wiki root path; defaults to project-wiki")
    wiki_validate.set_defaults(func=_dispatch_validate_wiki)

    wiki = subparsers.add_parser("wiki", help="Maintain human wiki surfaces")
    wiki_sub = wiki.add_subparsers(dest="wiki_command", required=True)
    scaffold = wiki_sub.add_parser("scaffold", help="Create project-wiki/<project-name> starter pages")
    scaffold.add_argument("project")
    scaffold.add_argument("--title", default="")
    scaffold.add_argument("--force", action="store_true")
    scaffold.set_defaults(func=_dispatch_wiki_scaffold)


def _dispatch_validate_wiki(args, ctx) -> int:
    return command_validate_wiki(args, ctx.wiki_paths()).exit_code


def _dispatch_wiki_scaffold(args, ctx) -> int:
    return command_wiki_scaffold(args, ctx.wiki_paths()).exit_code
