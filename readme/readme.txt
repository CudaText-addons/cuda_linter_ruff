Linter for CudaLint plugin.
It adds support for Python lexer.
It uses "Ruff".

'Ruff' must be in your system PATH or in the tools/Ruff folder (portable use) inside CudaText directory.

Ruff is an extremely fast Python linter and code formatter:
https://github.com/astral-sh/ruff

For example, to install it on Windows, download ruff.exe from GitHub releases and place it in tools/Ruff folder inside CudaText directory.
On Linux: curl -LsSf https://astral.sh/ruff/install.sh | sh
On macOS: brew install ruff

Access configuration via menu: Options > Settings-plugins > Ruff > Config
Access fix command via menu: Plugins > Ruff > Fix current file
Access fix command with unsafe flag via menu: Plugins > Ruff > Fix current file (unsafe)
Access format command via menu: Plugins > Ruff > Format current file
Access help via menu: Options > Settings-plugins > Ruff > Help

To customize rules, create settings/ruff_config.json with:
{
  "timeout": 30,
  "ignore": [
    "E501",
    "W191"
  ],
  "select": [
    "E",
    "W",
    "F",
    "B",
    "I"
  ]
}

Ruff automatically reads pyproject.toml or ruff.toml from your project directory.
Plugin select/ignore settings take precedence over project configuration.

Author: Bruno Eduardo

License: MIT
