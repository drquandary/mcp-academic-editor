#!/usr/bin/env python3
"""
MCP Academic Editor Server

Provides surgical, line-anchored editing tools for academic manuscripts
through the Model Context Protocol (MCP).
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# MCP imports
from mcp.server.fastmcp import FastMCP
from mcp.server import NotificationOptions
from mcp.types import Resource, Tool, TextContent, ImageContent

# Local imports
from src.ingest import DocumentIngestor
from src.comment_parsers import UniversalCommentParser
from src.models import VisionBrief, Comment, Manuscript, CommentType, Priority
from src.plan import EditPlanner
from src.patch import SurgicalEditor
from src.verify import SemanticVerifier, MinimumWordCountVerifier  
from src.assemble import RevisionAssembler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Academic Editor")

# Global state
_current_manuscript: Optional[Manuscript] = None
_current_comments: List[Comment] = []
_current_vision: Optional[VisionBrief] = None
_ingestor: Optional[DocumentIngestor] = None

def _get_ingestor() -> DocumentIngestor:
    """Get or create document ingestor."""
    global _ingestor
    if _ingestor is None:
        config = {
            "preserve_formatting": True,
            "auto_detect_format": True,
            "extract_quoted_text": True,
            "infer_comment_types": True
        }
        _ingestor = DocumentIngestor(config)
    return _ingestor

@mcp.tool()
def process_manuscript(
    manuscript_path: str,
    comments_source: Union[str, List[str]] = None,
    vision_thesis: str = None,
    vision_claims: List[str] = None,
    do_not_change: List[str] = None
) -> str:
    """
    Process academic manuscript with reviewer comments.
    
    Args:
        manuscript_path: Path to manuscript file (.md, .docx, .tex)
        comments_source: Comments in any format (file path, JSON string, plain text, or list)
        vision_thesis: Core thesis statement to preserve
        vision_claims: List of key claims to maintain
        do_not_change: Sections that must not be modified
    
    Returns:
        JSON string with processing results
    """
    global _current_manuscript, _current_comments, _current_vision
    
    try:
        logger.info(f"Processing manuscript: {manuscript_path}")
        
        # Initialize ingestor
        ingestor = _get_ingestor()
        
        # Process manuscript
        manuscript_file = Path(manuscript_path)
        if not manuscript_file.exists():
            return json.dumps({
                "success": False,
                "error": f"Manuscript file not found: {manuscript_path}"
            })
        
        _current_manuscript = ingestor.ingest_manuscript(manuscript_file)
        logger.info(f"Processed manuscript with {len(_current_manuscript.spans)} spans")
        
        # Process comments if provided
        if comments_source:
            _current_comments = ingestor.ingest_comments(comments_source)
            logger.info(f"Processed {len(_current_comments)} comments")
        else:
            _current_comments = []
        
        # Create vision brief
        if vision_thesis:
            _current_vision = VisionBrief(
                thesis=vision_thesis,
                claims=vision_claims or [],
                scope="Academic manuscript revision",
                do_not_change=do_not_change or [],
                journal_style="Academic Journal"
            )
        else:
            _current_vision = VisionBrief(
                thesis="Preserve core argument while addressing reviewer concerns",
                claims=["Main findings are valid"],
                scope="Academic manuscript revision", 
                do_not_change=do_not_change or [],
                journal_style="Academic Journal"
            )
        
        # Analyze manuscript structure
        sections = set(span.section for span in _current_manuscript.spans.values())
        
        # Analyze comment types
        comment_types = {}
        for comment in _current_comments:
            ctype = comment.type.value
            comment_types[ctype] = comment_types.get(ctype, 0) + 1
        
        result = {
            "success": True,
            "manuscript": {
                "title": _current_manuscript.title,
                "total_spans": len(_current_manuscript.spans),
                "sections": list(sections),
                "word_count": len(_current_manuscript.content.split())
            },
            "comments": {
                "total": len(_current_comments),
                "types": comment_types,
                "sample": [
                    {
                        "id": comment.id,
                        "type": comment.type.value,
                        "text": comment.text[:100] + ("..." if len(comment.text) > 100 else "")
                    }
                    for comment in _current_comments[:3]
                ]
            },
            "vision": {
                "thesis": _current_vision.thesis,
                "claims": _current_vision.claims,
                "protected_sections": _current_vision.do_not_change
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error processing manuscript: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def parse_comments(source: Union[str, List[str]]) -> str:
    """
    Parse reviewer comments from any format.
    
    Args:
        source: Comments in any format:
            - File path (JSON, TXT, MD, PDF, DOCX)
            - JSON string with structured comments
            - Plain text with comments
            - List of comment strings
            - Diff-style suggestions
    
    Returns:
        JSON string with parsed comments
    """
    try:
        logger.info(f"Parsing comments from: {type(source).__name__}")
        
        ingestor = _get_ingestor()
        comments = ingestor.ingest_comments(source)
        
        result = {
            "success": True,
            "total_comments": len(comments),
            "comments": [
                {
                    "id": comment.id,
                    "source": comment.source,
                    "type": comment.type.value,
                    "text": comment.text,
                    "priority": comment.priority.value if comment.priority else "medium",
                    "links": comment.links,
                    "suggested_edit": comment.suggested_edit,
                    "rationale": comment.rationale
                }
                for comment in comments
            ],
            "type_summary": {}
        }
        
        # Add type summary
        for comment in comments:
            ctype = comment.type.value
            result["type_summary"][ctype] = result["type_summary"].get(ctype, 0) + 1
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error parsing comments: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def get_manuscript_structure() -> str:
    """
    Get detailed structure of the currently loaded manuscript.
    
    Returns:
        JSON string with manuscript structure details
    """
    if not _current_manuscript:
        return json.dumps({
            "success": False,
            "error": "No manuscript loaded. Use process_manuscript first."
        })
    
    try:
        # Group spans by section
        sections = {}
        for span_id, span in _current_manuscript.spans.items():
            section = span.section
            if section not in sections:
                sections[section] = {
                    "spans": [],
                    "paragraphs": set(),
                    "protected": False
                }
            
            sections[section]["spans"].append({
                "id": span_id,
                "type": span.block_type,
                "text": span.text[:100] + ("..." if len(span.text) > 100 else ""),
                "line_range": f"{span.start_line}-{span.end_line}",
                "protected": span.protected
            })
            
            sections[section]["paragraphs"].add(span.paragraph)
            if span.protected:
                sections[section]["protected"] = True
        
        # Convert sets to lists for JSON serialization
        for section in sections.values():
            section["paragraph_count"] = len(section["paragraphs"])
            section["paragraphs"] = sorted(section["paragraphs"])
        
        result = {
            "success": True,
            "manuscript": {
                "title": _current_manuscript.title,
                "total_spans": len(_current_manuscript.spans),
                "total_sections": len(sections)
            },
            "sections": sections
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting manuscript structure: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def create_vision_brief(
    thesis: str,
    claims: List[str],
    scope: str = "Academic manuscript revision",
    do_not_change: List[str] = None,
    journal_style: str = "Academic Journal",
    target_length: str = "maintain current"
) -> str:
    """
    Create or update vision brief for manuscript revision.
    
    Args:
        thesis: Core thesis statement to preserve
        claims: List of key claims to maintain  
        scope: Revision scope description
        do_not_change: Sections that must not be modified
        journal_style: Target journal style
        target_length: Target length instruction
    
    Returns:
        JSON string with vision brief details
    """
    global _current_vision
    
    try:
        _current_vision = VisionBrief(
            thesis=thesis,
            claims=claims,
            scope=scope,
            do_not_change=do_not_change or [],
            journal_style=journal_style,
            target_length=target_length
        )
        
        result = {
            "success": True,
            "vision_brief": {
                "thesis": _current_vision.thesis,
                "claims": _current_vision.claims,
                "scope": _current_vision.scope,
                "do_not_change": _current_vision.do_not_change,
                "journal_style": _current_vision.journal_style,
                "target_length": _current_vision.target_length
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error creating vision brief: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def analyze_comment_alignment() -> str:
    """
    Analyze how comments align with manuscript sections.
    
    Returns:
        JSON string with alignment analysis
    """
    if not _current_manuscript or not _current_comments:
        return json.dumps({
            "success": False,
            "error": "Need both manuscript and comments loaded. Use process_manuscript first."
        })
    
    try:
        # Simple keyword-based alignment analysis
        sections = list(set(span.section for span in _current_manuscript.spans.values()))
        
        alignment_results = []
        for comment in _current_comments:
            # Find potential sections based on keywords
            comment_lower = comment.text.lower()
            potential_sections = []
            
            for section in sections:
                section_keywords = section.replace('_', ' ').split()
                if any(keyword in comment_lower for keyword in section_keywords if len(keyword) > 3):
                    potential_sections.append(section)
            
            # Look for common academic section keywords
            if "method" in comment_lower or "approach" in comment_lower:
                potential_sections.extend([s for s in sections if "method" in s])
            if "result" in comment_lower or "finding" in comment_lower:
                potential_sections.extend([s for s in sections if "result" in s])
            if "introduction" in comment_lower or "intro" in comment_lower:
                potential_sections.extend([s for s in sections if "introduction" in s])
            if "conclusion" in comment_lower or "discuss" in comment_lower:
                potential_sections.extend([s for s in sections if any(x in s for x in ["conclusion", "discuss"])])
            
            alignment_results.append({
                "comment_id": comment.id,
                "comment_type": comment.type.value,
                "comment_preview": comment.text[:100] + ("..." if len(comment.text) > 100 else ""),
                "potential_sections": list(set(potential_sections)),
                "confidence": "high" if potential_sections else "manual_review_needed"
            })
        
        result = {
            "success": True,
            "total_comments": len(_current_comments),
            "total_sections": len(sections),
            "alignments": alignment_results,
            "unaligned_comments": len([a for a in alignment_results if not a["potential_sections"]]),
            "sections_available": sections
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error analyzing comment alignment: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def get_comment_types_info() -> str:
    """
    Get information about available comment types and their meanings.
    
    Returns:
        JSON string with comment type definitions
    """
    try:
        comment_types = {
            "clarify": "Requests for explanation or clarification",
            "add_citation": "Needs for additional sources or references", 
            "restructure": "Organizational or structural changes needed",
            "tighten": "Concision improvements or wordiness reduction",
            "counterargument": "Address opposing viewpoints or criticisms",
            "copyedit": "Grammar, style, or formatting fixes",
            "evidence_gap": "Missing evidence or support for claims"
        }
        
        priorities = {
            "high": "Critical issues that must be addressed",
            "medium": "Important improvements that should be made",
            "low": "Minor suggestions or nice-to-have changes"
        }
        
        result = {
            "success": True,
            "comment_types": comment_types,
            "priority_levels": priorities,
            "usage_note": "The system automatically detects comment types based on content, but you can specify types explicitly in structured formats."
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def apply_surgical_edits(
    comments_source: Union[str, List[str]] = None,
    output_directory: str = "revision_output",
    apply_edits: bool = False,
    generate_report: bool = True
) -> str:
    """
    Apply surgical edits to the loaded manuscript based on comments.
    
    Args:
        comments_source: Additional comments to process (optional)
        output_directory: Directory to save revision files
        apply_edits: Whether to actually apply edits (False = preview only)
        generate_report: Whether to generate detailed revision report
        
    Returns:
        JSON string with surgical editing results
    """
    if not _current_manuscript or not _current_vision:
        return json.dumps({
            "success": False,
            "error": "Need manuscript and vision brief loaded. Use process_manuscript first."
        })
    
    try:
        logger.info("Starting surgical editing pipeline")
        
        # Get comments (use loaded ones or new ones)
        comments = _current_comments.copy()
        if comments_source:
            ingestor = _get_ingestor()
            new_comments = ingestor.ingest_comments(comments_source)
            comments.extend(new_comments)
        
        if not comments:
            return json.dumps({
                "success": False,
                "error": "No comments available for surgical editing"
            })
        
        # Initialize surgical editing components with CRITICAL SAFETY FLAGS
        config = {
            "preserve_formatting": True,
            "verify_before_apply": True,
            "backup_original": True,
            "generate_report": generate_report,
            
            # CRITICAL: Word count protection
            "preserve_word_count": True,
            "minimum_word_count_ratio": 0.95,  # Don't reduce by more than 5%
            "augment_only_mode": True,  # Only allow additions for journal submissions
            "minimum_total_words": 8000,  # Journal requirement
            "enforce_growth_only": True  # Safer for academic papers
        }
        
        planner = EditPlanner(config)
        surgeon = SurgicalEditor(config)
        verifier = SemanticVerifier(config)
        word_count_verifier = MinimumWordCountVerifier(config)  # CRITICAL: Word count protection
        assembler = RevisionAssembler(config)
        
        # Step 1: Plan surgical edits
        logger.info("Planning surgical edits...")
        edit_intents = planner.create_edit_plan(comments, _current_manuscript, _current_vision)
        
        # CRITICAL SAFETY CHECK: Word count verification BEFORE applying edits
        logger.info("CRITICAL: Verifying word count requirements...")
        word_count_check = word_count_verifier.verify_batch_edits_word_count(edit_intents, _current_manuscript)
        if not word_count_check["safe_to_proceed"]:
            return json.dumps({
                "success": False,
                "error": f"CRITICAL: Word count safety check failed - {word_count_check['errors']}",
                "word_count_analysis": word_count_check,
                "original_word_count": len(_current_manuscript.content.split()),
                "minimum_required": config["minimum_total_words"]
            })
        
        # Step 2: Verify edits for semantic preservation
        logger.info("Verifying edits for semantic preservation...")
        verification_results = verifier.verify_batch_edits(edit_intents, _current_manuscript, _current_vision)
        
        # Filter out unsafe edits
        safe_intents = [
            intent for intent in edit_intents 
            if verification_results["individual_results"][intent.comment_id]["safe_to_apply"]
        ]
        unsafe_intents = [
            intent for intent in edit_intents
            if not verification_results["individual_results"][intent.comment_id]["safe_to_apply"]
        ]
        
        logger.info(f"Safe edits: {len(safe_intents)}, Unsafe edits: {len(unsafe_intents)}")
        
        result = {
            "success": True,
            "pipeline_stage": "planning_complete",
            "total_intents": len(edit_intents),
            "safe_intents": len(safe_intents),
            "unsafe_intents": len(unsafe_intents),
            "verification_summary": {
                "batch_thesis_preserved": verification_results["batch_thesis_preserved"],
                "batch_claims_preserved": verification_results["batch_claims_preserved"],
                "overall_safe": verification_results["overall_safe"]
            },
            "preview_edits": []
        }
        
        # Show preview of planned edits
        for intent in safe_intents[:5]:  # Show first 5
            result["preview_edits"].append({
                "comment_id": intent.comment_id,
                "operation": intent.operation,
                "edit_type": getattr(intent, "edit_type", "unknown"),
                "target_spans": intent.target_spans,
                "rationale": intent.rationale[:100] + "..." if len(intent.rationale) > 100 else intent.rationale
            })
        
        if apply_edits and safe_intents:
            # Step 3: Apply surgical edits
            logger.info("Applying surgical edits...")
            modified_manuscript, applied_edits, failed_edits = surgeon.apply_edit_intents(
                safe_intents, _current_manuscript
            )
            
            # Step 4: Assemble final revision
            logger.info("Assembling final revision...")
            from pathlib import Path
            output_path = Path(output_directory)
            assembly_result = assembler.assemble_revision(
                _current_manuscript, modified_manuscript,
                applied_edits, failed_edits + unsafe_intents,
                _current_vision, output_path
            )
            
            result.update({
                "pipeline_stage": "complete",
                "edits_applied": len(applied_edits),
                "edits_failed": len(failed_edits),
                "assembly_result": assembly_result
            })
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in surgical editing pipeline: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def preview_surgical_edits(
    comments_source: Union[str, List[str]] = None,
    max_preview: int = 10
) -> str:
    """
    Preview what surgical edits would be made without applying them.
    
    Args:
        comments_source: Additional comments to process (optional) 
        max_preview: Maximum number of edit previews to show
        
    Returns:
        JSON string with edit preview
    """
    if not _current_manuscript or not _current_vision:
        return json.dumps({
            "success": False,
            "error": "Need manuscript and vision brief loaded. Use process_manuscript first."
        })
    
    try:
        # Get comments
        comments = _current_comments.copy()
        if comments_source:
            ingestor = _get_ingestor()
            new_comments = ingestor.ingest_comments(comments_source)
            comments.extend(new_comments)
        
        # Plan edits
        config = {"preserve_formatting": True}
        planner = EditPlanner(config)
        verifier = SemanticVerifier(config)
        
        edit_intents = planner.create_edit_plan(comments, _current_manuscript, _current_vision)
        verification_results = verifier.verify_batch_edits(edit_intents, _current_manuscript, _current_vision)
        
        preview_edits = []
        for i, intent in enumerate(edit_intents[:max_preview]):
            verification = verification_results["individual_results"][intent.comment_id]
            
            preview_edits.append({
                "edit_number": i + 1,
                "comment_id": intent.comment_id,
                "operation": intent.operation,
                "edit_type": getattr(intent, "edit_type", "unknown"),
                "target_spans": intent.target_spans,
                "original_text": intent.original_text[:200] + "..." if intent.original_text and len(intent.original_text) > 200 else intent.original_text,
                "new_text": intent.new_text[:200] + "..." if intent.new_text and len(intent.new_text) > 200 else intent.new_text,
                "rationale": intent.rationale,
                "confidence": getattr(intent, "confidence", 0.5),
                "safe_to_apply": verification["safe_to_apply"],
                "semantic_similarity": verification["semantic_similarity"],
                "warnings": verification["warnings"]
            })
        
        result = {
            "success": True,
            "total_planned_edits": len(edit_intents),
            "previews_shown": len(preview_edits),
            "batch_verification": {
                "thesis_preserved": verification_results["batch_thesis_preserved"],
                "claims_preserved": verification_results["batch_claims_preserved"],
                "overall_safe": verification_results["overall_safe"]
            },
            "edit_previews": preview_edits
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error previewing surgical edits: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()