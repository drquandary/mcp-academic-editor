# MCP Academic Editor Server Setup

## Quick Start

The MCP Academic Editor is now running as a proper MCP server that can be used directly within Claude Code and other MCP clients.

### 1. Install Dependencies

```bash
cd /Users/jeffreyvadala/Downloads/modallatour/MCPACADEMICEDITOR
pip install mcp pandas numpy pyyaml
```

### 2. Test the MCP Server

```bash
# Test that the server starts correctly
python server.py --help
```

### 3. Add to Claude Code Configuration

Add this to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "academic-editor": {
      "command": "python",
      "args": ["/Users/jeffreyvadala/Downloads/modallatour/MCPACADEMICEDITOR/server.py"],
      "cwd": "/Users/jeffreyvadala/Downloads/modallatour/MCPACADEMICEDITOR"
    }
  }
}
```

## Available MCP Tools

Once connected, you'll have these tools available in Claude Code:

### 📄 `process_manuscript`
Process academic manuscript with reviewer comments
- **manuscript_path**: Path to manuscript (.md, .docx, .tex)
- **comments_source**: Comments in any format (file, JSON, text, list)
- **vision_thesis**: Core thesis to preserve
- **vision_claims**: Key claims to maintain
- **do_not_change**: Protected sections

**Example:**
```python
process_manuscript(
    manuscript_path="/path/to/paper.md",
    comments_source="Add more citations in introduction", 
    vision_thesis="Modal literacy enables nuanced AI interaction",
    do_not_change=["Methodology", "Results"]
)
```

### 💬 `parse_comments`
Parse reviewer comments from any format
- **source**: Comments (file path, JSON, text, or list)

**Examples:**
```python
# Plain text
parse_comments("Please add more detail to the methodology section")

# JSON string
parse_comments('{"id": "1", "type": "clarify", "text": "Unclear argument"}')

# File path
parse_comments("/path/to/reviewer_comments.txt")

# List of comments
parse_comments(["Add citations", "Fix typo", "Expand conclusion"])
```

### 🏗️ `get_manuscript_structure`
Get detailed structure of loaded manuscript
- Shows sections, spans, paragraphs, protected areas

### 🎯 `create_vision_brief`
Create/update vision brief for manuscript revision
- **thesis**: Core thesis statement
- **claims**: Key claims to preserve
- **do_not_change**: Protected sections
- **journal_style**: Target style

### 🔗 `analyze_comment_alignment`
Analyze how comments align with manuscript sections
- Keyword-based section matching
- Alignment confidence scoring

### 📚 `get_comment_types_info`
Get information about comment types and classifications

## Usage Workflow

1. **Load manuscript and comments:**
   ```python
   result = process_manuscript(
       manuscript_path="paper.md",
       comments_source="reviewer_feedback.json",
       vision_thesis="Your core argument"
   )
   ```

2. **Analyze structure:**
   ```python
   structure = get_manuscript_structure()
   alignment = analyze_comment_alignment() 
   ```

3. **Parse additional comments:**
   ```python
   more_comments = parse_comments("Additional feedback text")
   ```

## Flexible Comment Input

The system handles comments "however they are given":

- **Files**: `.json`, `.txt`, `.md`, `.pdf`, `.docx`
- **Plain text**: Any reviewer feedback as string
- **Structured data**: JSON with comment objects
- **Lists**: Array of comment strings  
- **Diff format**: Git-style suggested changes

## Integration with Your Paper

For your Modal Agencies paper:

```python
# Process your paper with any reviewer feedback
process_manuscript(
    manuscript_path="/Users/jeffreyvadala/Downloads/modallatour/Modal_Agencies_Final_Revision.md",
    comments_source="Need more detail on coding procedures and intercoder reliability",
    vision_thesis="Modal literacy enables nuanced human-AI interaction", 
    vision_claims=[
        "Users develop modal literacy across AI domains",
        "Agency emerges from human-machine assemblages",
        "Power structures shape modal navigation"
    ],
    do_not_change=["Core theoretical framework", "Methodology"]
)
```

## Next Steps

1. The server is now ready to use as an MCP tool
2. Full surgical editing pipeline can be implemented
3. Comment alignment and edit planning stages available
4. Semantic verification and conflict resolution ready

The foundation is complete - you now have a working MCP server for academic manuscript editing!