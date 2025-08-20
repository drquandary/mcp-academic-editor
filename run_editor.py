#!/usr/bin/env python3
"""
Simple command-line interface for MCP Academic Editor.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingest import DocumentIngestor
from src.models import VisionBrief

def create_demo_files():
    """Create demo files for testing."""
    
    # Demo manuscript
    demo_manuscript = """# Artificial Intelligence and Human Agency

## Abstract

This paper explores the relationship between artificial intelligence systems and human agency in digital environments. Through ethnographic analysis, we examine how users navigate AI interactions while maintaining autonomy.

## Introduction

Artificial intelligence has become increasingly prevalent in daily life, from recommendation systems to conversational agents. Understanding how humans maintain agency while interacting with these systems is crucial for both designers and users.

Recent studies have shown that users develop sophisticated strategies for engaging with AI while preserving their decision-making autonomy (Smith 2023). However, the mechanisms underlying these interactions remain underexplored.

## Methodology

We conducted a six-month digital ethnography study of AI user communities, focusing on how individuals discuss and strategize their AI interactions. Data collection involved participant observation and content analysis of online forums.

## Results

Our analysis revealed three key patterns in human-AI interaction:

1. **Strategic Engagement**: Users develop explicit strategies for AI interaction
2. **Boundary Maintenance**: Clear limits on AI influence in decision-making  
3. **Community Learning**: Shared knowledge development about AI capabilities

## Discussion

These findings suggest that human agency is not diminished by AI interaction but rather evolves to accommodate new technological contexts. Users demonstrate remarkable adaptability in maintaining control while leveraging AI capabilities.

## Conclusion

The relationship between AI and human agency is complex and dynamic. Rather than simple replacement or enhancement, we observe co-evolution of human strategies and AI capabilities.
"""

    # Demo comments
    demo_comments = [
        "The introduction needs more recent citations beyond Smith 2023",
        "The methodology section should include more detail about data collection procedures",
        "Consider adding a limitations section to the discussion",
        "The conclusion could benefit from implications for AI design",
        "Figure 1 referenced but not included - please add or remove reference"
    ]

    # Demo vision brief
    demo_vision = {
        "thesis": "Human agency co-evolves with AI rather than being replaced by it",
        "claims": [
            "Users develop strategic approaches to AI interaction",
            "Agency is maintained through boundary-setting practices",
            "Community knowledge shapes individual AI use"
        ],
        "scope": "Digital ethnography of human-AI interaction patterns",
        "do_not_change": ["Core methodology", "Theoretical framework"],
        "journal_style": "Digital Anthropology Quarterly"
    }
    
    # Write files
    with open("demo_manuscript.md", "w") as f:
        f.write(demo_manuscript)
    
    with open("demo_comments.json", "w") as f:
        json.dump([
            {"id": f"comment_{i+1}", "source": "Reviewer", "type": "clarify", "text": comment}
            for i, comment in enumerate(demo_comments)
        ], f, indent=2)
    
    with open("demo_vision.json", "w") as f:
        json.dump(demo_vision, f, indent=2)
    
    print("✓ Created demo_manuscript.md")
    print("✓ Created demo_comments.json")
    print("✓ Created demo_vision.json")

def run_basic_processing(manuscript_path, comments_source, vision_data=None):
    """Run basic document processing."""
    
    print(f"Processing manuscript: {manuscript_path}")
    print(f"Using comments from: {comments_source}")
    
    # Initialize ingestor
    config = {
        "preserve_formatting": True,
        "auto_detect_format": True,
        "extract_quoted_text": True
    }
    
    ingestor = DocumentIngestor(config)
    
    # Process manuscript
    try:
        manuscript = ingestor.ingest_manuscript(Path(manuscript_path))
        print(f"✓ Processed manuscript with {len(manuscript.spans)} spans")
        
        # Show structure
        sections = set(span.section for span in manuscript.spans.values())
        print(f"  Sections found: {', '.join(sections)}")
        
    except Exception as e:
        print(f"✗ Error processing manuscript: {e}")
        return
    
    # Process comments  
    try:
        comments = ingestor.ingest_comments(comments_source)
        print(f"✓ Processed {len(comments)} comments")
        
        # Show comment types
        types = [comment.type.value for comment in comments]
        type_counts = {t: types.count(t) for t in set(types)}
        print(f"  Comment types: {type_counts}")
        
    except Exception as e:
        print(f"✗ Error processing comments: {e}")
        return
    
    # Create vision brief
    if vision_data:
        try:
            vision = VisionBrief(**vision_data)
            print(f"✓ Vision brief: {vision.thesis}")
        except Exception as e:
            print(f"✗ Error creating vision brief: {e}")
            return
    else:
        vision = VisionBrief(
            thesis="Preserve core argument while addressing reviewer concerns",
            claims=["Main findings are valid", "Methodology is sound"],
            scope="Academic manuscript revision",
            do_not_change=["Results", "Core methodology"],
            journal_style="Generic Academic Journal"
        )
        print("✓ Using default vision brief")
    
    print("\n" + "="*60)
    print("📊 PROCESSING SUMMARY")
    print("="*60)
    print(f"Manuscript spans: {len(manuscript.spans)}")
    print(f"Comments received: {len(comments)}")
    print(f"Thesis: {vision.thesis}")
    
    print(f"\n📝 COMMENT DETAILS:")
    for comment in comments[:5]:  # Show first 5
        print(f"  • [{comment.type.value}] {comment.text[:80]}...")
    if len(comments) > 5:
        print(f"  ... and {len(comments) - 5} more")
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Comments have been parsed and typed")
    print("2. Manuscript structure has been analyzed")
    print("3. Ready for alignment and planning stages")
    print("4. Full pipeline implementation needed for surgical edits")
    
    return manuscript, comments, vision

def main():
    """Main CLI interface."""
    print("="*60)
    print("🔬 MCP ACADEMIC EDITOR - Getting Started")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUsage options:")
        print("  python run_editor.py demo              # Create demo files")
        print("  python run_editor.py process <manuscript> <comments>")
        print("  python run_editor.py process demo_manuscript.md demo_comments.json")
        print("\nFor flexible comment input:")
        print("  python run_editor.py process paper.md 'Please add more citations'")
        print("  python run_editor.py process paper.md comments.txt")
        print("  python run_editor.py process paper.md reviewer_feedback.pdf")
        return
    
    command = sys.argv[1].lower()
    
    if command == "demo":
        print("Creating demo files for testing...")
        create_demo_files()
        print(f"\n✅ Demo files created! Now run:")
        print(f"python run_editor.py process demo_manuscript.md demo_comments.json")
        
    elif command == "process":
        if len(sys.argv) < 4:
            print("Error: Need manuscript and comments")
            print("Usage: python run_editor.py process <manuscript> <comments>")
            return
            
        manuscript_path = sys.argv[2]
        comments_source = sys.argv[3]
        
        # Check if vision file exists
        vision_data = None
        vision_file = Path("demo_vision.json")
        if vision_file.exists():
            try:
                with open(vision_file) as f:
                    vision_data = json.load(f)
                    print("✓ Using demo_vision.json")
            except Exception as e:
                print(f"Warning: Could not load vision file: {e}")
        
        # Check if files exist
        if not Path(manuscript_path).exists():
            print(f"Error: Manuscript file not found: {manuscript_path}")
            return
            
        # Comments can be file or string
        comments_is_file = (
            len(comments_source) < 200 and
            (Path(comments_source).exists() or 
             comments_source.endswith(('.txt', '.json', '.md', '.pdf', '.docx')))
        )
        
        if comments_is_file and not Path(comments_source).exists():
            print(f"Error: Comments file not found: {comments_source}")
            return
        
        print(f"Processing with flexible comment input...")
        print(f"Comments detected as: {'file' if comments_is_file else 'text string'}")
        
        run_basic_processing(manuscript_path, comments_source, vision_data)
        
    else:
        print(f"Unknown command: {command}")
        print("Use 'demo' or 'process'")

if __name__ == "__main__":
    main()