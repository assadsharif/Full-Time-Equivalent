"""
Skill Management Commands

Commands for discovering, inspecting, and validating Agent Skills
installed under .claude/skills/.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from cli.utils import display_error, display_info, display_success


console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_skills_dir() -> Path:
    """Locate .claude/skills/ relative to the repo root."""
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = candidate.parent
        skills = candidate / ".claude" / "skills"
        if skills.is_dir():
            return skills
    raise FileNotFoundError(".claude/skills/ not found")


def find_validate_script() -> Path:
    """Locate scripts/validate_skill.py relative to repo root."""
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = candidate.parent
        script = candidate / "scripts" / "validate_skill.py"
        if script.exists():
            return script
    raise FileNotFoundError("scripts/validate_skill.py not found")


def parse_skill_meta(skill_dir: Path) -> Optional[Dict]:
    """Parse SKILL.md frontmatter from a skill directory.  Returns None on failure."""
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None
    content = skill_file.read_text()
    # Extract YAML between --- fences
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(content[3:end])
        if isinstance(fm, dict):
            fm["_dir"] = str(skill_dir)
            fm["_slug"] = skill_dir.name
            return fm
    except yaml.YAMLError:
        return None
    return None


def load_all_skills(skills_dir: Path) -> List[Dict]:
    """Walk skills_dir and parse every SKILL.md."""
    skills = []
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir():
            meta = parse_skill_meta(child)
            if meta:
                skills.append(meta)
    return skills


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group(name="skill")
def skill_group():
    """Agent Skill management commands"""
    pass


@skill_group.command(name="list")
@click.pass_context
def skill_list_command(ctx: click.Context):
    """
    List all installed Agent Skills grouped by category.

    \b
    Examples:
      fte skill list
    """
    try:
        skills_dir = find_skills_dir()
        skills = load_all_skills(skills_dir)

        if not skills:
            display_info("No skills found.")
            return

        # Group by category
        groups: Dict[str, List[Dict]] = {}
        for s in skills:
            cat = s.get("category", "uncategorised")
            groups.setdefault(cat, []).append(s)

        table = Table(title=f"Installed Skills ({len(skills)} total)", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan", min_width=30)
        table.add_column("Category", style="yellow", width=14)
        table.add_column("Safety", style="white", width=8)
        table.add_column("Description", style="dim")

        for cat in sorted(groups.keys()):
            for s in groups[cat]:
                name = s.get("name", s.get("_slug", "?"))
                safety = s.get("safety_level", "—")
                desc = str(s.get("description", ""))[:80]
                table.add_row(name, cat, safety, desc)

        console.print(table)

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@skill_group.command(name="show")
@click.argument("name")
@click.pass_context
def skill_show_command(ctx: click.Context, name: str):
    """
    Show full metadata for a single skill.

    NAME can be a skill name (fte.vault.init) or a slug (fte-vault-init).

    \b
    Examples:
      fte skill show fte.vault.init
      fte skill show skill-validator
    """
    try:
        skills_dir = find_skills_dir()
        skills = load_all_skills(skills_dir)

        # Match by name field or slug
        slug = name.replace(".", "-")
        match = None
        for s in skills:
            if s.get("name") == name or s.get("_slug") == name or s.get("_slug") == slug:
                match = s
                break

        if not match:
            display_error(f"Skill not found: '{name}'", verbose=False)
            ctx.exit(1)
            return

        # Print all fields
        console.print(f"\n[bold cyan]Skill:[/bold cyan] {match.get('name', match['_slug'])}")
        for key in ("version", "description", "command", "aliases", "category",
                    "tags", "safety_level", "approval_required", "destructive",
                    "author", "created", "last_updated"):
            val = match.get(key)
            if val is not None:
                console.print(f"  [bold]{key}:[/bold] {val}")

        if "triggers" in match:
            console.print(f"  [bold]triggers:[/bold] {match['triggers']}")
        if "requires" in match:
            console.print(f"  [bold]requires:[/bold] {match['requires']}")
        if "parameters" in match:
            console.print(f"  [bold]parameters:[/bold] {match['parameters']}")
        if "constitutional_compliance" in match:
            console.print(f"  [bold]constitutional_compliance:[/bold] sections {match['constitutional_compliance']}")
        console.print()

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@skill_group.command(name="search")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--category", "-c", help="Filter by category")
@click.pass_context
def skill_search_command(ctx: click.Context, tag: Optional[str], category: Optional[str]):
    """
    Search installed skills by tag or category.

    \b
    Examples:
      fte skill search --tag vault
      fte skill search --category git
    """
    try:
        if not tag and not category:
            display_info("Provide at least --tag or --category.")
            ctx.exit(1)
            return

        skills_dir = find_skills_dir()
        skills = load_all_skills(skills_dir)

        results = skills
        if tag:
            results = [s for s in results if tag.lower() in [t.lower() for t in s.get("tags", [])]]
        if category:
            results = [s for s in results if s.get("category", "").lower() == category.lower()]

        if not results:
            display_info(f"No skills match the filter.")
            return

        table = Table(title=f"Search Results ({len(results)})", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan", min_width=30)
        table.add_column("Category", style="yellow", width=14)
        table.add_column("Description", style="dim")

        for s in results:
            name = s.get("name", s.get("_slug", "?"))
            cat = s.get("category", "—")
            desc = str(s.get("description", ""))[:80]
            table.add_row(name, cat, desc)

        console.print(table)

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@skill_group.command(name="validate")
@click.argument("name")
@click.option(
    "--level",
    type=click.Choice(["syntax", "complete", "quality"]),
    default="complete",
    help="Validation depth (default: complete)",
)
@click.pass_context
def skill_validate_command(ctx: click.Context, name: str, level: str):
    """
    Validate a skill against the schema.

    NAME can be a skill name (fte.vault.init) or a slug (fte-vault-init).

    \b
    Examples:
      fte skill validate fte.vault.init
      fte skill validate skill-validator --level quality
    """
    try:
        validate_script = find_validate_script()

        # Resolve slug → path
        skills_dir = find_skills_dir()
        slug = name.replace(".", "-")
        skill_dir = skills_dir / slug
        if not skill_dir.is_dir():
            skill_dir = skills_dir / name
        if not skill_dir.is_dir():
            display_error(f"Skill not found: '{name}'", verbose=False)
            ctx.exit(1)
            return

        result = subprocess.run(
            [sys.executable, str(validate_script), str(skill_dir), "--level", level],
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        if result.stderr:
            console.print(f"[dim]{result.stderr}[/dim]")

        if result.returncode != 0:
            ctx.exit(1)

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
