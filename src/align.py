"""
Comment alignment - matching reviewer comments to manuscript spans.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import difflib

from .models import Comment, Manuscript, ManuscriptSpan, CommentType

logger = logging.getLogger(__name__)


class CommentAligner:
    """Align reviewer comments to specific manuscript spans."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        self.top_k = config.get("top_k", 5)
        self.context_window = config.get("context_window", 3)
        self.boost_exact_matches = config.get("boost_exact_matches", True)
        
    def align_comments(self, comments: List[Comment], manuscript: Manuscript) -> List[Comment]:
        """
        Align comments to manuscript spans using multiple strategies.
        
        Args:
            comments: List of reviewer comments
            manuscript: Parsed manuscript with spans
            
        Returns:
            Comments with updated links to manuscript spans
        """
        logger.info(f"Aligning {len(comments)} comments to manuscript spans")
        
        aligned_comments = []
        for comment in comments:
            # Try multiple alignment strategies
            aligned_spans = self._find_best_alignment(comment, manuscript)
            
            # Update comment with aligned spans
            comment.links = aligned_spans
            aligned_comments.append(comment)
            
            logger.debug(f"Comment {comment.id} aligned to {len(aligned_spans)} spans")
        
        return aligned_comments
    
    def _find_best_alignment(self, comment: Comment, manuscript: Manuscript) -> List[str]:
        """Find best matching spans for a comment using multiple strategies."""
        # Strategy 1: Explicit references in comment text
        explicit_matches = self._find_explicit_references(comment, manuscript)
        if explicit_matches:
            return explicit_matches
        
        # Strategy 2: Keyword overlap
        keyword_matches = self._find_keyword_matches(comment, manuscript)
        
        # Strategy 3: Context similarity (would use embeddings in full implementation)
        context_matches = self._find_context_matches(comment, manuscript)
        
        # Strategy 4: Comment type heuristics
        type_matches = self._find_type_based_matches(comment, manuscript)
        
        # Combine and rank matches
        all_matches = self._combine_matches(
            explicit_matches, keyword_matches, context_matches, type_matches
        )
        
        # Return top-k matches above threshold
        return [match[0] for match in all_matches[:self.top_k] if match[1] >= self.similarity_threshold]
    
    def _find_explicit_references(self, comment: Comment, manuscript: Manuscript) -> List[str]:
        """Find spans explicitly referenced in comment text."""
        matches = []
        comment_text = comment.text.lower()
        
        # Look for section references
        section_patterns = [
            r'section\s+(\w+)',
            r'in\s+the\s+(\w+)\s+section',
            r'(\w+)\s+section',
        ]
        
        for pattern in section_patterns:
            for match in re.finditer(pattern, comment_text):
                section_name = match.group(1)
                # Find spans in that section
                for span_id, span in manuscript.spans.items():
                    if section_name in span.section.lower():
                        matches.append(span_id)
        
        # Look for paragraph/page references
        if 'paragraph' in comment_text or 'para' in comment_text:
            # Extract paragraph numbers
            para_matches = re.findall(r'paragraph\s+(\d+)|para\s+(\d+)', comment_text)
            for match in para_matches:
                para_num = int(match[0] or match[1])
                # Find spans in that paragraph
                for span_id, span in manuscript.spans.items():
                    if span.paragraph == para_num:
                        matches.append(span_id)
        
        # Look for figure/table references
        if 'figure' in comment_text or 'table' in comment_text:
            for span_id, span in manuscript.spans.items():
                if span.block_type in ['figure', 'table']:
                    matches.append(span_id)
        
        return list(set(matches))  # Remove duplicates
    
    def _find_keyword_matches(self, comment: Comment, manuscript: Manuscript) -> List[Tuple[str, float]]:
        """Find spans with high keyword overlap."""
        comment_words = set(self._extract_keywords(comment.text))
        matches = []
        
        for span_id, span in manuscript.spans.items():
            span_words = set(self._extract_keywords(span.text))
            
            if not comment_words or not span_words:
                continue
                
            # Calculate Jaccard similarity
            intersection = comment_words.intersection(span_words)
            union = comment_words.union(span_words)
            similarity = len(intersection) / len(union) if union else 0.0
            
            # Boost for exact phrase matches
            if self.boost_exact_matches:
                comment_phrases = self._extract_phrases(comment.text)
                for phrase in comment_phrases:
                    if phrase.lower() in span.text.lower():
                        similarity += 0.3  # Boost for exact phrase match
            
            matches.append((span_id, similarity))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def _find_context_matches(self, comment: Comment, manuscript: Manuscript) -> List[Tuple[str, float]]:
        """Find spans with similar context (simplified version)."""
        # In full implementation, this would use sentence embeddings
        # For MVP, use simple text similarity
        matches = []
        
        for span_id, span in manuscript.spans.items():
            # Use difflib for text similarity
            similarity = difflib.SequenceMatcher(
                None, comment.text.lower(), span.text.lower()
            ).ratio()
            
            matches.append((span_id, similarity))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def _find_type_based_matches(self, comment: Comment, manuscript: Manuscript) -> List[Tuple[str, float]]:
        """Find spans based on comment type heuristics."""
        matches = []
        base_score = 0.1  # Low base score for type-based matching
        
        if comment.type == CommentType.CLARIFY:
            # Look for complex sentences or technical terms
            for span_id, span in manuscript.spans.items():
                if self._is_complex_text(span.text):
                    matches.append((span_id, base_score))
        
        elif comment.type == CommentType.ADD_CITATION:
            # Look for claims without citations
            for span_id, span in manuscript.spans.items():
                if self._lacks_citations(span.text):
                    matches.append((span_id, base_score))
        
        elif comment.type == CommentType.RESTRUCTURE:
            # Look for section headings
            for span_id, span in manuscript.spans.items():
                if span.block_type == "heading":
                    matches.append((span_id, base_score))
        
        elif comment.type == CommentType.TIGHTEN:
            # Look for verbose paragraphs
            for span_id, span in manuscript.spans.items():
                if len(span.text.split()) > 50:  # Long sentences
                    matches.append((span_id, base_score))
        
        return matches
    
    def _combine_matches(self, *match_lists) -> List[Tuple[str, float]]:
        """Combine multiple match lists with weighted scoring."""
        combined_scores = defaultdict(float)
        weights = [1.0, 0.7, 0.5, 0.3]  # Weights for different strategies
        
        for weight, matches in zip(weights, match_lists):
            for item in matches:
                if isinstance(item, tuple):
                    span_id, score = item
                    combined_scores[span_id] += weight * score
                else:
                    # Just span_id, assign default score
                    combined_scores[item] += weight * 0.8
        
        # Convert to sorted list
        return sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Simple keyword extraction - would use NLP in full implementation
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'that', 'this', 'with', 'for', 'are', 'was', 'were',
            'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may',
            'can', 'must', 'shall', 'might', 'did', 'does', 'said', 'says'
        }
        
        return [word for word in words if word not in stop_words]
    
    def _extract_phrases(self, text: str, min_length: int = 3) -> List[str]:
        """Extract meaningful phrases from text."""
        # Simple phrase extraction - find sequences of 2-4 words
        words = re.findall(r'\b\w+\b', text)
        phrases = []
        
        for i in range(len(words) - 1):
            for length in range(2, min(5, len(words) - i + 1)):
                phrase = ' '.join(words[i:i + length])
                if len(phrase) >= min_length:
                    phrases.append(phrase)
        
        return phrases
    
    def _is_complex_text(self, text: str) -> bool:
        """Check if text is complex (has jargon, long sentences, etc.)."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        # Heuristics for complexity
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        return avg_word_length > 6 or avg_sentence_length > 25
    
    def _lacks_citations(self, text: str) -> bool:
        """Check if text makes claims without citations."""
        # Look for claim indicators without citation patterns
        claim_indicators = ['research shows', 'studies indicate', 'evidence suggests', 'according to']
        citation_patterns = [r'\([A-Za-z]+\s+\d{4}\)', r'\[[A-Za-z]+\s+\d{4}\]']
        
        has_claims = any(indicator in text.lower() for indicator in claim_indicators)
        has_citations = any(re.search(pattern, text) for pattern in citation_patterns)
        
        return has_claims and not has_citations