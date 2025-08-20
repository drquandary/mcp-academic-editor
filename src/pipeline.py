"""
Main processing pipeline for academic manuscript revision.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

from .models import (
    VisionBrief, Comment, Manuscript, RevisionPlan, 
    UnifiedDiff, VerificationResult, Status
)
from .ingest import DocumentIngestor
from .align import CommentAligner
from .plan import EditPlanner
from .patch import DiffGenerator
from .verify import EditVerifier
from .assemble import DocumentAssembler


logger = logging.getLogger(__name__)


class AcademicEditor:
    """
    Main pipeline orchestrator for academic manuscript revision.
    
    Implements the workflow: Ingest → Align → Plan → Patch → Verify → Assemble
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the academic editor with configuration."""
        self.config = self._load_config(config_path)
        
        # Initialize pipeline components
        self.ingestor = DocumentIngestor(self.config.get("ingest", {}))
        self.aligner = CommentAligner(self.config.get("align", {}))
        self.planner = EditPlanner(self.config.get("plan", {}))
        self.patcher = DiffGenerator(self.config.get("patch", {}))
        self.verifier = EditVerifier(self.config.get("verify", {}))
        self.assembler = DocumentAssembler(self.config.get("assemble", {}))
        
    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load configuration from file or use defaults."""
        if config_path and config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration for the pipeline."""
        return {
            "ingest": {
                "preserve_formatting": True,
                "extract_citations": True,
                "chunk_size": "paragraph"
            },
            "align": {
                "embedding_model": "all-MiniLM-L6-v2",
                "similarity_threshold": 0.7,
                "top_k": 5
            },
            "plan": {
                "classification_model": "distilbert-base-uncased",
                "risk_assessment": True,
                "conflict_detection": True
            },
            "patch": {
                "llm_model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 512,
                "locality_constraint": "paragraph"
            },
            "verify": {
                "nli_model": "roberta-large-mnli",
                "entailment_threshold": 0.8,
                "citation_validation": True,
                "style_checking": True
            },
            "assemble": {
                "conflict_resolution": "manual",
                "backup_original": True,
                "track_changes": True
            }
        }
    
    def process_manuscript(
        self,
        manuscript_path: Path,
        comments_source: Path,
        vision_brief: VisionBrief,
        output_path: Optional[Path] = None
    ) -> RevisionPlan:
        """
        Complete manuscript processing pipeline.
        
        Args:
            manuscript_path: Path to input manuscript (.docx, .md, .tex)
            comments_source: Path to reviewer comments (.pdf, .docx, or text)
            vision_brief: Project constraints and goals
            output_path: Optional output path for revised manuscript
            
        Returns:
            RevisionPlan with all edits, verifications, and metadata
        """
        logger.info(f"Starting manuscript processing: {manuscript_path}")
        
        # Step 1: Ingest
        logger.info("Step 1: Ingesting manuscript and comments")
        manuscript = self.ingestor.ingest_manuscript(manuscript_path)
        raw_comments = self.ingestor.ingest_comments(comments_source)
        
        # Step 2: Align 
        logger.info("Step 2: Aligning comments to text spans")
        aligned_comments = self.aligner.align_comments(raw_comments, manuscript)
        
        # Step 3: Plan
        logger.info("Step 3: Planning edits")
        edit_intents = self.planner.create_edit_plan(
            aligned_comments, manuscript, vision_brief
        )
        
        # Step 4: Patch
        logger.info("Step 4: Generating diffs")
        diffs = []
        for intent in edit_intents:
            diff = self.patcher.generate_diff(intent, manuscript)
            if diff:
                diffs.append(diff)
        
        # Step 5: Verify
        logger.info("Step 5: Verifying edits")
        verified_diffs = []
        for diff in diffs:
            verification = self.verifier.verify_edit(diff, manuscript, vision_brief)
            if verification.passed:
                verified_diffs.append(diff)
                # Update comment status
                for comment in aligned_comments:
                    if any(intent.comment_id == comment.id for intent in edit_intents):
                        comment.status = Status.VERIFIED
            else:
                logger.warning(f"Edit verification failed for {diff.span_id}: {verification.errors}")
        
        # Step 6: Assemble
        logger.info("Step 6: Assembling final document")
        if output_path:
            revised_manuscript = self.assembler.apply_diffs(
                manuscript, verified_diffs, output_path
            )
        
        # Create revision plan
        revision_plan = RevisionPlan(
            vision=vision_brief,
            comments=aligned_comments,
            intents=edit_intents,
            diffs=verified_diffs
        )
        
        logger.info(f"Processing complete. {len(verified_diffs)} edits applied.")
        logger.info(f"Completion rate: {revision_plan.get_completion_rate():.1%}")
        
        return revision_plan
    
    def interactive_review(self, revision_plan: RevisionPlan) -> RevisionPlan:
        """
        Interactive review mode for manual approval of edits.
        
        Args:
            revision_plan: Plan with proposed edits
            
        Returns:
            Updated plan with user decisions
        """
        print(f"\n=== Interactive Review ===")
        print(f"Total comments: {len(revision_plan.comments)}")
        print(f"Proposed edits: {len(revision_plan.diffs)}")
        print(f"Current completion rate: {revision_plan.get_completion_rate():.1%}")
        
        for i, diff in enumerate(revision_plan.diffs):
            print(f"\n--- Edit {i+1}/{len(revision_plan.diffs)} ---")
            print(f"Section: {diff.section}")
            print(f"Confidence: {diff.confidence:.2f}")
            print(f"\nProposed change:")
            print(diff.format_diff())
            
            while True:
                choice = input("\nApprove this edit? [y/n/s(kip)/q(uit)]: ").lower()
                if choice in ['y', 'yes']:
                    print("✓ Edit approved")
                    break
                elif choice in ['n', 'no']:
                    revision_plan.diffs.remove(diff)
                    print("✗ Edit rejected")
                    break
                elif choice in ['s', 'skip']:
                    print("→ Edit skipped for now")
                    break
                elif choice in ['q', 'quit']:
                    print("Exiting interactive review")
                    return revision_plan
                else:
                    print("Invalid choice. Use y/n/s/q")
        
        return revision_plan
    
    def generate_report(self, revision_plan: RevisionPlan) -> str:
        """Generate a human-readable report of all changes."""
        report = []
        report.append("# Manuscript Revision Report\n")
        
        # Summary statistics
        report.append("## Summary")
        report.append(f"- Total comments: {len(revision_plan.comments)}")
        report.append(f"- Applied edits: {len(revision_plan.diffs)}")
        report.append(f"- Completion rate: {revision_plan.get_completion_rate():.1%}")
        report.append(f"- Conflicts detected: {len(revision_plan.conflicts)}")
        report.append("")
        
        # Comment breakdown by type
        comment_types = {}
        for comment in revision_plan.comments:
            comment_types[comment.type.value] = comment_types.get(comment.type.value, 0) + 1
        
        report.append("## Comments by Type")
        for comment_type, count in comment_types.items():
            report.append(f"- {comment_type}: {count}")
        report.append("")
        
        # Detailed changes
        report.append("## Applied Changes")
        for i, diff in enumerate(revision_plan.diffs, 1):
            report.append(f"\n### Change {i}: {diff.section}")
            report.append(f"**Confidence:** {diff.confidence:.2f}")
            report.append(f"**Preserves semantics:** {'Yes' if diff.preserves_semantics else 'No'}")
            report.append(f"\n```diff")
            report.append(diff.format_diff())
            report.append("```")
        
        return "\n".join(report)


# Convenience functions for CLI usage

def process_manuscript_cli(
    manuscript_path: str,
    comments_path: str,
    vision_path: str,
    output_path: Optional[str] = None,
    interactive: bool = False
) -> None:
    """CLI wrapper for manuscript processing."""
    # Load vision brief
    vision = VisionBrief.from_json(vision_path)
    
    # Initialize editor
    editor = AcademicEditor()
    
    # Process
    plan = editor.process_manuscript(
        Path(manuscript_path),
        Path(comments_path), 
        vision,
        Path(output_path) if output_path else None
    )
    
    # Interactive review if requested
    if interactive:
        plan = editor.interactive_review(plan)
    
    # Generate report
    report = editor.generate_report(plan)
    
    # Save report
    report_path = Path(output_path).with_suffix('.report.md') if output_path else Path('revision_report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Revision complete! Report saved to {report_path}")