"""Fix suggestion engine – produces non-destructive patch recommendations."""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from typing import Any

from .trace import TraceResult

logger = logging.getLogger(__name__)

# Regex patterns reused across fixers
_STR_CONCAT_PATTERN = re.compile(r"(\w[\w.]*)\s*\+\s*(\w[\w.]*)")
_BRACKET_ACCESS_PATTERN = re.compile(r"(\w[\w.]*)\[([^\]]+)\]")
_DIV_PATTERN = re.compile(r"(\w[\w.]*)\s*/\s*(\w[\w.]*)")
_MOD_PATTERN = re.compile(r"(\w[\w.]*)\s*%\s*(\w[\w.]*)")


@dataclass
class PatchSuggestion:
    """A single suggested code change.

    Attributes:
        line_number: 1-based line where the change should be applied.
        original_line: The current source line content.
        suggested_line: The proposed replacement line.
        description: Human-readable explanation of the fix.
        confidence: How confident the engine is (0.0 – 1.0).
        diff: Unified-diff string for the change (computed on access).
    """

    line_number: int
    original_line: str
    suggested_line: str
    description: str
    confidence: float

    @property
    def diff(self) -> str:
        """Return a unified diff of the change."""
        a = self.original_line.splitlines(keepends=True) or [""]
        b = self.suggested_line.splitlines(keepends=True) or [""]
        lines = list(difflib.unified_diff(
            a, b,
            fromfile=f"original (line {self.line_number})",
            tofile="suggested",
            lineterm="",
        ))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dictionary."""
        return {
            "line_number": self.line_number,
            "original_line": self.original_line,
            "suggested_line": self.suggested_line,
            "description": self.description,
            "confidence": round(self.confidence, 2),
        }


class Fixer:
    """Generates :class:`PatchSuggestion` objects for a given exception trace.

    No source files are ever modified.  All suggestions are advisory only.
    """

    def suggest_fixes(self, trace: TraceResult) -> list[PatchSuggestion]:
        """Return a list of fix suggestions for *trace*.

        Args:
            trace: :class:`~codemedic.trace.TraceResult` from the collector.

        Returns:
            Possibly empty list of :class:`PatchSuggestion` objects,
            ordered by confidence (highest first).
        """
        exc = trace.exception_type
        dispatch: dict[str, Any] = {
            "TypeError": self._fix_type_error,
            "NameError": self._fix_name_error,
            "UnboundLocalError": self._fix_name_error,
            "IndexError": self._fix_index_error,
            "KeyError": self._fix_key_error,
            "AttributeError": self._fix_attribute_error,
            "ZeroDivisionError": self._fix_zero_division,
            "FileNotFoundError": self._fix_file_not_found,
            "ImportError": self._fix_import_error,
            "ModuleNotFoundError": self._fix_import_error,
            "RecursionError": self._fix_recursion_error,
            "ValueError": self._fix_value_error,
            "AssertionError": self._fix_assertion_error,
        }

        handler = dispatch.get(exc)
        suggestions: list[PatchSuggestion] = handler(trace) if handler else []

        if not suggestions and trace.innermost_frame:
            suggestions.append(self._generic_suggestion(trace))

        # Sort by descending confidence
        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)

    def _fix_type_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        msg = trace.exception_message.lower()

        for frame in trace.frames:
            line = (frame.code_context or "").strip()
            if not line:
                continue

            # str + non-str concatenation
            if "can only concatenate" in msg or "must be str" in msg:
                match = _STR_CONCAT_PATTERN.search(line)
                if match:
                    v1, v2 = match.group(1), match.group(2)
                    new_line = line.replace(match.group(0), f"str({v1}) + str({v2})")
                    suggestions.append(PatchSuggestion(
                        line_number=frame.lineno,
                        original_line=line,
                        suggested_line=new_line,
                        description=f"Convert both operands to str: str({v1}) + str({v2}). "
                                    f"Or use an f-string: f'{{{v1}}}{{{v2}}}'.",
                        confidence=0.80,
                    ))

            # unsupported operand types
            if "unsupported operand type" in msg:
                suggestions.append(PatchSuggestion(
                    line_number=frame.lineno,
                    original_line=line,
                    suggested_line=f"# Ensure both operands are the same type before this line",
                    description="Operands have incompatible types. Add explicit type conversion.",
                    confidence=0.55,
                ))

            # not callable
            if "object is not callable" in msg:
                suggestions.append(PatchSuggestion(
                    line_number=frame.lineno,
                    original_line=line,
                    suggested_line=line,
                    description="You are calling something that is not a function. "
                                 "Check if you accidentally overrode a built-in name "
                                 "or forgot to reference the callable.",
                    confidence=0.60,
                ))

        return suggestions

    def _fix_name_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        match = re.search(r"name '(\w+)' is not defined", trace.exception_message)
        if not match:
            match = re.search(r"free variable '(\w+)' referenced", trace.exception_message)
        if not match:
            return suggestions

        undefined = match.group(1)
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()

        # Look for similar names in the frame's local variables
        candidates = list(frame.locals.keys())
        similar = difflib.get_close_matches(undefined, candidates, n=3, cutoff=0.75)

        if similar:
            new_line = line.replace(undefined, similar[0])
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=new_line,
                description=(
                    f"Did you mean '{similar[0]}'? "
                    + (
                        f"Other close matches: {', '.join(similar[1:])}."
                        if similar[1:]
                        else ""
                    )
                ),
                confidence=0.85,
            ))
        else:
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=f"{undefined} = None  # TODO: assign the correct value",
                description=f"'{undefined}' is not defined. Define it before this line.",
                confidence=0.50,
            ))

        return suggestions

    def _fix_index_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        match = _BRACKET_ACCESS_PATTERN.search(line)
        if not match:
            return suggestions

        var, idx_expr = match.group(1), match.group(2)
        # Only suggest bounds check for numeric literals
        if re.match(r"^\d+$", idx_expr.strip()):
            idx = int(idx_expr.strip())
            new_line = f"if len({var}) > {idx}:\n    {line}"
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=new_line,
                description=f"Guard the access: check len({var}) > {idx} first. "
                            f"Alternatively use: {var}[{idx}] if len({var}) > {idx} else None",
                confidence=0.80,
            ))
        else:
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=f"# Ensure index '{idx_expr}' is within range before: {line}",
                description=f"Check that '{idx_expr}' is a valid index for '{var}'.",
                confidence=0.60,
            ))

        return suggestions

    def _fix_key_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()

        # Try to extract a simple varname[key] pattern
        # Matches either  varname['key']  or  varname[key]  or  varname[expr]
        match = re.search(r"(\w[\w.]*)\[([^\]]+)\]", line)

        if match:
            var, key_expr = match.group(1), match.group(2)
            # Suggest .get()
            get_version = line.replace(
                match.group(0), f"{var}.get({key_expr}, None)"
            )
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=get_version,
                description=f"Use {var}.get({key_expr}, default) to avoid KeyError.",
                confidence=0.85,
            ))
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=f"if {key_expr} in {var}:\n    {line}",
                description=f"Guard with: if {key_expr} in {var}: before accessing.",
                confidence=0.75,
            ))
        else:
            # Fallback: use the key from the exception message
            key_name = trace.exception_message.strip("'\"")
            suggestions.append(PatchSuggestion(
                line_number=frame.lineno,
                original_line=line,
                suggested_line=f"# Use dict.get('{key_name}', default) to avoid KeyError",
                description=(
                    f"Key '{key_name}' does not exist. Use "
                    f"dict.get('{key_name}', default) instead of direct access."
                ),
                confidence=0.70,
            ))

        return suggestions

    def _fix_attribute_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        msg = trace.exception_message
        # Extract: 'type' object has no attribute 'attr'
        match = re.search(r"'(\w+)' object has no attribute '(\w+)'", msg)
        if not match:
            return suggestions

        obj_type, attr = match.group(1), match.group(2)
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        suggestions.append(PatchSuggestion(
            line_number=frame.lineno,
            original_line=line,
            suggested_line=f"# '{obj_type}' has no attribute '{attr}'. Use hasattr() to check.",
            description=(
                f"'{obj_type}' objects do not have '{attr}'. "
                f"Use hasattr(obj, '{attr}') to check before accessing. "
                f"Run dir(obj) to list available attributes."
            ),
            confidence=0.70,
        ))

        return suggestions

    def _fix_zero_division(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        for pattern, op in ((_DIV_PATTERN, "/"), (_MOD_PATTERN, "%")):
            match = pattern.search(line)
            if match:
                numer, denom = match.group(1), match.group(2)
                new_line = line.replace(
                    match.group(0), f"({numer} {op} {denom} if {denom} != 0 else 0)"
                )
                suggestions.append(PatchSuggestion(
                    line_number=frame.lineno,
                    original_line=line,
                    suggested_line=new_line,
                    description=f"Guard against zero: check '{denom} != 0' before dividing.",
                    confidence=0.85,
                ))
                break

        return suggestions

    def _fix_file_not_found(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        suggestions.append(PatchSuggestion(
            line_number=frame.lineno,
            original_line=line,
            suggested_line=(
                "from pathlib import Path\n"
                f"path = Path(...)  # set correct path\n"
                "if path.exists():\n"
                f"    {line}"
            ),
            description="Verify the file exists with Path.exists() before opening it.",
            confidence=0.75,
        ))

        return suggestions

    def _fix_import_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        match = re.search(r"No module named '([\w.]+)'", trace.exception_message)
        if not match:
            return suggestions

        module = match.group(1)
        frame = trace.innermost_frame
        line = (frame.code_context or "").strip() if frame else ""
        module_name = module.split('.')[0]
        suggestions.append(PatchSuggestion(
            line_number=frame.lineno if frame else 0,
            original_line=line,
            suggested_line=f"# pip install {module_name}",
            description=(
                f"Module '{module}' is not installed. "
                f"Run: pip install {module_name}"
            ),
            confidence=0.90,
        ))

        return suggestions

    def _fix_recursion_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        suggestions.append(PatchSuggestion(
            line_number=frame.lineno,
            original_line=line,
            suggested_line=f"# Ensure a base case terminates recursion before: {line}",
            description=(
                "Your function calls itself without a proper base case. "
                "Add a condition that stops the recursion. "
                "Consider refactoring to an iterative approach."
            ),
            confidence=0.80,
        ))

        return suggestions

    def _fix_value_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        suggestions.append(PatchSuggestion(
            line_number=frame.lineno,
            original_line=line,
            suggested_line=(
                "try:\n"
                f"    {line}\n"
                "except ValueError as e:\n"
                "    # handle invalid value\n"
                "    pass"
            ),
            description="Wrap the operation in try/except ValueError to handle invalid values.",
            confidence=0.65,
        ))

        return suggestions

    def _fix_assertion_error(self, trace: TraceResult) -> list[PatchSuggestion]:
        suggestions: list[PatchSuggestion] = []
        frame = trace.innermost_frame
        if frame is None:
            return suggestions

        line = (frame.code_context or "").strip()
        suggestions.append(PatchSuggestion(
            line_number=frame.lineno,
            original_line=line,
            suggested_line=line.replace("assert ", "if not (") + ": raise ValueError(...)",
            description=(
                "Convert the assert to an explicit raise for "
                "clearer error messages in production."
            ),
            confidence=0.60,
        ))

        return suggestions

    def _generic_suggestion(self, trace: TraceResult) -> PatchSuggestion:
        frame = trace.innermost_frame
        assert frame is not None
        line = (frame.code_context or "").strip()
        return PatchSuggestion(
            line_number=frame.lineno,
            original_line=line,
            suggested_line=line,
            description=(
                f"Review line {frame.lineno} in '{frame.short_filename}'. "
                f"Error: {trace.exception_type}: {trace.exception_message}"
            ),
            confidence=0.30,
        )
