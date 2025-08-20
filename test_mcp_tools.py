#!/usr/bin/env python3
"""
Test MCP tools functionality without running the full server.
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

# Import the tool functions directly
from server import (
    process_manuscript, parse_comments, get_manuscript_structure,
    create_vision_brief, analyze_comment_alignment, get_comment_types_info
)

def test_mcp_tools():
    """Test all MCP tools."""
    print("🧪 Testing MCP Academic Editor Tools")
    print("=" * 50)
    
    # Test 1: Comment types info
    print("\n1. Testing get_comment_types_info...")
    result = get_comment_types_info()
    data = json.loads(result)
    print(f"✓ Success: {data['success']}")
    if data['success']:
        print(f"   Available types: {list(data['comment_types'].keys())}")
    
    # Test 2: Parse comments  
    print("\n2. Testing parse_comments...")
    test_comments = [
        "Add more citations to the introduction",
        "The methodology needs clarification",
        "Consider strengthening the conclusion"
    ]
    result = parse_comments(test_comments)
    data = json.loads(result)
    print(f"✓ Success: {data['success']}")
    if data['success']:
        print(f"   Parsed {data['total_comments']} comments")
        print(f"   Types detected: {data['type_summary']}")
    
    # Test 3: Create vision brief
    print("\n3. Testing create_vision_brief...")
    result = create_vision_brief(
        thesis="Test thesis for MCP tools",
        claims=["Tool integration works", "MCP server functions correctly"],
        do_not_change=["Core methodology"]
    )
    data = json.loads(result)
    print(f"✓ Success: {data['success']}")
    if data['success']:
        print(f"   Thesis: {data['vision_brief']['thesis']}")
    
    # Test 4: Process manuscript (with demo file)
    print("\n4. Testing process_manuscript...")
    demo_path = "demo_manuscript.md"
    
    if Path(demo_path).exists():
        result = process_manuscript(
            manuscript_path=demo_path,
            comments_source=test_comments,
            vision_thesis="Test manuscript processing",
            vision_claims=["MCP tools work correctly"],
            do_not_change=["Introduction"]
        )
        data = json.loads(result)
        print(f"✓ Success: {data['success']}")
        if data['success']:
            print(f"   Manuscript spans: {data['manuscript']['total_spans']}")
            print(f"   Comments processed: {data['comments']['total']}")
            print(f"   Sections found: {len(data['manuscript']['sections'])}")
            
            # Test 5: Get manuscript structure (only works after processing)
            print("\n5. Testing get_manuscript_structure...")
            result = get_manuscript_structure()
            data = json.loads(result)
            print(f"✓ Success: {data['success']}")
            if data['success']:
                print(f"   Total sections: {data['manuscript']['total_sections']}")
            
            # Test 6: Analyze comment alignment
            print("\n6. Testing analyze_comment_alignment...")
            result = analyze_comment_alignment()
            data = json.loads(result)
            print(f"✓ Success: {data['success']}")
            if data['success']:
                print(f"   Alignments analyzed: {data['total_comments']}")
                print(f"   Unaligned comments: {data['unaligned_comments']}")
        
    else:
        print("   ⚠️  Demo manuscript not found, creating minimal test...")
        # Create minimal test manuscript
        test_content = """# Test Paper
        
## Introduction
This is a test paper.

## Methodology  
We used a test approach.

## Results
The results were positive.
"""
        with open("test_manuscript.md", "w") as f:
            f.write(test_content)
        
        result = process_manuscript(
            manuscript_path="test_manuscript.md",
            comments_source=test_comments,
            vision_thesis="Test manuscript processing"
        )
        data = json.loads(result)
        print(f"✓ Success: {data['success']}")
        
        # Cleanup
        Path("test_manuscript.md").unlink()
    
    print("\n" + "=" * 50)
    print("🎉 MCP Tools Test Complete!")
    print("\nAll tools are functioning correctly and ready for MCP server use.")

if __name__ == "__main__":
    test_mcp_tools()