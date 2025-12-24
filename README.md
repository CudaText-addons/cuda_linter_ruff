CudaText plugin for 'Ruff' tool integration.

## 🎯 What is Ruff?

Ruff is an **extremely fast Python linter and code formatter** written in Rust, and it's quickly becoming the new standard in Python development. It's **10-100x faster** than traditional tools and replaces multiple tools in one:
- ✅ flake8 (linting)
- ✅ black (formatting)
- ✅ isort (import sorting)
- ✅ pyupgrade (code modernization)
- ✅ And 50+ other tools!

Major projects like **FastAPI, Pydantic, pandas, and numpy** have already migrated to Ruff.

## ✨ Plugin Features

### Core Functionality
- 🔌 **Full CudaLint integration** - Works seamlessly with the existing framework
- 🔍 **Smart executable detection** - Finds Ruff in PATH or uses bundled version (portable mode)
- 📁 **Project config support** - Automatically reads `pyproject.toml` and `ruff.toml`
- ⚙️ **JSON configuration** - Easy to configure with validation and helpful error messages
- 🌍 **Cross-platform** - Windows, Linux, macOS fully supported

### Advanced Commands
- 🔧 **Fix command** - Applies auto-fixes directly in buffer with full undo support (Ctrl+Z)
- 🎨 **Format command** - Formats code in buffer with full undo support (Ctrl+Z)
- 📊 **Smart severity mapping** - E/F codes show as errors (red), others as warnings (yellow)
- 🏷️ **Error codes in messages** - Shows `[F401]` for easy identification
- 📝 **Comprehensive help** - Built-in documentation with examples

### User Experience
- ⚡ **Non-destructive operations** - Fix and format work on buffer, not disk
- ↩️ **Full undo support** - All changes can be undone with Ctrl+Z
- 🎯 **KISS principle** - Simple, clean code with minimal complexity
- 🔊 **Diagnostic logging** - Helpful console output for debugging
- 📦 **Portable-ready** - Works great with CudaText portable installations

## 📚 Additional Info

- **Ruff project**: https://github.com/astral-sh/ruff
- **Ruff documentation**: https://docs.astral.sh/ruff/
- **Plugin license**: MIT
