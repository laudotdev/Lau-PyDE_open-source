#define AppVersion "1.1.0"
#define AppName "Lau-PyDE"
#define AppPublisher "John Laurence Aramay / ryu.dev"
#define AppExeName "Lau-PyDE.exe"

[Setup]
AppId={{B2A2E0EA-6B59-4BB7-B3B4-3B9C6A8E1B10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Lau-PyDE
DefaultGroupName={#AppName}
OutputDir=..\..\dist\installer
OutputBaseFilename=Lau-PyDE-Setup-v{#AppVersion}
SetupIconFile=lau-pyde_logo.ico
UninstallDisplayIcon={app}\{#AppExeName}
LicenseFile=LICENSE.txt
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\..\dist\Lau-PyDE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "launchafterinstall"; Description: "Launch Lau-PyDE after installation"; GroupDescription: "Additional options:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch Lau-PyDE"; Flags: nowait postinstall skipifsilent; Tasks: launchafterinstall

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
