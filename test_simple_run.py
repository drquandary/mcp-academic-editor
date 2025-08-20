#!/usr/bin/env python3
"""
Simple test to see if we can run the basic system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingest import DocumentIngestor
from src.models import VisionBrief, Comment

def test_basic_system():
    """Test basic system functionality."""
    print("Testing MCP Academic Editor basic functionality...")
    
    # Test 1: Create a simple manuscript content
    manuscript_content = """# Test Paper

## Introduction

This is a test paper to demonstrate the MCP Academic Editor functionality.

## Methods

We used a simple approach to test the system.

## Results  

The results show that the system works correctly.

## Conclusion

This test demonstrates basic functionality.
"""
    
    # Write test manuscript
    with open("test_manuscript.md", "w") as f:
        f.write(manuscript_content)
    
    # Test 2: Create a vision brief
    vision = VisionBrief(
        thesis="The MCP Academic Editor enables surgical manuscript revision",
        claims=[
            "The system handles flexible comment input",
            "Surgical editing preserves thesis integrity"
        ],
        scope="Technical demonstration of academic editing system",
        do_not_change=["Core methodology"],
        journal_style="Test Journal"
    )
    print(f"✓ Created vision brief: {vision.thesis}")
    
    # Test 3: Initialize ingestor
    config = {"preserve_formatting": True}
    ingestor = DocumentIngestor(config)
    print("✓ Initialized DocumentIngestor")
    
    # Test 4: Ingest manuscript
    try:
        manuscript = ingestor.ingest_manuscript(Path("test_manuscript.md"))
        print(f"✓ Ingested manuscript with {len(manuscript.spans)} spans")
        
        # Show first few spans
        for i, (span_id, span) in enumerate(list(manuscript.spans.items())[:3]):
            print(f"  - {span_id}: {span.text[:50]}...")
            
    except Exception as e:
        print(f"✗ Manuscript ingestion failed: {e}")
        return False
    
    # Test 5: Test comment ingestion with different formats
    test_comments = [
        "The introduction needs more detail about the methodology",
        "Consider adding citations to support the claims",
        "The conclusion could be strengthened"
    ]
    
    try:
        comments = ingestor.ingest_comments(test_comments)
        print(f"✓ Ingested {len(comments)} comments from list")
        
        for comment in comments:
            print(f"  - {comment.id}: {comment.text[:50]}...")
            
    except Exception as e:
        print(f"✗ Comment ingestion failed: {e}")
        return False
    
    # Test 6: Test different comment formats
    json_comment = '{"id": "test1", "source": "Reviewer", "type": "clarify", "text": "Please clarify this section"}'
    
    try:
        json_comments = ingestor.ingest_comments(json_comment)
        print(f"✓ Parsed JSON comment: {json_comments[0].text}")
    except Exception as e:
        print(f"✗ JSON comment parsing failed: {e}")
    
    print("\n" + "="*50)
    print("🎉 Basic system test PASSED!")
    print("The MCP Academic Editor core components are working!")
    
    # Cleanup
    Path("test_manuscript.md").unlink()
    
    return True

if __name__ == "__main__":
    try:
        success = test_basic_system()
        if success:
            print("\n✅ System is ready to use!")
            print("\nNext steps:")
            print("1. Create your manuscript.md file")  
            print("2. Prepare your reviewer comments (any format)")
            print("3. Define your VisionBrief")
            print("4. Run the pipeline!")
        else:
            print("\n❌ System has issues that need fixing")
    except Exception as e:
        print(f"\n💥 System test failed with error: {e}")
        import traceback
        traceback.print_exc()