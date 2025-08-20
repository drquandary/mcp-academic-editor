#!/bin/bash

# MCP Academic Editor - GitHub Deployment Script
# This script will initialize git, create commits, and prepare for GitHub push

echo "🚀 Deploying MCP Academic Editor to GitHub..."
echo "================================================"

# Check if we're in the right directory
if [ ! -f "server.py" ] || [ ! -f "README.md" ]; then
    echo "❌ Error: Not in the correct project directory"
    echo "Please run this script from the MCPACADEMICEDITOR directory"
    exit 1
fi

# Initialize git repository if not already done
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "📁 Git repository already exists"
fi

# Create .gitignore
echo "📝 Creating .gitignore..."
cat > .gitignore << EOF
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# macOS
.DS_Store

# Backup files
*.backup
*.bak
*~

# Test outputs
test_output/
revision_output/
*.log

# Development files
.env.local
.env.development
.env.test
EOF

# Add all files to git
echo "📦 Adding files to git..."
git add .

# Check git status
echo "📊 Git status:"
git status --short

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "feat: initial release of MCP Academic Editor with word count protection

🔒 CRITICAL SAFETY FEATURES:
- Word count protection guarantees (95% minimum retention)
- Augmentation-only mode for journal submissions  
- Emergency recovery system for manuscript safety
- Multi-layer verification prevents destructive edits

🚀 CORE CAPABILITIES:
- Surgical editing with line-anchored diffs
- Multi-format document support (.md, .docx, .tex, .pdf)
- Universal comment parsing (any format)
- Semantic preservation of thesis and claims
- Claude Desktop MCP integration

🛠 COMPONENTS:
- Document ingestor with structure detection
- Edit planner with conflict resolution
- Surgical editor with word count verification
- Semantic verifier with NLI checking
- Revision assembler with backup systems

📚 ACADEMIC FOCUS:
- Journal submission workflow support
- Peer review response handling
- Collaborative editing tools
- Research manuscript preservation

🎯 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

echo "✅ Initial commit created"

echo ""
echo "🎉 Git repository prepared successfully!"
echo "================================================"
echo ""
echo "📋 NEXT STEPS TO COMPLETE GITHUB DEPLOYMENT:"
echo ""
echo "1️⃣  CREATE GITHUB REPOSITORY:"
echo "   • Go to https://github.com"
echo "   • Click 'New repository'"
echo "   • Repository name: mcp-academic-editor"
echo "   • Description: 'Surgical manuscript editing with word count protection via Model Context Protocol'"
echo "   • Make it PUBLIC (recommended)"
echo "   • DON'T initialize with README (we have one)"
echo ""
echo "2️⃣  PUSH TO GITHUB:"
echo "   Replace YOUR_USERNAME with your GitHub username and run:"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/mcp-academic-editor.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3️⃣  ADD REPOSITORY TOPICS (optional):"
echo "   On GitHub, add these topics to your repository:"
echo "   academic-writing, manuscript-editing, word-count-protection, mcp, anthropology, research, surgical-editing"
echo ""
echo "🔒 SAFETY GUARANTEE: This system protects your manuscripts and will never reduce word count below 95%"
echo ""

# Make the script executable
chmod +x deploy_to_github.sh

echo "💡 TIP: You can also run 'bash deploy_to_github.sh' to see these instructions again"