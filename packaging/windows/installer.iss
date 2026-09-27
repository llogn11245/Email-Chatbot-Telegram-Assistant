; Inno Setup script cho Chatbot Gmail (onedir build từ PyInstaller)
; Build:  iscc packaging\windows\installer.iss
; Yêu cầu đã có .\dist\ChatbotGmail\ (PyInstaller output).

#define MyAppName "Chatbot Gmail"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Chatbot Gmail"
#define MyAppExeName "ChatbotGmail.exe"

[Setup]
AppId={{8F3C2A14-6B7D-4E52-9C1A-CHATBOTGMAIL01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\ChatbotGmail
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist\installer
OutputBaseFilename=ChatbotGmail-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut ngoài Desktop"; GroupDescription: "Shortcut:"; Flags: unchecked

[Files]
Source: "..\..\dist\ChatbotGmail\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Chạy {#MyAppName}"; Flags: nowait postinstall skipifsilent
