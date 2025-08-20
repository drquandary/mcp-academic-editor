"""
Edit planning - classify comments and create edit intents.
"""

import logging
from typing import List, Dict, Optional, Set
import re

from .models import (
    Comment, Manuscript, EditIntent, CommentType, 
    VisionBrief, ManuscriptSpan, Priority, Status
)

logger = logging.getLogger(__name__)


class EditPlanner:
    """Plan surgical edits based on aligned comments and vision constraints."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.risk_assessment = config.get("risk_assessment", True)
        self.conflict_detection = config.get("conflict_detection", True)
        self.intent_templates = config.get("intent_templates", {})
        
    def create_edit_plan(
        self, 
        comments: List[Comment], 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> List[EditIntent]:
        """
        Create a comprehensive edit plan from aligned comments.
        
        Args:
            comments: Reviewer comments aligned to manuscript spans
            manuscript: Parsed manuscript
            vision: Project vision and constraints
            
        Returns:
            List of edit intents ready for patch generation
        """
        logger.info(f"Planning edits for {len(comments)} comments")
        
        # Filter out comments targeting protected content
        actionable_comments = self._filter_protected_comments(comments, manuscript, vision)
        logger.info(f"{len(actionable_comments)} comments are actionable (not protected)")
        
        # Create edit intents
        intents = []
        
        for comment in actionable_comments:
            try:
                # Generate edit intents based on comment type
                comment_intents = self._generate_edit_intents(comment, manuscript, vision)
                intents.extend(comment_intents)
            except Exception as e:
                logger.error(f"Failed to plan edits for comment {comment.id}: {e}")
                continue
        
        # Detect and resolve conflicts
        if self.conflict_detection:
            intents = self._resolve_conflicts(intents, vision)
        
        # Priority sort
        intents = self._prioritize_edits(intents, vision)
        
        logger.info(f"Generated {len(intents)} edit intents")
        return intents
    
    def _generate_edit_intents(
        self, 
        comment: Comment, 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> List[EditIntent]:
        """Generate edit intents for a single comment."""
        intents = []
        
        # Handle different comment types with surgical precision
        if comment.type == CommentType.ADD_CITATION:
            intents.extend(self._generate_citation_intents(comment, manuscript))
        elif comment.type == CommentType.CLARIFY:
            intents.extend(self._generate_clarification_intents(comment, manuscript))
        elif comment.type == CommentType.RESTRUCTURE:
            intents.extend(self._generate_restructure_intents(comment, manuscript))
        elif comment.type == CommentType.TIGHTEN:
            intents.extend(self._generate_concision_intents(comment, manuscript))
        elif comment.type == CommentType.COUNTERARGUMENT:
            intents.extend(self._generate_counterargument_intents(comment, manuscript))
        elif comment.type == CommentType.COPYEDIT:
            intents.extend(self._generate_copyedit_intents(comment, manuscript))
        elif comment.type == CommentType.EVIDENCE_GAP:
            intents.extend(self._generate_evidence_intents(comment, manuscript))
        
        # Set comment reference and metadata for all intents
        for intent in intents:
            intent.comment_id = comment.id
            intent.priority = comment.priority or Priority.MEDIUM
            intent.rationale = f"Addressing {comment.type.value}: {comment.text[:100]}"
        
        return intents
    
    def _generate_citation_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate surgical citation addition intents."""
        intents = []
        
        for span_id in comment.links:
            span = manuscript.spans.get(span_id)
            if not span:
                continue
                
            # Find claims that need citations
            sentences = re.split(r'[.!?]+', span.text)
            for i, sentence in enumerate(sentences):
                if self._needs_citation(sentence):
                    # Create precise insertion point
                    citation_text = self._extract_citation_from_comment(comment.text)
                    new_text = sentence.strip() + f" {citation_text}."
                    
                    intent = EditIntent(
                        target_spans=[span_id],
                        operation="replace",
                        original_text=sentence.strip() + ".",
                        new_text=new_text,
                        edit_type="citation_addition",
                        confidence=0.9
                    )
                    intents.append(intent)
        
        return intents
    
    def _generate_clarification_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate clarification intents with minimal text changes."""
        intents = []
        
        for span_id in comment.links:
            span = manuscript.spans.get(span_id)
            if not span:
                continue
            
            # Identify unclear passages
            unclear_phrases = self._find_unclear_phrases(span.text, comment.text)
            
            for phrase in unclear_phrases:
                clarification = self._generate_clarification_text(phrase, comment.text)
                new_text = span.text.replace(phrase, f"{phrase} ({clarification})")
                
                intent = EditIntent(
                    target_spans=[span_id],
                    operation="replace",
                    original_text=span.text,
                    new_text=new_text,
                    edit_type="clarification",
                    confidence=0.8
                )
                intents.append(intent)
        
        return intents
    
    def _resolve_conflicts(self, intents: List[EditIntent], vision: VisionBrief) -> List[EditIntent]:
        """Detect and resolve conflicts between edit intents."""
        # Group intents by target span
        span_groups = {}
        for intent in intents:
            for span_id in intent.target_spans:
                if span_id not in span_groups:
                    span_groups[span_id] = []
                span_groups[span_id].append(intent)
        
        resolved_intents = []
        
        for span_id, group_intents in span_groups.items():
            if len(group_intents) == 1:
                resolved_intents.extend(group_intents)
            else:
                # Resolve conflicts by priority and compatibility
                resolved = self._resolve_span_conflicts(group_intents, vision)
                resolved_intents.extend(resolved)
        
        return resolved_intents
    
    def _prioritize_edits(self, intents: List[EditIntent], vision: VisionBrief) -> List[EditIntent]:
        """Sort edits by priority and risk assessment."""
        def priority_score(intent):
            base_score = {"high": 100, "medium": 50, "low": 10}.get(intent.priority.value, 50)
            confidence_bonus = intent.confidence * 20
            return base_score + confidence_bonus
        
        return sorted(intents, key=priority_score, reverse=True)
    
    def _filter_protected_comments(
        self, 
        comments: List[Comment], 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> List[Comment]:
        """Filter out comments targeting protected content."""
        actionable = []
        
        for comment in comments:
            is_protected = False
            
            # Check if comment targets protected spans
            for link in comment.links:
                span = manuscript.spans.get(link)
                if span and span.protected:
                    logger.info(f"Comment {comment.id} targets protected span {link}")
                    is_protected = True
                    break
            
            # Check against do-not-change list
            comment_lower = comment.text.lower()
            for protected_item in vision.do_not_change:
                if protected_item.lower() in comment_lower:
                    logger.info(f"Comment {comment.id} conflicts with protected item: {protected_item}")
                    is_protected = True
                    break
            
            if not is_protected:
                actionable.append(comment)
            else:
                # Mark as rejected due to protection
                comment.status = Status.REJECTED
                comment.rationale = "Targets protected content specified in vision brief"
        
        return actionable
    
    def _create_edit_intent(
        self, 
        comment: Comment, 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> Optional[EditIntent]:
        """Create an edit intent for a single comment."""
        if not comment.links:
            logger.warning(f"Comment {comment.id} has no aligned spans")
            return None
        
        # Determine edit operation based on comment type
        operation = self._determine_operation(comment)
        
        # Generate new text based on comment and operation
        new_text = self._generate_edit_text(comment, manuscript, operation)
        
        # Create justification
        justification = self._create_justification(comment, operation)
        
        # Check if edit preserves core claims
        preserves_claims = self._check_claim_preservation(comment, vision, new_text)
        
        intent = EditIntent(
            comment_id=comment.id,
            target_spans=comment.links,
            operation=operation,
            new_text=new_text,
            justification=justification,
            preserves_claims=preserves_claims,
            risk_level="safe"  # Will be updated in risk assessment
        )
        
        return intent
    
    def _determine_operation(self, comment: Comment) -> str:
        """CRITICAL FIX: Determine edit operation with preference for augmentation."""
        comment_text = comment.text.lower()
        
        # SAFE OPERATIONS: Prefer additions over replacements to preserve word count
        
        if comment.type == CommentType.CLARIFY:
            if 'define' in comment_text or 'explain' in comment_text:
                return "insert_after"  # Add definition/explanation
            else:
                return "expand"  # Expand existing text instead of replace
        
        elif comment.type == CommentType.ADD_CITATION:
            if 'add' in comment_text:
                return "insert_after"  # Add citations after existing text
            else:
                return "expand"  # Expand with citations instead of replace
        
        elif comment.type == CommentType.RESTRUCTURE:
            if 'move' in comment_text or 'reorganize' in comment_text:
                return "restructure"
            else:
                return "expand"  # Expand and restructure instead of replace
        
        elif comment.type == CommentType.TIGHTEN:
            # DANGEROUS: Only allow tightening if explicitly requested
            if 'remove' in comment_text or 'delete' in comment_text:
                logger.warning(f"DANGEROUS: Tightening operation that may reduce content: {comment.text}")
                return "replace"  
            else:
                return "expand"  # Make more precise but don't reduce content
        
        elif comment.type == CommentType.COUNTERARGUMENT:
            return "insert_after"  # Add counterargument discussion
        
        elif comment.type == CommentType.EVIDENCE_GAP:
            return "insert_after"  # Add supporting evidence
        
        else:  # COPYEDIT or unknown
            return "expand"  # Default to expansion, not replacement
    
    def _generate_edit_text(
        self, 
        comment: Comment, 
        manuscript: Manuscript, 
        operation: str
    ) -> str:
        """Generate the new text for the edit."""
        # Get the original text from target spans
        original_texts = []
        for span_id in comment.target_spans:
            span = manuscript.spans.get(span_id)
            if span:
                original_texts.append(span.text)
        
        original_text = " ".join(original_texts)
        
        # Use templates based on comment type
        template = self.intent_templates.get(comment.type.value, "")
        
        if operation == "replace":
            if comment.type == CommentType.CLARIFY:
                return self._generate_clarification(original_text, comment.text)
            elif comment.type == CommentType.TIGHTEN:
                return self._generate_concise_version(original_text)
            elif comment.type == CommentType.ADD_CITATION:
                return self._add_citation_placeholder(original_text, comment.text)
            else:
                return original_text  # Placeholder - would use LLM in full implementation
        
        elif operation == "insert_after":
            if comment.type == CommentType.CLARIFY:
                return self._generate_definition(comment.text)
            elif comment.type == CommentType.COUNTERARGUMENT:
                return self._generate_counterargument(comment.text)
            elif comment.type == CommentType.EVIDENCE_GAP:
                return self._generate_evidence_addition(comment.text)
            else:
                return f"[Added in response to: {comment.text}]"
        
        elif operation == "restructure":
            return self._generate_restructured_text(original_text, comment.text)
        
        else:
            return original_text
    
    def _generate_clarification(self, original_text: str, comment_text: str) -> str:
        """Generate clarified version of text."""
        # Simple template-based clarification
        if 'define' in comment_text.lower():
            # Extract the term to be defined
            terms = re.findall(r'define\s+(["\']?)(\w+(?:\s+\w+)*)\1', comment_text, re.IGNORECASE)
            if terms:
                term = terms[0][1]
                return f"{original_text} {term} refers to [DEFINITION_NEEDED]."
        
        # Default: add clarifying phrase
        return f"{original_text} To clarify, [CLARIFICATION_NEEDED]."
    
    def _generate_concise_version(self, original_text: str) -> str:
        """Generate more concise version of text."""
        # Simple heuristics for concision
        sentences = re.split(r'[.!?]+', original_text)
        
        # Remove filler words and redundant phrases
        filler_words = ['really', 'very', 'quite', 'rather', 'somewhat', 'essentially']
        concise_sentences = []
        
        for sentence in sentences:
            if sentence.strip():
                # Remove filler words
                words = sentence.split()
                filtered_words = [word for word in words if word.lower() not in filler_words]
                concise_sentences.append(' '.join(filtered_words))
        
        return '. '.join(concise_sentences) + '.'
    
    def _add_citation_placeholder(self, original_text: str, comment_text: str) -> str:
        """Add citation placeholder to text."""
        # Simple citation addition
        return f"{original_text} [CITATION_NEEDED]"
    
    def _generate_definition(self, comment_text: str) -> str:
        """Generate definition text based on comment."""
        # Extract term from comment
        terms = re.findall(r'define\s+(["\']?)(\w+(?:\s+\w+)*)\1', comment_text, re.IGNORECASE)
        if terms:
            term = terms[0][1]
            return f"\n\n{term} is defined as [DEFINITION_NEEDED]."
        return "\n\n[DEFINITION_NEEDED based on reviewer comment]."
    
    def _generate_counterargument(self, comment_text: str) -> str:
        """Generate counterargument discussion."""
        return f"\n\nHowever, it is important to consider [COUNTERARGUMENT_NEEDED based on: {comment_text}]."
    
    def _generate_evidence_addition(self, comment_text: str) -> str:
        """Generate additional evidence text."""
        return f"\n\nSupporting evidence includes [EVIDENCE_NEEDED based on: {comment_text}]."
    
    def _generate_restructured_text(self, original_text: str, comment_text: str) -> str:
        """Generate restructured version of text."""
        # Placeholder for restructuring logic
        return f"[RESTRUCTURED: {original_text}]"
    
    def _create_justification(self, comment: Comment, operation: str) -> str:
        """Create justification for the edit intent."""
        return f"Addressing {comment.source}'s {comment.type.value} request: {comment.text}"
    
    def _check_claim_preservation(
        self, 
        comment: Comment, 
        vision: VisionBrief, 
        new_text: str
    ) -> bool:
        """Check if the proposed edit preserves core claims."""
        # Simple check - ensure core claims are not contradicted
        comment_lower = comment.text.lower()
        new_text_lower = new_text.lower()
        
        # Look for negation words that might contradict claims
        negation_words = ['not', 'never', 'cannot', 'fails to', 'lacks', 'wrong', 'incorrect']
        
        for claim in vision.claims:
            claim_lower = claim.lower()
            
            # Check if comment or new text contains negation of claim
            for neg_word in negation_words:
                if neg_word in comment_lower and any(word in claim_lower for word in comment_lower.split()):
                    logger.warning(f"Potential claim contradiction in comment: {comment.text}")
                    return False
        
        return True  # Default to preserving claims
    
    def _detect_conflicts(self, intents: List[EditIntent], manuscript: Manuscript) -> None:
        """Detect conflicts between edit intents."""
        # Group intents by target spans
        span_to_intents = {}
        for intent in intents:
            for span_id in intent.target_spans:
                if span_id not in span_to_intents:
                    span_to_intents[span_id] = []
                span_to_intents[span_id].append(intent)
        
        # Check for conflicts
        for span_id, span_intents in span_to_intents.items():
            if len(span_intents) > 1:
                logger.warning(f"Conflict detected: {len(span_intents)} intents target span {span_id}")
                
                # Mark intents as risky due to conflict
                for intent in span_intents:
                    intent.risk_level = "risky"
                    intent.justification += f" [CONFLICT: {len(span_intents)} intents target same span]"
    
    def _assess_risks(
        self, 
        intents: List[EditIntent], 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> None:
        """Assess risk level for each edit intent."""
        for intent in intents:
            risk_factors = []
            
            # Check if editing protected or important spans
            for span_id in intent.target_spans:
                span = manuscript.spans.get(span_id)
                if not span:
                    continue
                    
                # Check if span is in a critical section
                critical_sections = ['abstract', 'introduction', 'conclusion', 'methodology']
                if any(section in span.section.lower() for section in critical_sections):
                    risk_factors.append("critical_section")
                
                # Check span length (long spans are riskier to edit)
                if len(span.text.split()) > 100:
                    risk_factors.append("long_span")
                
                # Check if span contains thesis or core claims
                span_lower = span.text.lower()
                for claim in vision.claims:
                    if any(word in span_lower for word in claim.lower().split()[:5]):  # First 5 words
                        risk_factors.append("contains_core_claim")
                        break
            
            # Check operation type risk
            if intent.operation == "restructure":
                risk_factors.append("major_restructure")
            elif intent.operation == "delete":
                risk_factors.append("deletion")
            
            # Check if claims are preserved
            if not intent.preserves_claims:
                risk_factors.append("claim_violation")
            
            # Assign risk level based on factors
            if "claim_violation" in risk_factors or "major_restructure" in risk_factors:
                intent.risk_level = "risky"
            elif len(risk_factors) >= 2:
                intent.risk_level = "moderate"
            elif risk_factors:
                intent.risk_level = "moderate"
            else:
                intent.risk_level = "safe"
    
    # Additional methods for surgical edit generation
    
    def _needs_citation(self, sentence: str) -> bool:
        """Check if sentence makes claims that need citations."""
        claim_indicators = [
            "research shows", "studies indicate", "evidence suggests",
            "according to", "findings reveal", "data shows",
            "scholars argue", "experts believe", "recent work"
        ]
        sentence_lower = sentence.lower()
        return any(indicator in sentence_lower for indicator in claim_indicators)
    
    def _extract_citation_from_comment(self, comment_text: str) -> str:
        """Extract citation information from comment text."""
        # Look for citation patterns in comment
        citation_patterns = [
            r'\(([A-Za-z]+\s+\d{4}[a-z]?)\)',  # (Author 2024)
            r'([A-Za-z]+\s+\d{4}[a-z]?)',      # Author 2024
            r'([A-Za-z]+\s+et\s+al\.?\s+\d{4}[a-z]?)'  # Author et al. 2024
        ]
        
        for pattern in citation_patterns:
            match = re.search(pattern, comment_text)
            if match:
                return f"({match.group(1)})"
        
        # Default placeholder
        return "(Author YYYY)"
    
    def _find_unclear_phrases(self, text: str, comment_text: str) -> List[str]:
        """Find phrases in text that need clarification based on comment."""
        # Extract keywords from comment that indicate what's unclear
        unclear_keywords = []
        comment_lower = comment_text.lower()
        
        # Look for quoted phrases in comment
        quoted_phrases = re.findall(r'"([^"]+)"', comment_text)
        quoted_phrases.extend(re.findall(r"'([^']+)'", comment_text))
        
        if quoted_phrases:
            return [phrase for phrase in quoted_phrases if phrase in text]
        
        # Look for technical terms or concepts mentioned
        if "define" in comment_lower or "unclear" in comment_lower:
            # Extract potential terms to clarify
            words = text.split()
            # Return technical-looking words (capitalized, long, or containing hyphens)
            unclear_phrases = []
            for word in words:
                word = word.strip('.,!?;:')
                if (len(word) > 8 or 
                    word[0].isupper() and not word.isupper() or 
                    '-' in word):
                    unclear_phrases.append(word)
            
            return unclear_phrases[:2]  # Limit to avoid over-editing
        
        return []
    
    def _generate_clarification_text(self, phrase: str, comment_text: str) -> str:
        """Generate clarification text for a phrase."""
        if "define" in comment_text.lower():
            return f"i.e., [definition of {phrase}]"
        elif "explain" in comment_text.lower():
            return f"specifically, [explanation of {phrase}]"
        else:
            return f"[clarification needed for {phrase}]"
    
    def _resolve_span_conflicts(self, intents: List[EditIntent], vision: VisionBrief) -> List[EditIntent]:
        """Resolve conflicts between intents targeting the same span."""
        if len(intents) <= 1:
            return intents
        
        # Sort by priority and confidence
        sorted_intents = sorted(intents, 
            key=lambda x: (x.priority.value == "high", x.confidence), 
            reverse=True)
        
        # Check if intents can be merged or if only the highest priority should be kept
        compatible_intents = []
        
        for intent in sorted_intents:
            # Check compatibility with existing intents
            is_compatible = True
            for existing in compatible_intents:
                if not self._are_intents_compatible(intent, existing):
                    is_compatible = False
                    break
            
            if is_compatible:
                compatible_intents.append(intent)
            else:
                # Log conflict resolution
                logger.info(f"Conflict resolved: Skipping {intent.comment_id} due to incompatibility")
        
        return compatible_intents
    
    def _are_intents_compatible(self, intent1: EditIntent, intent2: EditIntent) -> bool:
        """Check if two intents can be applied to the same span without conflicts."""
        # Citation additions are usually compatible with clarifications
        if (intent1.edit_type == "citation_addition" and intent2.edit_type == "clarification" or
            intent2.edit_type == "citation_addition" and intent1.edit_type == "clarification"):
            return True
        
        # Restructuring conflicts with most other edits
        if intent1.edit_type == "restructure" or intent2.edit_type == "restructure":
            return False
        
        # Multiple edits of the same type usually conflict
        if intent1.edit_type == intent2.edit_type:
            return False
        
        return True
    
    # Placeholder methods for other comment types (to be implemented)
    def _generate_restructure_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate restructuring intents."""
        # Placeholder - complex restructuring requires more sophisticated logic
        return []
    
    def _generate_concision_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate concision intents."""
        # Placeholder - would use text compression algorithms
        return []
    
    def _generate_counterargument_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate counterargument intents."""
        # Placeholder - requires understanding of opposing viewpoints
        return []
    
    def _generate_copyedit_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate copyediting intents."""
        # Placeholder - would use grammar/style checking
        return []
    
    def _generate_evidence_intents(self, comment: Comment, manuscript: Manuscript) -> List[EditIntent]:
        """Generate evidence addition intents."""
        # Placeholder - requires domain knowledge for evidence
        return []