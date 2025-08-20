#!/usr/bin/env python3
"""
CLI interface for MCP Academic Editor.
"""

import click
import logging
from pathlib import Path
from typing import Optional

from src.models import VisionBrief
from src.pipeline import AcademicEditor, process_manuscript_cli


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MCP Academic Editor - Surgical manuscript revision tool."""
    pass


@cli.command()
@click.argument('manuscript', type=click.Path(exists=True))
@click.argument('comments', type=click.Path(exists=True))  
@click.argument('vision', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output path for revised manuscript')
@click.option('--interactive', '-i', is_flag=True, help='Interactive review mode')
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
def process(manuscript: str, comments: str, vision: str, output: Optional[str], interactive: bool, config: Optional[str]):
    """Process a manuscript with reviewer comments."""
    click.echo(f"🔬 Processing manuscript: {manuscript}")
    click.echo(f"📝 Using comments from: {comments}")
    click.echo(f"🎯 Vision brief: {vision}")
    
    try:
        process_manuscript_cli(
            manuscript_path=manuscript,
            comments_path=comments,
            vision_path=vision,
            output_path=output,
            interactive=interactive
        )
        click.echo("✅ Processing complete!")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise


@cli.command()
@click.argument('path', type=click.Path())
@click.option('--template', '-t', default='default', help='Template to use (default, anthropology, etc.)')
def init(path: str, template: str):
    """Initialize a new project with template files."""
    project_path = Path(path)
    project_path.mkdir(exist_ok=True)
    
    click.echo(f"🚀 Initializing project in: {project_path}")
    
    # Create directory structure
    (project_path / "manuscripts").mkdir(exist_ok=True)
    (project_path / "comments").mkdir(exist_ok=True)
    (project_path / "output").mkdir(exist_ok=True)
    (project_path / "config").mkdir(exist_ok=True)
    
    # Copy template vision brief
    vision_template = {
        "thesis": "Your main thesis statement here",
        "claims": [
            "First key claim",
            "Second key claim", 
            "Third key claim"
        ],
        "scope": "Description of paper scope and length",
        "do_not_change": [
            "Core methodology",
            "Key figures and tables",
            "Essential theoretical framework"
        ],
        "journal_style": "Target journal name",
        "target_length": "maintain current"
    }
    
    vision_path = project_path / "vision_brief.json"
    VisionBrief(**vision_template).to_json(vision_path)
    
    click.echo(f"📄 Created vision brief: {vision_path}")
    click.echo(f"📁 Project structure ready!")
    click.echo(f"\nNext steps:")
    click.echo(f"1. Edit {vision_path} with your project details")
    click.echo(f"2. Place your manuscript in manuscripts/")
    click.echo(f"3. Place reviewer comments in comments/")
    click.echo(f"4. Run: mapedit process <manuscript> <comments> vision_brief.json")


@cli.command()
@click.argument('vision_path', type=click.Path(exists=True))
def validate(vision_path: str):
    """Validate a vision brief file."""
    try:
        vision = VisionBrief.from_json(vision_path)
        click.echo("✅ Vision brief is valid!")
        click.echo(f"Thesis: {vision.thesis}")
        click.echo(f"Claims: {len(vision.claims)}")
        click.echo(f"Protected elements: {len(vision.do_not_change)}")
        click.echo(f"Journal style: {vision.journal_style}")
    except Exception as e:
        click.echo(f"❌ Vision brief validation failed: {e}")


@cli.command()
@click.argument('manuscript', type=click.Path(exists=True))
def analyze(manuscript: str):
    """Analyze a manuscript structure and provide statistics."""
    click.echo(f"📊 Analyzing manuscript: {manuscript}")
    
    # Basic analysis - would expand this
    with open(manuscript) as f:
        content = f.read()
    
    lines = content.split('\n')
    words = len(content.split())
    chars = len(content)
    
    # Count sections (lines starting with #)
    sections = len([line for line in lines if line.startswith('#')])
    
    click.echo(f"Lines: {len(lines):,}")
    click.echo(f"Words: {words:,}")
    click.echo(f"Characters: {chars:,}")
    click.echo(f"Sections: {sections}")
    
    # Estimate reading time (250 words/minute)
    reading_time = words / 250
    click.echo(f"Estimated reading time: {reading_time:.1f} minutes")


@cli.command()
@click.option('--host', default='localhost', help='Host to serve on')
@click.option('--port', default=8000, help='Port to serve on')
def ui(host: str, port: int):
    """Launch the web interface."""
    try:
        import streamlit
        import subprocess
        
        click.echo(f"🌐 Launching web interface at http://{host}:{port}")
        subprocess.run([
            "streamlit", "run", "ui/app.py",
            "--server.address", host,
            "--server.port", str(port)
        ])
    except ImportError:
        click.echo("❌ Web interface dependencies not installed.")
        click.echo("Install with: pip install streamlit")
    except Exception as e:
        click.echo(f"❌ Failed to launch UI: {e}")


if __name__ == '__main__':
    cli()