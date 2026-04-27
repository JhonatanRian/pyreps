# Contributing to pyreps

First off, thank you for considering contributing to `pyreps`! It's people like you that make `pyreps` such a great tool for the community.

## Development Environment Setup

This project uses [uv](https://github.com/astral-sh/uv) as the package and project manager.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/JhonatanRian/pyreps.git
   cd pyreps
   ```

2. **Install dependencies**:
   ```bash
   uv sync --all-extras --dev
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate  # On Linux/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

## Development Workflow

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bug-name
   ```

2. **Make your changes**. Ensure you follow the project's coding style:
   - Use strict typing for all functions and classes.
   - Use `slots=True` for dataclasses.
   - Prefer streaming (generators) for performance.

3. **Run tests**:
   ```bash
   uv run pytest
   ```

4. **Lint and Format**:
   We use `ruff` for linting and formatting.
   ```bash
   uvx ruff format .
   uvx ruff check . --fix
   ```

5. **Type Checking**:
   ```bash
   uvx pyright src
   ```

## Pull Request Process

1. Ensure all tests pass.
2. Update the `README.md` or documentation if you're adding new features.
3. Submit a Pull Request targeting the `main` branch.
4. Provide a clear description of the changes and link any related issues.

## Commit Message Style

We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` for new features.
- `fix:` for bug fixes.
- `docs:` for documentation changes.
- `refactor:` for code changes that neither fix a bug nor add a feature.
- `perf:` for performance improvements.
- `test:` for adding missing tests.
- `chore:` for updating build tasks, package manager configs, etc.

---

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
