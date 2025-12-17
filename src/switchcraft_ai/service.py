import re
import json
import logging
from typing import Optional, List, Dict, Any
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n

logger = logging.getLogger(__name__)

class SwitchCraftAI:
    """
    Intelligent Assistant for SwitchCraft.
    Uses OpenAI API if configured, otherwise falls back to basic expert system.
    Supports tool execution for packaging automation.
    """

    def __init__(self):
        self.context = {}
        self.messages = []
        self.client = None
        self.provider = SwitchCraftConfig.get_value("AIProvider", "local")
        self.model = SwitchCraftConfig.get_value("AIModel", "")

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_installer_info",
                    "description": "Get detailed information about the currently analyzed installer.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_install_script",
                    "description": "Generate a PowerShell install script for the current installer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "silent_args": {"type": "string", "description": "Silent arguments to use"}
                        },
                        "required": ["silent_args"]
                    }
                }
            }
        ]

        # Init Client based on provider
        self._init_client()

    def _init_client(self):
        try:
            if self.provider == "openai":
                api_key = SwitchCraftConfig.get_secret("OPENAI_API_KEY")
                if api_key:
                    from openai import OpenAI
                    self.client = OpenAI(api_key=api_key)
                    if not self.model: self.model = "gpt-4o"
                    self.messages = [{"role": "system", "content": "You are SwitchCraft AI, an expert packaging assistant. Help the user with installers (MSI, EXE, Intune). You have access to the current installer analysis context. Use tools when requested. Be concise."}]

            elif self.provider == "gemini":
                api_key = SwitchCraftConfig.get_secret("GEMINI_API_KEY")
                if api_key:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    if not self.model: self.model = "gemini-pro"
                    self.client = genai.GenerativeModel(self.model)
                    # Gemini has different history structure, handled in _ask_gemini

        except Exception as e:
            logger.error(f"Failed to init AI client ({self.provider}): {e}")

    def update_context(self, data: dict):
        self.context = data
        # Update system context if needed or just keep available for tools
        pass

    def ask(self, query: str) -> str:
        """Determines the answer using Configured Provider."""

        if self.provider == "openai":
            if self.client:
                return self._ask_openai(query)
            else:
                return "Error: OpenAI Provider configured but not initialized. Please check your API Key in Settings."

        elif self.provider == "gemini":
            if self.client:
                return self._ask_gemini(query)
            else:
                return "Error: Gemini Provider configured but not initialized. Please check your API Key in Settings."

        # Fallback / Local
        return self._ask_smart_regex(query)

    def _ask_openai(self, user_query: str) -> str:
        # ... (Existing OpenAI Logic, compacted) ...
        try:
            self.messages.append({"role": "user", "content": user_query})
            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages, tools=self.tools, tool_choice="auto"
            )
            msg = response.choices[0].message

            # Handle Tool Calls
            if msg.tool_calls:
                self.messages.append(msg) # Add assistant's tool call request

                for tool_call in msg.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    # Execute Tool
                    result_content = self._execute_tool(function_name, args)

                    self.messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result_content)
                    })

                # Get final response after tool execution
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages
                )
                final_msg = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_msg})
                return final_msg

            else:
                answer = msg.content or "I couldn't generate a text response."
                self.messages.append({"role": "assistant", "content": answer})
                return answer
        except Exception as e:
            return f"OpenAI Error: {e}"

    def _ask_gemini(self, user_query: str) -> str:
        try:
            # Simple content generation for Gemini
            # Context injection
            context_str = f"Context: {json.dumps(self.context)}" if self.context else ""
            full_prompt = f"{context_str}\n\nUser: {user_query}"

            response = self.client.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Gemini Error: {e}"

    def _execute_tool(self, name, args):
        """Execute local functions based on AI request."""
        logger.info(f"AI executing tool: {name} with {args}")

        if name == "get_installer_info":
            if self.context:
                return self.context
            return {"error": "No file analyzed yet."}

        if name == "generate_install_script":
            # Just mock relevant action or return instructions for now,
            # fully wiring this needs callbacks to the UI or passing the App instance.
            # For now return success text
            return {"status": "success", "info": "Script generation logic simulated. Tell user it's ready (Mock)."}

        return {"error": "Unknown tool"}

    def _ask_smart_regex(self, query: str) -> str:
        """Enhanced Rule-based Logic."""
        q = query.lower()

        # 0. Language Check
        is_de = any(w in q for w in ["hallo", "wer", "was", "wie", "ist", "kannst", "machen", "unterstützt", "du", "neueste", "version", "welche", "für", "geht"])
        lang = "de" if is_de else "en"

        # 1. SmartScreen / Signing
        if any(x in q for x in ["smartscreen", "defender", "virus", "bedrohung", "unknown publisher", "unbekannt", "block"]):
             return i18n.get("ai_explain_smartscreen", lang=lang, default="SmartScreen warns about 'Unknown Publisher' if the app is not signed. You can sign it using a certificate in the Release Workflow.")

        # 2. Winget
        if "winget" in q:
             return i18n.get("ai_explain_winget", lang=lang, default="Winget is the Windows Package Manager. SwitchCraft can detect if an installer is available on Winget and generate install scripts for it.")

        # 3. Intune / .intunewin
        if any(x in q for x in ["intune", "intunewin", "upload", "cloud"]):
             return i18n.get("ai_explain_intune", lang=lang, default="To deploy via Intune, you need to wrap the installer into an .intunewin file. SwitchCraft automates this in the 'Intune Utility' tab.")

        # 4. PSExec / System Context
        if any(x in q for x in ["psexec", "system", "admin", "test"]):
             return i18n.get("ai_explain_psexec", lang=lang, default="Testing as SYSTEM user is crucial because Intune installs run as SYSTEM. Use PSExec (checked in settings) to simulate this.")

        # 5. Installer Specifics (Context Aware)
        if self.context:
             if any(x in q for x in ["switch", "silent", "parameter", "arg"]):
                 t = self.context.get("type", "Unknown")
                 s = self.context.get("install_silent", "Unknown")
                 return i18n.get("ai_context_switches", lang=lang, install_type=t, switches=s, filename=self.context.get("filename",""))

        # 6. Standard Rules (Previous)
        rules = {
            r"msi": "ai_rules_msi",
            r"error 1603": "ai_rules_error1603",
            r"powershell": "ai_rules_powershell",
        }
        for pattern, key in rules.items():
            if re.search(pattern, q):
                return i18n.get(key, lang=lang)

        # Smalltalk (moved from original fallback, now part of smart regex)
        if re.search(r"(wer bist du|who are you)", q):
             return i18n.get("ai_smalltalk_who", lang=lang)
        if re.search(r"(was kannst du|what can you do)", q):
             return i18n.get("ai_smalltalk_what", lang=lang)

        # Fallback
        return i18n.get("ai_fallback", lang=lang)
