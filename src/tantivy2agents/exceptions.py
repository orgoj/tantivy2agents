"""Structured exception system for CLI errors."""

import json
import os
import sys
from typing import Any, Dict, Optional


class CLIError(Exception):
    """Base exception with structured output for both AI and humans.

    Provides JSON output for machine consumption and friendly messages
    with emojis and hints for human users.
    """

    def __init__(
        self,
        message: str,
        hint: Optional[str] = None,
        exit_code: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.hint = hint
        self.exit_code = exit_code
        self.context = context or {}
        super().__init__(message)

    def format_human(self) -> str:
        """Format error for human consumption with emojis and hints."""
        lines = [f"❌ Error: {self.message}"]
        if self.hint:
            lines.append(f"💡 Hint: {self.hint}")
        if self.context:
            lines.append("\nContext:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def format_json(self) -> str:
        """Format error as structured JSON for AI agents."""
        error_data = {
            "success": False,
            "error": {
                "message": self.message,
                "exit_code": self.exit_code,
            },
        }
        if self.hint:
            error_data["error"]["hint"] = self.hint
        if self.context:
            error_data["error"]["context"] = self.context
        return json.dumps(error_data, indent=2)

    def print(self) -> None:
        """Print with appropriate format based on environment."""
        is_json = os.getenv("TANTIVY_JSON_OUTPUT", "").lower() == "true"

        if is_json:
            print(self.format_json(), file=sys.stderr)
        else:
            print(self.format_human(), file=sys.stderr)


class ValidationError(CLIError):
    """Input validation errors with parameter context.

    Use when user provides invalid input (empty query, bad format, etc.).
    """

    def __init__(
        self,
        message: str,
        parameter: Optional[str] = None,
        expected: Optional[str] = None,
        got: Optional[str] = None,
    ):
        context = {}
        if parameter:
            context["parameter"] = parameter
        if expected:
            context["expected"] = expected
        if got:
            context["got"] = got

        hint = self._generate_hint(parameter, expected, got)
        super().__init__(message=message, hint=hint, context=context)

    def _generate_hint(
        self, parameter: Optional[str], expected: Optional[str], got: Optional[str]
    ) -> Optional[str]:
        """Generate helpful hint based on validation error."""
        if parameter == "query" and got == "(empty)":
            return "Provide a search query after 'search' command"
        if parameter == "format":
            return f"Use one of: {expected}"
        return None


class ConfigError(CLIError):
    """Configuration-related errors.

    Use when config file is missing, malformed, or contains invalid values.
    """

    def __init__(self, message: str, config_path: Optional[str] = None):
        context = {}
        if config_path:
            context["config_path"] = config_path
            hint = f"Check {config_path} or run 'tantivy2agents install'"
        else:
            hint = "Run 'tantivy2agents install' to create config"

        super().__init__(message=message, hint=hint, context=context)


class IndexNotFoundError(CLIError):
    """Search index doesn't exist or is outdated.

    Use when search is attempted without building index first.
    """

    def __init__(self, index_dir: Optional[str] = None):
        message = "Search index not found or outdated"
        hint = "Run 'tantivy2agents index' to build the search index"

        context = {}
        if index_dir:
            context["index_dir"] = index_dir

        super().__init__(message=message, hint=hint, context=context)


class FileSystemError(CLIError):
    """File system related errors (permissions, missing files, etc.)."""

    def __init__(self, message: str, path: Optional[str] = None):
        context = {}
        if path:
            context["path"] = path

        hint = "Check file permissions and paths" if path else None
        super().__init__(message=message, hint=hint, context=context)
