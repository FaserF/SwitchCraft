# Stack Manager

**Stacks** (or Application Dependencies) allow you to chain applications together. This is useful when App A requires App B and C to be installed first.

## Concept
A "Stack" is a meta-definition. For example, a "Developer Stack" might contain:
1.  Visual Studio Code
2.  Git
3.  Node.js
4.  Python

## Features
*   **Visual Editor**: Drag and drop apps from your Library into the stack list.
*   **Ordering**: Reorder apps to define dependency usage (Top installs first).
*   **Intune Output**:
    *   *Dependency Chain*: Configures Intune Dependencies (App B depends on App A).
    *   *Super-Package*: (Optional) Creates a single PowerShell wrapper script that installs all apps in sequence (useful if you don't want to manage multiple Intune IDs).

## Usage
1.  Create a Stack named "Base Utils".
2.  Add "7-Zip" and "Notepad++".
3.  Deploy "Base Utils" to "All Users". SwitchCraft handles the backend assignment logic.
