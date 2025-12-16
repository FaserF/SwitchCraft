; SwitchCraft Inno Setup Script

#define MyAppName "SwitchCraft"
#define MyAppVersion "2025.12.1"
#define MyAppPublisher "FaserF"
#define MyAppURL "https://github.com/FaserF/SwitchCraft"
#define MyAppExeName "SwitchCraft.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{C6E72169-E342-4363-9D67-37A4928A613F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DisableProgramGroupPage=yes
; UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayIcon={app}\SwitchCraft.exe
LicenseFile=LICENSE
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=admin
OutputDir=build_installer
OutputBaseFilename=SwitchCraft_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Ensure you run 'pyinstaller switchcraft.spec' first so 'dist/SwitchCraft.exe' exists!
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Include other assets if they are not bundled by PyInstaller (e.g., config, if external)
; Source: "src\switchcraft\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
