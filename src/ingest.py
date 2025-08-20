"""
Document ingestion and parsing for academic manuscripts.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import logging

from .models import Manuscript, ManuscriptSpan, Comment, CommentType
from .comment_parsers import UniversalCommentParser

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Ingest manuscripts and comments from various formats."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.preserve_formatting = config.get("preserve_formatting", True)
        self.extract_citations = config.get("extract_citations", True)
        self.chunk_size = config.get("chunk_size", "paragraph")
        self.comment_parser = UniversalCommentParser(config)
        
    def ingest_manuscript(self, path: Path) -> Manuscript:
        """
        Ingest manuscript from file and convert to internal format.
        
        Args:
            path: Path to manuscript file (.md, .docx, .tex)
            
        Returns:
            Manuscript object with parsed content and spans
        """
        logger.info(f"Ingesting manuscript: {path}")
        
        if path.suffix.lower() == '.md':
            return self._ingest_markdown(path)
        elif path.suffix.lower() == '.docx':
            return self._ingest_docx(path)
        elif path.suffix.lower() in ['.tex', '.latex']:
            return self._ingest_latex(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _ingest_markdown(self, path: Path) -> Manuscript:
        """Ingest Markdown manuscript."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse structure
        spans = self._parse_markdown_spans(content)
        
        # Extract metadata
        metadata = self._extract_markdown_metadata(content)
        
        # Extract citations
        citations = self._extract_citations(content) if self.extract_citations else {}
        
        # Identify figures and tables
        figures, tables = self._identify_figures_tables(spans)
        
        return Manuscript(
            title=metadata.get('title', 'Untitled'),
            content=content,
            spans=spans,
            metadata=metadata,
            citations=citations,
            figures=figures,
            tables=tables
        )
    
    def _parse_markdown_spans(self, content: str) -> Dict[str, ManuscriptSpan]:
        """Parse markdown content into structured spans."""
        lines = content.split('\n')
        spans = {}
        current_section = "untitled"
        paragraph_count = 0
        sentence_count = 0
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            if not line.strip():
                continue
                
            # Detect headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_text = line.strip('#').strip()
                current_section = self._slugify(heading_text)
                paragraph_count = 0
                
                span = ManuscriptSpan(
                    id=f"heading_{current_section}_{line_num}",
                    text=line,
                    section=current_section,
                    paragraph=0,
                    sentence=0,
                    start_line=line_num,
                    end_line=line_num,
                    block_type="heading",
                    protected=level <= 2  # Protect main headings
                )
                spans[span.id] = span
                
            # Detect figures
            elif '![' in line and '](' in line:
                span = ManuscriptSpan(
                    id=f"figure_{current_section}_{line_num}",
                    text=line,
                    section=current_section,
                    paragraph=paragraph_count,
                    sentence=0,
                    start_line=line_num,
                    end_line=line_num,
                    block_type="figure",
                    protected=True
                )
                spans[span.id] = span
                
            # Detect tables
            elif '|' in line and line.count('|') >= 2:
                span = ManuscriptSpan(
                    id=f"table_{current_section}_{line_num}",
                    text=line,
                    section=current_section,
                    paragraph=paragraph_count,
                    sentence=0,
                    start_line=line_num,
                    end_line=line_num,
                    block_type="table",
                    protected=True
                )
                spans[span.id] = span
                
            # Regular text paragraphs
            else:
                paragraph_count += 1
                sentences = self._split_sentences(line)
                
                for j, sentence in enumerate(sentences):
                    if sentence.strip():
                        sentence_count += 1
                        span = ManuscriptSpan(
                            id=f"text_{current_section}_p{paragraph_count}_s{j+1}",
                            text=sentence,
                            section=current_section,
                            paragraph=paragraph_count,
                            sentence=j+1,
                            start_line=line_num,
                            end_line=line_num,
                            block_type="text"
                        )
                        spans[span.id] = span
        
        return spans
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using basic rules."""
        # Simple sentence splitting - could be enhanced with spaCy/NLTK
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        return re.sub(r'[^\w\s-]', '', text).strip().lower().replace(' ', '_')
    
    def _extract_markdown_metadata(self, content: str) -> Dict[str, str]:
        """Extract YAML frontmatter or markdown metadata."""
        metadata = {}
        
        # Try to extract YAML frontmatter
        if content.startswith('---'):
            try:
                end_marker = content.find('---', 3)
                if end_marker > 0:
                    frontmatter = content[3:end_marker].strip()
                    # Simple key: value parsing (would use yaml library in production)
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()
            except Exception:
                logger.warning("Failed to parse YAML frontmatter")
        
        # Extract title from first heading
        if 'title' not in metadata:
            for line in content.split('\n'):
                if line.startswith('# '):
                    metadata['title'] = line[2:].strip()
                    break
        
        return metadata
    
    def _extract_citations(self, content: str) -> Dict[str, Dict[str, str]]:
        """Extract citations from markdown text."""
        citations = {}
        
        # Find citation patterns like (Author 2023) or [Author, 2023]
        patterns = [
            r'\(([A-Za-z]+(?:\s+et\s+al\.?)?\s+\d{4}[a-z]?(?::\s*\d+)?)\)',  # (Author 2023)
            r'\[([A-Za-z]+(?:\s+et\s+al\.?)?\s+\d{4}[a-z]?(?::\s*\d+)?)\]',  # [Author 2023]
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                citation_text = match.group(1)
                citation_key = self._generate_citation_key(citation_text)
                citations[citation_key] = {
                    'text': citation_text,
                    'type': 'intext',
                    'line': content[:match.start()].count('\n') + 1
                }
        
        return citations
    
    def _generate_citation_key(self, citation_text: str) -> str:
        """Generate unique key for citation."""
        return re.sub(r'[^\w\d]', '_', citation_text.lower())
    
    def _identify_figures_tables(self, spans: Dict[str, ManuscriptSpan]) -> Tuple[List[str], List[str]]:
        """Identify figure and table span IDs."""
        figures = [span_id for span_id, span in spans.items() if span.block_type == "figure"]
        tables = [span_id for span_id, span in spans.items() if span.block_type == "table"]
        return figures, tables
    
    def _ingest_docx(self, path: Path) -> Manuscript:
        """Ingest Word document (placeholder - would use python-docx)."""
        raise NotImplementedError("DOCX ingestion not yet implemented")
    
    def _ingest_latex(self, path: Path) -> Manuscript:
        """Ingest LaTeX document (placeholder - would use custom parser).""" 
        raise NotImplementedError("LaTeX ingestion not yet implemented")
    
    def ingest_comments(self, source: Union[str, Path, List[str]]) -> List[Comment]:
        """
        Ingest reviewer comments from any format or source.
        
        Args:
            source: Can be:
                - Path to file (JSON, PDF, DOCX, TXT, MD, etc.)
                - Raw text string containing comments
                - List of comment strings
                
        Returns:
            List of Comment objects
        """
        logger.info(f"Ingesting comments from: {source}")
        
        # Use the universal comment parser to handle any format
        return self.comment_parser.parse_comments(source)