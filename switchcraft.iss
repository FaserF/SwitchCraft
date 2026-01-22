; SwitchCraft Modern Installer Script for Inno Setup 6.x
; Supports both User and Admin installation modes
; Silent Install: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
; Silent Uninstall: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
; Debug Mode: /DEBUGMODE=1 (enables verbose logging)

#define MyAppName "SwitchCraft"
#ifndef MyAppVersion
  #define MyAppVersion "2026.1.5.dev0+9166056"
#endif
#ifndef MyAppVersionNumeric
  #define MyAppVersionNumeric "2026.1.5"
#endif
#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "2026.1.5.0"
#endif
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
AppPublisherURL=https://switchcraft.fabiseitz.de/
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}

; Default directory (changes based on admin/user mode)
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}\{#MyAppName}

; Allows user to choose install directory
AllowNoIcons=yes
DisableDirPage=no

; Privileges - force admin for machine-wide install
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline

; Output settings
OutputDir=dist
OutputBaseFilename=SwitchCraft-Setup
SetupIconFile=src\switchcraft\assets\switchcraft_logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Windows version requirements
MinVersion=10.0

; Ensure 64-bit install mode for correct Program Files mapping and Registry keys
ArchitecturesInstallIn64BitMode=x64

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
; Main executable (Modern One-File)
Source: "dist\SwitchCraft.exe"; DestDir: "{app}"; Flags: ignoreversion

; Logo/Icon
Source: "src\switchcraft\assets\switchcraft_logo.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

[Registry]
; Add to Add/Remove Programs with additional info
; Use HKA (HKEY_AUTO) to adapt to Admin (HKLM) or User (HKCU) install mode
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; Debug mode flag - set based on task selection or command line parameter
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: dword; ValueName: "DebugMode"; ValueData: "1"; Tasks: debugmode; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: dword; ValueName: "DebugMode"; ValueData: "0"; Tasks: not debugmode; Flags: uninsdeletevalue

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

// Write debug mode registry value and force silent uninstall string
procedure CurStepChanged(CurStep: TSetupStep);
var
  UninstallKey: String;
  UninstallString: String;
  RootKey: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // 1. Handle Debug Mode Registry
    if DebugModeParam then
    begin
      RegWriteDWordValue(HKEY_CURRENT_USER, 'Software\{#MyAppPublisher}\{#MyAppName}', 'DebugMode', 1);
    end;

    // 2. Force Silent Uninstall String
    // Determine the correct registry root based on install mode
    if IsAdminInstallMode then
      RootKey := HKEY_LOCAL_MACHINE
    else
      RootKey := HKEY_CURRENT_USER;

    // The key is AppId_is1. Note: Preprocessor handles {{ -> {
    UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{F4A53RF0-5W1T-CH3R-AFTF-ASE3RF453RF0}_is1';

    // Read existing UninstallString
    if RegQueryStringValue(RootKey, UninstallKey, 'UninstallString', UninstallString) then
    begin
      // Check if flags are already present (avoid duplication)
      if Pos('/VERYSILENT', UninstallString) = 0 then
      begin
        UninstallString := UninstallString + ' /VERYSILENT /SUPPRESSMSGBOXES /NORESTART';
        if RegWriteStringValue(RootKey, UninstallKey, 'UninstallString', UninstallString) then
        begin
          Log('Successfully updated UninstallString to be silent.');
        end
        else
        begin
          Log('Failed to update UninstallString.');
        end;
      end;
    end;
  end;
end;

[UninstallDelete]
; Clean up any leftover files
; Clean up any leftover files
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.json"
Type: files; Name: "{app}\*.db"
Type: files; Name: "{app}\*.tmp"
Type: files; Name: "{app}\SwitchCraft.exe"
Type: filesandordirs; Name: "{app}"
