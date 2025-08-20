#!/usr/bin/env python3
"""
Test script for MCP Academic Editor MVP.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models import VisionBrief, Comment, CommentType
from pipeline import AcademicEditor
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def create_test_manuscript():
    """Create a simple test manuscript."""
    content = """# Modal Agencies: Test Paper

## Introduction

Large language models used for mental health support reveal forms of agency that challenge traditional frameworks. Users develop modal literacy, learning to leverage different modes of AI operation. This research examines how people navigate technical, political, and moral domains when interacting with AI systems.

## Methods

Our digital ethnography approach involved observing r/ChatGPT community discussions over eight months. We collected 1,247 posts and 8,934 comments from users describing therapeutic AI interactions.

## Findings

The most significant finding is the paradox of artificial intimacy. Users describe profound connections to AI while acknowledging how the system functions. Community discussions reveal collective understanding of modal boundaries.

## Conclusion

Agency in AI emerges through distributed assemblages rather than residing in discrete entities. Modal literacy develops through community participation and personal experimentation.
"""
    
    test_manuscript = Path("test_manuscript.md")
    with open(test_manuscript, 'w') as f:
        f.write(content)
    return test_manuscript

def create_test_comments():
    """Create test reviewer comments."""
    comments_data = [
        {
            "id": "R1-C1",
            "source": "Reviewer 1",
            "type": "clarify",
            "text": "Please define 'modal literacy' more clearly in the introduction.",
            "priority": "high"
        },
        {
            "id": "R2-C1", 
            "source": "Reviewer 2",
            "type": "add_citation",
            "text": "The claim about agency in AI needs supporting citations.",
            "priority": "medium"
        },
        {
            "id": "R3-C1",
            "source": "Reviewer 3", 
            "type": "tighten",
            "text": "The conclusion section could be more concise.",
            "priority": "low"
        }
    ]
    
    test_comments = Path("test_comments.json")
    with open(test_comments, 'w') as f:
        json.dump(comments_data, f, indent=2)
    return test_comments

def create_test_vision():
    """Create test vision brief."""
    vision_data = {
        "thesis": "Agency in AI emerges through distributed assemblages rather than residing in discrete entities",
        "claims": [
            "Users develop modal literacy through practice",
            "AI therapy operates within power structures", 
            "Modal boundaries are collectively negotiated"
        ],
        "scope": "Test paper for MVP validation",
        "do_not_change": [
            "Core modal literacy framework",
            "Research methodology section"
        ],
        "journal_style": "Test Journal",
        "target_length": "maintain current"
    }
    
    test_vision = Path("test_vision.json")
    with open(test_vision, 'w') as f:
        json.dump(vision_data, f, indent=2)
    return test_vision

def test_mvp():
    """Test the MVP pipeline."""
    print("🧪 Testing MCP Academic Editor MVP")
    print("=" * 50)
    
    # Create test files
    print("📄 Creating test files...")
    manuscript_path = create_test_manuscript()
    comments_path = create_test_comments()
    vision_path = create_test_vision()
    
    # Load vision brief
    print("🎯 Loading vision brief...")
    vision = VisionBrief.from_json(vision_path)
    print(f"   Thesis: {vision.thesis}")
    print(f"   Claims: {len(vision.claims)}")
    
    # Initialize editor
    print("🔧 Initializing editor...")
    editor = AcademicEditor()
    
    # Test individual pipeline components
    print("\n🧩 Testing pipeline components...")
    
    # 1. Test ingestion
    print("1️⃣ Testing document ingestion...")
    try:
        manuscript = editor.ingestor.ingest_manuscript(manuscript_path)
        comments = editor.ingestor.ingest_comments(comments_path)
        print(f"   ✅ Ingested manuscript with {len(manuscript.spans)} spans")
        print(f"   ✅ Ingested {len(comments)} comments")
    except Exception as e:
        print(f"   ❌ Ingestion failed: {e}")
        return False
    
    # 2. Test alignment
    print("2️⃣ Testing comment alignment...")
    try:
        aligned_comments = editor.aligner.align_comments(comments, manuscript)
        total_links = sum(len(c.links) for c in aligned_comments)
        print(f"   ✅ Aligned comments with {total_links} total links")
    except Exception as e:
        print(f"   ❌ Alignment failed: {e}")
        return False
    
    # 3. Test planning
    print("3️⃣ Testing edit planning...")
    try:
        intents = editor.planner.create_edit_plan(aligned_comments, manuscript, vision)
        print(f"   ✅ Created {len(intents)} edit intents")
        for intent in intents:
            print(f"      - {intent.comment_id}: {intent.operation} ({intent.risk_level})")
    except Exception as e:
        print(f"   ❌ Planning failed: {e}")
        return False
    
    # 4. Test patch generation
    print("4️⃣ Testing diff generation...")
    try:
        diffs = []
        for intent in intents[:2]:  # Test first 2 intents
            diff = editor.patcher.generate_diff(intent, manuscript)
            if diff:
                diffs.append(diff)
        print(f"   ✅ Generated {len(diffs)} diffs")
        for diff in diffs:
            print(f"      - {diff.span_id}: confidence {diff.confidence:.2f}")
    except Exception as e:
        print(f"   ❌ Patch generation failed: {e}")
        return False
    
    # 5. Test verification
    print("5️⃣ Testing edit verification...")
    try:
        verified_diffs = []
        for diff in diffs:
            result = editor.verifier.verify_edit(diff, manuscript, vision)
            print(f"      - {diff.span_id}: {'PASS' if result.passed else 'FAIL'} (conf: {result.confidence:.2f})")
            if result.warnings:
                print(f"        Warnings: {', '.join(result.warnings)}")
            if result.errors:
                print(f"        Errors: {', '.join(result.errors)}")
            if result.passed:
                verified_diffs.append(diff)
        print(f"   ✅ Verified {len(verified_diffs)}/{len(diffs)} diffs")
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False
    
    # 6. Test assembly
    print("6️⃣ Testing document assembly...")
    try:
        output_path = Path("test_output.md")
        final_manuscript = editor.assembler.apply_diffs(manuscript, verified_diffs, output_path)
        print(f"   ✅ Applied {len(verified_diffs)} diffs")
        print(f"   ✅ Saved to {output_path}")
        
        # Show a snippet of the result
        with open(output_path) as f:
            lines = f.readlines()[:10]
            print(f"   📄 Output preview:")
            for line in lines:
                print(f"      {line.rstrip()}")
    except Exception as e:
        print(f"   ❌ Assembly failed: {e}")
        return False
    
    print("\n🎉 MVP test completed successfully!")
    print("\nFiles created:")
    print(f"   - {manuscript_path}")
    print(f"   - {comments_path}")  
    print(f"   - {vision_path}")
    print(f"   - test_output.md")
    print(f"   - test_output.changes.md (if generated)")
    
    # Clean up
    cleanup = input("\n🧹 Clean up test files? (y/N): ").lower().strip()
    if cleanup == 'y':
        for path in [manuscript_path, comments_path, vision_path, Path("test_output.md"), Path("test_output.changes.md")]:
            try:
                path.unlink(missing_ok=True)
                print(f"   🗑️  Removed {path}")
            except Exception:
                pass
    
    return True

if __name__ == "__main__":
    success = test_mvp()
    sys.exit(0 if success else 1)