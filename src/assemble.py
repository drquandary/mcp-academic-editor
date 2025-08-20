"""
Document assembly - create final manuscript from surgical edits.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import difflib
from datetime import datetime
import json

from .models import Manuscript, EditIntent, ManuscriptSpan, VisionBrief, UnifiedDiff

logger = logging.getLogger(__name__)


class RevisionAssembler:
    """Assemble final manuscript from surgical edits with tracking and reporting."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.backup_original = config.get("backup_original", True)
        self.generate_report = config.get("generate_report", True)
        self.preserve_formatting = config.get("preserve_formatting", True)
        self.output_formats = config.get("output_formats", ["md"])
        
    def assemble_revision(
        self,
        original_manuscript: Manuscript,
        modified_manuscript: Manuscript,
        applied_edits: List[EditIntent],
        failed_edits: List[EditIntent],
        vision: VisionBrief,
        output_path: Path
    ) -> Dict[str, any]:
        """
        Create final revised manuscript with complete documentation.
        
        Args:
            original_manuscript: Original manuscript
            modified_manuscript: Manuscript with applied edits
            applied_edits: Successfully applied edit intents
            failed_edits: Failed edit intents
            vision: Project vision brief
            output_path: Output directory path
            
        Returns:
            Dict with assembly results and file paths
        """
        logger.info(f"Assembling revision with {len(applied_edits)} applied edits")
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            "success": True,
            "output_dir": str(output_dir),
            "files_created": [],
            "applied_edits": len(applied_edits),
            "failed_edits": len(failed_edits),
            "edit_summary": {}
        }
        
        try:
            # 1. Backup original if requested
            if self.backup_original:
                backup_path = self._create_backup(original_manuscript, output_dir)
                result["files_created"].append(str(backup_path))
            
            # 2. Generate final manuscript
            final_path = self._write_final_manuscript(modified_manuscript, output_dir)
            result["files_created"].append(str(final_path))
            
            # 3. Generate revision report
            if self.generate_report:
                report_path = self._generate_revision_report(
                    original_manuscript, modified_manuscript, 
                    applied_edits, failed_edits, vision, output_dir
                )
                result["files_created"].append(str(report_path))
            
            # 4. Generate edit summary
            result["edit_summary"] = self._create_edit_summary(applied_edits, failed_edits)
            
            # 5. Create diff file
            diff_path = self._create_diff_file(
                original_manuscript, modified_manuscript, output_dir
            )
            result["files_created"].append(str(diff_path))
            
            logger.info(f"Assembly complete. Created {len(result['files_created'])} files.")
            
        except Exception as e:
            logger.error(f"Error during assembly: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def _create_backup(self, manuscript: Manuscript, output_dir: Path) -> Path:
        """Create backup of original manuscript."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = output_dir / f"original_backup_{timestamp}.md"
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(manuscript.content)
        
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def _write_final_manuscript(self, manuscript: Manuscript, output_dir: Path) -> Path:
        """Write the final revised manuscript."""
        final_path = output_dir / "revised_manuscript.md"
        
        # Ensure content is properly assembled
        final_content = self._reconstruct_content(manuscript)
        
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        logger.info(f"Created final manuscript: {final_path}")
        return final_path
    
    def _reconstruct_content(self, manuscript: Manuscript) -> str:
        """CRITICAL FIX: Reconstruct manuscript content preserving ALL original content."""
        
        # SAFETY CHECK: Never return content shorter than original
        original_content = manuscript.content
        original_word_count = len(original_content.split())
        
        # If we have no spans or something went wrong, return original content
        if not manuscript.spans:
            logger.warning("No spans found - returning original content to prevent data loss")
            return original_content
        
        # Try span-based reconstruction first
        try:
            # Get original lines for fallback
            original_lines = original_content.split('\n')
            reconstructed_lines = original_lines.copy()  # Start with original as base
            
            # Sort spans by line number
            sorted_spans = sorted(manuscript.spans.values(), key=lambda s: s.start_line)
            
            # Apply span changes to specific lines only
            for span in sorted_spans:
                start_line = max(0, span.start_line - 1)  # 0-based indexing
                end_line = min(len(original_lines) - 1, span.end_line - 1)
                
                if start_line < len(reconstructed_lines):
                    # Replace only the specific lines covered by this span
                    span_lines = span.text.split('\n')
                    reconstructed_lines[start_line:end_line+1] = span_lines
            
            reconstructed_content = '\n'.join(reconstructed_lines)
            
            # CRITICAL SAFETY CHECK: Word count validation
            reconstructed_word_count = len(reconstructed_content.split())
            word_count_ratio = reconstructed_word_count / max(original_word_count, 1)
            
            if word_count_ratio < 0.9:  # More than 10% reduction
                logger.error(f"CRITICAL: Reconstruction would reduce word count from {original_word_count} to {reconstructed_word_count} (ratio: {word_count_ratio:.2f})")
                logger.error("Falling back to original content to prevent data loss")
                return original_content
            
            logger.info(f"Successful reconstruction: {original_word_count} → {reconstructed_word_count} words (ratio: {word_count_ratio:.2f})")
            return reconstructed_content
            
        except Exception as e:
            logger.error(f"Error in content reconstruction: {e}")
            logger.error("Falling back to original content to prevent data loss")
            return original_content
    
    def _generate_revision_report(
        self,
        original: Manuscript,
        modified: Manuscript,
        applied_edits: List[EditIntent],
        failed_edits: List[EditIntent],
        vision: VisionBrief,
        output_dir: Path
    ) -> Path:
        """Generate comprehensive revision report."""
        report_path = output_dir / "revision_report.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report_content = f"""# Manuscript Revision Report
Generated: {timestamp}

## Vision Brief
**Thesis:** {vision.thesis}

**Key Claims:**
{chr(10).join(f"- {claim}" for claim in vision.claims)}

**Protected Sections:** {', '.join(vision.do_not_change)}

**Journal Style:** {vision.journal_style}

## Revision Summary

### Applied Edits ({len(applied_edits)})
"""
        
        # Group edits by type for summary
        edit_types = {}
        for edit in applied_edits:
            edit_type = getattr(edit, 'edit_type', 'unknown')
            if edit_type not in edit_types:
                edit_types[edit_type] = []
            edit_types[edit_type].append(edit)
        
        for edit_type, edits in edit_types.items():
            report_content += f"\n#### {edit_type.replace('_', ' ').title()} ({len(edits)} edits)\n"
            for edit in edits[:5]:  # Show first 5 of each type
                comment_preview = edit.rationale[:100] + "..." if len(edit.rationale) > 100 else edit.rationale
                report_content += f"- **{edit.comment_id}**: {comment_preview}\n"
            if len(edits) > 5:
                report_content += f"- ... and {len(edits) - 5} more\n"
        
        # Failed edits section
        if failed_edits:
            report_content += f"\n### Failed Edits ({len(failed_edits)})\n"
            for edit in failed_edits:
                reason = getattr(edit, 'rationale', 'Unknown reason')
                report_content += f"- **{edit.comment_id}**: {reason}\n"
        
        # Statistics
        total_spans = len(modified.spans)
        modified_spans = len(set().union(*[edit.target_spans for edit in applied_edits]))
        
        report_content += f"""
## Statistics
- **Original manuscript spans:** {len(original.spans)}
- **Final manuscript spans:** {total_spans}
- **Spans modified:** {modified_spans}
- **Modification rate:** {(modified_spans/total_spans)*100:.1f}%
- **Success rate:** {(len(applied_edits)/(len(applied_edits)+len(failed_edits)))*100:.1f}%

## Files Generated
- `revised_manuscript.md` - Final revised manuscript
- `revision_diff.patch` - Unified diff showing all changes
- `original_backup_*.md` - Backup of original manuscript
- `revision_report.md` - This report

---
*Generated by MCP Academic Editor - Surgical manuscript revision system*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Generated revision report: {report_path}")
        return report_path
    
    def _create_edit_summary(self, applied_edits: List[EditIntent], failed_edits: List[EditIntent]) -> Dict:
        """Create structured summary of edits."""
        summary = {
            "total_edits_attempted": len(applied_edits) + len(failed_edits),
            "successful_edits": len(applied_edits),
            "failed_edits": len(failed_edits),
            "success_rate": len(applied_edits) / max(len(applied_edits) + len(failed_edits), 1),
            "edit_types": {},
            "target_sections": {}
        }
        
        # Analyze by edit type
        all_edits = applied_edits + failed_edits
        for edit in all_edits:
            edit_type = getattr(edit, 'edit_type', 'unknown')
            if edit_type not in summary["edit_types"]:
                summary["edit_types"][edit_type] = {"applied": 0, "failed": 0}
            
            if edit in applied_edits:
                summary["edit_types"][edit_type]["applied"] += 1
            else:
                summary["edit_types"][edit_type]["failed"] += 1
        
        # Analyze by target section
        for edit in applied_edits:
            for span_id in edit.target_spans:
                # Extract section from span_id
                section = span_id.split('_')[1] if '_' in span_id else 'unknown'
                summary["target_sections"][section] = summary["target_sections"].get(section, 0) + 1
        
        return summary
    
    def _create_diff_file(self, original: Manuscript, modified: Manuscript, output_dir: Path) -> Path:
        """Create unified diff file showing all changes."""
        diff_path = output_dir / "revision_diff.patch"
        
        original_lines = original.content.splitlines(keepends=True)
        modified_lines = modified.content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="original_manuscript.md",
            tofile="revised_manuscript.md",
            lineterm=""
        )
        
        with open(diff_path, 'w', encoding='utf-8') as f:
            f.writelines(diff)
        
        logger.info(f"Created diff file: {diff_path}")
        return diff_path


class DocumentAssembler:
    """Apply verified diffs to create the final revised manuscript."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.conflict_resolution = config.get("conflict_resolution", "manual")
        self.backup_original = config.get("backup_original", True)
        self.track_changes = config.get("track_changes", True)
        self.output_formats = config.get("output_formats", [".md"])
        
    def apply_diffs(
        self, 
        manuscript: Manuscript, 
        diffs: List[UnifiedDiff], 
        output_path: Path
    ) -> Manuscript:
        """
        Apply verified diffs to manuscript and save result.
        
        Args:
            manuscript: Original manuscript
            diffs: List of verified diffs to apply
            output_path: Path for output file
            
        Returns:
            Updated manuscript object
        """
        logger.info(f"Applying {len(diffs)} diffs to manuscript")
        
        # Backup original if requested
        if self.backup_original:
            self._backup_original(manuscript, output_path)
        
        # Sort diffs by line number to apply in order
        sorted_diffs = sorted(diffs, key=lambda d: d.line_start, reverse=True)
        
        # Detect and resolve conflicts
        conflicts = self._detect_conflicts(sorted_diffs)
        if conflicts:
            resolved_diffs = self._resolve_conflicts(sorted_diffs, conflicts)
        else:
            resolved_diffs = sorted_diffs
        
        # Apply diffs to content
        updated_content = self._apply_diffs_to_content(manuscript.content, resolved_diffs)
        
        # Update manuscript object
        updated_manuscript = self._create_updated_manuscript(manuscript, updated_content, resolved_diffs)
        
        # Save to file(s)
        self._save_manuscript(updated_manuscript, output_path)
        
        # Generate change log if tracking enabled
        if self.track_changes:
            self._generate_change_log(resolved_diffs, output_path)
        
        logger.info(f"Successfully applied {len(resolved_diffs)} diffs")
        return updated_manuscript
    
    def _backup_original(self, manuscript: Manuscript, output_path: Path) -> None:
        """Create backup of original manuscript."""
        backup_path = output_path.with_suffix(f".backup{output_path.suffix}")
        
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(manuscript.content)
            logger.info(f"Original manuscript backed up to: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    def _detect_conflicts(self, diffs: List[UnifiedDiff]) -> List[Tuple[int, int]]:
        """Detect overlapping diffs that might conflict."""
        conflicts = []
        
        for i, diff1 in enumerate(diffs):
            for j, diff2 in enumerate(diffs[i+1:], i+1):
                # Check if line ranges overlap
                if self._ranges_overlap(
                    (diff1.line_start, diff1.line_end),
                    (diff2.line_start, diff2.line_end)
                ):
                    conflicts.append((i, j))
                    logger.warning(
                        f"Conflict detected between diffs {diff1.span_id} and {diff2.span_id}"
                    )
        
        return conflicts
    
    def _ranges_overlap(self, range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
        """Check if two line ranges overlap."""
        start1, end1 = range1
        start2, end2 = range2
        return not (end1 < start2 or end2 < start1)
    
    def _resolve_conflicts(
        self, 
        diffs: List[UnifiedDiff], 
        conflicts: List[Tuple[int, int]]
    ) -> List[UnifiedDiff]:
        """Resolve conflicts between diffs."""
        if self.conflict_resolution == "manual":
            return self._manual_conflict_resolution(diffs, conflicts)
        elif self.conflict_resolution == "confidence":
            return self._confidence_based_resolution(diffs, conflicts)
        elif self.conflict_resolution == "first_wins":
            return self._first_wins_resolution(diffs, conflicts)
        else:
            logger.warning(f"Unknown conflict resolution: {self.conflict_resolution}")
            return diffs
    
    def _manual_conflict_resolution(
        self, 
        diffs: List[UnifiedDiff], 
        conflicts: List[Tuple[int, int]]
    ) -> List[UnifiedDiff]:
        """Manual conflict resolution (for now, just skip conflicting diffs)."""
        # For MVP, skip all conflicting diffs
        conflicting_indices = set()
        for i, j in conflicts:
            conflicting_indices.update([i, j])
        
        resolved = []
        for i, diff in enumerate(diffs):
            if i not in conflicting_indices:
                resolved.append(diff)
            else:
                logger.info(f"Skipping conflicting diff {diff.span_id}")
        
        return resolved
    
    def _confidence_based_resolution(
        self, 
        diffs: List[UnifiedDiff], 
        conflicts: List[Tuple[int, int]]
    ) -> List[UnifiedDiff]:
        """Resolve conflicts by keeping highest confidence diff."""
        skip_indices = set()
        
        for i, j in conflicts:
            diff1, diff2 = diffs[i], diffs[j]
            if diff1.confidence > diff2.confidence:
                skip_indices.add(j)
                logger.info(f"Keeping {diff1.span_id} over {diff2.span_id} (higher confidence)")
            else:
                skip_indices.add(i)
                logger.info(f"Keeping {diff2.span_id} over {diff1.span_id} (higher confidence)")
        
        return [diff for i, diff in enumerate(diffs) if i not in skip_indices]
    
    def _first_wins_resolution(
        self, 
        diffs: List[UnifiedDiff], 
        conflicts: List[Tuple[int, int]]
    ) -> List[UnifiedDiff]:
        """Resolve conflicts by keeping the first diff."""
        skip_indices = set()
        
        for i, j in conflicts:
            skip_indices.add(j)  # Skip the second one
            logger.info(f"Keeping {diffs[i].span_id}, skipping {diffs[j].span_id} (first wins)")
        
        return [diff for i, diff in enumerate(diffs) if i not in skip_indices]
    
    def _apply_diffs_to_content(self, content: str, diffs: List[UnifiedDiff]) -> str:
        """Apply diffs to manuscript content."""
        lines = content.split('\n')
        
        # Apply diffs in reverse order (highest line numbers first) to preserve line numbering
        for diff in diffs:
            lines = self._apply_single_diff(lines, diff)
        
        return '\n'.join(lines)
    
    def _apply_single_diff(self, lines: List[str], diff: UnifiedDiff) -> List[str]:
        """Apply a single diff to the lines list."""
        start_idx = diff.line_start - 1  # Convert to 0-based indexing
        end_idx = diff.line_end - 1
        
        # Validate line ranges
        if start_idx < 0 or end_idx >= len(lines):
            logger.warning(f"Diff {diff.span_id} has invalid line range: {diff.line_start}-{diff.line_end}")
            return lines
        
        # Find the actual text to replace (might span multiple lines)
        old_text_lines = []
        for i in range(start_idx, end_idx + 1):
            old_text_lines.append(lines[i])
        
        current_old_text = '\n'.join(old_text_lines)
        
        # Check if old text matches expectation
        if not self._text_matches(current_old_text, diff.old_text):
            logger.warning(f"Old text mismatch for diff {diff.span_id}")
            logger.debug(f"Expected: {diff.old_text[:100]}...")
            logger.debug(f"Found: {current_old_text[:100]}...")
            # Still apply, but log the issue
        
        # Split new text into lines
        new_text_lines = diff.new_text.split('\n') if diff.new_text else ['']
        
        # Replace the lines
        new_lines = lines[:start_idx] + new_text_lines + lines[end_idx + 1:]
        
        return new_lines
    
    def _text_matches(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are similar enough to be considered a match."""
        # Normalize whitespace
        norm1 = ' '.join(text1.split())
        norm2 = ' '.join(text2.split())
        
        if norm1 == norm2:
            return True
        
        # Use sequence similarity
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= threshold
    
    def _create_updated_manuscript(
        self, 
        original: Manuscript, 
        updated_content: str, 
        applied_diffs: List[UnifiedDiff]
    ) -> Manuscript:
        """Create updated manuscript object with new content."""
        # For MVP, create a simple updated manuscript
        # In full implementation, would reparse the updated content
        
        updated_manuscript = Manuscript(
            title=original.title,
            content=updated_content,
            spans=original.spans,  # Would need to re-parse spans
            metadata=original.metadata,
            citations=original.citations,
            figures=original.figures,
            tables=original.tables
        )
        
        # Update metadata to reflect changes
        updated_manuscript.metadata['last_modified'] = datetime.now().isoformat()
        updated_manuscript.metadata['applied_diffs'] = len(applied_diffs)
        
        return updated_manuscript
    
    def _save_manuscript(self, manuscript: Manuscript, output_path: Path) -> None:
        """Save manuscript to file(s)."""
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as Markdown (primary format)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(manuscript.content)
        logger.info(f"Saved manuscript to: {output_path}")
        
        # Save in additional formats if specified
        for format_ext in self.output_formats:
            if format_ext != output_path.suffix:
                format_path = output_path.with_suffix(format_ext)
                try:
                    self._convert_format(manuscript.content, format_path, format_ext)
                except Exception as e:
                    logger.warning(f"Failed to save in format {format_ext}: {e}")
    
    def _convert_format(self, content: str, output_path: Path, format_ext: str) -> None:
        """Convert content to different formats."""
        if format_ext == '.txt':
            # Simple text conversion
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif format_ext == '.docx':
            # Would use pandoc or python-docx
            logger.info(f"DOCX conversion not implemented yet")
        elif format_ext == '.pdf':
            # Would use pandoc
            logger.info(f"PDF conversion not implemented yet")
        else:
            logger.warning(f"Unknown format: {format_ext}")
    
    def _generate_change_log(self, diffs: List[UnifiedDiff], output_path: Path) -> None:
        """Generate a detailed change log."""
        log_path = output_path.with_suffix('.changes.md')
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write("# Manuscript Changes Log\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Applied changes: {len(diffs)}\n\n")
                
                for i, diff in enumerate(diffs, 1):
                    f.write(f"## Change {i}: {diff.section}\n\n")
                    f.write(f"**Span ID**: {diff.span_id}\n")
                    f.write(f"**Lines**: {diff.line_start}-{diff.line_end}\n")
                    f.write(f"**Confidence**: {diff.confidence:.2f}\n")
                    f.write(f"**Preserves Semantics**: {diff.preserves_semantics}\n\n")
                    
                    f.write("### Original Text\n")
                    f.write("```\n")
                    f.write(diff.old_text)
                    f.write("\n```\n\n")
                    
                    f.write("### Revised Text\n")
                    f.write("```\n")
                    f.write(diff.new_text)
                    f.write("\n```\n\n")
                    
                    f.write("### Unified Diff\n")
                    f.write("```diff\n")
                    f.write(diff.format_diff())
                    f.write("\n```\n\n")
                    f.write("---\n\n")
            
            logger.info(f"Change log saved to: {log_path}")
        except Exception as e:
            logger.warning(f"Failed to generate change log: {e}")
    
    def create_track_changes_version(
        self, 
        original_content: str, 
        revised_content: str, 
        output_path: Path
    ) -> None:
        """Create a track-changes version showing all modifications."""
        # For MVP, create a simple diff view
        # In full implementation, would create .docx with track changes
        
        diff_path = output_path.with_suffix('.diff.md')
        
        try:
            original_lines = original_content.split('\n')
            revised_lines = revised_content.split('\n')
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                original_lines,
                revised_lines,
                fromfile='original',
                tofile='revised',
                lineterm=''
            ))
            
            with open(diff_path, 'w', encoding='utf-8') as f:
                f.write("# Track Changes View\n\n")
                f.write("```diff\n")
                f.write('\n'.join(diff_lines))
                f.write("\n```\n")
            
            logger.info(f"Track changes version saved to: {diff_path}")
        except Exception as e:
            logger.warning(f"Failed to create track changes version: {e}")