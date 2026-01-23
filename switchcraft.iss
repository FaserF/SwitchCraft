; SwitchCraft Modern Installer Script for Inno Setup 6.x
; Supports both User and Admin installation modes
; Silent Install: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
; Silent Uninstall: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
; Debug Mode: /DEBUGMODE=1 (enables verbose logging)

#define MyAppName "SwitchCraft"
#ifndef MyAppVersion
  #define MyAppVersion "2026.1.4"
#endif
#ifndef MyAppVersionNumeric
  #define MyAppVersionNumeric "2026.1.4"
#endif
#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "2026.1.4.0"
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
UsePreviousPrivileges=no

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
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"; AppUserModelID: "FaserF.SwitchCraft.Modern.Release"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"; AppUserModelID: "FaserF.SwitchCraft.Modern.Release"

[Registry]
; Add to Add/Remove Programs with additional info
; Use HKA (HKEY_AUTO) to adapt to Admin (HKLM) or User (HKCU) install mode
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; Debug mode flag - set based on task selection or command line parameter
; We use HKA to ensure it goes to HKLM for Admin installs (visible to all users) vs HKCU for User installs
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: dword; ValueName: "DebugMode"; ValueData: "1"; Tasks: debugmode; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: dword; ValueName: "DebugMode"; ValueData: "0"; Tasks: not debugmode; Flags: uninsdeletevalue

[Run]
; Option to run after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DebugModeParam: Boolean;
  FullCleanupParam: Boolean;

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
    // Determine the correct registry root based on install mode
    if IsAdminInstallMode then
      RootKey := HKEY_LOCAL_MACHINE
    else
      RootKey := HKEY_CURRENT_USER;

    // 1. Handle Debug Mode Registry (Explicitly using correct RootKey)
    // Note: The [Registry] section now handles this via HKA, but if we need to enforce it from parameter:
    if DebugModeParam then
    begin
       // We write to the same location HKA would pick
       RegWriteDWordValue(RootKey, 'Software\{#MyAppPublisher}\{#MyAppName}', 'DebugMode', 1);
    end;

    // 2. Force Silent Uninstall String
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
    end
    else
    begin
       // Try 64-bit wrapper check - Inno Setup x64 mode should handle this partially,
       // but sometimes keys end up in WOW6432Node if ArchitecturesInstallIn64BitMode isn't fully respected or mixed.
       // However, since we defined ArchitecturesInstallIn64BitMode=x64, RootKey should be correct for native 64-bit key.
       Log('Could not find UninstallString key to update. Checked Root: ' + IntToStr(RootKey) + ' Key: ' + UninstallKey);
    end;
  end;
end;

// Kill app before uninstall
function InitializeUninstall(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  // Silently kill the process if it's running
  Exec('taskkill.exe', '/F /IM {#MyAppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);

  // Check for /FULLCLEANUP parameter
  FullCleanupParam := False;
  if Pos('/FULLCLEANUP', Uppercase(GetCmdTail)) > 0 then
  begin
    FullCleanupParam := True;
  end;
end;

// Ensure folder is gone after uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Standard cleanup: Attempt to remove the app directory recursively if it still exists
    if DirExists(ExpandConstant('{app}')) then
    begin
      DelTree(ExpandConstant('{app}'), True, True, True);
    end;

    // Factory Reset Cleanup
    if FullCleanupParam then
    begin
      // 1. Registry (HKCU)
      if RegKeyExists(HKEY_CURRENT_USER, 'Software\FaserF\SwitchCraft') then
      begin
         RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\FaserF\SwitchCraft');
      end;

      // 2. Addons Folder (.switchcraft)
      if DirExists(ExpandConstant('{userprofile}\.switchcraft')) then
      begin
        DelTree(ExpandConstant('{userprofile}\.switchcraft'), True, True, True);
      end;

      // 3. Roaming AppData (Logs, History, Cache)
      if DirExists(ExpandConstant('{userappdata}\FaserF\SwitchCraft')) then
      begin
        DelTree(ExpandConstant('{userappdata}\FaserF\SwitchCraft'), True, True, True);
      end;

      // 4. Local AppData (WebView2 Cache if any, or other local data)
      if DirExists(ExpandConstant('{localappdata}\FaserF\SwitchCraft')) then
      begin
        DelTree(ExpandConstant('{localappdata}\FaserF\SwitchCraft'), True, True, True);
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
