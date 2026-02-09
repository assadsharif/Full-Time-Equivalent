"""
Theme Factory MCP Server — theme styling toolkit for artifacts including slides,
docs, reports, HTML landing pages, and more.

TOOLS:
    theme_list_themes           List all 10 available themes
    theme_get_theme             Get full theme specification
    theme_generate_css          Generate CSS custom properties for a theme
    theme_generate_tailwind     Generate Tailwind CSS config for a theme
    theme_generate_sass         Generate SASS/SCSS variables for a theme
    theme_create_custom         Create a custom theme from description
    theme_apply_to_html         Apply theme styling to HTML content
    theme_generate_preview      Generate color palette preview (HTML/SVG)
    theme_suggest_theme         Suggest best theme for a given context
    theme_validate_contrast     Validate WCAG contrast ratios
"""

import json
import math
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("theme_factory_mcp")

# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

THEMES = {
    "ocean_depths": {
        "name": "Ocean Depths",
        "description": "Professional and calming maritime theme",
        "colors": {
            "primary": {"hex": "#1a5276", "name": "Deep Sea", "desc": "Rich navy base"},
            "secondary": {
                "hex": "#2e86ab",
                "name": "Ocean Blue",
                "desc": "Bright mid-tone",
            },
            "accent": {"hex": "#5dade2", "name": "Sky Wave", "desc": "Light accent"},
            "surface": {
                "hex": "#d6eaf8",
                "name": "Sea Foam",
                "desc": "Light backgrounds",
            },
        },
        "typography": {"headers": "FreeSans Bold", "body": "FreeSans"},
        "use_cases": [
            "Corporate presentations",
            "Financial reports",
            "Professional services",
            "Healthcare",
        ],
    },
    "sunset_boulevard": {
        "name": "Sunset Boulevard",
        "description": "Warm and vibrant sunset colors",
        "colors": {
            "primary": {"hex": "#c0392b", "name": "Crimson", "desc": "Bold red base"},
            "secondary": {
                "hex": "#e74c3c",
                "name": "Sunset Red",
                "desc": "Vibrant mid-tone",
            },
            "accent": {"hex": "#f39c12", "name": "Golden", "desc": "Warm accent"},
            "surface": {
                "hex": "#fdebd0",
                "name": "Peach Cream",
                "desc": "Warm backgrounds",
            },
        },
        "typography": {"headers": "DejaVu Sans Bold", "body": "DejaVu Sans"},
        "use_cases": ["Entertainment", "Food & beverage", "Travel", "Lifestyle brands"],
    },
    "forest_canopy": {
        "name": "Forest Canopy",
        "description": "Natural and grounded earth tones",
        "colors": {
            "primary": {
                "hex": "#1e8449",
                "name": "Forest Green",
                "desc": "Deep green base",
            },
            "secondary": {
                "hex": "#27ae60",
                "name": "Leaf Green",
                "desc": "Fresh mid-tone",
            },
            "accent": {"hex": "#82e0aa", "name": "Mint", "desc": "Light accent"},
            "surface": {
                "hex": "#e9f7ef",
                "name": "Morning Dew",
                "desc": "Natural backgrounds",
            },
        },
        "typography": {"headers": "FreeSans Bold", "body": "FreeSans"},
        "use_cases": ["Environmental", "Sustainability", "Agriculture", "Wellness"],
    },
    "modern_minimalist": {
        "name": "Modern Minimalist",
        "description": "Clean and contemporary grayscale",
        "colors": {
            "primary": {"hex": "#2c3e50", "name": "Charcoal", "desc": "Deep gray base"},
            "secondary": {"hex": "#566573", "name": "Slate", "desc": "Mid gray tone"},
            "accent": {"hex": "#95a5a6", "name": "Silver", "desc": "Light accent"},
            "surface": {"hex": "#f4f6f6", "name": "Cloud", "desc": "Clean backgrounds"},
        },
        "typography": {"headers": "DejaVu Sans Bold", "body": "DejaVu Sans"},
        "use_cases": ["Architecture", "Design agencies", "Consulting", "Luxury brands"],
    },
    "golden_hour": {
        "name": "Golden Hour",
        "description": "Rich and warm autumnal palette",
        "colors": {
            "primary": {"hex": "#b9770e", "name": "Bronze", "desc": "Rich gold base"},
            "secondary": {"hex": "#d4ac0d", "name": "Amber", "desc": "Warm mid-tone"},
            "accent": {"hex": "#f7dc6f", "name": "Honey", "desc": "Light accent"},
            "surface": {"hex": "#fef9e7", "name": "Cream", "desc": "Warm backgrounds"},
        },
        "typography": {"headers": "FreeSans Bold", "body": "FreeSans"},
        "use_cases": [
            "Autumn events",
            "Harvest themes",
            "Luxury goods",
            "Financial services",
        ],
    },
    "arctic_frost": {
        "name": "Arctic Frost",
        "description": "Cool and crisp winter-inspired theme",
        "colors": {
            "primary": {"hex": "#1b4f72", "name": "Ice Blue", "desc": "Deep cool base"},
            "secondary": {
                "hex": "#2980b9",
                "name": "Glacier",
                "desc": "Bright mid-tone",
            },
            "accent": {"hex": "#85c1e9", "name": "Frost", "desc": "Light accent"},
            "surface": {"hex": "#ebf5fb", "name": "Snow", "desc": "Crisp backgrounds"},
        },
        "typography": {"headers": "DejaVu Sans Bold", "body": "DejaVu Sans"},
        "use_cases": ["Winter campaigns", "Technology", "Science", "Healthcare"],
    },
    "desert_rose": {
        "name": "Desert Rose",
        "description": "Soft and sophisticated dusty tones",
        "colors": {
            "primary": {"hex": "#8e5e4d", "name": "Terracotta", "desc": "Earthy base"},
            "secondary": {"hex": "#c49a8a", "name": "Blush", "desc": "Soft mid-tone"},
            "accent": {"hex": "#e8c6b8", "name": "Rose Sand", "desc": "Light accent"},
            "surface": {"hex": "#faf0ed", "name": "Linen", "desc": "Warm backgrounds"},
        },
        "typography": {"headers": "FreeSans Bold", "body": "FreeSans"},
        "use_cases": ["Beauty", "Fashion", "Interior design", "Wedding"],
    },
    "tech_innovation": {
        "name": "Tech Innovation",
        "description": "Bold and modern tech aesthetic",
        "colors": {
            "primary": {
                "hex": "#1e1e1e",
                "name": "Dark Gray",
                "desc": "Deep backgrounds",
            },
            "secondary": {
                "hex": "#0066ff",
                "name": "Electric Blue",
                "desc": "Vibrant primary",
            },
            "accent": {
                "hex": "#00ffff",
                "name": "Neon Cyan",
                "desc": "Bright highlight",
            },
            "surface": {"hex": "#ffffff", "name": "White", "desc": "Clean contrast"},
        },
        "typography": {"headers": "DejaVu Sans Bold", "body": "DejaVu Sans"},
        "use_cases": [
            "Tech startups",
            "Software launches",
            "AI/ML",
            "Digital transformation",
        ],
    },
    "botanical_garden": {
        "name": "Botanical Garden",
        "description": "Fresh and organic garden colors",
        "colors": {
            "primary": {
                "hex": "#145a32",
                "name": "Deep Green",
                "desc": "Rich plant base",
            },
            "secondary": {"hex": "#229954", "name": "Fern", "desc": "Natural mid-tone"},
            "accent": {"hex": "#abebc6", "name": "Spring", "desc": "Fresh accent"},
            "surface": {
                "hex": "#e8f8f5",
                "name": "Dewdrop",
                "desc": "Organic backgrounds",
            },
        },
        "typography": {"headers": "FreeSans Bold", "body": "FreeSans"},
        "use_cases": [
            "Organic brands",
            "Gardening",
            "Eco-friendly",
            "Natural products",
        ],
    },
    "midnight_galaxy": {
        "name": "Midnight Galaxy",
        "description": "Dramatic and cosmic deep tones",
        "colors": {
            "primary": {
                "hex": "#2b1e3e",
                "name": "Deep Purple",
                "desc": "Rich dark base",
            },
            "secondary": {
                "hex": "#4a4e8f",
                "name": "Cosmic Blue",
                "desc": "Mystical mid-tone",
            },
            "accent": {"hex": "#a490c2", "name": "Lavender", "desc": "Soft accent"},
            "surface": {"hex": "#e6e6fa", "name": "Silver", "desc": "Light highlights"},
        },
        "typography": {"headers": "FreeSans Bold", "body": "FreeSans"},
        "use_cases": [
            "Entertainment",
            "Gaming",
            "Nightlife",
            "Luxury brands",
            "Creative agencies",
        ],
    },
}

# Theme keywords for suggestion
THEME_KEYWORDS = {
    "ocean_depths": [
        "ocean",
        "sea",
        "marine",
        "corporate",
        "professional",
        "financial",
        "bank",
        "healthcare",
        "calm",
    ],
    "sunset_boulevard": [
        "sunset",
        "warm",
        "vibrant",
        "entertainment",
        "food",
        "travel",
        "lifestyle",
        "restaurant",
    ],
    "forest_canopy": [
        "forest",
        "nature",
        "green",
        "eco",
        "sustainable",
        "environment",
        "organic",
        "wellness",
        "health",
    ],
    "modern_minimalist": [
        "minimal",
        "modern",
        "clean",
        "architecture",
        "design",
        "consulting",
        "luxury",
        "elegant",
    ],
    "golden_hour": [
        "gold",
        "autumn",
        "fall",
        "harvest",
        "luxury",
        "premium",
        "financial",
        "bronze",
        "rich",
    ],
    "arctic_frost": [
        "winter",
        "cold",
        "ice",
        "snow",
        "arctic",
        "tech",
        "science",
        "medical",
        "clean",
    ],
    "desert_rose": [
        "rose",
        "blush",
        "pink",
        "beauty",
        "fashion",
        "wedding",
        "feminine",
        "soft",
        "elegant",
    ],
    "tech_innovation": [
        "tech",
        "technology",
        "startup",
        "software",
        "ai",
        "digital",
        "innovation",
        "modern",
        "cyber",
    ],
    "botanical_garden": [
        "botanical",
        "garden",
        "plant",
        "organic",
        "natural",
        "eco",
        "green",
        "fresh",
        "spring",
    ],
    "midnight_galaxy": [
        "galaxy",
        "cosmic",
        "space",
        "night",
        "dark",
        "gaming",
        "entertainment",
        "creative",
        "luxury",
    ],
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class GetThemeInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier (snake_case)")

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(
                f"Unknown theme: {v}. Use theme_list_themes for available options."
            )
        return v


class GenerateCssInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier")
    prefix: str = Field(default="theme", description="CSS variable prefix")
    include_typography: bool = Field(
        default=True, description="Include font-family vars"
    )

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(f"Unknown theme: {v}")
        return v


class GenerateTailwindInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier")
    extend_only: bool = Field(default=True, description="Use extend block (vs replace)")

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(f"Unknown theme: {v}")
        return v


class GenerateSassInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier")
    use_maps: bool = Field(
        default=False, description="Use SASS maps instead of variables"
    )

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(f"Unknown theme: {v}")
        return v


class CreateCustomInput(BaseModel):
    model_config = _CFG
    name: str = Field(..., min_length=2, max_length=50, description="Theme name")
    description: str = Field(
        ..., min_length=10, max_length=200, description="Theme description"
    )
    mood: str = Field(
        ..., description="Mood/feeling (e.g., 'calm', 'energetic', 'professional')"
    )
    primary_color: Optional[str] = Field(
        default=None, description="Optional primary color hex"
    )
    industry: Optional[str] = Field(
        default=None, description="Optional target industry"
    )

    @field_validator("primary_color")
    @classmethod
    def _validate_hex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^#[0-9a-fA-F]{6}$", v):
                raise ValueError("Color must be 6-digit hex (e.g., #1a5276)")
        return v


class ApplyToHtmlInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier")
    html: str = Field(
        ..., min_length=1, max_length=50000, description="HTML content to style"
    )
    inject_fonts: bool = Field(default=True, description="Inject Google Fonts link")

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(f"Unknown theme: {v}")
        return v


class GeneratePreviewInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier")
    format: str = Field(default="html", description="Output format: html, svg")

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(f"Unknown theme: {v}")
        return v

    @field_validator("format")
    @classmethod
    def _validate_format(cls, v: str) -> str:
        if v.lower() not in ("html", "svg"):
            raise ValueError("format must be html or svg")
        return v.lower()


class SuggestThemeInput(BaseModel):
    model_config = _CFG
    context: str = Field(
        ..., min_length=5, max_length=500, description="Description of use case"
    )
    mood: Optional[str] = Field(default=None, description="Optional mood preference")


class ValidateContrastInput(BaseModel):
    model_config = _CFG
    theme_id: str = Field(..., description="Theme identifier")
    level: str = Field(default="AA", description="WCAG level: AA or AAA")

    @field_validator("theme_id")
    @classmethod
    def _validate_theme(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in THEMES:
            raise ValueError(f"Unknown theme: {v}")
        return v

    @field_validator("level")
    @classmethod
    def _validate_level(cls, v: str) -> str:
        if v.upper() not in ("AA", "AAA"):
            raise ValueError("level must be AA or AAA")
        return v.upper()


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1."""

    def _adjust(c: int) -> float:
        c_norm = c / 255.0
        return (
            c_norm / 12.92 if c_norm <= 0.03928 else ((c_norm + 0.055) / 1.055) ** 2.4
        )

    return 0.2126 * _adjust(r) + 0.7152 * _adjust(g) + 0.0722 * _adjust(b)


def _contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    l1 = _relative_luminance(*_hex_to_rgb(hex1))
    l2 = _relative_luminance(*_hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _generate_complementary(hex_color: str) -> str:
    """Generate complementary color."""
    r, g, b = _hex_to_rgb(hex_color)
    return f"#{255 - r:02x}{255 - g:02x}{255 - b:02x}"


def _lighten(hex_color: str, amount: float = 0.3) -> str:
    """Lighten a color by amount (0-1)."""
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, amount: float = 0.3) -> str:
    """Darken a color by amount (0-1)."""
    r, g, b = _hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _mood_to_colors(mood: str, primary: Optional[str] = None) -> dict:
    """Generate colors based on mood."""
    mood_bases = {
        "calm": "#2e86ab",
        "energetic": "#e74c3c",
        "professional": "#2c3e50",
        "creative": "#9b59b6",
        "natural": "#27ae60",
        "warm": "#d4ac0d",
        "cool": "#2980b9",
        "luxurious": "#8e5e4d",
        "playful": "#f39c12",
        "serious": "#1e1e1e",
    }

    base = primary or mood_bases.get(mood.lower(), "#2c3e50")
    return {
        "primary": {"hex": base, "name": "Primary", "desc": "Main brand color"},
        "secondary": {
            "hex": _lighten(base, 0.2),
            "name": "Secondary",
            "desc": "Lighter variation",
        },
        "accent": {
            "hex": _lighten(base, 0.5),
            "name": "Accent",
            "desc": "Highlight color",
        },
        "surface": {
            "hex": _lighten(base, 0.85),
            "name": "Surface",
            "desc": "Background color",
        },
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def theme_list_themes() -> str:
    """List all 10 available themes with names and descriptions."""
    themes = []
    for tid, theme in THEMES.items():
        themes.append(
            {
                "id": tid,
                "name": theme["name"],
                "description": theme["description"],
                "use_cases": theme["use_cases"],
            }
        )
    return json.dumps({"themes": themes, "count": len(themes)})


@mcp.tool()
async def theme_get_theme(theme_id: str) -> str:
    """Get full specification for a theme including colors, typography, and use cases."""
    try:
        inp = GetThemeInput(theme_id=theme_id)
        theme = THEMES[inp.theme_id]
        return json.dumps({"theme_id": inp.theme_id, **theme})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_generate_css(
    theme_id: str,
    prefix: str = "theme",
    include_typography: bool = True,
) -> str:
    """Generate CSS custom properties (variables) for a theme."""
    try:
        inp = GenerateCssInput(
            theme_id=theme_id, prefix=prefix, include_typography=include_typography
        )
        theme = THEMES[inp.theme_id]
        colors = theme["colors"]

        lines = [":root {"]
        for key, color in colors.items():
            lines.append(f"  --{inp.prefix}-{key}: {color['hex']};")
            lines.append(
                f"  --{inp.prefix}-{key}-rgb: {', '.join(map(str, _hex_to_rgb(color['hex'])))};"
            )

        if inp.include_typography:
            lines.append(
                f"  --{inp.prefix}-font-headers: '{theme['typography']['headers']}', sans-serif;"
            )
            lines.append(
                f"  --{inp.prefix}-font-body: '{theme['typography']['body']}', sans-serif;"
            )

        lines.append("}")

        css = "\n".join(lines)
        return json.dumps({"theme_id": inp.theme_id, "css": css})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_generate_tailwind(
    theme_id: str,
    extend_only: bool = True,
) -> str:
    """Generate Tailwind CSS configuration for a theme."""
    try:
        inp = GenerateTailwindInput(theme_id=theme_id, extend_only=extend_only)
        theme = THEMES[inp.theme_id]
        colors = theme["colors"]

        color_config = {}
        for key, color in colors.items():
            color_config[key] = color["hex"]

        if inp.extend_only:
            config = {
                "theme": {
                    "extend": {
                        "colors": {inp.theme_id.replace("_", "-"): color_config},
                        "fontFamily": {
                            "headers": [theme["typography"]["headers"], "sans-serif"],
                            "body": [theme["typography"]["body"], "sans-serif"],
                        },
                    }
                }
            }
        else:
            config = {
                "theme": {
                    "colors": color_config,
                    "fontFamily": {
                        "headers": [theme["typography"]["headers"], "sans-serif"],
                        "body": [theme["typography"]["body"], "sans-serif"],
                    },
                }
            }

        return json.dumps({"theme_id": inp.theme_id, "config": config})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_generate_sass(
    theme_id: str,
    use_maps: bool = False,
) -> str:
    """Generate SASS/SCSS variables for a theme."""
    try:
        inp = GenerateSassInput(theme_id=theme_id, use_maps=use_maps)
        theme = THEMES[inp.theme_id]
        colors = theme["colors"]

        if inp.use_maps:
            lines = [f"$theme-colors: ("]
            for key, color in colors.items():
                lines.append(f"  '{key}': {color['hex']},")
            lines.append(");")
            lines.append("")
            lines.append("$theme-fonts: (")
            lines.append(f"  'headers': '{theme['typography']['headers']}',")
            lines.append(f"  'body': '{theme['typography']['body']}',")
            lines.append(");")
        else:
            lines = []
            for key, color in colors.items():
                lines.append(f"$theme-{key}: {color['hex']};")
            lines.append("")
            lines.append(f"$theme-font-headers: '{theme['typography']['headers']}';")
            lines.append(f"$theme-font-body: '{theme['typography']['body']}';")

        sass = "\n".join(lines)
        return json.dumps(
            {"theme_id": inp.theme_id, "sass": sass, "use_maps": inp.use_maps}
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_create_custom(
    name: str,
    description: str,
    mood: str,
    primary_color: str | None = None,
    industry: str | None = None,
) -> str:
    """Create a custom theme based on mood and optional specifications."""
    try:
        inp = CreateCustomInput(
            name=name,
            description=description,
            mood=mood,
            primary_color=primary_color,
            industry=industry,
        )

        colors = _mood_to_colors(inp.mood, inp.primary_color)

        # Select typography based on mood
        if inp.mood.lower() in ("professional", "serious", "luxurious"):
            typography = {"headers": "DejaVu Sans Bold", "body": "DejaVu Sans"}
        else:
            typography = {"headers": "FreeSans Bold", "body": "FreeSans"}

        use_cases = (
            [inp.industry] if inp.industry else [f"{inp.mood.title()} presentations"]
        )

        custom_theme = {
            "name": inp.name,
            "description": inp.description,
            "colors": colors,
            "typography": typography,
            "use_cases": use_cases,
            "custom": True,
        }

        return json.dumps(custom_theme)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_apply_to_html(
    theme_id: str,
    html: str,
    inject_fonts: bool = True,
) -> str:
    """Apply theme styling to HTML content by injecting CSS variables and optional fonts."""
    try:
        inp = ApplyToHtmlInput(theme_id=theme_id, html=html, inject_fonts=inject_fonts)
        theme = THEMES[inp.theme_id]
        colors = theme["colors"]

        # Generate inline style
        css_vars = []
        for key, color in colors.items():
            css_vars.append(f"--theme-{key}: {color['hex']};")
        css_vars.append(
            f"--theme-font-headers: '{theme['typography']['headers']}', sans-serif;"
        )
        css_vars.append(
            f"--theme-font-body: '{theme['typography']['body']}', sans-serif;"
        )

        style_block = f"<style>:root {{ {' '.join(css_vars)} }}</style>"

        # Font injection
        font_link = ""
        if inp.inject_fonts:
            fonts = theme["typography"]
            font_families = f"{fonts['headers'].replace(' ', '+')},{fonts['body'].replace(' ', '+')}"
            font_link = f'<link href="https://fonts.googleapis.com/css2?family={font_families}&display=swap" rel="stylesheet">'

        # Inject into HTML
        if "<head>" in inp.html:
            styled_html = inp.html.replace("<head>", f"<head>{font_link}{style_block}")
        elif "<html>" in inp.html:
            styled_html = inp.html.replace(
                "<html>", f"<html><head>{font_link}{style_block}</head>"
            )
        else:
            styled_html = f"{font_link}{style_block}{inp.html}"

        return json.dumps({"theme_id": inp.theme_id, "styled_html": styled_html})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_generate_preview(
    theme_id: str,
    format: str = "html",
) -> str:
    """Generate a visual preview of a theme's color palette."""
    try:
        inp = GeneratePreviewInput(theme_id=theme_id, format=format)
        theme = THEMES[inp.theme_id]
        colors = theme["colors"]

        if inp.format == "svg":
            swatches = []
            x = 0
            for key, color in colors.items():
                swatches.append(
                    f'<rect x="{x}" y="0" width="80" height="60" fill="{color["hex"]}" />'
                    f'<text x="{x + 40}" y="75" text-anchor="middle" font-size="10">{color["name"]}</text>'
                    f'<text x="{x + 40}" y="88" text-anchor="middle" font-size="8" fill="#666">{color["hex"]}</text>'
                )
                x += 85

            svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x} 100">
  <text x="{x // 2}" y="-10" text-anchor="middle" font-weight="bold">{theme["name"]}</text>
  {chr(10).join(swatches)}
</svg>"""
            return json.dumps(
                {"theme_id": inp.theme_id, "preview": svg, "format": "svg"}
            )

        # HTML format
        swatches = []
        for key, color in colors.items():
            text_color = (
                "#fff"
                if _relative_luminance(*_hex_to_rgb(color["hex"])) < 0.5
                else "#000"
            )
            swatches.append(
                f'<div style="background:{color["hex"]};color:{text_color};padding:20px;text-align:center;">'
                f'<strong>{color["name"]}</strong><br><small>{color["hex"]}</small></div>'
            )

        html = f"""<div style="font-family:sans-serif;">
  <h3 style="margin:0 0 10px;">{theme["name"]}</h3>
  <p style="margin:0 0 15px;color:#666;">{theme["description"]}</p>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:5px;">
    {"".join(swatches)}
  </div>
</div>"""
        return json.dumps({"theme_id": inp.theme_id, "preview": html, "format": "html"})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_suggest_theme(
    context: str,
    mood: str | None = None,
) -> str:
    """Suggest the best theme based on context description and optional mood preference."""
    try:
        inp = SuggestThemeInput(context=context, mood=mood)
        context_lower = inp.context.lower()
        mood_lower = (inp.mood or "").lower()

        scores = {}
        for theme_id, keywords in THEME_KEYWORDS.items():
            score = sum(2 if kw in context_lower else 0 for kw in keywords)
            if mood_lower:
                score += sum(1 if kw in mood_lower else 0 for kw in keywords)
            scores[theme_id] = score

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_matches = []
        for theme_id, score in ranked[:3]:
            if score > 0:
                theme = THEMES[theme_id]
                top_matches.append(
                    {
                        "theme_id": theme_id,
                        "name": theme["name"],
                        "description": theme["description"],
                        "score": score,
                        "use_cases": theme["use_cases"],
                    }
                )

        if not top_matches:
            # Default to modern_minimalist
            theme = THEMES["modern_minimalist"]
            top_matches.append(
                {
                    "theme_id": "modern_minimalist",
                    "name": theme["name"],
                    "description": theme["description"],
                    "score": 0,
                    "use_cases": theme["use_cases"],
                    "reason": "Default suggestion - no strong keyword matches",
                }
            )

        return json.dumps({"suggestions": top_matches, "context": inp.context[:100]})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def theme_validate_contrast(
    theme_id: str,
    level: str = "AA",
) -> str:
    """Validate WCAG contrast ratios for a theme's color combinations."""
    try:
        inp = ValidateContrastInput(theme_id=theme_id, level=level)
        theme = THEMES[inp.theme_id]
        colors = theme["colors"]

        # WCAG thresholds
        min_normal = 4.5 if inp.level == "AA" else 7.0
        min_large = 3.0 if inp.level == "AA" else 4.5

        results = []
        color_list = list(colors.items())

        # Test key combinations
        test_pairs = [
            ("primary", "surface"),
            ("secondary", "surface"),
            ("accent", "surface"),
            ("primary", "accent"),
        ]

        all_pass = True
        for fg_key, bg_key in test_pairs:
            fg = colors.get(fg_key, {}).get("hex")
            bg = colors.get(bg_key, {}).get("hex")
            if fg and bg:
                ratio = _contrast_ratio(fg, bg)
                passes_normal = ratio >= min_normal
                passes_large = ratio >= min_large
                if not passes_normal:
                    all_pass = False
                results.append(
                    {
                        "foreground": fg_key,
                        "background": bg_key,
                        "ratio": round(ratio, 2),
                        "passes_normal_text": passes_normal,
                        "passes_large_text": passes_large,
                    }
                )

        return json.dumps(
            {
                "theme_id": inp.theme_id,
                "level": inp.level,
                "all_pass": all_pass,
                "min_ratio_normal": min_normal,
                "min_ratio_large": min_large,
                "results": results,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
