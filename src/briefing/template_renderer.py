"""
Template Renderer — Jinja2-based report generation.

Loads ``.j2`` templates from a configurable directory, renders them
with a BriefingData payload, and writes the output to a target path.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.briefing.models import BriefingData


class TemplateRenderer:
    """Renders Jinja2 briefing templates."""

    def __init__(self, template_dir: Path):
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # Markdown output — no HTML escaping
            keep_trailing_newline=True,
        )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def render(self, template_name: str, data: BriefingData) -> str:
        """Render *template_name* with *data* and return the output string."""
        template = self._env.get_template(template_name)
        return template.render(briefing=data)

    def render_to_file(
        self, template_name: str, data: BriefingData, output_path: Path
    ) -> Path:
        """Render and write to *output_path*.  Creates parents as needed."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(template_name, data))
        return output_path
