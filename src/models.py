"""
Data models for manuscript processing and revision tracking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Literal
from enum import Enum
import json
from pathlib import Path


class CommentType(Enum):
    """Types of reviewer comments."""
    CLARIFY = "clarify"
    ADD_CITATION = "add_citation"
    RESTRUCTURE = "restructure"
    TIGHTEN = "tighten"
    COUNTERARGUMENT = "counterargument"
    COPYEDIT = "copyedit"
    EVIDENCE_GAP = "evidence_gap"


class Priority(Enum):
    """Comment priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(Enum):
    """Comment processing status."""
    PENDING = "pending"
    PLANNED = "planned"
    PATCHED = "patched"
    VERIFIED = "verified"
    APPLIED = "applied"
    REJECTED = "rejected"


@dataclass
class VisionBrief:
    """Core vision and constraints for manuscript revision."""
    thesis: str
    claims: List[str]
    scope: str
    do_not_change: List[str]
    journal_style: str
    target_length: Optional[str] = "maintain current"
    additional_constraints: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "VisionBrief":
        """Load vision brief from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    def to_json(self, path: Union[str, Path]) -> None:
        """Save vision brief to JSON file."""
        with open(path, 'w') as f:
            json.dump({
                "thesis": self.thesis,
                "claims": self.claims,
                "scope": self.scope,
                "do_not_change": self.do_not_change,
                "journal_style": self.journal_style,
                "target_length": self.target_length,
                "additional_constraints": self.additional_constraints
            }, f, indent=2)


@dataclass
class Comment:
    """A single reviewer comment with metadata."""
    id: str
    source: str
    type: CommentType
    text: str
    links: List[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    status: Status = Status.PENDING
    confidence: Optional[float] = None
    suggested_edit: Optional[str] = None
    rationale: Optional[str] = None

    def __post_init__(self):
        """Convert string enums to proper enum types."""
        if isinstance(self.type, str):
            self.type = CommentType(self.type)
        if isinstance(self.priority, str):
            self.priority = Priority(self.priority)
        if isinstance(self.status, str):
            self.status = Status(self.status)


@dataclass
class ManuscriptSpan:
    """A text span in the manuscript with structural metadata."""
    id: str
    text: str
    section: str
    paragraph: int
    sentence: int
    start_line: int
    end_line: int
    block_type: Literal["text", "heading", "figure", "table", "citation", "equation"]
    protected: bool = False  # Cannot be modified
    
    def __contains__(self, line_number: int) -> bool:
        """Check if line number falls within this span."""
        return self.start_line <= line_number <= self.end_line


@dataclass
class EditIntent:
    """An intended edit to address a reviewer comment."""
    comment_id: str
    target_spans: List[str]  # ManuscriptSpan IDs
    operation: Literal["replace", "insert_before", "insert_after", "delete", "restructure"]
    new_text: str
    justification: str
    preserves_claims: bool = True
    risk_level: Literal["safe", "moderate", "risky"] = "safe"


@dataclass 
class UnifiedDiff:
    """A unified diff representing changes to the manuscript."""
    span_id: str
    section: str
    paragraph: int
    old_text: str
    new_text: str
    line_start: int
    line_end: int
    confidence: float
    preserves_semantics: bool = True

    def format_diff(self) -> str:
        """Format as unified diff string."""
        header = f"@@ {self.section} p:{self.paragraph} @@"
        old_lines = [f"- {line}" for line in self.old_text.split('\n')]
        new_lines = [f"+ {line}" for line in self.new_text.split('\n')]
        return '\n'.join([header] + old_lines + new_lines)


@dataclass
class Manuscript:
    """Complete manuscript representation."""
    title: str
    content: str  # Full markdown content
    spans: Dict[str, ManuscriptSpan]
    metadata: Dict[str, str]
    citations: Dict[str, Dict[str, str]]  # Citation key -> metadata
    figures: List[str]  # Figure span IDs
    tables: List[str]   # Table span IDs
    
    def get_span_by_line(self, line_number: int) -> Optional[ManuscriptSpan]:
        """Find the span containing a given line number."""
        for span in self.spans.values():
            if line_number in span:
                return span
        return None
    
    def get_protected_spans(self) -> List[ManuscriptSpan]:
        """Get all spans marked as protected."""
        return [span for span in self.spans.values() if span.protected]


@dataclass
class RevisionPlan:
    """Complete plan for manuscript revision."""
    vision: VisionBrief
    comments: List[Comment]
    intents: List[EditIntent]
    diffs: List[UnifiedDiff]
    conflicts: List[Dict[str, str]] = field(default_factory=list)
    
    def get_comments_by_status(self, status: Status) -> List[Comment]:
        """Get all comments with given status."""
        return [c for c in self.comments if c.status == status]
    
    def get_completion_rate(self) -> float:
        """Calculate percentage of comments that have been addressed."""
        if not self.comments:
            return 1.0
        addressed = len([c for c in self.comments if c.status in [Status.APPLIED, Status.REJECTED]])
        return addressed / len(self.comments)


@dataclass
class VerificationResult:
    """Result of verifying a proposed edit."""
    passed: bool
    checks: Dict[str, bool]  # check_name -> passed
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    confidence: float = 0.0