# AI Context & Instructions for SwitchCraft

## 🧬 Project DNA
**Repository:** `SwitchCraft`
**Type:** General Software Project
**Description:** **SwitchCraft is your comprehensive packaging assistant for IT Professionals. It goes beyond simple switch identification to streamline your entire application packaging workflow.**

## 🛠 Tech Stack & Standards
- **Core Languages/Frameworks:** Node.js, Python, Docker
- **Toolchain:** Ruff/Flake8 (Linting)

## 📐 Coding Guidelines
- **Modularity:** Keep functions small, testable, and focused.
- **Quality Assurance:** Write clean, readable code following standard conventions for the respective language.
- **State Management:** Avoid global state. Use dependency injection where possible.
- **Error Handling:** Use granular try-catch/except blocks. Log contexts cleanly without exposing secrets.

## 🤖 Tool-Specific Optimization

### 🐙 GitHub Copilot
- **Inline Generation:** Align closely with the formatting of adjacent code blocks. Provide meaningful docstrings or JSDoc comments.

### 🧠 Claude Code
- **Architectural Changes:** Propose an execution plan first. Parse the repository structure to identify shared utilities before re-implementing logic.

### 🚀 Google Antigravity
- **Autonomous Operations:** Focus on zero-regression edits. Before creating new files, analyze the directory tree to determine if the logic belongs in an existing helper module.

## 🧪 Test Procedures
- **Running Tests:** Check for standard test runners or scripts.
- **Strategy:** Isolate unit tests from integration tests. Use appropriate mock objects.

## 🚫 Exclusion Rules
- **DO NOT TOUCH:**
  - Build artifacts, `dist/`, or `build/` directories.
  - Package lock files (`package-lock.json`, `poetry.lock`) unless specifically upgrading a dependency.
