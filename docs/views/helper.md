# AI Helper

The **AI Helper** is your intelligent assistant for packaging tasks, powered by OpenAI (GPT-4o) or similar models configured in settings. It understands context from your currently analyzed installers and can generate code, explain errors, or suggest detection logic.

## Key Features

### 1. Context-Aware Chat
*   **Active Context**: The AI automatically receives metadata from the **Analyzer** (e.g., "Analyzing Firefox 120.0, detected Inno Setup").
*   **Prompting**: Ask natural language questions like:
    *   *"Write a PowerShell script to install this and delete the desktop shortcut."*
    *   *"How do I detect this application using the Registry?"*
    *   *"Explain this error code: 1603"*

### 2. Specialized Modes
*   **General Chat**: Standard Q&A.
*   **Script Gen**: Optimized for generating `Install-App.ps1` or Remediation scripts.
*   **Detection**: Focuses on creating robust Intune detection rules (File/Registry/Script).

### 3. Code Actions
When the AI generates code blocks (PowerShell, XML, JSON):
*   **Copy**: One-click copy to clipboard.
*   **Save As**: Save directly to a `.ps1` file.
*   **Test**: (Assuming future integration) Send directly to the Detection Tester.

## Requirements
*   **API Key**: You must configure a valid API Key in **Settings > General**.
*   **Internet Access**: Required to reach the AI provider API.

## Tips
*   **Be Specific**: "Write an install script" is good, but "Write an install script that handles potential reboot pending states and logs to C:\Logs" is better.
*   **Use the Analyzer First**: Analyze an installer *before* asking questions about it so the AI has the file metadata.
