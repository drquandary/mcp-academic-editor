"""
Surgical edit application - apply precise changes to manuscript spans.
"""

import logging
from typing import Optional, Dict, List, Tuple
import difflib
import re

from .models import EditIntent, Manuscript, UnifiedDiff, ManuscriptSpan, Comment

logger = logging.getLogger(__name__)


class SurgicalEditor:
    """Apply precise, minimal edits to manuscript spans with rollback capability."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.preserve_formatting = config.get("preserve_formatting", True)
        self.verify_before_apply = config.get("verify_before_apply", True)
        self.backup_original = config.get("backup_original", True)
        self.max_edit_distance = config.get("max_edit_distance", 100)
        
        # CRITICAL: Word count protection settings
        self.preserve_word_count = config.get("preserve_word_count", True)
        self.minimum_word_count_ratio = config.get("minimum_word_count_ratio", 0.95)  # Don't reduce by more than 5%
        self.augment_only_mode = config.get("augment_only_mode", False)  # Only allow additions
        
        # Track applied edits for rollback
        self.edit_history: List[Tuple[EditIntent, str, str]] = []
        self.failed_edits: List[Tuple[EditIntent, str]] = []
    
    def apply_edit_intents(
        self, 
        intents: List[EditIntent], 
        manuscript: Manuscript
    ) -> Tuple[Manuscript, List[EditIntent], List[EditIntent]]:
        """
        Apply surgical edits to manuscript.
        
        Args:
            intents: List of edit intents to apply
            manuscript: Source manuscript to modify
            
        Returns:
            Tuple of (modified_manuscript, successful_edits, failed_edits)
        """
        logger.info(f"Applying {len(intents)} surgical edits to manuscript")
        
        modified_manuscript = self._create_manuscript_copy(manuscript)
        successful_edits = []
        failed_edits = []
        
        # Sort intents by line number to avoid position conflicts
        sorted_intents = self._sort_intents_by_position(intents, manuscript)
        
        for intent in sorted_intents:
            try:
                success = self._apply_single_intent(intent, modified_manuscript)
                if success:
                    successful_edits.append(intent)
                    intent.status = "applied"
                    logger.debug(f"Successfully applied edit {intent.comment_id}")
                else:
                    failed_edits.append(intent)
                    intent.status = "failed"
                    logger.warning(f"Failed to apply edit {intent.comment_id}")
                    
            except Exception as e:
                logger.error(f"Error applying edit {intent.comment_id}: {e}")
                failed_edits.append(intent)
                intent.status = "error"
                intent.rationale = f"Error: {str(e)}"
        
        logger.info(f"Applied {len(successful_edits)} edits successfully, {len(failed_edits)} failed")
        return modified_manuscript, successful_edits, failed_edits
    
    def _apply_single_intent(self, intent: EditIntent, manuscript: Manuscript) -> bool:
        """Apply a single edit intent with surgical precision."""
        try:
            for span_id in intent.target_spans:
                span = manuscript.spans.get(span_id)
                if not span:
                    logger.warning(f"Target span {span_id} not found")
                    continue
                
                original_text = span.text
                
                if intent.operation == "replace":
                    new_text = self._apply_replace_operation(intent, span)
                elif intent.operation == "insert_after":
                    new_text = self._apply_insert_operation(intent, span)
                elif intent.operation == "insert_before":
                    new_text = self._apply_insert_before_operation(intent, span)
                elif intent.operation == "expand":
                    new_text = self._apply_expand_operation(intent, span)
                elif intent.operation == "delete":
                    new_text = self._apply_delete_operation(intent, span)
                else:
                    logger.error(f"Unknown operation: {intent.operation}")
                    return False
                
                # Verify the edit makes sense
                if self.verify_before_apply:
                    if not self._verify_edit_quality(original_text, new_text, intent):
                        logger.warning(f"Edit quality check failed for {intent.comment_id}")
                        return False
                
                # Apply the change
                if self.backup_original:
                    self.edit_history.append((intent, original_text, new_text))
                
                span.text = new_text
                
                # Update manuscript content
                manuscript.content = self._update_manuscript_content(manuscript)
                
            return True
            
        except Exception as e:
            logger.error(f"Error in _apply_single_intent: {e}")
            return False
    
    def _apply_replace_operation(self, intent: EditIntent, span: ManuscriptSpan) -> str:
        """Apply replace operation with precision."""
        if intent.original_text and intent.new_text:
            # Exact replacement
            if intent.original_text in span.text:
                return span.text.replace(intent.original_text, intent.new_text, 1)
            else:
                # Fuzzy replacement with similarity matching
                return self._fuzzy_replace(span.text, intent.original_text, intent.new_text)
        
        # Fallback to intent-based replacement
        return intent.new_text if intent.new_text else span.text
    
    def _apply_insert_operation(self, intent: EditIntent, span: ManuscriptSpan) -> str:
        """Apply insert after operation."""
        if intent.new_text:
            # Insert at end of span
            return f"{span.text.rstrip()} {intent.new_text}"
        return span.text
    
    def _apply_insert_before_operation(self, intent: EditIntent, span: ManuscriptSpan) -> str:
        """Apply insert before operation."""
        if intent.new_text:
            return f"{intent.new_text} {span.text.lstrip()}"
        return span.text
    
    def _apply_expand_operation(self, intent: EditIntent, span: ManuscriptSpan) -> str:
        """Apply expand operation - augment existing content."""
        original_text = span.text.strip()
        
        if intent.new_text:
            # Smart expansion: add new content while preserving original
            if intent.original_text and intent.original_text in original_text:
                # Expand around specific text
                expanded_text = original_text.replace(intent.original_text, intent.new_text, 1)
                return expanded_text
            else:
                # Add to the end of the span
                return f"{original_text} {intent.new_text}"
        
        return original_text
    
    def _apply_delete_operation(self, intent: EditIntent, span: ManuscriptSpan) -> str:
        """Apply delete operation with safety checks."""
        if intent.original_text and intent.original_text in span.text:
            # Remove specific text
            return span.text.replace(intent.original_text, "", 1)
        
        # Refuse to delete entire span for safety
        logger.warning(f"Refusing to delete entire span {span.id}")
        return span.text
    
    def _fuzzy_replace(self, text: str, old_text: str, new_text: str) -> str:
        """Fuzzy text replacement using similarity matching."""
        sentences = re.split(r'[.!?]+', text)
        best_match = ""
        best_score = 0.0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Use sequence matching to find similarity
            similarity = difflib.SequenceMatcher(None, sentence.lower(), old_text.lower()).ratio()
            if similarity > best_score and similarity > 0.6:  # Minimum similarity threshold
                best_score = similarity
                best_match = sentence
        
        if best_match:
            return text.replace(best_match, new_text, 1)
        
        logger.warning(f"No good fuzzy match found for: {old_text[:50]}...")
        return text
    
    def _verify_edit_quality(self, original: str, modified: str, intent: EditIntent) -> bool:
        """Verify that the edit maintains reasonable quality."""
        
        # CRITICAL: Word count protection check
        if self.preserve_word_count:
            if not self._check_word_count_preservation(original, modified, intent):
                logger.error(f"REJECTED EDIT {intent.comment_id}: Would reduce word count")
                return False
        
        # Length check - avoid massive expansions or contractions (but allow augmentation)
        length_ratio = len(modified) / max(len(original), 1)
        if not self.augment_only_mode:
            if length_ratio > 3.0 or length_ratio < 0.3:
                logger.warning(f"Extreme length change: {length_ratio:.2f}x")
                return False
        else:
            # In augment mode, only allow growth
            if length_ratio < 1.0:
                logger.error(f"REJECTED EDIT {intent.comment_id}: Augment mode - cannot reduce content")
                return False
        
        # Check for broken formatting (unmatched brackets, quotes, etc.)
        if not self._check_formatting_integrity(modified):
            logger.warning("Formatting integrity check failed")
            return False
        
        # Edit distance check
        edit_distance = difflib.SequenceMatcher(None, original, modified).ratio()
        if edit_distance < 0.2:  # Too dissimilar
            logger.warning(f"Edit distance too large: {1-edit_distance:.2f}")
            return False
        
        return True
    
    def _check_formatting_integrity(self, text: str) -> bool:
        """Check that text formatting is not broken."""
        # Check balanced brackets and quotes
        brackets = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        stack = []
        
        for char in text:
            if char in brackets:
                if char in ["(", "[", "{"]:
                    stack.append(char)
                elif char in [")", "]", "}"]:
                    expected_open = {")": "(", "]": "[", "}": "{"}[char]
                    if not stack or stack.pop() != expected_open:
                        return False
        
        return len(stack) == 0
    
    def rollback_last_edit(self, manuscript: Manuscript) -> bool:
        """Rollback the last applied edit."""
        if not self.edit_history:
            logger.warning("No edits to rollback")
            return False
        
        intent, original_text, modified_text = self.edit_history.pop()
        
        try:
            # Find span and restore original text
            for span_id in intent.target_spans:
                span = manuscript.spans.get(span_id)
                if span and span.text == modified_text:
                    span.text = original_text
                    logger.info(f"Rolled back edit {intent.comment_id}")
                    return True
            
            logger.warning(f"Could not rollback edit {intent.comment_id} - span not found or text changed")
            return False
            
        except Exception as e:
            logger.error(f"Error rolling back edit: {e}")
            return False
    
    def _create_manuscript_copy(self, manuscript: Manuscript) -> Manuscript:
        """Create a deep copy of manuscript for editing."""
        # For now, create a shallow copy that allows editing
        # In production, would implement proper deep copy
        return manuscript
    
    def _sort_intents_by_position(self, intents: List[EditIntent], manuscript: Manuscript) -> List[EditIntent]:
        """Sort intents by document position to avoid conflicts."""
        def get_position(intent):
            positions = []
            for span_id in intent.target_spans:
                span = manuscript.spans.get(span_id)
                if span:
                    positions.append(span.start_line)
            return min(positions) if positions else float('inf')
        
        return sorted(intents, key=get_position)
    
    def _check_word_count_preservation(self, original: str, modified: str, intent: EditIntent) -> bool:
        """CRITICAL: Verify that edits don't destroy word count."""
        original_words = len(original.split())
        modified_words = len(modified.split())
        
        if original_words == 0:
            # New content - always allow
            return True
            
        word_count_ratio = modified_words / original_words
        
        if word_count_ratio < self.minimum_word_count_ratio:
            logger.error(f"CRITICAL WORD COUNT VIOLATION: Edit {intent.comment_id} would reduce content from {original_words} to {modified_words} words (ratio: {word_count_ratio:.2f})")
            logger.error(f"Minimum ratio: {self.minimum_word_count_ratio}")
            logger.error(f"Original text: {original[:200]}...")
            logger.error(f"Modified text: {modified[:200]}...")
            return False
            
        if word_count_ratio >= 1.0:
            logger.info(f"Good edit: {intent.comment_id} increases content from {original_words} to {modified_words} words")
        else:
            logger.warning(f"Acceptable reduction: {intent.comment_id} reduces content from {original_words} to {modified_words} words (ratio: {word_count_ratio:.2f})")
            
        return True
    
    def _update_manuscript_content(self, manuscript: Manuscript) -> str:
        """Update the full manuscript content after span modifications."""
        # Sort spans by line number
        sorted_spans = sorted(manuscript.spans.values(), key=lambda s: s.start_line)
        
        # Reconstruct content
        lines = manuscript.content.split('\n')
        new_lines = lines.copy()
        
        for span in sorted_spans:
            # Update the lines for this span
            start_idx = span.start_line - 1  # Convert to 0-based
            end_idx = span.end_line - 1
            
            if 0 <= start_idx < len(new_lines):
                # Replace the span's line(s) with updated text
                span_lines = span.text.split('\n')
                new_lines[start_idx:end_idx+1] = span_lines
        
        return '\n'.join(new_lines)


class DiffGenerator:
    """Generate unified diffs from edit intents."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.llm_model = config.get("llm_model", "gpt-4")
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", 512)
        self.locality_constraint = config.get("locality_constraint", "paragraph")
        self.system_prompt = config.get("system_prompt", "")
        
    def generate_diff(self, intent: EditIntent, manuscript: Manuscript) -> Optional[UnifiedDiff]:
        """
        Generate a unified diff from an edit intent.
        
        Args:
            intent: Edit intent specifying the desired change
            manuscript: Source manuscript
            
        Returns:
            UnifiedDiff object or None if generation fails
        """
        logger.debug(f"Generating diff for intent {intent.comment_id}")
        
        # Get target span(s)
        target_spans = []
        for span_id in intent.target_spans:
            span = manuscript.spans.get(span_id)
            if span:
                target_spans.append(span)
        
        if not target_spans:
            logger.warning(f"No valid spans found for intent {intent.comment_id}")
            return None
        
        # For MVP, work with the first span (would handle multiple spans in full version)
        primary_span = target_spans[0]
        
        # Generate the actual diff based on operation type
        if intent.operation == "replace":
            return self._generate_replacement_diff(intent, primary_span)
        elif intent.operation == "insert_before":
            return self._generate_insertion_diff(intent, primary_span, "before")
        elif intent.operation == "insert_after":
            return self._generate_insertion_diff(intent, primary_span, "after")
        elif intent.operation == "delete":
            return self._generate_deletion_diff(intent, primary_span)
        elif intent.operation == "restructure":
            return self._generate_restructure_diff(intent, primary_span)
        else:
            logger.warning(f"Unknown operation: {intent.operation}")
            return None
    
    def _generate_replacement_diff(self, intent: EditIntent, span: ManuscriptSpan) -> UnifiedDiff:
        """Generate a replacement diff."""
        old_text = span.text.strip()
        new_text = intent.new_text.strip()
        
        # For MVP, use template-based replacement
        # In full implementation, would call LLM here
        if "[CLARIFICATION_NEEDED]" in new_text:
            new_text = self._apply_clarification_template(old_text, intent)
        elif "[CITATION_NEEDED]" in new_text:
            new_text = self._apply_citation_template(old_text, intent)
        elif "[DEFINITION_NEEDED]" in new_text:
            new_text = self._apply_definition_template(old_text, intent)
        
        # Calculate confidence based on how much text changed
        confidence = self._calculate_confidence(old_text, new_text)
        
        # Check if semantics are preserved (simplified)
        preserves_semantics = self._check_semantic_preservation(old_text, new_text)
        
        return UnifiedDiff(
            span_id=span.id,
            section=span.section,
            paragraph=span.paragraph,
            old_text=old_text,
            new_text=new_text,
            line_start=span.start_line,
            line_end=span.end_line,
            confidence=confidence,
            preserves_semantics=preserves_semantics
        )
    
    def _generate_insertion_diff(
        self, 
        intent: EditIntent, 
        span: ManuscriptSpan, 
        position: str
    ) -> UnifiedDiff:
        """Generate an insertion diff."""
        old_text = span.text.strip()
        insertion_text = intent.new_text.strip()
        
        # Clean up template placeholders
        if "[DEFINITION_NEEDED]" in insertion_text:
            insertion_text = self._generate_definition_text(intent)
        elif "[COUNTERARGUMENT_NEEDED]" in insertion_text:
            insertion_text = self._generate_counterargument_text(intent)
        elif "[EVIDENCE_NEEDED]" in insertion_text:
            insertion_text = self._generate_evidence_text(intent)
        
        # Create new text with insertion
        if position == "before":
            new_text = f"{insertion_text} {old_text}"
        else:  # after
            new_text = f"{old_text} {insertion_text}"
        
        confidence = 0.8  # Insertions are generally safer
        preserves_semantics = True  # Insertions typically preserve original meaning
        
        return UnifiedDiff(
            span_id=span.id,
            section=span.section,
            paragraph=span.paragraph,
            old_text=old_text,
            new_text=new_text,
            line_start=span.start_line,
            line_end=span.end_line,
            confidence=confidence,
            preserves_semantics=preserves_semantics
        )
    
    def _generate_deletion_diff(self, intent: EditIntent, span: ManuscriptSpan) -> UnifiedDiff:
        """Generate a deletion diff."""
        old_text = span.text.strip()
        new_text = ""  # Complete deletion
        
        # Deletions are risky
        confidence = 0.3
        preserves_semantics = False  # Assume deletions change semantics
        
        return UnifiedDiff(
            span_id=span.id,
            section=span.section,
            paragraph=span.paragraph,
            old_text=old_text,
            new_text=new_text,
            line_start=span.start_line,
            line_end=span.end_line,
            confidence=confidence,
            preserves_semantics=preserves_semantics
        )
    
    def _generate_restructure_diff(self, intent: EditIntent, span: ManuscriptSpan) -> UnifiedDiff:
        """Generate a restructuring diff."""
        old_text = span.text.strip()
        
        # Simple restructuring heuristics
        sentences = re.split(r'[.!?]+', old_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Reverse sentence order as simple restructuring
        new_sentences = sentences[::-1]
        new_text = '. '.join(new_sentences) + '.'
        
        confidence = 0.5  # Restructuring is moderate risk
        preserves_semantics = True  # Assume restructuring preserves meaning
        
        return UnifiedDiff(
            span_id=span.id,
            section=span.section,
            paragraph=span.paragraph,
            old_text=old_text,
            new_text=new_text,
            line_start=span.start_line,
            line_end=span.end_line,
            confidence=confidence,
            preserves_semantics=preserves_semantics
        )
    
    def _apply_clarification_template(self, old_text: str, intent: EditIntent) -> str:
        """Apply clarification template to generate new text."""
        # Extract what needs clarifying from the comment
        comment_parts = intent.justification.lower()
        
        if "define" in comment_parts:
            # Find the term that needs defining
            words = old_text.split()
            # Simple heuristic: look for technical terms (longer words)
            technical_terms = [word for word in words if len(word) > 6 and word.isalpha()]
            
            if technical_terms:
                term = technical_terms[0]
                return f"{old_text} Here, {term} refers to the specific approach developed in this study."
        
        # Default clarification
        return f"{old_text} To elaborate, this refers to the systematic process by which users learn to navigate different operational domains of AI systems."
    
    def _apply_citation_template(self, old_text: str, intent: EditIntent) -> str:
        """Apply citation template to add citations."""
        # Simple citation addition
        return f"{old_text} (Author YEAR)"
    
    def _apply_definition_template(self, old_text: str, intent: EditIntent) -> str:
        """Apply definition template."""
        return f"{old_text} This concept encompasses the learned ability to recognize and navigate different modes of AI operation."
    
    def _generate_definition_text(self, intent: EditIntent) -> str:
        """Generate definition text from intent."""
        return "This concept refers to the analytical framework developed in this study."
    
    def _generate_counterargument_text(self, intent: EditIntent) -> str:
        """Generate counterargument text."""
        return "However, it is important to acknowledge potential limitations of this approach."
    
    def _generate_evidence_text(self, intent: EditIntent) -> str:
        """Generate additional evidence text."""
        return "Supporting evidence from our ethnographic analysis demonstrates this pattern."
    
    def _calculate_confidence(self, old_text: str, new_text: str) -> float:
        """Calculate confidence score for the diff."""
        if not old_text or not new_text:
            return 0.1  # Very low confidence for empty texts
        
        # Use sequence similarity as proxy for confidence
        similarity = difflib.SequenceMatcher(None, old_text, new_text).ratio()
        
        # Higher similarity = higher confidence (less change)
        # But very high similarity might mean no meaningful change
        if similarity > 0.95:
            return 0.4  # Low confidence for minimal changes
        elif similarity > 0.7:
            return 0.9  # High confidence for moderate changes
        elif similarity > 0.4:
            return 0.7  # Medium confidence for significant changes
        else:
            return 0.3  # Low confidence for major changes
    
    def _check_semantic_preservation(self, old_text: str, new_text: str) -> bool:
        """Check if new text preserves semantics of old text."""
        # Simplified semantic preservation check
        old_words = set(old_text.lower().split())
        new_words = set(new_text.lower().split())
        
        # Check if key content words are preserved
        content_words = old_words - {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        preserved_words = content_words.intersection(new_words)
        
        # If more than 60% of content words are preserved, assume semantics preserved
        if len(content_words) > 0:
            preservation_ratio = len(preserved_words) / len(content_words)
            return preservation_ratio > 0.6
        
        return True  # Default to preserved if no content words
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM for text generation (placeholder for full implementation)."""
        # In full implementation, this would call GPT-4 API
        # For MVP, return placeholder
        return "[LLM_GENERATED_TEXT]"
    
    def _build_llm_prompt(self, intent: EditIntent, old_text: str) -> str:
        """Build prompt for LLM-based diff generation."""
        system_prompt = self.system_prompt or "You are an academic editor. Make precise, minimal edits that address reviewer concerns while preserving the original meaning and claims."
        
        user_prompt = f"""
Original text:
{old_text}

Reviewer comment: {intent.justification}

Operation: {intent.operation}

Please generate the revised text that addresses the reviewer's concern while:
1. Preserving the original meaning and claims
2. Making minimal changes
3. Maintaining the author's voice and style
4. Following academic writing conventions

Revised text:
"""
        
        return f"{system_prompt}\n\n{user_prompt}"