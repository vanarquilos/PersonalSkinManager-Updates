; Personal Skin Manager Installer Script for Inno Setup
; This creates a proper Windows installer that registers the app

#define MyAppName "Personal Skin Manager"
#define MyAppVersion "1.0.1"
#define MyAppVersionInfo "1.0.1.0"
#define MyAppPublisher "Van Arquilos"
#define MyAppExeName "PersonalSkinManager.exe"
#define MyAppDescription "Personal skin manager for League of Legends"
; Must match config.SINGLE_INSTANCE_MUTEX_NAME (used by the app to enforce single-instance)
#define MyAppMutex "Local\PersonalSkinManagerSingleInstance"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{6832ED9B-6ACC-4455-A12F-476A963952E0}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; No public PSM publisher URL (private personal build)
; No public PSM support URL (private personal build)
; PSM controlled update channel is configured separately
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=PersonalSkinManager_Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
; Prevent install/uninstall while Personal Skin Manager is running (mutex is created by the running app)
AppMutex={#MyAppMutex}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files
; hashes.game.txt is user-managed and must be preserved across installations.
Source: "dist\PersonalSkinManager\*"; DestDir: "{app}"; Excludes: "hashes.game.txt,cslol-dll.dll"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}} (as Administrator)"; Flags: nowait postinstall skipifsilent shellexec; Verb: runas

[UninstallRun]
; Uninstall Pengu Loader (removes its IFEO activation and disables the native hook)
Filename: "{localappdata}\Rose\Pengu Loader\Pengu Loader.exe"; Parameters: "--uninstall --silent"; Flags: runhidden waituntilterminated skipifdoesntexist
; Always remove the Rose auto-start scheduled task (created via schtasks /TN "Rose")
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN PersonalSkinManager /F"; Flags: runhidden
; Legacy cleanup from the upstream Rose baseline
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN Rose /F"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\injection\overlay"
Type: filesandordirs; Name: "{app}\injection\mods"
; Preserve compatibility/user data under %LOCALAPPDATA%\Rose.
; This contains cached skins/Fantome files and must not be removed by PSM uninstall.
; Note: State files are now stored in user data directory, not in app directory

[Code]
function _IsLeagueRunning(): Boolean;
var
  WbemLocator, WMIService, Processes: Variant;
begin
  Result := False;
  try
    WbemLocator := CreateOleObject('WbemScripting.SWbemLocator');
    WMIService := WbemLocator.ConnectServer('localhost', 'root\CIMV2');
    Processes := WMIService.ExecQuery(
      'SELECT Name FROM Win32_Process WHERE ' +
      'Name="LeagueClient.exe" OR ' +
      'Name="LeagueClientUx.exe" OR ' +
      'Name="LeagueClientUxRender.exe" OR ' +
      'Name="League of Legends.exe"'
    );
    Result := (Processes.Count > 0);
  except
    { If WMI fails, don't block the uninstall }
    Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
var
  PSMRunning: Boolean;
  LeagueRunning: Boolean;
begin
  PSMRunning := CheckForMutexes('{#MyAppMutex}');
  LeagueRunning := _IsLeagueRunning();

  if PSMRunning and LeagueRunning then
  begin
    MsgBox(
      '{#MyAppName} and League of Legends are both currently running.'#13#10 +
      'Please close both applications and try uninstalling again.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  if PSMRunning then
  begin
    MsgBox(
      '{#MyAppName} is currently running.'#13#10 +
      'Please close it completely (including the tray) and try uninstalling again.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  if LeagueRunning then
  begin
    MsgBox(
      'League of Legends is currently running.'#13#10 +
      'Please close League of Legends and try uninstalling again.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  Result := True;
end;

function _ContainsTextLower(const Haystack: string; const NeedleLower: string): Boolean;
begin
  Result := Pos(NeedleLower, LowerCase(Haystack)) > 0;
end;

procedure _DeleteStartupValuesIfMatch(const RootKey: Integer; const SubKey: string);
var
  Names: TArrayOfString;
  I: Integer;
  Val: string;
  ValLower: string;
begin
  if not RegGetValueNames(RootKey, SubKey, Names) then
    exit;

  for I := 0 to GetArrayLength(Names) - 1 do
  begin
    if RegQueryStringValue(RootKey, SubKey, Names[I], Val) then
    begin
      ValLower := LowerCase(Val);

      { Remove legacy/broken startup entries that invoke rundll32 on Pengu Loader core.dll.
        This is what produces the RunDLL "module not found" dialog after uninstall. }
      if (_ContainsTextLower(ValLower, 'rundll32') and _ContainsTextLower(ValLower, 'pengu loader\core.dll')) or
         _ContainsTextLower(ValLower, '\rose\_internal\pengu loader\core.dll') then
      begin
        RegDeleteValue(RootKey, SubKey, Names[I]);
      end;
    end;
  end;
end;

const
  RunKey      = 'Software\Microsoft\Windows\CurrentVersion\Run';
  RunOnceKey  = 'Software\Microsoft\Windows\CurrentVersion\RunOnce';
  RunKey6432  = 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run';
  RunOnce6432 = 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce';

procedure _CleanupStartupRegistry();
begin
  { 64-bit and user/machine startup keys }
  _DeleteStartupValuesIfMatch(HKCU, RunKey);
  _DeleteStartupValuesIfMatch(HKLM, RunKey);
  _DeleteStartupValuesIfMatch(HKCU, RunOnceKey);
  _DeleteStartupValuesIfMatch(HKLM, RunOnceKey);

  { 32-bit view keys (defensive) }
  _DeleteStartupValuesIfMatch(HKCU, RunKey6432);
  _DeleteStartupValuesIfMatch(HKLM, RunKey6432);
  _DeleteStartupValuesIfMatch(HKCU, RunOnce6432);
  _DeleteStartupValuesIfMatch(HKLM, RunOnce6432);
end;


procedure _CleanupLegacyPsmUninstallRegistry();
begin
  { Previous RC installers manually created this redundant key. }
  { Inno Setup manages the real AppId uninstall registration separately. }
  RegDeleteKeyIncludingSubkeys(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Personal Skin Manager');
  RegDeleteKeyIncludingSubkeys(HKLM32, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Personal Skin Manager');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    _CleanupStartupRegistry();
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    _CleanupLegacyPsmUninstallRegistry();
    { Remove the entire Personal Skin Manager install directory in case
      runtime-generated files (logs, caches, etc.) were left behind. }
    DelTree(ExpandConstant('{app}'), True, True, True);
  end;
end;
