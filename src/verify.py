"""
Edit verification - validate edits for semantic preservation and quality.
"""

import logging
import re
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse
import difflib

from .models import EditIntent, Manuscript, VisionBrief, ManuscriptSpan, UnifiedDiff

# Simple verification result class
class VerificationResult:
    def __init__(self, passed: bool, warnings: List[str] = None, errors: List[str] = None):
        self.passed = passed
        self.warnings = warnings or []
        self.errors = errors or []

logger = logging.getLogger(__name__)


class MinimumWordCountVerifier:
    """CRITICAL: Enforce minimum word count preservation during edits."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.minimum_total_words = config.get("minimum_total_words", 8000)  # For journal requirements
        self.minimum_word_count_ratio = config.get("minimum_word_count_ratio", 0.95)  # Don't reduce by >5%
        self.enforce_growth_only = config.get("enforce_growth_only", False)  # Only allow word count increases
        
    def verify_manuscript_word_count(self, original: Manuscript, modified: Manuscript) -> Dict[str, any]:
        """CRITICAL: Verify manuscript meets minimum word count requirements."""
        original_word_count = len(original.content.split())
        modified_word_count = len(modified.content.split())
        word_count_ratio = modified_word_count / max(original_word_count, 1)
        
        result = {
            "meets_minimum": modified_word_count >= self.minimum_total_words,
            "preserves_content": word_count_ratio >= self.minimum_word_count_ratio,
            "original_words": original_word_count,
            "modified_words": modified_word_count,
            "word_count_ratio": word_count_ratio,
            "warnings": [],
            "errors": []
        }
        
        # Check minimum word count for journal submission
        if modified_word_count < self.minimum_total_words:
            result["errors"].append(f"CRITICAL: Manuscript has only {modified_word_count} words, needs {self.minimum_total_words}")
            
        # Check word count preservation
        if word_count_ratio < self.minimum_word_count_ratio:
            result["errors"].append(f"CRITICAL: Word count reduced by {(1-word_count_ratio)*100:.1f}% (from {original_word_count} to {modified_word_count})")
            
        # Check growth-only enforcement
        if self.enforce_growth_only and word_count_ratio < 1.0:
            result["errors"].append(f"CRITICAL: Growth-only mode violated - word count cannot decrease")
            
        # Warnings
        if word_count_ratio < 1.0:
            result["warnings"].append(f"Word count reduced by {(1-word_count_ratio)*100:.1f}%")
            
        return result
    
    def verify_batch_edits_word_count(self, intents: List[EditIntent], manuscript: Manuscript) -> Dict[str, any]:
        """Verify batch of edits won't violate word count requirements."""
        # Estimate word count impact of all edits
        estimated_word_change = 0
        
        for intent in intents:
            if intent.new_text and intent.original_text:
                new_words = len(intent.new_text.split())
                original_words = len(intent.original_text.split())
                estimated_word_change += (new_words - original_words)
            elif intent.new_text:
                estimated_word_change += len(intent.new_text.split())
                
        original_word_count = len(manuscript.content.split())
        estimated_new_word_count = original_word_count + estimated_word_change
        
        result = {
            "estimated_word_change": estimated_word_change,
            "estimated_final_word_count": estimated_new_word_count,
            "meets_minimum_estimated": estimated_new_word_count >= self.minimum_total_words,
            "safe_to_proceed": True,
            "warnings": [],
            "errors": []
        }
        
        if estimated_word_change < 0:
            result["warnings"].append(f"Estimated word count reduction: {estimated_word_change}")
            
        if estimated_new_word_count < self.minimum_total_words:
            result["errors"].append(f"CRITICAL: Estimated final word count ({estimated_new_word_count}) below minimum ({self.minimum_total_words})")
            result["safe_to_proceed"] = False
            
        return result


class SemanticVerifier:
    """Lightweight semantic verification without external NLP models."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.preserve_thesis = config.get("preserve_thesis", True)
        self.check_claim_consistency = config.get("check_claim_consistency", True)
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        self.max_semantic_drift = config.get("max_semantic_drift", 0.5)
        
        # Keywords that might indicate semantic changes
        self.negation_words = {'not', 'never', 'no', 'none', 'cannot', 'unable', 'fails', 'lacks', 'without', 'impossible'}
        self.contradiction_words = {'however', 'but', 'although', 'despite', 'yet', 'whereas', 'conversely', 'instead'}
        self.uncertainty_words = {'might', 'maybe', 'possibly', 'perhaps', 'unclear', 'ambiguous', 'uncertain'}
        
    def verify_edit_intent(
        self, 
        intent: EditIntent, 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> Dict[str, any]:
        """
        Verify that an edit intent preserves semantic meaning.
        
        Args:
            intent: Edit intent to verify
            manuscript: Source manuscript
            vision: Project vision with thesis and claims
            
        Returns:
            Dict with verification results
        """
        logger.debug(f"Verifying edit intent {intent.comment_id}")
        
        verification = {
            "thesis_preserved": True,
            "claims_preserved": True,
            "semantic_similarity": 1.0,
            "warnings": [],
            "errors": [],
            "safe_to_apply": True
        }
        
        # Get original and new text
        original_text = self._get_original_text(intent, manuscript)
        new_text = intent.new_text
        
        if not original_text or not new_text:
            verification["warnings"].append("Missing original or new text for verification")
            return verification
        
        # Check thesis preservation
        if self.preserve_thesis:
            thesis_check = self._check_thesis_preservation(original_text, new_text, vision)
            verification.update(thesis_check)
        
        # Check claim consistency  
        if self.check_claim_consistency:
            claims_check = self._check_claims_preservation(original_text, new_text, vision)
            verification.update(claims_check)
        
        # Semantic similarity check
        similarity = self._calculate_semantic_similarity(original_text, new_text)
        verification["semantic_similarity"] = similarity
        
        if similarity < self.similarity_threshold:
            verification["warnings"].append(f"Low semantic similarity: {similarity:.2f}")
            
        if similarity < self.max_semantic_drift:
            verification["errors"].append(f"Excessive semantic drift: {similarity:.2f}")
            verification["safe_to_apply"] = False
        
        # Overall safety check
        verification["safe_to_apply"] = (
            verification["thesis_preserved"] and 
            verification["claims_preserved"] and 
            len(verification["errors"]) == 0
        )
        
        return verification
    
    def _get_original_text(self, intent: EditIntent, manuscript: Manuscript) -> str:
        """Extract original text from targeted spans."""
        texts = []
        for span_id in intent.target_spans:
            span = manuscript.spans.get(span_id)
            if span:
                texts.append(span.text)
        return " ".join(texts)
    
    def _check_thesis_preservation(self, original: str, new: str, vision: VisionBrief) -> Dict[str, any]:
        """Check if the edit preserves the core thesis."""
        result = {"thesis_preserved": True, "thesis_warnings": []}
        
        # Extract key thesis terms
        thesis_words = set(word.lower().strip('.,!?;:"()[]') 
                          for word in vision.thesis.split() 
                          if len(word) > 3)
        
        original_words = set(word.lower().strip('.,!?;:"()[]') 
                            for word in original.split())
        new_words = set(word.lower().strip('.,!?;:"()[]') 
                       for word in new.split())
        
        # Check if thesis keywords are preserved
        thesis_in_original = thesis_words.intersection(original_words)
        thesis_in_new = thesis_words.intersection(new_words)
        
        # Check for negation of thesis concepts
        new_lower = new.lower()
        for negation in self.negation_words:
            for thesis_word in thesis_in_new:
                if f"{negation} {thesis_word}" in new_lower or f"{thesis_word} {negation}" in new_lower:
                    result["thesis_preserved"] = False
                    result["thesis_warnings"].append(f"Potential thesis negation: '{negation} {thesis_word}'")
        
        # Check for contradictions
        for contradiction in self.contradiction_words:
            if contradiction in new_lower:
                result["thesis_warnings"].append(f"Contradiction word detected: '{contradiction}'")
        
        # Check if key thesis concepts are removed
        lost_concepts = thesis_in_original - thesis_in_new
        if lost_concepts and len(lost_concepts) > 1:  # Allow some flexibility
            result["thesis_warnings"].append(f"Lost thesis concepts: {lost_concepts}")
        
        return result
    
    def _check_claims_preservation(self, original: str, new: str, vision: VisionBrief) -> Dict[str, any]:
        """Check if key claims are preserved."""
        result = {"claims_preserved": True, "claims_warnings": []}
        
        original_lower = original.lower()
        new_lower = new.lower()
        
        for i, claim in enumerate(vision.claims):
            claim_words = set(word.lower().strip('.,!?;:"()[]') 
                             for word in claim.split() 
                             if len(word) > 3)
            
            # Check if claim concepts appear in the edit
            claim_in_original = any(word in original_lower for word in claim_words)
            claim_in_new = any(word in new_lower for word in claim_words)
            
            if claim_in_original and not claim_in_new:
                result["claims_warnings"].append(f"Claim {i+1} concepts may be removed")
            
            # Check for direct negation of claims
            for negation in self.negation_words:
                for claim_word in claim_words:
                    if (f"{negation} {claim_word}" in new_lower or 
                        f"{claim_word} {negation}" in new_lower):
                        result["claims_preserved"] = False
                        result["claims_warnings"].append(f"Claim {i+1} potentially negated")
        
        return result
    
    def _calculate_semantic_similarity(self, original: str, new: str) -> float:
        """Calculate semantic similarity using simple text analysis."""
        # Normalize texts
        orig_words = self._normalize_text(original)
        new_words = self._normalize_text(new)
        
        # Calculate Jaccard similarity
        intersection = len(orig_words.intersection(new_words))
        union = len(orig_words.union(new_words))
        
        if union == 0:
            return 1.0
        
        jaccard = intersection / union
        
        # Calculate sequence similarity for word order
        orig_list = list(orig_words)
        new_list = list(new_words)
        
        sequence_sim = difflib.SequenceMatcher(None, orig_list, new_list).ratio()
        
        # Combine metrics (weighted average)
        return 0.7 * jaccard + 0.3 * sequence_sim
    
    def _normalize_text(self, text: str) -> Set[str]:
        """Normalize text for similarity comparison."""
        # Remove punctuation, convert to lowercase, filter stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        words = set()
        for word in text.lower().split():
            # Clean word
            word = re.sub(r'[^\w]', '', word)
            if len(word) > 2 and word not in stop_words:
                words.add(word)
        
        return words
    
    def verify_batch_edits(
        self, 
        intents: List[EditIntent], 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> Dict[str, any]:
        """Verify a batch of edits for cumulative effects."""
        logger.info(f"Verifying batch of {len(intents)} edits")
        
        batch_result = {
            "individual_results": {},
            "batch_thesis_preserved": True,
            "batch_claims_preserved": True,
            "overall_safe": True,
            "batch_warnings": [],
            "batch_errors": []
        }
        
        # Verify individual edits
        for intent in intents:
            result = self.verify_edit_intent(intent, manuscript, vision)
            batch_result["individual_results"][intent.comment_id] = result
            
            # Update batch status
            if not result["thesis_preserved"]:
                batch_result["batch_thesis_preserved"] = False
            if not result["claims_preserved"]:
                batch_result["batch_claims_preserved"] = False
            if not result["safe_to_apply"]:
                batch_result["overall_safe"] = False
            
            batch_result["batch_warnings"].extend(result["warnings"])
            batch_result["batch_errors"].extend(result["errors"])
        
        # Check for cumulative effects
        high_risk_count = sum(1 for result in batch_result["individual_results"].values() 
                             if result["semantic_similarity"] < self.similarity_threshold)
        
        if high_risk_count > len(intents) * 0.3:  # More than 30% high-risk edits
            batch_result["batch_warnings"].append(f"High proportion of risky edits: {high_risk_count}/{len(intents)}")
        
        return batch_result


class EditVerifier:
    """Verify that proposed edits meet quality and safety standards."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.nli_model = config.get("nli_model", "roberta-large-mnli")
        self.entailment_threshold = config.get("entailment_threshold", 0.8)
        self.citation_validation = config.get("citation_validation", True)
        self.style_checking = config.get("style_checking", True)
        self.protected_elements = set(config.get("protected_elements", []))
        
    def verify_edit(
        self, 
        diff: UnifiedDiff, 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> VerificationResult:
        """
        Comprehensive verification of a proposed edit.
        
        Args:
            diff: Proposed unified diff
            manuscript: Original manuscript
            vision: Project vision and constraints
            
        Returns:
            VerificationResult with pass/fail and detailed feedback
        """
        logger.debug(f"Verifying edit for span {diff.span_id}")
        
        checks = {}
        warnings = []
        errors = []
        
        # 1. Semantic preservation check
        checks["semantic_preservation"] = self._check_semantic_preservation(diff, vision)
        if not checks["semantic_preservation"]:
            errors.append("Edit may violate semantic preservation requirements")
        
        # 2. Protected content check
        checks["protected_content"] = self._check_protected_content(diff, manuscript, vision)
        if not checks["protected_content"]:
            errors.append("Edit targets protected content")
        
        # 3. Length constraint check
        checks["length_constraints"] = self._check_length_constraints(diff, vision)
        if not checks["length_constraints"]:
            warnings.append("Edit significantly changes text length")
        
        # 4. Citation integrity check
        if self.citation_validation:
            checks["citation_integrity"] = self._check_citation_integrity(diff)
            if not checks["citation_integrity"]:
                errors.append("Edit violates citation integrity rules")
        
        # 5. Style compliance check
        if self.style_checking:
            checks["style_compliance"] = self._check_style_compliance(diff, vision)
            if not checks["style_compliance"]:
                warnings.append("Edit may not comply with journal style guidelines")
        
        # 6. Claim preservation check
        checks["claim_preservation"] = self._check_claim_preservation(diff, vision)
        if not checks["claim_preservation"]:
            errors.append("Edit may contradict core claims")
        
        # 7. Formatting preservation check
        checks["formatting_preservation"] = self._check_formatting_preservation(diff)
        if not checks["formatting_preservation"]:
            warnings.append("Edit may disrupt document formatting")
        
        # Overall verification result
        passed = all(checks.values()) and len(errors) == 0
        confidence = diff.confidence * (1.0 - 0.1 * len(warnings)) * (1.0 - 0.3 * len(errors))
        
        return VerificationResult(
            passed=passed,
            checks=checks,
            warnings=warnings,
            errors=errors,
            confidence=max(0.0, confidence)
        )
    
    def _check_semantic_preservation(self, diff: UnifiedDiff, vision: VisionBrief) -> bool:
        """Check if edit preserves semantic meaning."""
        # For MVP, use the diff's own semantic preservation flag
        # In full implementation, would use NLI model
        if not diff.preserves_semantics:
            return False
        
        # Check for negation words that might flip meaning
        negation_words = {'not', 'never', 'cannot', 'fails', 'lacks', 'wrong', 'incorrect', 'false'}
        
        old_words = set(diff.old_text.lower().split())
        new_words = set(diff.new_text.lower().split())
        
        # Check if negation was added or removed
        old_negations = old_words.intersection(negation_words)
        new_negations = new_words.intersection(negation_words)
        
        if old_negations != new_negations:
            logger.warning(f"Negation change detected in diff {diff.span_id}")
            return False
        
        return True
    
    def _check_protected_content(
        self, 
        diff: UnifiedDiff, 
        manuscript: Manuscript, 
        vision: VisionBrief
    ) -> bool:
        """Check if edit affects protected content."""
        span = manuscript.spans.get(diff.span_id)
        if not span:
            return False
        
        # Check if span is marked as protected
        if span.protected:
            return False
        
        # Check if span is a figure or table (always protected)
        if span.block_type in ['figure', 'table']:
            return False
        
        # Check against do-not-change list
        for protected_item in vision.do_not_change:
            if protected_item.lower() in diff.old_text.lower():
                logger.warning(f"Edit affects protected item: {protected_item}")
                return False
        
        # Check if edit is in a protected section
        protected_sections = {'figures', 'tables', 'references'}
        if diff.section.lower() in protected_sections:
            return False
        
        return True
    
    def _check_length_constraints(self, diff: UnifiedDiff, vision: VisionBrief) -> bool:
        """Check if edit respects length constraints."""
        # Get target length constraint from vision
        target_length = vision.target_length or "maintain current"
        
        if "maintain" in target_length.lower():
            # Check that edit doesn't dramatically change length
            old_len = len(diff.old_text.split())
            new_len = len(diff.new_text.split())
            
            if old_len == 0:
                return new_len < 50  # Insertions shouldn't be too long
            
            length_ratio = new_len / old_len
            
            # Allow 50% variance for individual edits
            return 0.5 <= length_ratio <= 1.5
        
        return True  # No specific constraint
    
    def _check_citation_integrity(self, diff: UnifiedDiff) -> bool:
        """Check that edit maintains citation integrity."""
        # Find citations in old and new text
        citation_patterns = [
            r'\([A-Za-z]+(?:\s+et\s+al\.?)?\s+\d{4}[a-z]?(?::\s*\d+)?\)',  # (Author 2023)
            r'\[[A-Za-z]+(?:\s+et\s+al\.?)?\s+\d{4}[a-z]?(?::\s*\d+)?\]',  # [Author 2023]
        ]
        
        old_citations = set()
        new_citations = set()
        
        for pattern in citation_patterns:
            old_citations.update(re.findall(pattern, diff.old_text))
            new_citations.update(re.findall(pattern, diff.new_text))
        
        # Check if citations were deleted without replacement
        deleted_citations = old_citations - new_citations
        if deleted_citations:
            logger.warning(f"Citations deleted: {deleted_citations}")
            return False
        
        # Validate new citations (basic format check)
        added_citations = new_citations - old_citations
        for citation in added_citations:
            if not self._validate_citation_format(citation):
                logger.warning(f"Invalid citation format: {citation}")
                return False
        
        return True
    
    def _validate_citation_format(self, citation: str) -> bool:
        """Validate that citation follows proper format."""
        # Basic validation - has author and year
        has_author = re.search(r'[A-Za-z]+', citation)
        has_year = re.search(r'\d{4}', citation)
        
        return bool(has_author and has_year)
    
    def _check_style_compliance(self, diff: UnifiedDiff, vision: VisionBrief) -> bool:
        """Check compliance with journal style guidelines."""
        journal_style = vision.journal_style.lower()
        
        # Basic style checks based on journal
        if "anthropologist" in journal_style:
            return self._check_anthropology_style(diff)
        else:
            return self._check_general_academic_style(diff)
    
    def _check_anthropology_style(self, diff: UnifiedDiff) -> bool:
        """Check American Anthropologist style guidelines."""
        text = diff.new_text
        warnings = []
        
        # Check for passive voice (discouraged)
        passive_indicators = ['was', 'were', 'been', 'being']
        if any(word in text.lower() for word in passive_indicators):
            warnings.append("Possible passive voice usage")
        
        # Check for contractions (should be avoided)
        contractions = ["don't", "won't", "can't", "isn't", "aren't", "hasn't", "haven't", "doesn't"]
        if any(contraction in text.lower() for contraction in contractions):
            warnings.append("Contractions should be avoided in academic writing")
        
        # Check for first person (should be limited)
        first_person = ['I ', 'we ', 'our ', 'us ']
        first_person_count = sum(text.lower().count(word) for word in first_person)
        if first_person_count > 2:  # Allow some first person in anthropology
            warnings.append("High usage of first person pronouns")
        
        # Log warnings but don't fail (style is advisory)
        for warning in warnings:
            logger.info(f"Style check: {warning}")
        
        return True  # Don't fail on style issues
    
    def _check_general_academic_style(self, diff: UnifiedDiff) -> bool:
        """Check general academic writing style."""
        text = diff.new_text
        
        # Check for informal language
        informal_words = ['really', 'very', 'quite', 'pretty', 'kind of', 'sort of']
        if any(word in text.lower() for word in informal_words):
            logger.info("Style check: Informal language detected")
        
        return True  # Advisory only
    
    def _check_claim_preservation(self, diff: UnifiedDiff, vision: VisionBrief) -> bool:
        """Check that edit preserves core claims."""
        # Simple keyword-based check for claim preservation
        for claim in vision.claims:
            claim_keywords = set(claim.lower().split())
            old_keywords = set(diff.old_text.lower().split())
            new_keywords = set(diff.new_text.lower().split())
            
            # If old text contained claim keywords, new text should too
            old_claim_overlap = len(claim_keywords.intersection(old_keywords))
            new_claim_overlap = len(claim_keywords.intersection(new_keywords))
            
            if old_claim_overlap >= 3 and new_claim_overlap < old_claim_overlap - 1:
                logger.warning(f"Potential claim dilution detected for: {claim[:50]}...")
                return False
        
        return True
    
    def _check_formatting_preservation(self, diff: UnifiedDiff) -> bool:
        """Check that edit preserves important formatting."""
        old_text = diff.old_text
        new_text = diff.new_text
        
        # Check for markdown formatting preservation
        markdown_elements = ['**', '*', '`', '#', '![', '](', '|']
        
        for element in markdown_elements:
            old_count = old_text.count(element)
            new_count = new_text.count(element)
            
            # Allow some variance but not complete removal
            if old_count > 0 and new_count == 0:
                logger.warning(f"Markdown element '{element}' removed in edit")
                return False
        
        return True
    
    def _run_nli_check(self, old_text: str, new_text: str) -> float:
        """Run NLI model to check entailment (placeholder for full implementation)."""
        # In full implementation, would use actual NLI model
        # For MVP, use simple heuristics
        
        old_words = set(old_text.lower().split())
        new_words = set(new_text.lower().split())
        
        # Simple overlap-based entailment score
        if len(old_words) == 0:
            return 1.0
        
        overlap = len(old_words.intersection(new_words))
        return overlap / len(old_words)