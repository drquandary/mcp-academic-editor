#!/usr/bin/env python3
"""
Test script for flexible comment parsing.
Tests the system's ability to handle comments "however they are given".
"""

import json
from pathlib import Path
from src.ingest import DocumentIngestor
from src.models import CommentType

def test_json_comments():
    """Test structured JSON comments."""
    print("Testing JSON comments...")
    
    json_comments = [
        {
            "id": "json_1",
            "source": "Reviewer A",
            "type": "revise",
            "text": "The methodology section needs more detail on data collection procedures.",
            "priority": "high"
        },
        {
            "id": "json_2", 
            "source": "Reviewer B",
            "type": "clarify",
            "text": "Please clarify the statistical analysis approach."
        }
    ]
    
    # Test as JSON string
    json_str = json.dumps(json_comments)
    
    config = {"preserve_formatting": True}
    ingestor = DocumentIngestor(config)
    
    comments = ingestor.ingest_comments(json_str)
    print(f"Parsed {len(comments)} comments from JSON string")
    for comment in comments:
        print(f"  - {comment.id}: {comment.text[:50]}...")

def test_plain_text_comments():
    """Test plain text comments."""
    print("\nTesting plain text comments...")
    
    plain_text = """
    The introduction could be stronger. Consider adding more context about the research problem.
    
    The literature review section seems incomplete. More recent studies should be included.
    
    Figure 2 is unclear and needs better labeling.
    """
    
    config = {"preserve_formatting": True}
    ingestor = DocumentIngestor(config)
    
    comments = ingestor.ingest_comments(plain_text)
    print(f"Parsed {len(comments)} comments from plain text")
    for comment in comments:
        print(f"  - {comment.id}: {comment.text[:50]}...")

def test_diff_format_comments():
    """Test diff-style comments."""
    print("\nTesting diff-style comments...")
    
    diff_text = """
    @@ -45,7 +45,7 @@ methodology section
    -The sample size was adequate for this study.
    +The sample size (n=150) was adequate for this study, providing 80% power to detect medium effect sizes.
    
    @@ -67,3 +67,5 @@ results section  
     The findings indicate significant differences between groups.
    +However, the clinical significance of these differences remains unclear.
    +Future research should examine practical implications.
    """
    
    config = {"preserve_formatting": True}
    ingestor = DocumentIngestor(config)
    
    comments = ingestor.ingest_comments(diff_text)
    print(f"Parsed {len(comments)} comments from diff format")
    for comment in comments:
        print(f"  - {comment.id}: {comment.text[:50]}...")

def test_list_comments():
    """Test list of comment strings."""
    print("\nTesting list of comments...")
    
    comment_list = [
        "The abstract needs to better summarize the key findings.",
        "Consider reorganizing the discussion section for better flow.",
        "Table 3 formatting needs improvement.",
        "Add more detail about participant recruitment."
    ]
    
    config = {"preserve_formatting": True}
    ingestor = DocumentIngestor(config)
    
    comments = ingestor.ingest_comments(comment_list)
    print(f"Parsed {len(comments)} comments from list")
    for comment in comments:
        print(f"  - {comment.id}: {comment.text[:50]}...")

def test_markdown_comments():
    """Test markdown-formatted comments."""
    print("\nTesting markdown comments...")
    
    markdown_text = """
    # Reviewer Comments
    
    ## Major Issues
    
    1. **Methodology concerns**: The sampling strategy is not clearly explained.
    2. **Statistical analysis**: Please provide more detail on the analytical approach.
    
    ## Minor Issues
    
    - Fix typo on page 5: "teh" should be "the"  
    - Citation format inconsistent in references
    - Figure 1 caption too brief
    
    ## Suggestions
    
    > Consider adding a limitations section to the discussion
    
    The paper would benefit from a more detailed conclusion.
    """
    
    config = {"preserve_formatting": True}
    ingestor = DocumentIngestor(config)
    
    comments = ingestor.ingest_comments(markdown_text)
    print(f"Parsed {len(comments)} comments from markdown")
    for comment in comments:
        print(f"  - {comment.id}: {comment.text[:50]}...")

if __name__ == "__main__":
    print("Testing Flexible Comment Parsing System")
    print("=" * 50)
    
    try:
        test_json_comments()
        test_plain_text_comments() 
        test_diff_format_comments()
        test_list_comments()
        test_markdown_comments()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("The system can handle comments 'however they are given'")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()