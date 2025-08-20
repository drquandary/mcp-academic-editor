"""
Flexible comment parsing for multiple formats and sources.
"""

import re
import json
import logging
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .models import Comment, CommentType, Priority

logger = logging.getLogger(__name__)


class CommentSource(Enum):
    """Types of comment sources we can handle."""
    JSON_STRUCTURED = "json_structured"
    PLAIN_TEXT = "plain_text"
    DIFF_FORMAT = "diff_format"
    MARKDOWN_INLINE = "markdown_inline"
    DOCX_COMMENTS = "docx_comments"
    PDF_ANNOTATIONS = "pdf_annotations"
    REVIEWER_RESPONSE = "reviewer_response"
    EMAIL_FEEDBACK = "email_feedback"
    PASTED_TEXT = "pasted_text"


@dataclass
class ParsedComment:
    """Raw parsed comment before conversion to Comment object."""
    text: str
    source: str = "Unknown"
    line_reference: Optional[str] = None
    section_reference: Optional[str] = None
    quoted_text: Optional[str] = None
    comment_type: Optional[str] = None
    priority: Optional[str] = None
    reviewer_id: Optional[str] = None


class UniversalCommentParser:
    """Parse comments from any format or source."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.auto_detect = config.get("auto_detect_format", True)
        self.extract_quotes = config.get("extract_quoted_text", True)
        self.infer_types = config.get("infer_comment_types", True)
        
        # Type mapping for common aliases
        self.type_mapping = {
            'revise': CommentType.RESTRUCTURE,
            'revision': CommentType.RESTRUCTURE,
            'edit': CommentType.COPYEDIT,
            'citation': CommentType.ADD_CITATION,
            'evidence': CommentType.EVIDENCE_GAP,
            'improve': CommentType.TIGHTEN,
            'explain': CommentType.CLARIFY,
            'unclear': CommentType.CLARIFY
        }
        
    def parse_comments(self, source: Union[str, Path, List[str]]) -> List[Comment]:
        """
        Parse comments from any source format.
        
        Args:
            source: Can be:
                - Path to file (.json, .txt, .md, .docx, .pdf)
                - Raw text string with comments
                - List of comment strings
                
        Returns:
            List of Comment objects
        """
        if isinstance(source, Path):
            return self._parse_from_file(source)
        elif isinstance(source, str):
            # Check if it looks like a file path (reasonable length, no newlines)
            if len(source) < 500 and '\n' not in source and ('/' in source or '\\' in source or source.endswith(('.json', '.txt', '.md', '.pdf', '.docx'))):
                path = Path(source)
                if path.exists():
                    return self._parse_from_file(path)
            # Treat as raw text
            return self._parse_from_text(source)
        elif isinstance(source, list):
            return self._parse_from_list(source)
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")
    
    def _map_comment_type(self, type_str: str) -> CommentType:
        """Map comment type string to CommentType enum, with fallbacks."""
        if not type_str:
            return CommentType.CLARIFY
        
        type_str = type_str.lower().strip()
        
        # Try direct enum match first
        try:
            return CommentType(type_str)
        except ValueError:
            pass
        
        # Try mapping
        if type_str in self.type_mapping:
            return self.type_mapping[type_str]
        
        # Default fallback
        return CommentType.CLARIFY
    
    def _parse_from_file(self, path: Path) -> List[Comment]:
        """Parse comments from a file."""
        logger.info(f"Parsing comments from file: {path}")
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Auto-detect format based on file extension and content
        if path.suffix.lower() == '.json':
            return self._parse_json_comments(content)
        elif path.suffix.lower() in ['.txt', '.md']:
            return self._parse_text_comments(content, path.suffix)
        elif path.suffix.lower() == '.diff':
            return self._parse_diff_comments(content)
        elif path.suffix.lower() == '.docx':
            return self._parse_docx_comments(path)
        elif path.suffix.lower() == '.pdf':
            return self._parse_pdf_comments(path)
        else:
            # Auto-detect from content
            return self._auto_detect_and_parse(content)
    
    def _parse_from_text(self, text: str) -> List[Comment]:
        """Parse comments from raw text."""
        logger.info("Parsing comments from raw text")
        return self._auto_detect_and_parse(text)
    
    def _parse_from_list(self, comment_list: List[str]) -> List[Comment]:
        """Parse comments from a list of strings."""
        logger.info(f"Parsing {len(comment_list)} comments from list")
        
        parsed_comments = []
        for i, comment_text in enumerate(comment_list):
            parsed = ParsedComment(
                text=comment_text.strip(),
                source=f"List item {i+1}",
                reviewer_id=f"Reviewer_{i+1}"
            )
            comment = self._convert_parsed_comment(parsed, f"LIST-{i+1}")
            parsed_comments.append(comment)
        
        return parsed_comments
    
    def _auto_detect_and_parse(self, content: str) -> List[Comment]:
        """Auto-detect format and parse accordingly."""
        content = content.strip()
        
        # Try JSON first
        if content.startswith('[') or content.startswith('{'):
            try:
                return self._parse_json_comments(content)
            except json.JSONDecodeError:
                pass
        
        # Check for diff format
        if '@@' in content and ('---' in content or '+++' in content):
            return self._parse_diff_comments(content)
        
        # Check for structured reviewer format
        if re.search(r'reviewer?\s+\d+', content, re.IGNORECASE):
            return self._parse_reviewer_response(content)
        
        # Check for markdown-style comments
        if re.search(r'#{1,6}\s+', content) or '**Comment**' in content:
            return self._parse_markdown_comments(content)
        
        # Default to plain text parsing
        return self._parse_plain_text(content)
    
    def _parse_json_comments(self, content: str) -> List[Comment]:
        """Parse structured JSON comments."""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                data = [data]  # Single comment object
            
            comments = []
            for i, item in enumerate(data):
                comment_id = item.get('id', f'JSON-{i+1}')
                comment = Comment(
                    id=comment_id,
                    source=item.get('source', 'JSON File'),
                    type=self._map_comment_type(item.get('type', 'clarify')),
                    text=item['text'],
                    links=item.get('links', []),
                    priority=Priority(item.get('priority', 'medium')),
                    suggested_edit=item.get('suggested_edit'),
                    rationale=item.get('rationale')
                )
                comments.append(comment)
            
            return comments
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON comments: {e}")
            # Fall back to text parsing
            return self._parse_plain_text(content)
    
    def _parse_diff_comments(self, content: str) -> List[Comment]:
        """Parse comments from diff format."""
        comments = []
        
        # Find diff blocks with comments
        diff_blocks = re.split(r'@@.*?@@', content)
        
        for i, block in enumerate(diff_blocks):
            if not block.strip():
                continue
                
            # Extract context from diff headers
            header_match = re.search(r'@@ -(\d+),?\d* \+(\d+),?\d* @@(.*)$', block, re.MULTILINE)
            
            # Look for comment markers in the block
            comment_patterns = [
                r'#\s*(.*?)(?:\n|$)',  # # Comment
                r'//\s*(.*?)(?:\n|$)',  # // Comment
                r'<!--\s*(.*?)\s*-->',  # <!-- Comment -->
                r'>\s*(.*?)(?:\n|$)',   # > Quoted comment
            ]
            
            for pattern in comment_patterns:
                matches = re.finditer(pattern, block, re.MULTILINE)
                for match in matches:
                    comment_text = match.group(1).strip()
                    if len(comment_text) > 10:  # Filter out short noise
                        parsed = ParsedComment(
                            text=comment_text,
                            source="Diff Block",
                            line_reference=header_match.group(2) if header_match else None,
                            quoted_text=self._extract_diff_context(block)
                        )
                        comment = self._convert_parsed_comment(parsed, f"DIFF-{i+1}")
                        comments.append(comment)
        
        return comments
    
    def _parse_reviewer_response(self, content: str) -> List[Comment]:
        """Parse structured reviewer responses."""
        comments = []
        
        # Split by reviewer sections
        reviewer_sections = re.split(r'(?:^|\n)\s*reviewer?\s*(\d+)', content, flags=re.IGNORECASE | re.MULTILINE)
        
        current_reviewer = "Unknown"
        
        for i, section in enumerate(reviewer_sections):
            if i % 2 == 1:  # Reviewer number
                current_reviewer = f"Reviewer {section.strip()}"
                continue
            
            if not section.strip():
                continue
            
            # Look for numbered comments or bullet points
            comment_patterns = [
                r'(\d+)\.\s*(.*?)(?=\n\d+\.|$)',  # 1. Comment text
                r'[-*•]\s*(.*?)(?=\n[-*•]|$)',     # - Comment text
                r'Comment:?\s*(.*?)(?=\nComment:|$)',  # Comment: text
                r'(?:^|\n)([^.\n]{20,}?)(?=\n|$)',     # Paragraph-like comments
            ]
            
            for pattern in comment_patterns:
                matches = re.finditer(pattern, section, re.MULTILINE | re.DOTALL)
                for j, match in enumerate(matches):
                    comment_text = match.group(-1).strip()  # Last group
                    if len(comment_text) > 15:  # Filter short comments
                        parsed = ParsedComment(
                            text=comment_text,
                            source=current_reviewer,
                            reviewer_id=current_reviewer.replace(" ", "_")
                        )
                        comment = self._convert_parsed_comment(parsed, f"{current_reviewer}-C{j+1}")
                        comments.append(comment)
        
        return comments
    
    def _parse_markdown_comments(self, content: str) -> List[Comment]:
        """Parse markdown-formatted comments."""
        comments = []
        
        # Look for structured markdown comments
        patterns = [
            r'#{1,6}\s*(.*?)\n(.*?)(?=\n#{1,6}|$)',  # Headings with content
            r'\*\*Comment\*\*:?\s*(.*?)(?=\n\*\*|$)',  # **Comment**: text
            r'>\s*(.*?)(?=\n[^>]|$)',  # > Blockquotes
            r'(?:^|\n)(\d+)\.\s*(.*?)(?=\n\d+\.|$)',  # Numbered lists
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for i, match in enumerate(matches):
                if len(match.groups()) == 2:
                    title, comment_text = match.groups()
                    full_text = f"{title.strip()}: {comment_text.strip()}"
                else:
                    full_text = match.group(1).strip()
                
                if len(full_text) > 15:
                    parsed = ParsedComment(
                        text=full_text,
                        source="Markdown Document",
                        section_reference=title.strip() if len(match.groups()) == 2 else None
                    )
                    comment = self._convert_parsed_comment(parsed, f"MD-{i+1}")
                    comments.append(comment)
        
        return comments
    
    def _parse_plain_text(self, content: str) -> List[Comment]:
        """Parse unstructured plain text comments."""
        comments = []
        
        # Split by common delimiters
        potential_comments = []
        
        # Try different splitting strategies
        strategies = [
            content.split('\n\n'),  # Paragraph splits
            content.split('\n---\n'),  # Horizontal rules
            content.split('\n===\n'),  # Double lines
            re.split(r'\n\d+\.', content),  # Numbered items
            re.split(r'\n[-*•]', content),  # Bullet points
        ]
        
        # Use the strategy that gives the most reasonable chunks
        best_split = max(strategies, key=lambda x: len([chunk for chunk in x if 20 <= len(chunk.strip()) <= 1000]))
        
        for i, chunk in enumerate(best_split):
            chunk = chunk.strip()
            if 20 <= len(chunk) <= 2000:  # Reasonable comment length
                # Try to extract quoted text if present
                quoted_text = self._extract_quoted_text(chunk)
                
                parsed = ParsedComment(
                    text=chunk,
                    source="Plain Text",
                    quoted_text=quoted_text
                )
                comment = self._convert_parsed_comment(parsed, f"TEXT-{i+1}")
                comments.append(comment)
        
        return comments
    
    def _parse_text_comments(self, content: str, file_extension: str) -> List[Comment]:
        """Parse text file comments with format-specific logic."""
        if file_extension == '.md':
            return self._parse_markdown_comments(content)
        else:
            return self._parse_plain_text(content)
    
    def _parse_docx_comments(self, path: Path) -> List[Comment]:
        """Parse Word document comments (placeholder for full implementation)."""
        logger.warning("DOCX comment parsing not yet implemented")
        # In full implementation, would use python-docx to extract comments
        return []
    
    def _parse_pdf_comments(self, path: Path) -> List[Comment]:
        """Parse PDF annotations (placeholder for full implementation).""" 
        logger.warning("PDF comment parsing not yet implemented")
        # In full implementation, would use PyPDF2 or pdfplumber
        return []
    
    def _extract_quoted_text(self, text: str) -> Optional[str]:
        """Extract quoted/referenced text from comment."""
        if not self.extract_quotes:
            return None
        
        # Look for quoted text patterns
        quote_patterns = [
            r'"([^"]{10,})"',  # "Quoted text"
            r"'([^']{10,})'",  # 'Quoted text'
            r'`([^`]{10,})`',  # `Code or text`
            r'>\s*([^\n]{10,})',  # > Blockquoted text
            r'(?:in|from|the text)\s*["\']([^"\']{10,})["\']',  # "in the text 'quoted'"
        ]
        
        for pattern in quote_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_diff_context(self, diff_block: str) -> Optional[str]:
        """Extract context from diff block."""
        # Look for lines being modified (- or + prefix)
        context_lines = []
        for line in diff_block.split('\n'):
            if line.startswith('-') and not line.startswith('---'):
                context_lines.append(line[1:].strip())
            elif line.startswith('+') and not line.startswith('+++'):
                context_lines.append(line[1:].strip())
        
        if context_lines:
            return '\n'.join(context_lines[:3])  # First few lines
        return None
    
    def _convert_parsed_comment(self, parsed: ParsedComment, comment_id: str) -> Comment:
        """Convert ParsedComment to Comment object."""
        # Infer comment type if not provided
        comment_type = self._infer_comment_type(parsed) if self.infer_types else CommentType.CLARIFY
        
        # Infer priority
        priority = self._infer_priority(parsed)
        
        # Create links from references
        links = []
        if parsed.line_reference:
            links.append(f"line:{parsed.line_reference}")
        if parsed.section_reference:
            links.append(f"section:{parsed.section_reference}")
        
        return Comment(
            id=comment_id,
            source=parsed.source,
            type=comment_type,
            text=parsed.text,
            links=links,
            priority=priority,
            suggested_edit=parsed.quoted_text  # Use quoted text as suggested edit context
        )
    
    def _infer_comment_type(self, parsed: ParsedComment) -> CommentType:
        """Infer comment type from text content."""
        text_lower = parsed.text.lower()
        
        # Type inference patterns
        type_patterns = {
            CommentType.CLARIFY: [
                'clarify', 'explain', 'define', 'unclear', 'confusing', 'what do you mean',
                'elaborate', 'specify', 'ambiguous'
            ],
            CommentType.ADD_CITATION: [
                'citation', 'reference', 'source', 'cite', 'bibliography', 'support this claim',
                'evidence', 'documentation'
            ],
            CommentType.RESTRUCTURE: [
                'restructure', 'reorganize', 'move', 'reorder', 'section', 'placement',
                'structure', 'flow', 'sequence'
            ],
            CommentType.TIGHTEN: [
                'concise', 'shorten', 'verbose', 'wordy', 'tighten', 'trim', 'reduce',
                'lengthy', 'repetitive'
            ],
            CommentType.COUNTERARGUMENT: [
                'however', 'but', 'counter', 'alternative', 'opposing', 'criticism',
                'limitation', 'weakness'
            ],
            CommentType.EVIDENCE_GAP: [
                'evidence', 'support', 'data', 'proof', 'substantiate', 'demonstrate',
                'show', 'justify'
            ]
        }
        
        # Score each type
        type_scores = {}
        for comment_type, keywords in type_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                type_scores[comment_type] = score
        
        # Return highest scoring type, or CLARIFY as default
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        return CommentType.CLARIFY
    
    def _infer_priority(self, parsed: ParsedComment) -> Priority:
        """Infer comment priority from text content."""
        text_lower = parsed.text.lower()
        
        # High priority indicators
        high_priority = ['must', 'critical', 'essential', 'required', 'major', 'serious', 'important']
        if any(word in text_lower for word in high_priority):
            return Priority.HIGH
        
        # Low priority indicators  
        low_priority = ['minor', 'small', 'optional', 'suggest', 'consider', 'might', 'could']
        if any(word in text_lower for word in low_priority):
            return Priority.LOW
        
        return Priority.MEDIUM  # Default