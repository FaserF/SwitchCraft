; SwitchCraft Installer Script for Inno Setup 6.x
; Supports both User and Admin installation modes
; Silent Install: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
; Silent Uninstall: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
; Debug Mode: /DEBUGMODE=1 (enables verbose logging)

#define MyAppName "SwitchCraft"
#define MyAppVersion "2025.12.4"
#define MyAppPublisher "FaserF"
#define MyAppURL "https://github.com/FaserF/SwitchCraft"
#define MyAppExeName "SwitchCraft.exe"
#define MyAppDescription "Silent Install Switch Finder"

[Setup]
; Basic Info
AppId={{F4A53RF0-5W1T-CH3R-AFTF-ASE3RF453RF0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}

; Default directory (changes based on admin/user mode)
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}\{#MyAppName}

; Allows user to choose install directory
AllowNoIcons=yes
DisableDirPage=no

; Privileges - ask user or use admin if available
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; Output settings
OutputDir=dist
OutputBaseFilename=SwitchCraft-Setup
SetupIconFile=switchcraft_logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Windows version requirements
MinVersion=10.0

; Modern installer look
WizardStyle=modern
WizardSizePercent=110

; Uninstall info
Uninstallable=yes
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
english.DebugMode=Enable Debug Logging (verbose output for troubleshooting)
german.DebugMode=Debug-Protokollierung aktivieren (ausführliche Ausgabe für Fehlerbehebung)
english.DebugModeDesc=Advanced Options
german.DebugModeDesc=Erweiterte Optionen

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "debugmode"; Description: "{cm:DebugMode}"; GroupDescription: "{cm:DebugModeDesc}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\SwitchCraft.exe"; DestDir: "{app}"; Flags: ignoreversion

; Logo/Icon
Source: "switchcraft_logo.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

[Registry]
; Add to Add/Remove Programs with additional info
Root: SHCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: SHCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; Debug mode flag - set based on task selection or command line parameter
Root: SHCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: dword; ValueName: "DebugMode"; ValueData: "1"; Tasks: debugmode; Flags: uninsdeletevalue
Root: SHCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: dword; ValueName: "DebugMode"; ValueData: "0"; Tasks: not debugmode; Flags: uninsdeletevalue

[Run]
; Option to run after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DebugModeParam: Boolean;

// Check for /DEBUGMODE=1 command line parameter
function InitializeSetup(): Boolean;
var
  I: Integer;
  Param: String;
begin
  Result := True;
  DebugModeParam := False;

  for I := 1 to ParamCount do
  begin
    Param := ParamStr(I);
    if (Uppercase(Param) = '/DEBUGMODE=1') or (Uppercase(Param) = '/DEBUGMODE') then
    begin
      DebugModeParam := True;
      Break;
    end;
  end;
end;

// Dynamic default directory based on install mode
function GetDefaultDirName(Param: String): String;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{autopf}\{#MyAppPublisher}\{#MyAppName}')
  else
    Result := ExpandConstant('{localappdata}\{#MyAppPublisher}\{#MyAppName}');
end;

// Override default directory and set debug mode task
procedure InitializeWizard;
begin
  WizardForm.DirEdit.Text := GetDefaultDirName('');

  // If /DEBUGMODE was passed, pre-select the debug mode task
  if DebugModeParam then
  begin
    WizardForm.TasksList.Checked[2] := True; // debugmode is the 3rd task (index 2)
  end;
end;

// Write debug mode registry value based on command line param (for silent install)
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if DebugModeParam then
    begin
      RegWriteDWordValue(HKEY_CURRENT_USER, 'Software\{#MyAppPublisher}\{#MyAppName}', 'DebugMode', 1);
    end;
  end;
end;

[UninstallDelete]
; Clean up any leftover files
Type: filesandordirs; Name: "{app}"
