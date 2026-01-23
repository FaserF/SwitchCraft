---
layout: home

hero:
  name: "SwitchCraft"
  text: "The Ultimate Packaging Assistant"
  tagline: "Analyze installers, create Intune packages, and streamline your IT workflow — all in one powerful tool."
  image:
    src: /screenshots/switchcraft_logo_with_Text.png
    alt: SwitchCraft Logo
  actions:
    - theme: brand
      text: Get Started
      link: /installation
    - theme: alt
      text: Download
      link: https://github.com/FaserF/SwitchCraft/releases/latest
    - theme: alt
      text: Try Web Demo
      link: https://faserf.github.io/SwitchCraft/demo/
    - theme: alt
      text: GPO / Registry
      link: /Registry

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
    link: /Registry
    linkText: Registry & GPO
  - icon: 💻
    title: Powerful CLI
    details: Automate packaging workflows in CI/CD pipelines with JSON output and scriptable commands.
    link: /CLI_Reference
    linkText: CLI Reference
---

<div class="vp-doc" style="padding: 2rem 1.5rem;">

## Preview

<div style="text-align: center; margin: 2rem 0;">
  <img src="/screenshots/switchcraft_ui.png" alt="SwitchCraft Modern UI" style="max-width: 100%; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);" />
</div>

### Screenshots

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin: 2rem 0;">
  <div style="text-align: center;">
    <img src="/screenshots/switchcraft_ui_2.png" alt="SwitchCraft Screenshot 2" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);" />
  </div>
  <div style="text-align: center;">
    <img src="/screenshots/switchcraft_ui_3.png" alt="SwitchCraft Screenshot 3" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);" />
  </div>
  <div style="text-align: center;">
    <img src="/screenshots/switchcraft_ui_4.png" alt="SwitchCraft Screenshot 4" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);" />
  </div>
  <div style="text-align: center;">
    <img src="/screenshots/switchcraft_ui_5.png" alt="SwitchCraft Screenshot 5" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);" />
  </div>
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
| Browsing Intune apps | Intune Store browser with logo display and metadata |
| Managing Intune groups | Entra Group Manager - create, delete, and manage group members |
| Testing detection rules | Live Detection Tester before upload |
| Creating Winget manifests | WingetCreate Manager with GitHub integration |
| Keeping apps updated | Winget integration with auto-update scripts |
| Managing settings across devices | Cloud Sync via GitHub Gists |
| Enterprise configuration | GPO/ADMX and Intune OMA-URI support |
| macOS packaging | macOS Wizard for DMG/PKG creation |

## Platform Support

SwitchCraft is designed for **Windows**. Core features require Windows-specific components.

| Feature | Windows | macOS/Linux |
|---------|:-------:|:-----------:|
| Modern UI | ✅ | ✅ |
| Intune Packaging | ✅ | ❌ |
| Winget Store | ✅ | ❌ |
| Installer Analysis | ✅ | ⚠️ Basic |

## Web Demo vs Desktop App

SwitchCraft can be used in the browser as a demo or installed on Windows for full functionality.

| Feature | Desktop App (Windows) | Web Demo (Browser) |
|:---|:---:|:---:|
| **Description** | Full featured application | Client-side WASM Demo |
| **System Access** | ✅ Full (Registry, Files, PS) | ❌ Sandboxed |
| **Intune Packaging** | ✅ Full generation & upload | ❌ Not available |
| **Winget Search** | ✅ Live API + PowerShell | ⚠️ Visual Only |
| **Installer Analysis** | ✅ Deep analysis | ⚠️ Basic file inspection |
| **Use Case** | Production / Daily Use | Preview / Training |

> [!NOTE]
> The **Web Demo** is purely client-side (Python in the browser). It is perfect for exploring the UI, but cannot perform system-level tasks like installing software or configuring Windows.

</div>
