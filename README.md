# MCP Academic Editor

**Surgical manuscript editing with word count protection via Model Context Protocol**

A sophisticated academic manuscript revision system that provides surgical, line-anchored editing tools through the Model Context Protocol (MCP). Designed specifically for researchers who need precise manuscript revisions while maintaining word count requirements and semantic integrity.

## 🔒 Critical Safety Features

**Word Count Protection Guarantee**: This system will NEVER reduce your manuscript below 95% of its original word count. All edits are designed to augment and enhance your work, not replace or delete content.

- ✅ **Augmentation Mode**: Prefers additions over replacements
- ✅ **Word Count Verification**: Blocks edits that would reduce word count significantly  
- ✅ **Emergency Recovery**: Built-in backup and recovery mechanisms
- ✅ **Semantic Preservation**: Maintains your core thesis and claims
- ✅ **Journal Compliance**: Enforces minimum word count requirements (configurable, default 8000)

## 🚀 Key Features

### Intelligent Document Processing
- **Universal Format Support**: Markdown (.md), Word (.docx), LaTeX (.tex), and PDF
- **Automatic Structure Detection**: Identifies sections, paragraphs, and citation patterns
- **Comment Integration**: Processes reviewer comments from any format (plain text, JSON, files)

### Surgical Editing Engine
- **Line-Anchored Diffs**: Precise edits that preserve document structure
- **Conflict Resolution**: Handles overlapping edit suggestions intelligently
- **Span-Based Reconstruction**: Maintains formatting and cross-references

### Semantic Safety
- **Vision Brief Integration**: Preserves your core thesis and key claims
- **Protected Sections**: Mark sections as untouchable during revision
- **Verification Pipeline**: Multi-layer checks before applying any changes

## Core Philosophy

- **Thesis Preservation**: Never compromise the core argument
- **Surgical Precision**: Make minimal, targeted changes
- **Semantic Awareness**: Understand meaning, not just text
- **Reviewer Integration**: Handle feedback in any format
- **Conflict Resolution**: Detect and resolve competing edits

## Key Features

### 🎯 Surgical Line-Anchored Editing
- Precise targeting of specific manuscript sections
- Line-level granularity for exact placement
- Conflict detection between overlapping edits
- Semantic verification of changes

### 📝 Universal Comment Parsing
Handles reviewer comments in **any format**:
- JSON structured data
- Plain text feedback  
- Diff-style suggestions
- Markdown formatted reviews
- PDF annotations (via text extraction)
- Word document comments
- Lists of comment strings
- Raw text with embedded feedback

### 🧠 Semantic Preservation
- Natural Language Inference (NLI) verification
- Meaning preservation checks
- Thesis alignment validation
- Argument structure maintenance

### ⚡ Six-Stage Pipeline
1. **Ingest** - Parse manuscript and comments
2. **Align** - Match comments to manuscript locations  
3. **Plan** - Generate edit strategies
4. **Patch** - Apply surgical modifications
5. **Verify** - Ensure semantic consistency
6. **Assemble** - Produce final manuscript

## 📦 Installation

### Requirements
- Python 3.9+
- MCP-compatible client (Claude Desktop recommended)

### Quick Install
```bash
git clone https://github.com/drquandary/mcp-academic-editor.git
cd mcp-academic-editor
pip install -r requirements.txt
```

### Development Install
```bash
pip install -e ".[dev]"
```

## 🔧 Configuration

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "academic-editor": {
      "command": "/path/to/your/python3",
      "args": ["/path/to/mcp-academic-editor/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-academic-editor"
      }
    }
  }
}
```

**Important**: Use the full path to Python where MCP packages are installed:
- If using conda: `/Users/username/miniconda3/bin/python3`  
- If using system Python with pip: `/usr/local/bin/python3`
- Find your path with: `which python3`

### Standalone Usage

```bash
python3 server.py
```

## 🎯 Usage Examples

### Basic Manuscript Processing

```python
# Through MCP tools in Claude Desktop
process_manuscript(
    manuscript_path="/path/to/paper.md",
    comments_source="reviewer_comments.txt",
    vision_thesis="AI therapy creates new forms of care",
    vision_claims=[
        "Modal literacy is measurable",
        "Therapeutic encounters are embodied", 
        "AI systems participate in care practices"
    ]
)
```

### Safe Surgical Editing

```python
# Preview edits first (recommended)
preview_surgical_edits(
    comments_source="additional_comments.json",
    max_preview=10
)

# Apply edits with safety guarantees
apply_surgical_edits(
    output_directory="revision_2024",
    apply_edits=True,
    generate_report=True
)
```

### Emergency Recovery

```bash
# If something goes wrong, restore from backup
python3 scripts/emergency_recovery.py
```

### Flexible Comment Input
The system accepts comments in **any format**:

```python
# From file
editor.process_manuscript("paper.md", "comments.json")

# From text string  
editor.process_manuscript("paper.md", "Please clarify the methodology...")

# From list
comments = [
    "Add more citations in introduction",
    "Figure 2 needs better caption", 
    "Conclusion too brief"
]
editor.process_manuscript("paper.md", comments)

# From diff format
diff_feedback = """
@@ -45,7 +45,7 @@
-The sample was adequate
+The sample (n=150) was adequate for 80% power
"""
editor.process_manuscript("paper.md", diff_feedback)
```

## 🛠 Available MCP Tools

### 1. `process_manuscript`
**Purpose**: Load and analyze academic manuscripts
- Supports multiple formats (.md, .docx, .tex, .pdf)
- Auto-detects structure and sections
- Integrates vision brief for semantic preservation

### 2. `parse_comments` 
**Purpose**: Process reviewer comments from any source
- Plain text, JSON, files, or lists
- Auto-detects comment types (clarify, add_citation, restructure, etc.)
- Assigns priority levels automatically

### 3. `get_manuscript_structure`
**Purpose**: Analyze document organization
- Section mapping and span analysis
- Protected content identification
- Paragraph and heading structure

### 4. `create_vision_brief`
**Purpose**: Define revision constraints and goals
- Core thesis preservation
- Key claims protection
- Section-level protection rules

### 5. `analyze_comment_alignment`
**Purpose**: Match comments to manuscript sections
- Keyword-based section detection
- Confidence scoring for alignments
- Manual review flagging

### 6. `preview_surgical_edits`
**Purpose**: Preview changes before applying
- Safe edit filtering
- Semantic similarity scoring
- Word count impact analysis

### 7. `apply_surgical_edits`
**Purpose**: Execute manuscript revisions
- Multi-layer safety verification
- Word count protection enforcement
- Detailed revision reporting

### 8. `get_comment_types_info`
**Purpose**: Reference for comment classification
- Available comment types and meanings
- Priority level definitions
- Usage guidelines

## 🧠 Core Components

### Document Ingestor (`src/ingest.py`)
- Multi-format document parsing
- Structure extraction and span creation
- Comment parsing from various sources

### Edit Planner (`src/plan.py`)  
- Comment-to-edit translation
- Operation type determination (expand, insert_after, replace)
- **Safety Feature**: Defaults to augmentation operations

### Surgical Editor (`src/patch.py`)
- Line-anchored diff application
- Conflict detection and resolution
- **Safety Feature**: Word count verification before applying

### Semantic Verifier (`src/verify.py`)
- Thesis and claim preservation checking
- Semantic similarity analysis
- **Safety Feature**: Minimum word count enforcement

### Revision Assembler (`src/assemble.py`)
- Content reconstruction with original preservation
- Report generation
- **Safety Feature**: Fallback to original content if issues detected

## ⚙️ Configuration Options

### Word Count Protection
```python
config = {
    "preserve_word_count": True,           # Enable word count protection
    "minimum_word_count_ratio": 0.95,      # Don't reduce by more than 5%
    "augment_only_mode": True,             # Only allow additions
    "minimum_total_words": 8000,           # Journal requirement
    "enforce_growth_only": True            # Safer for academic papers
}
```

### Edit Operations
```python
config = {
    "preserve_formatting": True,           # Maintain document structure
    "verify_before_apply": True,           # Multi-layer verification
    "backup_original": True,               # Create safety backups
    "generate_report": True                # Detailed change reports
}
```

## 📊 Example Workflow

### 1. Initial Processing
```bash
# Load your manuscript and reviewer comments
process_manuscript(
    manuscript_path="my_paper.md",
    comments_source="reviews.txt", 
    vision_thesis="Your core argument here"
)
```

### 2. Analysis
```bash
# Check manuscript structure
get_manuscript_structure()

# Analyze comment alignment  
analyze_comment_alignment()
```

### 3. Safe Editing
```bash
# Preview changes first
preview_surgical_edits(max_preview=5)

# Apply with full safety checks
apply_surgical_edits(
    apply_edits=True,
    output_directory="final_revision"
)
```

## Architecture

### Data Models
- **Manuscript**: Structured document with semantic spans
- **Comment**: Reviewer feedback with type classification
- **VisionBrief**: Core thesis and constraints
- **UnifiedDiff**: Line-anchored edit operations

### Comment Types
- `CLARIFY` - Requests for explanation
- `ADD_CITATION` - Source/reference needs
- `RESTRUCTURE` - Organizational changes
- `TIGHTEN` - Concision improvements  
- `COUNTERARGUMENT` - Address opposing views
- `COPYEDIT` - Grammar/style fixes
- `EVIDENCE_GAP` - Missing support

### Processing Pipeline

```
📄 Manuscript + 💬 Comments → 🎯 Surgical Edits → 📄 Revised Manuscript
     ↓                           ↓                        ↑
  [INGEST]                   [PATCH]                 [ASSEMBLE]
     ↓                           ↑                        ↑  
  [ALIGN] ←---------------→ [PLAN] ←------------→ [VERIFY]
```

## Configuration

### config/default.yaml
```yaml
# Parsing settings
preserve_formatting: true
auto_detect_format: true
extract_quoted_text: true
infer_comment_types: true

# Alignment settings  
use_embeddings: true
similarity_threshold: 0.75
keyword_weight: 0.3
context_window: 3

# Planning settings
max_edits_per_span: 3
preserve_protected_spans: true
conflict_resolution: "prioritize_high"

# Verification settings
enable_nli_checking: true
semantic_similarity_threshold: 0.8
preserve_thesis: true
```

## Advanced Features

### Conflict Resolution
When multiple edits target the same text:
```python
# Automatic conflict detection
conflicts = editor.detect_conflicts(planned_edits)

# Resolution strategies
editor.resolve_conflicts(conflicts, strategy="prioritize_high")
```

### Semantic Verification
```python
# Check if edits preserve meaning
verification = editor.verify_edits(original_spans, modified_spans)
if not verification.thesis_preserved:
    editor.rollback_problematic_edits()
```

### Interactive Review
```python
# Review edits before applying
editor.interactive_review_mode = True
result = editor.process_manuscript(manuscript, comments)
# Prompts for approval of each edit
```

## Example Workflows

### Standard Academic Revision
```python
# Process peer review feedback
vision = VisionBrief(
    thesis="Your core argument here",
    claims=["Key claim 1", "Key claim 2"],
    do_not_change=["Methodology", "Results"]
)

editor = AcademicEditor()
result = editor.process_manuscript(
    "draft.md", 
    "peer_review.pdf",  # Automatically extracts comments
    vision
)

print(f"Applied {len(result.applied_edits)} surgical edits")
print(f"Preserved thesis: {result.verification.thesis_preserved}")
```

### Multi-Reviewer Integration
```python
# Handle multiple reviewer files
reviewer_sources = [
    "reviewer1_comments.docx",
    "reviewer2_feedback.txt", 
    "reviewer3_suggestions.json"
]

for source in reviewer_sources:
    result = editor.process_manuscript("manuscript.md", source, vision)
    editor.merge_results(result)
```

### Diff-Style Editing
```python
# Process git-style diffs
diff_comments = """
@@ -120,3 +120,5 @@ methodology section
 The analysis followed standard procedures.
+However, we acknowledge limitations in sample diversity.
+Future work should address these constraints.
"""

result = editor.process_manuscript("paper.md", diff_comments, vision)
```

## 🔍 Troubleshooting

### Word Count Issues
If you experience word count reduction:

1. **Check Safety Settings**: Ensure `augment_only_mode: true`
2. **Use Emergency Recovery**: Run `scripts/emergency_recovery.py`
3. **Review Operation Types**: Verify edits use "expand" not "replace"

### Claude Desktop Connection Issues
```bash
# Test the MCP server
python3 scripts/test_mcp_connection.py

# Validate configuration
python3 tests/test_mcp_connection.py
```

### Import Errors
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH="/path/to/mcp-academic-editor:$PYTHONPATH"
```

### Python Path Issues
If you see `ModuleNotFoundError: No module named 'mcp'`:

1. **Check your Python installation**:
   ```bash
   which python3
   python3 -c "import mcp; print('MCP installed')"
   ```

2. **Update Claude Desktop config** with the correct Python path:
   ```json
   "command": "/full/path/to/python3"
   ```

3. **Install MCP in the right environment**:
   ```bash
   # If using conda
   conda install -c conda-forge mcp
   
   # If using pip
   pip install mcp fastmcp
   ```

## 🧪 Testing

### Run Test Suite
```bash
pytest tests/ -v
```

### Test MCP Connection
```bash
python3 tests/test_mcp_connection.py
```

### Manual Testing
```bash
# Test with sample files
python3 test_flexible_parsing.py
```

Expected output:
```
Testing Flexible Comment Parsing System
==================================================
Testing JSON comments...
Parsed 2 comments from JSON string
Testing plain text comments...  
Parsed 1 comments from plain text
Testing diff-style comments...
Parsed 1 comments from diff format
Testing list of comments...
Parsed 4 comments from list
Testing markdown comments...
Parsed 2 comments from markdown
==================================================
All tests completed successfully!
The system can handle comments 'however they are given'
```

## 📚 Academic Context

This system was developed for researchers working on complex academic manuscripts that require:

- **Journal Compliance**: Meeting specific word count requirements
- **Reviewer Response**: Systematic addressing of peer review comments
- **Thesis Preservation**: Maintaining core arguments during revision
- **Citation Integrity**: Preserving reference accuracy and formatting

### Supported Academic Workflows
- Manuscript revision for journal submission
- Response to peer reviewer comments
- Collaborative editing with supervisors
- Multi-round revision cycles
- Emergency manuscript recovery

### Use Cases

#### Academic Researchers
- Revise papers based on peer review
- Maintain thesis integrity during revision
- Handle multi-reviewer feedback efficiently
- Preserve methodological sections

#### Journal Editors  
- Assist authors with revision guidance
- Standardize feedback processing
- Ensure consistent editorial quality
- Track revision compliance

#### Graduate Students
- Learn surgical editing techniques
- Process advisor feedback systematically  
- Maintain argument coherence
- Handle complex revision requirements

## 🤝 Contributing

### Development Setup
```bash
git clone https://github.com/drquandary/mcp-academic-editor.git
cd mcp-academic-editor
pip install -e ".[dev]"
pre-commit install
```

### Code Style
- Black formatting
- isort import sorting  
- mypy type checking
- pytest testing

### Pull Requests
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📋 Changelog

### v1.0.0 (2024)
- ✅ **CRITICAL FIX**: Word count protection system
- ✅ **NEW**: Augmentation-only editing mode
- ✅ **NEW**: Emergency recovery scripts
- ✅ **NEW**: Semantic preservation verification
- ✅ **NEW**: Claude Desktop integration
- ✅ **NEW**: Multi-format document support

## ⚖️ License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

### Emergency Issues
If the system has damaged your manuscript:

1. **Immediate**: Run `scripts/emergency_recovery.py`
2. **Backup**: Check for auto-created backup files
3. **Contact**: Create GitHub issue with "URGENT" label

### General Support
- 📖 **Documentation**: See `docs/` directory
- 🐛 **Bug Reports**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Contact**: [Your contact information]

## 🙏 Acknowledgments

Developed for researchers who need sophisticated manuscript revision tools without risking their work. Special thanks to the academic community for testing and feedback that led to the critical safety features.

## Citation

If you use this system in academic work, please cite:
```
@software{mcp_academic_editor,
  title={MCP Academic Editor: Surgical Manuscript Editing with Word Count Protection},
  author={Jeffrey Vadala},
  year={2024},
  url={https://github.com/drquandary/mcp-academic-editor}
}
```

---

**⚠️ Safety Guarantee**: This system is designed to enhance your academic manuscripts, never to reduce or damage them. All edits are reversible and word count is actively protected.

**"Handle comments however they are given, preserve thesis however it matters."**