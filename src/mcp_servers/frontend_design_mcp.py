"""
Frontend Design MCP Server — distinctive, production-grade UI code generation.

Generates creative, polished frontend code that avoids generic "AI slop" aesthetics.
Focuses on bold aesthetic directions, typography, color, motion, and spatial composition.

TOOLS:
    frontend_generate_component      Generate React/Vue/HTML components
    frontend_generate_layout         Generate creative page layouts
    frontend_generate_typography     Generate typography systems
    frontend_generate_color_palette  Generate distinctive color palettes
    frontend_generate_animation      Generate CSS/Motion animations
    frontend_generate_background     Generate creative backgrounds
    frontend_generate_theme          Generate complete theme systems
    frontend_detect_antipatterns     Detect generic "AI slop" patterns
    frontend_suggest_aesthetic       Suggest bold aesthetic directions
    frontend_generate_scaffold       Generate project scaffold
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("frontend_design_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRAMEWORKS = ["react", "vue", "svelte", "html", "nextjs", "astro"]
COMPONENT_TYPES = [
    "button",
    "card",
    "hero",
    "nav",
    "footer",
    "form",
    "modal",
    "table",
    "list",
    "custom",
]
LAYOUT_TYPES = [
    "landing",
    "dashboard",
    "blog",
    "portfolio",
    "ecommerce",
    "saas",
    "magazine",
    "brutalist",
]

# Aesthetic directions (avoid generic)
AESTHETICS = {
    "brutalist": {
        "name": "Brutalist/Raw",
        "description": "Raw, honest, unpolished. Exposed structure, system fonts, harsh contrasts.",
        "fonts": ["Courier New", "Monaco", "SF Mono", "JetBrains Mono"],
        "characteristics": [
            "monospace typography",
            "harsh borders",
            "no rounded corners",
            "high contrast",
            "grid exposure",
        ],
    },
    "minimalist": {
        "name": "Refined Minimalist",
        "description": "Precise, restrained elegance. Every element justified.",
        "fonts": ["Helvetica Neue", "Suisse Int'l", "Akkurat", "Founders Grotesk"],
        "characteristics": [
            "generous whitespace",
            "single accent color",
            "subtle animations",
            "precise alignment",
        ],
    },
    "maximalist": {
        "name": "Maximalist Chaos",
        "description": "Controlled chaos. Layered, dense, vibrant.",
        "fonts": [
            "Playfair Display",
            "Libre Baskerville",
            "Space Grotesk",
            "Clash Display",
        ],
        "characteristics": [
            "overlapping elements",
            "multiple gradients",
            "bold typography",
            "texture layers",
        ],
    },
    "retro_futuristic": {
        "name": "Retro-Futuristic",
        "description": "Y2K meets cyberpunk. Chrome, neon, digital artifacts.",
        "fonts": ["Orbitron", "Audiowide", "Syncopate", "Michroma"],
        "characteristics": [
            "metallic gradients",
            "glitch effects",
            "scan lines",
            "neon accents",
        ],
    },
    "organic": {
        "name": "Organic/Natural",
        "description": "Soft, flowing, nature-inspired. Earthy warmth.",
        "fonts": ["Libre Baskerville", "Cormorant", "EB Garamond", "Lora"],
        "characteristics": [
            "curved shapes",
            "earth tones",
            "flowing animations",
            "natural textures",
        ],
    },
    "luxury": {
        "name": "Luxury/Refined",
        "description": "Premium, sophisticated, understated opulence.",
        "fonts": ["Didot", "Bodoni Moda", "Playfair Display", "Cormorant Garamond"],
        "characteristics": [
            "gold/black palette",
            "serif typography",
            "subtle animations",
            "generous spacing",
        ],
    },
    "playful": {
        "name": "Playful/Toy-like",
        "description": "Fun, bouncy, cartoon-inspired. Pure joy.",
        "fonts": ["Fredoka One", "Baloo 2", "Nunito", "Quicksand"],
        "characteristics": [
            "rounded corners",
            "bright colors",
            "bouncy animations",
            "hand-drawn elements",
        ],
    },
    "editorial": {
        "name": "Editorial/Magazine",
        "description": "Print-inspired. Strong typography, dramatic layouts.",
        "fonts": ["PP Editorial New", "Freight Display", "Canela", "GT Super"],
        "characteristics": [
            "asymmetric grids",
            "large type",
            "dramatic whitespace",
            "pull quotes",
        ],
    },
    "art_deco": {
        "name": "Art Deco/Geometric",
        "description": "1920s glamour. Geometric patterns, gold accents.",
        "fonts": ["Poiret One", "Josefin Sans", "Raleway", "Tenor Sans"],
        "characteristics": [
            "geometric patterns",
            "gold accents",
            "symmetry",
            "fan shapes",
        ],
    },
    "industrial": {
        "name": "Industrial/Utilitarian",
        "description": "Factory aesthetic. Functional, no-nonsense.",
        "fonts": ["DIN", "Eurostile", "Industry", "Barlow"],
        "characteristics": [
            "yellow/black palette",
            "stencil type",
            "exposed grid",
            "technical details",
        ],
    },
}

# Anti-patterns (generic AI slop)
ANTIPATTERNS = [
    {
        "pattern": r"font-family:\s*['\"]?Inter",
        "issue": "Generic font: Inter",
        "fix": "Use distinctive fonts like Space Grotesk, Clash Display, or context-appropriate choices",
    },
    {
        "pattern": r"font-family:\s*['\"]?Roboto",
        "issue": "Generic font: Roboto",
        "fix": "Use fonts with more character - try Outfit, Plus Jakarta Sans, or serif alternatives",
    },
    {
        "pattern": r"font-family:\s*['\"]?Arial",
        "issue": "Generic font: Arial",
        "fix": "Use web fonts with personality - Helvetica Neue, Suisse Int'l, or display fonts",
    },
    {
        "pattern": r"linear-gradient\([^)]*#[89a-f]{3}[89a-f]{3}[^)]*#[89a-f]{3}[89a-f]{3}",
        "issue": "Generic purple/blue gradient",
        "fix": "Use bolder color combinations or textured backgrounds",
    },
    {
        "pattern": r"border-radius:\s*(?:8|12|16)px",
        "issue": "Predictable border radius",
        "fix": "Use extreme values (0px for brutalist, 50% for playful) or vary by context",
    },
    {
        "pattern": r"shadow-(?:sm|md|lg)",
        "issue": "Generic Tailwind shadows",
        "fix": "Create custom shadows with personality - colored shadows, harsh edges, or layered effects",
    },
    {
        "pattern": r"bg-(?:white|gray-50|slate-50)",
        "issue": "Plain white/gray background",
        "fix": "Add depth with subtle gradients, textures, or atmospheric effects",
    },
    {
        "pattern": r"text-(?:gray-600|slate-600)",
        "issue": "Safe gray text color",
        "fix": "Use colors that match your aesthetic - warm grays, tinted neutrals, or bold choices",
    },
    {
        "pattern": r"gap-4.*gap-4.*gap-4",
        "issue": "Repetitive spacing",
        "fix": "Vary spacing rhythmically - use the golden ratio or intentional asymmetry",
    },
    {
        "pattern": r"hover:opacity-\d+",
        "issue": "Basic opacity hover",
        "fix": "Create memorable interactions - scale, color shift, or reveal animations",
    },
]

# Creative color palettes (non-generic)
COLOR_PALETTES = {
    "midnight_gold": {
        "name": "Midnight Gold",
        "colors": {
            "bg": "#0a0a0f",
            "surface": "#14141f",
            "primary": "#d4af37",
            "accent": "#ffd700",
            "text": "#e8e6e3",
        },
        "mood": "luxury, premium, sophisticated",
    },
    "coral_reef": {
        "name": "Coral Reef",
        "colors": {
            "bg": "#fff5f0",
            "surface": "#ffe8e0",
            "primary": "#ff6b6b",
            "accent": "#4ecdc4",
            "text": "#2d3436",
        },
        "mood": "vibrant, tropical, energetic",
    },
    "forest_moss": {
        "name": "Forest Moss",
        "colors": {
            "bg": "#1a1f16",
            "surface": "#2d3428",
            "primary": "#98b475",
            "accent": "#c4a35a",
            "text": "#e8e4dc",
        },
        "mood": "organic, natural, grounded",
    },
    "neon_noir": {
        "name": "Neon Noir",
        "colors": {
            "bg": "#0d0d0d",
            "surface": "#1a1a2e",
            "primary": "#ff00ff",
            "accent": "#00ffff",
            "text": "#ffffff",
        },
        "mood": "cyberpunk, futuristic, electric",
    },
    "paper_ink": {
        "name": "Paper & Ink",
        "colors": {
            "bg": "#f5f2eb",
            "surface": "#ebe6db",
            "primary": "#1a1a1a",
            "accent": "#c41e3a",
            "text": "#2d2d2d",
        },
        "mood": "editorial, classic, refined",
    },
    "desert_sunset": {
        "name": "Desert Sunset",
        "colors": {
            "bg": "#2b1f1a",
            "surface": "#3d2c24",
            "primary": "#e07a5f",
            "accent": "#f2cc8f",
            "text": "#f4f1de",
        },
        "mood": "warm, earthy, dramatic",
    },
    "arctic_blue": {
        "name": "Arctic Blue",
        "colors": {
            "bg": "#f0f4f8",
            "surface": "#d9e2ec",
            "primary": "#334e68",
            "accent": "#1992d4",
            "text": "#102a43",
        },
        "mood": "clean, professional, trust",
    },
    "brutalist_mono": {
        "name": "Brutalist Mono",
        "colors": {
            "bg": "#ffffff",
            "surface": "#f0f0f0",
            "primary": "#000000",
            "accent": "#ff0000",
            "text": "#000000",
        },
        "mood": "raw, honest, stark",
    },
}

# Typography pairings
TYPOGRAPHY_PAIRINGS = {
    "editorial": {
        "display": "Playfair Display",
        "body": "Source Serif Pro",
        "mono": "JetBrains Mono",
    },
    "modern": {"display": "Clash Display", "body": "Satoshi", "mono": "Fira Code"},
    "brutalist": {"display": "Space Mono", "body": "Space Mono", "mono": "Space Mono"},
    "luxury": {
        "display": "Cormorant Garamond",
        "body": "Montserrat",
        "mono": "IBM Plex Mono",
    },
    "playful": {"display": "Fredoka One", "body": "Nunito", "mono": "Comic Mono"},
    "tech": {"display": "Space Grotesk", "body": "Inter", "mono": "Fira Code"},
    "organic": {
        "display": "Libre Baskerville",
        "body": "Lora",
        "mono": "Courier Prime",
    },
    "geometric": {"display": "Bebas Neue", "body": "Barlow", "mono": "Roboto Mono"},
}

# Animation presets
ANIMATION_PRESETS = {
    "fade_up": {
        "name": "Fade Up",
        "css": """@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-up { animation: fadeUp 0.6s ease-out forwards; }""",
    },
    "scale_in": {
        "name": "Scale In",
        "css": """@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}
.scale-in { animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }""",
    },
    "slide_reveal": {
        "name": "Slide Reveal",
        "css": """@keyframes slideReveal {
  from { clip-path: inset(0 100% 0 0); }
  to { clip-path: inset(0 0 0 0); }
}
.slide-reveal { animation: slideReveal 0.8s cubic-bezier(0.77, 0, 0.175, 1) forwards; }""",
    },
    "glitch": {
        "name": "Glitch Effect",
        "css": """@keyframes glitch {
  0%, 100% { transform: translate(0); }
  20% { transform: translate(-2px, 2px); }
  40% { transform: translate(-2px, -2px); }
  60% { transform: translate(2px, 2px); }
  80% { transform: translate(2px, -2px); }
}
.glitch { animation: glitch 0.3s ease-in-out infinite; }""",
    },
    "float": {
        "name": "Floating",
        "css": """@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.float { animation: float 3s ease-in-out infinite; }""",
    },
    "pulse_glow": {
        "name": "Pulse Glow",
        "css": """@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 5px var(--glow-color, #fff); }
  50% { box-shadow: 0 0 20px var(--glow-color, #fff), 0 0 40px var(--glow-color, #fff); }
}
.pulse-glow { animation: pulseGlow 2s ease-in-out infinite; }""",
    },
    "typewriter": {
        "name": "Typewriter",
        "css": """@keyframes typewriter {
  from { width: 0; }
  to { width: 100%; }
}
@keyframes blink {
  50% { border-color: transparent; }
}
.typewriter {
  overflow: hidden;
  white-space: nowrap;
  border-right: 2px solid;
  animation: typewriter 2s steps(30) forwards, blink 0.7s step-end infinite;
}""",
    },
    "morph": {
        "name": "Border Morph",
        "css": """@keyframes morph {
  0%, 100% { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; }
  50% { border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%; }
}
.morph { animation: morph 8s ease-in-out infinite; }""",
    },
}

# Background patterns
BACKGROUND_PATTERNS = {
    "noise": {
        "name": "Noise Texture",
        "css": """background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
opacity: 0.05;""",
    },
    "grid": {
        "name": "Grid Pattern",
        "css": """background-image:
  linear-gradient(var(--grid-color, rgba(0,0,0,0.1)) 1px, transparent 1px),
  linear-gradient(90deg, var(--grid-color, rgba(0,0,0,0.1)) 1px, transparent 1px);
background-size: 50px 50px;""",
    },
    "dots": {
        "name": "Dot Pattern",
        "css": """background-image: radial-gradient(circle, var(--dot-color, #000) 1px, transparent 1px);
background-size: 20px 20px;""",
    },
    "diagonal_lines": {
        "name": "Diagonal Lines",
        "css": """background-image: repeating-linear-gradient(
  45deg,
  var(--line-color, rgba(0,0,0,0.1)),
  var(--line-color, rgba(0,0,0,0.1)) 1px,
  transparent 1px,
  transparent 10px
);""",
    },
    "gradient_mesh": {
        "name": "Gradient Mesh",
        "css": """background:
  radial-gradient(at 40% 20%, var(--mesh-1, #ff6b6b) 0px, transparent 50%),
  radial-gradient(at 80% 0%, var(--mesh-2, #feca57) 0px, transparent 50%),
  radial-gradient(at 0% 50%, var(--mesh-3, #48dbfb) 0px, transparent 50%),
  radial-gradient(at 80% 50%, var(--mesh-4, #ff9ff3) 0px, transparent 50%),
  radial-gradient(at 0% 100%, var(--mesh-5, #54a0ff) 0px, transparent 50%);""",
    },
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ComponentInput(BaseModel):
    model_config = _CFG
    component_type: str = Field(
        ...,
        description="Type: button, card, hero, nav, footer, form, modal, table, list, custom",
    )
    framework: str = Field(
        default="react",
        description="Framework: react, vue, svelte, html, nextjs, astro",
    )
    aesthetic: str = Field(
        default="", description="Aesthetic direction (brutalist, minimalist, etc.)"
    )
    description: str = Field(default="", description="Custom component description")

    @field_validator("framework")
    @classmethod
    def _check_framework(cls, v: str) -> str:
        if v.lower() not in FRAMEWORKS:
            raise ValueError(f"framework must be one of {FRAMEWORKS}")
        return v.lower()


class LayoutInput(BaseModel):
    model_config = _CFG
    layout_type: str = Field(
        ...,
        description="Type: landing, dashboard, blog, portfolio, ecommerce, saas, magazine, brutalist",
    )
    framework: str = Field(default="react", description="Framework")
    aesthetic: str = Field(default="", description="Aesthetic direction")
    sections: list[str] = Field(default_factory=list, description="Sections to include")

    @field_validator("layout_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v.lower() not in LAYOUT_TYPES:
            raise ValueError(f"layout_type must be one of {LAYOUT_TYPES}")
        return v.lower()


class TypographyInput(BaseModel):
    model_config = _CFG
    style: str = Field(
        default="modern",
        description="Style: editorial, modern, brutalist, luxury, playful, tech, organic, geometric",
    )
    include_scale: bool = Field(default=True, description="Include type scale")


class ColorPaletteInput(BaseModel):
    model_config = _CFG
    mood: str = Field(default="", description="Desired mood/atmosphere")
    base_color: str = Field(default="", description="Base color to build from (hex)")
    dark_mode: bool = Field(default=False, description="Generate dark mode palette")


class AnimationInput(BaseModel):
    model_config = _CFG
    animation_type: str = Field(
        default="fade_up",
        description="Type: fade_up, scale_in, slide_reveal, glitch, float, pulse_glow, typewriter, morph",
    )
    framework: str = Field(
        default="css", description="Framework: css, framer-motion, gsap"
    )
    custom_timing: str = Field(default="", description="Custom timing function")


class BackgroundInput(BaseModel):
    model_config = _CFG
    pattern_type: str = Field(
        default="noise",
        description="Type: noise, grid, dots, diagonal_lines, gradient_mesh",
    )
    colors: list[str] = Field(default_factory=list, description="Colors to use (hex)")


class ThemeInput(BaseModel):
    model_config = _CFG
    aesthetic: str = Field(..., description="Aesthetic direction")
    framework: str = Field(
        default="css", description="Framework: css, tailwind, styled-components"
    )
    include_dark_mode: bool = Field(default=True, description="Include dark mode")


class AntipatternInput(BaseModel):
    model_config = _CFG
    code: str = Field(
        ..., min_length=10, max_length=100000, description="Code to analyze"
    )


class AestheticInput(BaseModel):
    model_config = _CFG
    context: str = Field(
        ..., min_length=5, max_length=2000, description="Project context/purpose"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Technical constraints"
    )


class ScaffoldInput(BaseModel):
    model_config = _CFG
    project_name: str = Field(
        ..., min_length=1, max_length=100, description="Project name"
    )
    framework: str = Field(default="react", description="Framework")
    aesthetic: str = Field(default="modern", description="Aesthetic direction")

    @field_validator("project_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "project_name must start with letter, contain only alphanumeric, underscore, hyphen"
            )
        return v


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _get_aesthetic(name: str) -> dict:
    """Get aesthetic configuration."""
    return AESTHETICS.get(name.lower(), AESTHETICS["minimalist"])


def _detect_antipatterns(code: str) -> list[dict]:
    """Detect generic AI slop patterns."""
    findings = []
    for ap in ANTIPATTERNS:
        if re.search(ap["pattern"], code, re.IGNORECASE):
            findings.append(
                {
                    "issue": ap["issue"],
                    "fix": ap["fix"],
                }
            )
    return findings


def _generate_component_react(component_type: str, aesthetic: dict) -> str:
    """Generate React component code."""
    aes_name = aesthetic["name"]
    chars = aesthetic["characteristics"]

    templates = {
        "button": f"""import React from 'react';
import styles from './Button.module.css';

interface ButtonProps {{
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}}

/**
 * {aes_name} Button Component
 * Characteristics: {", ".join(chars[:3])}
 */
export const Button: React.FC<ButtonProps> = ({{
  children,
  variant = 'primary',
  size = 'md',
  onClick,
}}) => {{
  return (
    <button
      className={{`${{styles.button}} ${{styles[variant]}} ${{styles[size]}}`}}
      onClick={{onClick}}
    >
      <span className={{styles.content}}>{{children}}</span>
    </button>
  );
}};
""",
        "card": f"""import React from 'react';
import styles from './Card.module.css';

interface CardProps {{
  title: string;
  description?: string;
  image?: string;
  children?: React.ReactNode;
}}

/**
 * {aes_name} Card Component
 * Characteristics: {", ".join(chars[:3])}
 */
export const Card: React.FC<CardProps> = ({{
  title,
  description,
  image,
  children,
}}) => {{
  return (
    <article className={{styles.card}}>
      {{image && (
        <div className={{styles.imageWrapper}}>
          <img src={{image}} alt={{title}} className={{styles.image}} />
        </div>
      )}}
      <div className={{styles.content}}>
        <h3 className={{styles.title}}>{{title}}</h3>
        {{description && <p className={{styles.description}}>{{description}}</p>}}
        {{children}}
      </div>
    </article>
  );
}};
""",
        "hero": f"""import React from 'react';
import styles from './Hero.module.css';

interface HeroProps {{
  headline: string;
  subheadline?: string;
  ctaText?: string;
  ctaHref?: string;
  backgroundImage?: string;
}}

/**
 * {aes_name} Hero Component
 * Characteristics: {", ".join(chars[:3])}
 */
export const Hero: React.FC<HeroProps> = ({{
  headline,
  subheadline,
  ctaText = 'Get Started',
  ctaHref = '#',
  backgroundImage,
}}) => {{
  return (
    <section
      className={{styles.hero}}
      style={{backgroundImage ? {{ backgroundImage: `url(${{backgroundImage}})` }} : undefined}}
    >
      <div className={{styles.overlay}} />
      <div className={{styles.content}}>
        <h1 className={{styles.headline}}>{{headline}}</h1>
        {{subheadline && <p className={{styles.subheadline}}>{{subheadline}}</p>}}
        <a href={{ctaHref}} className={{styles.cta}}>
          {{ctaText}}
        </a>
      </div>
    </section>
  );
}};
""",
    }

    return templates.get(component_type, templates["button"])


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def frontend_generate_component(
    component_type: str,
    framework: str = "react",
    aesthetic: str = "",
    description: str = "",
) -> str:
    """Generate a distinctive UI component. Returns component code."""
    try:
        inp = ComponentInput(
            component_type=component_type,
            framework=framework,
            aesthetic=aesthetic,
            description=description,
        )

        aes = (
            _get_aesthetic(inp.aesthetic) if inp.aesthetic else AESTHETICS["minimalist"]
        )

        if inp.framework == "react":
            code = _generate_component_react(inp.component_type, aes)
        else:
            # HTML fallback
            code = f"""<!-- {aes["name"]} {inp.component_type.title()} Component -->
<!-- Characteristics: {", ".join(aes["characteristics"][:3])} -->
<div class="{inp.component_type}">
  <!-- Add your {inp.component_type} content here -->
</div>

<style>
.{inp.component_type} {{
  /* {aes["name"]} styling */
}}
</style>
"""

        return json.dumps(
            {
                "code": code,
                "component": inp.component_type,
                "framework": inp.framework,
                "aesthetic": aes["name"],
                "characteristics": aes["characteristics"],
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_layout(
    layout_type: str,
    framework: str = "react",
    aesthetic: str = "",
    sections: list[str] | None = None,
) -> str:
    """Generate a creative page layout. Returns layout code and structure."""
    try:
        inp = LayoutInput(
            layout_type=layout_type,
            framework=framework,
            aesthetic=aesthetic,
            sections=sections or [],
        )

        aes = (
            _get_aesthetic(inp.aesthetic) if inp.aesthetic else AESTHETICS["editorial"]
        )

        default_sections = {
            "landing": ["hero", "features", "testimonials", "cta", "footer"],
            "dashboard": ["sidebar", "header", "main", "stats", "activity"],
            "blog": ["header", "featured", "grid", "sidebar", "footer"],
            "portfolio": ["hero", "work", "about", "contact"],
            "ecommerce": ["header", "hero", "products", "categories", "footer"],
            "saas": ["nav", "hero", "features", "pricing", "faq", "footer"],
            "magazine": ["masthead", "featured", "grid", "sidebar", "footer"],
            "brutalist": ["header", "content", "footer"],
        }

        layout_sections = inp.sections or default_sections.get(
            inp.layout_type, ["header", "main", "footer"]
        )

        layout_code = f"""/**
 * {aes["name"]} {inp.layout_type.title()} Layout
 * Sections: {", ".join(layout_sections)}
 */

const {inp.layout_type.title()}Layout = () => {{
  return (
    <div className="layout layout--{inp.layout_type}">
      {chr(10).join(f'      <section className="section section--{s}">{s.title()}</section>' for s in layout_sections)}
    </div>
  );
}};

export default {inp.layout_type.title()}Layout;
"""

        css_code = f"""/* {aes["name"]} Layout Styles */
.layout--{inp.layout_type} {{
  display: grid;
  min-height: 100vh;
  /* {", ".join(aes["characteristics"][:2])} */
}}

{chr(10).join(f'.section--{s} {{ /* {s} styles */ }}' for s in layout_sections)}
"""

        return json.dumps(
            {
                "layout_code": layout_code,
                "css_code": css_code,
                "layout_type": inp.layout_type,
                "sections": layout_sections,
                "aesthetic": aes["name"],
                "recommendations": aes["characteristics"],
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_typography(
    style: str = "modern",
    include_scale: bool = True,
) -> str:
    """Generate a typography system. Returns font pairing and scale."""
    try:
        inp = TypographyInput(style=style, include_scale=include_scale)

        pairing = TYPOGRAPHY_PAIRINGS.get(inp.style, TYPOGRAPHY_PAIRINGS["modern"])

        css = f"""/* {inp.style.title()} Typography System */

/* Font Imports */
@import url('https://fonts.googleapis.com/css2?family={pairing["display"].replace(" ", "+")}:wght@400;700&family={pairing["body"].replace(" ", "+")}:wght@400;500;600&family={pairing["mono"].replace(" ", "+")}&display=swap');

:root {{
  /* Font Families */
  --font-display: '{pairing["display"]}', serif;
  --font-body: '{pairing["body"]}', sans-serif;
  --font-mono: '{pairing["mono"]}', monospace;
"""

        if inp.include_scale:
            css += """
  /* Type Scale (1.25 ratio) */
  --text-xs: 0.64rem;
  --text-sm: 0.8rem;
  --text-base: 1rem;
  --text-lg: 1.25rem;
  --text-xl: 1.563rem;
  --text-2xl: 1.953rem;
  --text-3xl: 2.441rem;
  --text-4xl: 3.052rem;
  --text-5xl: 3.815rem;

  /* Line Heights */
  --leading-tight: 1.1;
  --leading-snug: 1.3;
  --leading-normal: 1.5;
  --leading-relaxed: 1.7;

  /* Letter Spacing */
  --tracking-tight: -0.02em;
  --tracking-normal: 0;
  --tracking-wide: 0.05em;
  --tracking-wider: 0.1em;
"""

        css += """}

/* Base Typography */
body {
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-display);
  line-height: var(--leading-tight);
}

code, pre {
  font-family: var(--font-mono);
}
"""

        return json.dumps(
            {
                "css": css,
                "fonts": pairing,
                "style": inp.style,
                "google_fonts_url": f"https://fonts.googleapis.com/css2?family={pairing['display'].replace(' ', '+')}&family={pairing['body'].replace(' ', '+')}&family={pairing['mono'].replace(' ', '+')}&display=swap",
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_color_palette(
    mood: str = "",
    base_color: str = "",
    dark_mode: bool = False,
) -> str:
    """Generate a distinctive color palette. Returns CSS variables and recommendations."""
    try:
        inp = ColorPaletteInput(mood=mood, base_color=base_color, dark_mode=dark_mode)

        # Find matching palette by mood
        selected = None
        if inp.mood:
            mood_lower = inp.mood.lower()
            for name, palette in COLOR_PALETTES.items():
                if any(m in mood_lower for m in palette["mood"].split(", ")):
                    selected = palette
                    break

        if not selected:
            selected = (
                COLOR_PALETTES["paper_ink"]
                if not inp.dark_mode
                else COLOR_PALETTES["midnight_gold"]
            )

        colors = selected["colors"]

        css = f"""/* {selected["name"]} Color Palette */
/* Mood: {selected["mood"]} */

:root {{
  --color-bg: {colors["bg"]};
  --color-surface: {colors["surface"]};
  --color-primary: {colors["primary"]};
  --color-accent: {colors["accent"]};
  --color-text: {colors["text"]};

  /* Semantic Colors */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;
}}
"""

        return json.dumps(
            {
                "css": css,
                "palette": selected,
                "all_palettes": list(COLOR_PALETTES.keys()),
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_animation(
    animation_type: str = "fade_up",
    framework: str = "css",
    custom_timing: str = "",
) -> str:
    """Generate animation code. Returns CSS keyframes or motion library code."""
    try:
        inp = AnimationInput(
            animation_type=animation_type,
            framework=framework,
            custom_timing=custom_timing,
        )

        preset = ANIMATION_PRESETS.get(inp.animation_type, ANIMATION_PRESETS["fade_up"])

        if inp.framework == "css":
            code = preset["css"]
        elif inp.framework == "framer-motion":
            code = f"""// {preset["name"]} with Framer Motion
import {{ motion }} from 'framer-motion';

const {inp.animation_type.title().replace("_", "")}Animation = {{
  initial: {{ opacity: 0, y: 20 }},
  animate: {{ opacity: 1, y: 0 }},
  transition: {{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }},
}};

export const AnimatedComponent = ({{ children }}) => (
  <motion.div {{...{inp.animation_type.title().replace("_", "")}Animation}}>
    {{children}}
  </motion.div>
);
"""
        else:  # gsap
            code = f"""// {preset["name"]} with GSAP
import gsap from 'gsap';

export const animate{inp.animation_type.title().replace("_", "")} = (element) => {{
  gsap.from(element, {{
    opacity: 0,
    y: 20,
    duration: 0.6,
    ease: 'back.out(1.7)',
  }});
}};
"""

        return json.dumps(
            {
                "code": code,
                "animation": preset["name"],
                "framework": inp.framework,
                "all_animations": list(ANIMATION_PRESETS.keys()),
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_background(
    pattern_type: str = "noise",
    colors: list[str] | None = None,
) -> str:
    """Generate creative background CSS. Returns pattern/texture code."""
    try:
        inp = BackgroundInput(pattern_type=pattern_type, colors=colors or [])

        pattern = BACKGROUND_PATTERNS.get(
            inp.pattern_type, BACKGROUND_PATTERNS["noise"]
        )

        css = f"""/* {pattern["name"]} Background */
.bg-{inp.pattern_type} {{
  position: relative;
}}

.bg-{inp.pattern_type}::before {{
  content: '';
  position: absolute;
  inset: 0;
  {pattern["css"]}
  pointer-events: none;
}}
"""

        return json.dumps(
            {
                "css": css,
                "pattern": pattern["name"],
                "all_patterns": list(BACKGROUND_PATTERNS.keys()),
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_theme(
    aesthetic: str,
    framework: str = "css",
    include_dark_mode: bool = True,
) -> str:
    """Generate a complete theme system. Returns CSS variables and utilities."""
    try:
        inp = ThemeInput(
            aesthetic=aesthetic,
            framework=framework,
            include_dark_mode=include_dark_mode,
        )

        aes = _get_aesthetic(inp.aesthetic)
        typography = TYPOGRAPHY_PAIRINGS.get(
            inp.aesthetic, TYPOGRAPHY_PAIRINGS["modern"]
        )

        # Find matching palette
        palette = COLOR_PALETTES.get(
            "midnight_gold" if "luxury" in inp.aesthetic else "paper_ink",
            COLOR_PALETTES["paper_ink"],
        )

        css = f"""/* {aes["name"]} Theme System */
/* Characteristics: {", ".join(aes["characteristics"])} */

:root {{
  /* Colors */
  --color-bg: {palette["colors"]["bg"]};
  --color-surface: {palette["colors"]["surface"]};
  --color-primary: {palette["colors"]["primary"]};
  --color-accent: {palette["colors"]["accent"]};
  --color-text: {palette["colors"]["text"]};

  /* Typography */
  --font-display: '{typography["display"]}', serif;
  --font-body: '{typography["body"]}', sans-serif;
  --font-mono: '{typography["mono"]}', monospace;

  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;

  /* Borders */
  --radius-sm: 0.125rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.15);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 300ms ease;
  --transition-slow: 500ms ease;
}}
"""

        if inp.include_dark_mode:
            css += """
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0a0a0f;
    --color-surface: #14141f;
    --color-text: #e8e6e3;
  }
}
"""

        return json.dumps(
            {
                "css": css,
                "aesthetic": aes["name"],
                "characteristics": aes["characteristics"],
                "typography": typography,
                "palette": palette,
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_detect_antipatterns(
    code: str,
) -> str:
    """Detect generic 'AI slop' patterns in frontend code. Returns findings."""
    try:
        inp = AntipatternInput(code=code)
        findings = _detect_antipatterns(inp.code)

        return json.dumps(
            {
                "findings": findings,
                "count": len(findings),
                "clean": len(findings) == 0,
                "message": (
                    "No generic patterns detected! Code appears distinctive."
                    if len(findings) == 0
                    else f"Found {len(findings)} generic patterns to improve."
                ),
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_suggest_aesthetic(
    context: str,
    constraints: list[str] | None = None,
) -> str:
    """Suggest bold aesthetic directions based on project context. Returns recommendations."""
    try:
        inp = AestheticInput(context=context, constraints=constraints or [])

        context_lower = inp.context.lower()

        # Score aesthetics based on context keywords
        scores = []
        keywords = {
            "brutalist": ["raw", "honest", "tech", "developer", "minimal", "stark"],
            "minimalist": ["clean", "simple", "elegant", "professional", "corporate"],
            "maximalist": ["bold", "creative", "agency", "art", "expressive"],
            "retro_futuristic": ["tech", "gaming", "cyber", "future", "digital"],
            "organic": ["nature", "wellness", "health", "eco", "sustainable"],
            "luxury": ["premium", "high-end", "exclusive", "fashion", "jewelry"],
            "playful": ["kids", "fun", "game", "toy", "entertainment"],
            "editorial": ["magazine", "blog", "news", "content", "publishing"],
            "art_deco": ["vintage", "classic", "hotel", "restaurant", "gatsby"],
            "industrial": ["construction", "manufacturing", "tools", "factory"],
        }

        for aes_key, kws in keywords.items():
            score = sum(1 for kw in kws if kw in context_lower)
            if score > 0:
                scores.append((score, aes_key))

        scores.sort(reverse=True)

        # Get top 3 recommendations
        recommendations = []
        for _, aes_key in scores[:3]:
            aes = AESTHETICS[aes_key]
            recommendations.append(
                {
                    "aesthetic": aes_key,
                    "name": aes["name"],
                    "description": aes["description"],
                    "fonts": aes["fonts"],
                    "characteristics": aes["characteristics"],
                }
            )

        # Add a wildcard suggestion
        if len(recommendations) < 3:
            recommendations.append(
                {
                    "aesthetic": "editorial",
                    "name": AESTHETICS["editorial"]["name"],
                    "description": AESTHETICS["editorial"]["description"],
                    "fonts": AESTHETICS["editorial"]["fonts"],
                    "characteristics": AESTHETICS["editorial"]["characteristics"],
                }
            )

        return json.dumps(
            {
                "recommendations": recommendations,
                "context_analyzed": inp.context[:200],
                "all_aesthetics": list(AESTHETICS.keys()),
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def frontend_generate_scaffold(
    project_name: str,
    framework: str = "react",
    aesthetic: str = "modern",
) -> str:
    """Generate complete frontend project scaffold. Returns file structure."""
    try:
        inp = ScaffoldInput(
            project_name=project_name,
            framework=framework,
            aesthetic=aesthetic,
        )

        aes = _get_aesthetic(inp.aesthetic)
        typography = TYPOGRAPHY_PAIRINGS.get(
            inp.aesthetic, TYPOGRAPHY_PAIRINGS["modern"]
        )

        files = {
            f"{inp.project_name}/src/styles/theme.css": f"""/* {aes["name"]} Theme */
:root {{
  --font-display: '{typography["display"]}', serif;
  --font-body: '{typography["body"]}', sans-serif;
}}
""",
            f"{inp.project_name}/src/styles/reset.css": """/* Modern CSS Reset */
*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; }
body { line-height: 1.5; -webkit-font-smoothing: antialiased; }
img, picture, video, canvas, svg { display: block; max-width: 100%; }
input, button, textarea, select { font: inherit; }
p, h1, h2, h3, h4, h5, h6 { overflow-wrap: break-word; }
""",
            f"{inp.project_name}/src/components/Button/Button.tsx": _generate_component_react(
                "button", aes
            ),
            f"{inp.project_name}/README.md": f"""# {inp.project_name}

A {aes["name"].lower()} frontend project.

## Aesthetic Direction
{aes["description"]}

## Characteristics
{chr(10).join(f"- {c}" for c in aes["characteristics"])}

## Typography
- Display: {typography["display"]}
- Body: {typography["body"]}
- Mono: {typography["mono"]}
""",
        }

        return json.dumps(
            {
                "project": inp.project_name,
                "framework": inp.framework,
                "aesthetic": aes["name"],
                "files": files,
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
