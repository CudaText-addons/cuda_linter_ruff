"""Ruff linter plugin for CudaText with CudaLint integration."""

from cuda_lint import Linter
import os
import shutil
import json
import re
from cudatext import *

# Plugin loaded (lazy loading via on_lexer/on_open)
print("Ruff: Plugin initialized")

class Ruff(Linter):
    """Ruff linter interface for CudaLint framework.

    Supports Python scripts with configurable rules and
    automatic executable detection (PATH or bundled version).
    """

    # Default timeout for subprocess calls (seconds)
    DEFAULT_TIMEOUT = 30

    # Support all Python lexer variants
    syntax = 'Python'
    CONFIG_FILE = 'ruff_config.json'

    # Default values required by CudaLint framework
    executable = 'ruff'
    cmd = ('ruff', 'check', '--output-format=concise', '@')

    # Regex for Ruff concise format: filename:line:col: CODE message
    # Example: test.py:10:5: E501 Line too long (120 > 88 characters)
    # Example: test.py:4:8: F401 [*] `os` imported but unused
    # Example: test.py:3:7: invalid-syntax: Simple statements must be separated
    # Regex maps E*/F* codes as errors, others as warnings
    regex = (
        r'^.+?:(?P<line>\d+):(?P<col>\d+): '
        r'(?:(?P<error>E\d+|F\d+)|(?P<warning>[\w-]+))'
        r'\s*:?\s+'
        r'(?P<message>.*)'
    )

    # Compile regex once at class level
    _RULE_CODE_PATTERN = re.compile(r'^[A-Z]{1,4}(?:\d+)?$|^ALL$')

    multiline = False
    tempfile_suffix = 'py'

    def __init__(self, view):
        super().__init__(view)

        # Find Ruff executable
        self.ruff_path = self._find_executable()
        if not self.ruff_path:
            self.ignore_codes = []
            self.select_codes = []
            self.timeout = Ruff.DEFAULT_TIMEOUT
            return

        # Load configuration
        config = self._load_config()
        self.ignore_codes = config.get('ignore', [])
        self.select_codes = config.get('select', [])
        self.timeout = config.get('timeout', Ruff.DEFAULT_TIMEOUT)

        # Use sensible defaults if no config exists
        if not self.ignore_codes and not self.select_codes:
            print("Ruff: No config found, using default rules")
            self.select_codes = ['E', 'F', 'W', 'B', 'I']
            self.ignore_codes = []

        # Update executable and command
        self.executable = self.ruff_path
        self.cmd = self._build_cmd()

        # Show diagnostic information
        self._log_status()

    def _find_executable(self):
        """Locate Ruff: system PATH first, then bundled version."""
        # Try system PATH (cross-platform, including Windows)
        if path := shutil.which('ruff'):
            print(f"Ruff: Found in PATH: {path}")
            return path

        # Try bundled version (Windows-specific handling)
        try:
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            exe = 'ruff.exe' if os.name == 'nt' else 'ruff'
            bundled = os.path.join(base, 'tools', 'Ruff', exe)

            if os.path.isfile(bundled):
                print(f"Ruff: Using bundled version: {bundled}")
                return bundled

            print(f"NOTE: Ruff not found in PATH or: {bundled}")
        except (NameError, AttributeError) as e:
            print(f"NOTE: Cannot locate bundled Ruff: {e}")

        return None

    def _load_config(self):
        """Load configuration from JSON config."""
        path = os.path.join(app_path(APP_DIR_SETTINGS), self.CONFIG_FILE)

        # Guard clause: config file doesn't exist
        if not os.path.isfile(path):
            return {'ignore': [], 'select': [], 'timeout': Ruff.DEFAULT_TIMEOUT}

        # Read and parse config file
        content = self._read_config_file(path)
        if not content:
            return {'ignore': [], 'select': [], 'timeout': Ruff.DEFAULT_TIMEOUT}

        # Parse and validate
        return self._parse_and_validate_config(content)

    def _read_config_file(self, path):
        """Read config file with comment stripping and encoding fallback."""
        try:
            # Try UTF-8 first (standard)
            with open(path, 'r', encoding='utf-8') as f:
                lines = [ln for ln in f if (stripped := ln.strip()) and not stripped.startswith(('//', '#'))]
                return ''.join(lines).strip()

        except UnicodeDecodeError:
            # Fallback to system default encoding (legacy Windows)
            try:
                with open(path, 'r') as f:
                    lines = [ln for ln in f if (stripped := ln.strip()) and not stripped.startswith(('//', '#'))]
                    return ''.join(lines).strip()
            except Exception as e:
                print(f"ERROR: Failed to read Ruff config with fallback encoding: {e}")
                return None

        except Exception as e:
            print(f"ERROR: Failed to read Ruff config: {e}")
            return None

    def _validate_rule_code(self, code):
        """Validate Ruff rule code format.

        Valid formats:
        - Specific codes: E501, F401, W503, B008, I001
        - Category prefixes: E, W, F, B, I, C90, N, etc.
        - All rules: ALL
        """
        return self._RULE_CODE_PATTERN.match(code) is not None

    def _filter_valid_codes(self, codes):
        """Filter and validate rule codes."""
        return [c for c in codes if isinstance(c, str) and self._validate_rule_code(c)]

    def _parse_and_validate_config(self, content):
        """Parse JSON and validate rule codes."""
        try:
            config = json.loads(content)

            # Guard clause: config must be a dict
            if not isinstance(config, dict):
                print("ERROR: Ruff config must be JSON object, not array/string")
                return {'ignore': [], 'select': [], 'timeout': Ruff.DEFAULT_TIMEOUT}

            # Extract and validate ignore codes
            ignore = config.get('ignore', [])
            if not isinstance(ignore, list):
                print("ERROR: Ruff 'ignore' must be array")
                ignore = []

            # Extract and validate select codes
            select = config.get('select', [])
            if not isinstance(select, list):
                print("ERROR: Ruff 'select' must be array")
                select = []

            # Validate timeout
            timeout = config.get('timeout', Ruff.DEFAULT_TIMEOUT)
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                print(f"NOTE: Ruff - Invalid timeout '{timeout}', using default: {Ruff.DEFAULT_TIMEOUT}")
                timeout = Ruff.DEFAULT_TIMEOUT

            # Validate format: rule codes are strings
            valid_ignore = self._filter_valid_codes(ignore)
            valid_select = self._filter_valid_codes(select)

            # Warn about invalid codes
            if invalid := [c for c in ignore if c not in valid_ignore]:
                print(f"NOTE: Ruff - Invalid ignore codes: {invalid}")

            if invalid := [c for c in select if c not in valid_select]:
                print(f"NOTE: Ruff - Invalid select codes: {invalid}")

            # Log loaded codes
            if valid_ignore:
                print(f"Ruff: Loaded ignore codes: {valid_ignore}")
            if valid_select:
                print(f"Ruff: Loaded select codes: {valid_select}")

            return {
                'ignore': valid_ignore,
                'select': valid_select,
                'timeout': timeout
            }

        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in Ruff config: {e}")
            return {'ignore': [], 'select': [], 'timeout': Ruff.DEFAULT_TIMEOUT}

    def _build_cmd(self):
        """Build command with select/ignore flags.

        Uses temporary file approach (@) instead of stdin to avoid
        Ruff's 'ignoring file in favor of stdin' warning.
        """
        cmd = [
            self.ruff_path,
            'check',
            '--output-format=concise'
        ]

        # Add select codes before file argument
        if self.select_codes:
            cmd.extend(['--select', ','.join(self.select_codes)])

        # Add ignore codes before file argument
        if self.ignore_codes:
            cmd.extend(['--ignore', ','.join(self.ignore_codes)])

        # Use @ which CudaLint replaces with temp file path
        cmd.append('@')

        print(f"Ruff: Command: {' '.join(cmd)}")
        return tuple(cmd)

    def _log_status(self):
        """Print diagnostic information."""
        ignore_count = len(self.ignore_codes)
        select_count = len(self.select_codes)

        status = []
        if select_count:
            status.append(f"{select_count} selected rule{'s' if select_count != 1 else ''}")
        if ignore_count:
            status.append(f"{ignore_count} ignored rule{'s' if ignore_count != 1 else ''}")

        status_str = ', '.join(status) if status else "default rules"
        print(f"Ruff: Active with {status_str}")

    def tmpfile(self, cmd, code, suffix=''):
        """Ensure .py extension for proper Ruff detection."""
        _, ext = os.path.splitext(self.filename)
        return super().tmpfile(cmd, code, ext or '.py')

    def split_match(self, match):
        """Include error code in message display."""
        m, line, col, error, warning, message, near = super().split_match(match)
        code = error or warning
        return m, line, col, error, warning, f"[{code}] {message}" if code else message, near

    def run(self, cmd, code):
        """Override to capture and log Ruff summary lines."""
        output = super().run(cmd, code)

        if output:
            for line in output.splitlines():
                if line.startswith('[*] '):
                    print(f"Ruff: {line}")

        return output

    def _get_ruff_version(self):
        """Get Ruff version for diagnostics."""
        if not self.ruff_path:
            return None

        try:
            import subprocess
            result = subprocess.run(
                [self.ruff_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Output format: "ruff 0.1.8"
                return result.stdout.strip().split()[-1]
        except Exception:
            pass

        return None

class Command:
    """Menu commands for Ruff plugin."""

    DEFAULT_CONFIG = {
        "timeout": Ruff.DEFAULT_TIMEOUT,
        "ignore": [
            "E501",   # line too long (handled by formatter)
            "W191",   # tab indentation
            "E111"    # indentation not multiple of four
        ],
        "select": [
            "E",      # pycodestyle errors
            "W",      # pycodestyle warnings
            "F",      # Pyflakes
            "B",      # flake8-bugbear
            "I"       # isort
        ]
    }

    def on_lexer(self, ed_self):
        """Trigger plugin loading when Python lexer is activated."""
        pass

    def on_open(self, ed_self):
        """Trigger plugin loading when Python file is opened."""
        pass

    def config(self):
        """Open/create configuration file."""
        path = os.path.join(app_path(APP_DIR_SETTINGS), Ruff.CONFIG_FILE)

        if not os.path.isfile(path):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=2)
                print(f"Ruff: Created default config: {path}")
            except Exception as e:
                msg_box(f"Failed to create config:\n{e}", MB_OK | MB_ICONERROR)
                print(f"ERROR: Failed to create Ruff config: {e}")
                return

        if file_open(path):
            print(f"Ruff: Opened config file: {path}")
        else:
            msg_box(f"Failed to open config file:\n{path}", MB_OK | MB_ICONWARNING)

    def _apply_changes_preserving_states(self, old_text, new_text):
        """Apply changes preserving line states using hybrid approach.

        Fast path (same line count): Native API - O(1) replace + O(n) comparison
        Slow path (lines added/removed): Myers diff - O(ND)
        """
        old_lines = old_text.splitlines(keepends=False)
        new_lines = new_text.splitlines(keepends=False)

        # Fast path 1: No changes at all
        if old_text == new_text:
            print("Ruff: Applying changes - No changes (skipped)")
            return

        # Fast path 2: Same line count (95% of cases)
        # Use Native API for maximum speed
        if len(old_lines) == len(new_lines):
            print(f"Ruff: Applying changes - Fast path ({len(old_lines)} lines)")

            # Save current line states
            old_states = ed.get_prop(PROP_LINE_STATES)

            # Save caret position
            carets = ed.get_carets()
            if carets:
                caret_x, caret_y = carets[0][:2]

            # Single fast replace
            line_count = ed.get_line_count()
            last_line_len = ed.get_line_len(line_count - 1)

            ed.replace(
                0, 0,
                last_line_len, line_count - 1,
                new_text
            )

            # Restore states for unchanged lines
            if old_states and len(old_states) >= len(old_lines):
                unchanged_count = 0

                for i in range(len(new_lines)):
                    if i < len(old_lines) and old_lines[i] == new_lines[i]:
                        # Line unchanged, restore old state
                        ed.set_prop(PROP_LINE_STATE, (i, old_states[i]))
                        unchanged_count += 1
                    else:
                        # Line changed, mark as changed
                        ed.set_prop(PROP_LINE_STATE, (i, LINESTATE_CHANGED))

            # Restore caret position
            if carets:
                # Ensure caret is within valid range
                new_line_count = ed.get_line_count()
                if caret_y >= new_line_count:
                    caret_y = new_line_count - 1

                new_line_len = ed.get_line_len(caret_y)
                if caret_x > new_line_len:
                    caret_x = new_line_len

                ed.set_caret(caret_x, caret_y)

            ed.action(EDACTION_UPDATE)

            return

        # Slow path: Line count changed (5% of cases)
        # Use Myers diff algorithm for perfect accuracy
        print(f"Ruff: Applying changes - Slow path (Myers diff: {len(old_lines)} -> {len(new_lines)} lines)")

        import difflib

        # Save caret position
        carets = ed.get_carets()
        if carets:
            caret_x, caret_y = carets[0][:2]

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        opcodes = list(matcher.get_opcodes())

        # Apply changes from TOP to BOTTOM with offset tracking
        offset = 0  # Track how much we've shifted

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                continue

            # Adjust indices with current offset
            adj_i1 = i1 + offset
            adj_i2 = i2 + offset

            if tag == 'replace':
                # Delete old lines
                for _ in range(i2 - i1):
                    ed.delete(0, adj_i1, 0, adj_i1 + 1)

                # Insert new lines
                for idx in range(j1, j2):
                    ed.insert(0, adj_i1, new_lines[idx] + '\n')
                    adj_i1 += 1  # Move insertion point down

                # Update offset: removed (i2-i1) lines, added (j2-j1) lines
                offset += (j2 - j1) - (i2 - i1)

            elif tag == 'delete':
                for _ in range(i2 - i1):
                    ed.delete(0, adj_i1, 0, adj_i1 + 1)

                # Update offset
                offset -= (i2 - i1)

            elif tag == 'insert':
                for idx in range(j1, j2):
                    ed.insert(0, adj_i1, new_lines[idx] + '\n')
                    adj_i1 += 1

                # Update offset
                offset += (j2 - j1)

        # Ensure last line has newline (Myers may miss it)
        if new_text.endswith('\n'):
            last_line_idx = ed.get_line_count() - 1
            last_line_text = ed.get_text_line(last_line_idx)
            last_line_len = ed.get_line_len(last_line_idx)

            # Replace last line with itself + newline
            ed.replace(0, last_line_idx, last_line_len, last_line_idx, last_line_text + '\n')

        # Restore caret position
        if carets:
            # Ensure caret is within valid range
            new_line_count = ed.get_line_count()
            if caret_y >= new_line_count:
                caret_y = new_line_count - 1

            new_line_len = ed.get_line_len(caret_y)
            if caret_x > new_line_len:
                caret_x = new_line_len

            ed.set_caret(caret_x, caret_y)

        ed.action(EDACTION_UPDATE)

    def fix_file(self):
        """Run Ruff --fix on current buffer (safe fixes only)."""
        self._fix_file(unsafe=False)

    def fix_file_unsafe(self):
        """Run Ruff --fix with unsafe fixes (review changes carefully!)."""
        # Ask for confirmation
        result = msg_box(
            "Apply UNSAFE fixes?\n\n"
            "Unsafe fixes may change code behavior.\n"
            "Review changes carefully and use Ctrl+Z to undo if needed.\n\n"
            "Continue?",
            MB_YESNO | MB_ICONWARNING
        )

        if result == ID_YES:
            self._fix_file(unsafe=True)

    def _fix_file(self, unsafe=False):
        """Internal method to apply fixes. Run Ruff --fix on current buffer (non-destructive, supports undo)."""
        import subprocess

        linter = Ruff(ed)
        if not linter.ruff_path:
            msg_box("Ruff executable not found!", MB_OK | MB_ICONERROR)
            return

        code = ed.get_text_all()

        cmd = [linter.ruff_path, 'check', '--fix', '-']

        if unsafe:
            cmd.append('--unsafe-fixes')

        if linter.select_codes:
            cmd.extend(['--select', ','.join(linter.select_codes)])
        if linter.ignore_codes:
            cmd.extend(['--ignore', ','.join(linter.ignore_codes)])

        cmd.extend(['--stdin-filename', ed.get_filename() or 'untitled.py'])

        try:
            result = subprocess.run(
                cmd,
                input=code,
                capture_output=True,
                text=True,
                timeout=linter.timeout
            )

            if result.returncode == 0 or result.returncode == 1:
                fixed_code = result.stdout

                # Check for syntax errors in stderr (concise format)
                if result.stderr and ("invalid-syntax" in result.stderr or "Failed to parse" in result.stderr):
                    msg_status("Ruff: File has syntax errors - cannot apply fixes")
                elif fixed_code and fixed_code != code:
                    self._apply_changes_preserving_states(code, fixed_code)
                    msg_status("Ruff: Applied fixes (Ctrl+Z to undo)")
                else:
                    msg_status("Ruff: No fixes needed")
            else:
                msg_status(f"Ruff --fix error: {result.stderr or result.stdout}")

        except subprocess.TimeoutExpired:
            msg_box(f"Ruff --fix timed out (>{linter.timeout}s)", MB_OK | MB_ICONERROR)
        except Exception as e:
            msg_box(f"Ruff --fix failed:\n{e}", MB_OK | MB_ICONERROR)

    def format_file(self):
        """Run Ruff format on current buffer (non-destructive, supports undo)."""
        import subprocess

        linter = Ruff(ed)
        if not linter.ruff_path:
            msg_box("Ruff executable not found!", MB_OK | MB_ICONERROR)
            return

        code = ed.get_text_all()

        cmd = [linter.ruff_path, 'format', '-']

        cmd.extend(['--stdin-filename', ed.get_filename() or 'untitled.py'])

        try:
            result = subprocess.run(
                cmd,
                input=code,
                capture_output=True,
                text=True,
                timeout=linter.timeout
            )

            if result.returncode == 0:
                formatted_code = result.stdout

                if formatted_code and formatted_code != code:
                    # Apply changes preserving line states
                    self._apply_changes_preserving_states(code, formatted_code)
                    msg_status("Ruff: Formatted (Ctrl+Z to undo)")
                else:
                    msg_status("Ruff: Already formatted")
            else:
                # Check for syntax errors
                if result.stderr and ("invalid-syntax" in result.stderr or "Failed to parse" in result.stderr):
                    msg_status("Ruff: File has syntax errors - cannot format")
                else:
                    msg_status(f"Ruff format error: {result.stderr or result.stdout}")

        except subprocess.TimeoutExpired:
            msg_box(f"Ruff format timed out (>{linter.timeout}s)", MB_OK | MB_ICONERROR)
        except Exception as e:
            msg_box(f"Ruff format failed:\n{e}", MB_OK | MB_ICONERROR)

    def help(self):
        """Display plugin help."""
        linter = Ruff(ed)
        version_info = ""
        if linter.ruff_path:
            version = linter._get_ruff_version()
            if version:
                version_info = f"INSTALLED VERSION:\nRuff {version}\n\n"

        msg_box(
            "Ruff Linter for CudaText\n\n"
            "FEATURES:\n"
            "- Auto-detection (PATH or bundled)\n"
            "- Configurable rules (JSON)\n"
            "- Support for ignore/select patterns\n"
            "- Multi-platform support\n"
            "- Diagnostic logging\n"
            "- Severity differentiation (E/F=error, rest=warning)\n\n"
            "CONFIGURATION:\n"
            "Access via: Options > Settings-plugins > Ruff > Config\n"
            f"- timeout: Subprocess timeout in seconds (default: {Ruff.DEFAULT_TIMEOUT})\n"
            "- ignore: Rule codes to ignore\n"
            "- select: Rule codes to enable\n"
            "Supports // and # comments in JSON file\n\n"
            "PROJECT CONFIG (optional):\n"
            "Ruff automatically reads pyproject.toml or ruff.toml\n"
            "from your project directory\n"
            "Plugin select/ignore take precedence over project,\n"
            "other settings (line-length, etc.) come from project\n\n"
            "COMMON RULE CATEGORIES:\n"
            "- E/W: pycodestyle (style errors/warnings)\n"
            "- F: Pyflakes (logic errors)\n"
            "- B: flake8-bugbear (common bugs)\n"
            "- I: isort (import sorting)\n"
            "- C90: McCabe complexity\n"
            "- N: pep8-naming\n\n"
            "RULE SELECTION:\n"
            "- Specific codes: E501, F401\n"
            "- Category prefixes: E, W, F\n"
            "- All rules: ALL\n"
            "NOTE: ignore rules take precedence over select\n\n"
            "SEVERITY MAPPING:\n"
            "- Red (errors): E, F codes\n"
            "- Yellow (warnings): W, I, B, N, C90, etc.\n\n"
            "EXAMPLES:\n"
            '- Ignore: ["E501", "W191"]\n'
            '- Select: ["E", "W", "F", "B"]\n\n'
            "INSTALLATION:\n"
            "- Windows: Download ruff.exe from releases, place in tools/Ruff folder\n"
            "- Linux: curl -LsSf https://astral.sh/ruff/install.sh | sh\n"
            "- macOS: brew install ruff\n\n"
            f"{version_info}"
            "DOCUMENTATION:\n"
            "https://docs.astral.sh/ruff/",
            MB_OK
        )