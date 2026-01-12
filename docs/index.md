---
layout: home

hero:
  name: "SwitchCraft"
  text: "The Ultimate Packaging Assistant"
  tagline: "Analyze installers, create Intune packages, and streamline your IT workflow — all in one powerful tool."
  image:
    src: https://github.com/FaserF/SwitchCraft/raw/main/images/switchcraft_logo_with_Text.png
    alt: SwitchCraft Logo
  actions:
    - theme: brand
      text: Get Started
      link: /installation
    - theme: alt
      text: Download
      link: https://github.com/FaserF/SwitchCraft/releases/latest
    - theme: alt
      text: View on GitHub
      link: https://github.com/FaserF/SwitchCraft

features:
  - icon: 🔍
    title: Smart Installer Analysis
    details: Detect 20+ installer frameworks (MSI, NSIS, Inno Setup, InstallShield, and more) with automatic silent switch discovery.
    link: /FEATURES
    linkText: Learn more
  - icon: 📦
    title: One-Click Intune Packaging
    details: Generate .intunewin packages, detection scripts, and upload directly to Microsoft Intune via Graph API.
    link: /INTUNE
    linkText: Intune Guide
  - icon: 🛒
    title: Winget Store Integration
    details: Search the Microsoft Winget catalog, analyze apps, and deploy to Intune with intelligent automation.
    link: /WINGET
    linkText: Winget Guide
  - icon: 🤖
    title: AI-Powered Assistance
    details: Get packaging guidance from integrated AI (Local/Ollama, OpenAI, or Google Gemini) for complex installers.
    link: /ADDONS
    linkText: Addon System
  - icon: ⚙️
    title: Enterprise Ready
    details: Full GPO (ADMX) and Intune OMA-URI support. Centrally manage settings across your organization.
    link: /PolicyDefinitions/README
    linkText: GPO Reference
  - icon: 💻
    title: Powerful CLI
    details: Automate packaging workflows in CI/CD pipelines with JSON output and scriptable commands.
    link: /CLI_Reference
    linkText: CLI Reference
---

<div class="vp-doc" style="padding: 2rem 1.5rem;">

## Preview

<div style="text-align: center; margin: 2rem 0;">
  <img src="https://github.com/FaserF/SwitchCraft/raw/main/images/switchcraft_ui.png" alt="SwitchCraft Modern UI" style="max-width: 100%; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);" />
</div>

## Quick Start

### Install via Winget (Recommended)

```powershell
winget install FaserF.SwitchCraft
```

### Or Download Manually

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">

<a href="https://github.com/FaserF/SwitchCraft/releases/latest" style="display: block; padding: 1rem; border-radius: 12px; background: var(--vp-c-bg-soft); text-decoration: none; text-align: center; transition: transform 0.2s;">
  <strong>Modern Edition</strong><br/>
  <small style="color: var(--vp-c-text-2);">Latest features, Flet UI</small>
</a>

<a href="https://github.com/FaserF/SwitchCraft/releases/latest" style="display: block; padding: 1rem; border-radius: 12px; background: var(--vp-c-bg-soft); text-decoration: none; text-align: center; transition: transform 0.2s;">
  <strong>Legacy Edition</strong><br/>
  <small style="color: var(--vp-c-text-2);">Lightweight, Tkinter</small>
</a>

<a href="https://github.com/FaserF/SwitchCraft/releases/latest" style="display: block; padding: 1rem; border-radius: 12px; background: var(--vp-c-bg-soft); text-decoration: none; text-align: center; transition: transform 0.2s;">
  <strong>CLI</strong><br/>
  <small style="color: var(--vp-c-text-2);">Automation & Scripts</small>
</a>

</div>

## Why SwitchCraft?

| Challenge | SwitchCraft Solution |
|-----------|---------------------|
| Finding silent install switches | Automatic detection for 20+ frameworks |
| Creating Intune packages | One-click .intunewin creation + upload |
| Keeping apps updated | Winget integration with auto-update scripts |
| Managing settings across devices | Cloud Sync via GitHub Gists |
| Enterprise configuration | GPO/ADMX and Intune OMA-URI support |

## Platform Support

SwitchCraft is designed for **Windows**. Core features require Windows-specific components.

| Feature | Windows | macOS/Linux |
|---------|:-------:|:-----------:|
| Modern UI | ✅ | ✅ |
| Intune Packaging | ✅ | ❌ |
| Winget Store | ✅ | ❌ |
| Installer Analysis | ✅ | ⚠️ Basic |

</div>
