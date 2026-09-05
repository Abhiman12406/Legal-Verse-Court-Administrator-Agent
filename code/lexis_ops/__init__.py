"""
LexisOps: Court Administration AI Agent System
Automated procedural validation, constraint scheduling, and clerk-in-the-loop orchestration.
"""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from lexis_ops.graph import build_lexis_ops_graph
from lexis_ops.pdf_rule_validator import (
    PDFRuleValidator,
    PDFValidationResult,
    validate_pdf_rules,
)

__all__ = [
    "build_lexis_ops_graph",
    "PDFRuleValidator",
    "PDFValidationResult",
    "validate_pdf_rules",
]

