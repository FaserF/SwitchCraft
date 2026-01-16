import{_ as t,c as a,o as e,ag as s}from"./chunks/framework.Cwro3A8J.js";const f=JSON.parse('{"title":"Intune OMA-URI Configuration for SwitchCraft","description":"","frontmatter":{},"headers":[],"relativePath":"IntuneConfig.md","filePath":"IntuneConfig.md","lastUpdated":1768548093000}'),l={name:"IntuneConfig.md"};function p(o,n,i,d,r,c){return e(),a("div",null,[...n[0]||(n[0]=[s(`<h1 id="intune-oma-uri-configuration-for-switchcraft" tabindex="-1">Intune OMA-URI Configuration for SwitchCraft <a class="header-anchor" href="#intune-oma-uri-configuration-for-switchcraft" aria-label="Permalink to &quot;Intune OMA-URI Configuration for SwitchCraft&quot;">​</a></h1><p>Use the following settings to configure SwitchCraft via Microsoft Intune Custom Profiles.</p><h2 id="step-1-admx-ingestion-required" tabindex="-1">Step 1: ADMX Ingestion (Required) <a class="header-anchor" href="#step-1-admx-ingestion-required" aria-label="Permalink to &quot;Step 1: ADMX Ingestion (Required)&quot;">​</a></h2><p>You <strong>must</strong> first ingest the ADMX file so Intune understands the policy structure.</p><ul><li><strong>OMA-URI</strong>: <code>./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy</code></li><li><strong>Data Type</strong>: <code>String</code></li><li><strong>Value</strong>: <a href="https://github.com/FaserF/SwitchCraft/blob/main/docs/PolicyDefinitions/SwitchCraft.admx" target="_blank" rel="noreferrer">Copy content from SwitchCraft.admx</a></li></ul><h2 id="step-2-configure-settings" tabindex="-1">Step 2: Configure Settings <a class="header-anchor" href="#step-2-configure-settings" aria-label="Permalink to &quot;Step 2: Configure Settings&quot;">​</a></h2><p><strong>OMA-URI Prefix</strong>: <code>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced</code></p><table tabindex="0"><thead><tr><th style="text-align:left;">Setting</th><th style="text-align:left;">OMA-URI Suffix</th><th style="text-align:left;">Data Type</th><th style="text-align:left;">Value / Description</th></tr></thead><tbody><tr><td style="text-align:left;"><strong>Debug Mode</strong></td><td style="text-align:left;"><code>.../DebugMode_Enf</code></td><td style="text-align:left;">Integer</td><td style="text-align:left;"><code>0</code> (Disabled), <code>1</code> (Enabled)</td></tr><tr><td style="text-align:left;"><strong>Update Channel</strong></td><td style="text-align:left;"><code>...~Updates_Enf/UpdateChannel_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;UpdateChannelDropdown&quot; value=&quot;stable&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Enable Winget</strong></td><td style="text-align:left;"><code>...~General_Enf/EnableWinget_Enf</code></td><td style="text-align:left;">Integer</td><td style="text-align:left;"><code>0</code> (Disabled), <code>1</code> (Enabled)</td></tr><tr><td style="text-align:left;"><strong>Language</strong></td><td style="text-align:left;"><code>...~General_Enf/Language_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;LanguageDropdown&quot; value=&quot;en&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Git Repo Path</strong></td><td style="text-align:left;"><code>...~General_Enf/GitRepoPath_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;GitRepoPathBox&quot; value=&quot;C:\\Path&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Company Name</strong></td><td style="text-align:left;"><code>...~General_Enf/CompanyName_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;CompanyNameBox&quot; value=&quot;My Company&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>AI Provider</strong></td><td style="text-align:left;"><code>...~AI_Enf/AIProvider_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;AIProviderDropdown&quot; value=&quot;local&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>AI API Key</strong></td><td style="text-align:left;"><code>...~AI_Enf/AIKey_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;AIKeyBox&quot; value=&quot;...&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Sign Scripts</strong></td><td style="text-align:left;"><code>...~Security_Enf/SignScripts_Enf</code></td><td style="text-align:left;">Integer</td><td style="text-align:left;"><code>0</code> (Disabled), <code>1</code> (Enabled)</td></tr><tr><td style="text-align:left;"><strong>Cert Thumbprint</strong></td><td style="text-align:left;"><code>...~Security_Enf/CodeSigningCertThumbprint_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;CodeSigningCertThumbprintBox&quot; value=&quot;...&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Graph Tenant ID</strong></td><td style="text-align:left;"><code>...~Intune_Enf/GraphTenantId_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;GraphTenantIdBox&quot; value=&quot;...&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Graph Client ID</strong></td><td style="text-align:left;"><code>...~Intune_Enf/GraphClientId_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;GraphClientIdBox&quot; value=&quot;...&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Graph Client Secret</strong></td><td style="text-align:left;"><code>...~Intune_Enf/GraphClientSecret_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;GraphClientSecretBox&quot; value=&quot;...&quot;/&gt;</code></td></tr><tr><td style="text-align:left;"><strong>Intune Test Groups</strong></td><td style="text-align:left;"><code>...~Intune_Enf/IntuneTestGroups_Enf</code></td><td style="text-align:left;">String</td><td style="text-align:left;"><code>&lt;enabled/&gt;</code><br><code>&lt;data id=&quot;IntuneTestGroupsBox&quot; value=&quot;...&quot;/&gt;</code></td></tr></tbody></table><div class="important custom-block github-alert"><p class="custom-block-title">IMPORTANT</p><p><strong>String Policies</strong> in ADMX are complex XML strings, not simple text values. See the example block below for the correct format.</p></div><hr><h2 id="copy-paste-configuration-block" tabindex="-1">Copy &amp; Paste Configuration Block <a class="header-anchor" href="#copy-paste-configuration-block" aria-label="Permalink to &quot;Copy &amp; Paste Configuration Block&quot;">​</a></h2><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>ADMX Ingestion</span></span>
<span class="line"><span>./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;Copy contents of SwitchCraft.admx here&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Debug Mode</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced/DebugMode_Enf</span></span>
<span class="line"><span>Integer</span></span>
<span class="line"><span>1</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Update Channel</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Updates_Enf/UpdateChannel_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;UpdateChannelDropdown&quot; value=&quot;stable&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Enable Winget</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/EnableWinget_Enf</span></span>
<span class="line"><span>Integer</span></span>
<span class="line"><span>1</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Language</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/Language_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;LanguageDropdown&quot; value=&quot;en&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Git Repository Path</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/GitRepoPath_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;GitRepoPathBox&quot; value=&quot;C:\\ProgramData\\SwitchCraft\\ConfigRepo&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Company Name</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/CompanyName_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;CompanyNameBox&quot; value=&quot;My Company&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Custom Template Path</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/CustomTemplatePath_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;CustomTemplatePathBox&quot; value=&quot;C:\\ProgramData\\SwitchCraft\\Templates&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Winget Repo Path</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/WingetRepoPath_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;WingetRepoPathBox&quot; value=&quot;C:\\ProgramData\\SwitchCraft\\Winget&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Theme</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/Theme_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;ThemeDropdown&quot; value=&quot;System&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>AI Provider</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~AI_Enf/AIProvider_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;AIProviderDropdown&quot; value=&quot;local&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>AI API Key</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~AI_Enf/AIKey_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;AIKeyBox&quot; value=&quot;YOUR_API_KEY&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Sign Scripts</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Security_Enf/SignScripts_Enf</span></span>
<span class="line"><span>Integer</span></span>
<span class="line"><span>1</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Code Signing Cert Thumbprint</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Security_Enf/CodeSigningCertThumbprint_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;CodeSigningCertThumbprintBox&quot; value=&quot;THUMBPRINT&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Graph Tenant ID</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/GraphTenantId_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;GraphTenantIdBox&quot; value=&quot;00000000-0000-0000-0000-000000000000&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Graph Client ID</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/GraphClientId_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;GraphClientIdBox&quot; value=&quot;00000000-0000-0000-0000-000000000000&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Graph Client Secret</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/GraphClientSecret_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;GraphClientSecretBox&quot; value=&quot;YOUR_SECRET&quot;/&gt;</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Intune Test Groups</span></span>
<span class="line"><span>./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/IntuneTestGroups_Enf</span></span>
<span class="line"><span>String</span></span>
<span class="line"><span>&lt;enabled/&gt;</span></span>
<span class="line"><span>&lt;data id=&quot;IntuneTestGroupsBox&quot; value=&quot;GROUP_ID_1,GROUP_ID_2&quot;/&gt;</span></span></code></pre></div>`,12)])])}const u=t(l,[["render",p]]);export{f as __pageData,u as default};
