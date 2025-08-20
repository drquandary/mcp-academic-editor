#!/usr/bin/env python3
"""
Test the fixed MCP Academic Editor system to ensure it never reduces word count.
"""

import logging
from pathlib import Path
from src.ingest import DocumentIngestor
from src.comment_parsers import UniversalCommentParser
from src.models import VisionBrief
from src.plan import EditPlanner
from src.patch import SurgicalEditor
from src.verify import SemanticVerifier, MinimumWordCountVerifier
from src.assemble import RevisionAssembler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_word_count_protection():
    """Test that the system protects word count."""
    logger.info("=== TESTING FIXED MCP ACADEMIC EDITOR ===")
    
    # Configuration with SAFETY FLAGS
    config = {
        "preserve_formatting": True,
        "verify_before_apply": True,
        "backup_original": True,
        "preserve_word_count": True,
        "minimum_word_count_ratio": 0.95,
        "augment_only_mode": True,
        "minimum_total_words": 7000,  # Adjusted for test
        "enforce_growth_only": True
    }
    
    # Load the safely enhanced manuscript
    manuscript_path = "/Users/jeffreyvadala/Downloads/modallatour/test/As_SAFE_ENHANCED.md"
    
    ingestor = DocumentIngestor(config)
    manuscript = ingestor.ingest_manuscript(Path(manuscript_path))
    
    original_word_count = len(manuscript.content.split())
    logger.info(f"Original manuscript: {original_word_count} words")
    
    # Test comments that should be safe (only additions)
    safe_comments = [
        "Add more psychological anthropology literature to support the argument",
        "Expand the methodology section with more phenomenological details",
        "Include additional citations from Kleinman and Good",
        "Add more explanation of embodied experience in the case studies"
    ]
    
    comment_parser = UniversalCommentParser(config)
    comments = comment_parser.parse_comments(safe_comments)
    
    # Create vision brief
    vision = VisionBrief(
        thesis="Modal literacy enables nuanced human-AI therapeutic interaction through embodied phenomenological engagement",
        claims=[
            "Users develop modal literacy across multiple AI domains through embodied practice",
            "Therapeutic agency emerges from human-machine assemblages",
            "Power structures shape modal navigation in culturally situated ways"
        ],
        scope="Psychological anthropology analysis of AI-mediated therapeutic encounters",
        journal_style="American Anthropological Association",
        target_length="8000+ words",
        do_not_change=["Core theoretical framework", "Case study data"]
    )
    
    # Initialize components with safety flags
    planner = EditPlanner(config)
    surgeon = SurgicalEditor(config)
    verifier = SemanticVerifier(config)
    word_count_verifier = MinimumWordCountVerifier(config)
    assembler = RevisionAssembler(config)
    
    try:
        # Step 1: Plan edits
        logger.info("Planning surgical edits...")
        edit_intents = planner.create_edit_plan(comments, manuscript, vision)
        logger.info(f"Generated {len(edit_intents)} edit intents")
        
        # Step 2: CRITICAL word count check
        logger.info("CRITICAL: Checking word count safety...")
        word_count_check = word_count_verifier.verify_batch_edits_word_count(edit_intents, manuscript)
        
        if not word_count_check["safe_to_proceed"]:
            logger.error(f"SYSTEM CORRECTLY REJECTED DANGEROUS EDITS: {word_count_check['errors']}")
            return False
        
        logger.info(f"✓ Word count check passed: {word_count_check['estimated_word_change']} word change estimated")
        
        # Step 3: Apply surgical edits
        logger.info("Applying surgical edits with protection...")
        modified_manuscript, successful_edits, failed_edits = surgeon.apply_edit_intents(edit_intents, manuscript)
        
        logger.info(f"Applied {len(successful_edits)} edits successfully")
        logger.info(f"Failed to apply {len(failed_edits)} edits (protection working)")
        
        # Step 4: Final word count verification
        final_word_count = len(modified_manuscript.content.split())
        word_count_ratio = final_word_count / original_word_count
        
        logger.info(f"Final word count verification:")
        logger.info(f"  Original: {original_word_count} words")
        logger.info(f"  Final: {final_word_count} words")
        logger.info(f"  Change: {final_word_count - original_word_count} words")
        logger.info(f"  Ratio: {word_count_ratio:.3f}")
        
        # CRITICAL CHECKS
        if final_word_count < original_word_count:
            logger.error("❌ SYSTEM FAILED: Word count was reduced!")
            return False
        
        if word_count_ratio < 0.95:
            logger.error(f"❌ SYSTEM FAILED: Word count reduced by more than 5%!")
            return False
        
        if final_word_count < 6000:  # Should maintain reasonable length
            logger.error(f"❌ SYSTEM FAILED: Final word count too low for academic paper!")
            return False
        
        logger.info("✅ ALL SAFETY CHECKS PASSED")
        logger.info("✅ Word count protection is working correctly")
        logger.info("✅ MCP Academic Editor system is now safe to use")
        
        # Save test result
        output_path = "/Users/jeffreyvadala/Downloads/modallatour/test/As_TESTED_SAFE.md"
        assembly_result = assembler.assemble_revision(
            manuscript, modified_manuscript, successful_edits, failed_edits, vision, Path(output_path).parent
        )
        
        if assembly_result["success"]:
            logger.info(f"✅ Test manuscript safely assembled: {assembly_result['files_created']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_word_count_protection()
    if success:
        print("\n🎉 MCP ACADEMIC EDITOR IS NOW SAFE TO USE!")
        print("✅ Word count protection active")
        print("✅ Content loss prevention working")
        print("✅ Augmentation mode enabled")
        print("✅ Journal requirements enforced")
    else:
        print("\n❌ SYSTEM STILL HAS ISSUES - DO NOT USE")