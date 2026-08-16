; ============================================================
; Inno Setup Script - He thong Du bao Hai van Quang Tri
; ============================================================
; Cach dung:
;   1. Cai Inno Setup (mien phi): https://jrsoftware.org/isdl.php
;   2. Build .exe truoc bang desktop\build_exe.bat (script nay
;      dong goi dung folder desktop\dist\HaiVanQuangTri\ do
;      PyInstaller tao ra -- PHAI build .exe truoc khi chay file
;      nay).
;   3. Mo file .iss nay bang Inno Setup Compiler (hoac chuot
;      phai > Compile), hoac chay dong lenh:
;         ISCC.exe HaiVanQuangTri.iss
;   4. File installer .exe se nam trong desktop\installer\output\
; ============================================================

#define MyAppName "He thong Du bao Hai van Quang Tri"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Du an Du bao Hai van Quang Tri"
#define MyAppExeName "HaiVanQuangTri.exe"
#define MyBuildDir "..\dist\HaiVanQuangTri"
#define MyIconFile "..\..\HaiVan.ico"

[Setup]
AppId={{B6E1B6C1-6C1A-4B1A-9C1A-HAIVANQT0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HaiVanQuangTri
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Khong yeu cau quyen Administrator (cai vao thu muc rieng cua user) --
; doi thanh "admin" neu ban muon cai chung cho moi user tren may (can
; quyen Administrator khi cai).
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=HaiVanQuangTri_Setup_{#MyAppVersion}
SetupIconFile={#MyIconFile}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tao icon ngoai Desktop"; GroupDescription: "Icon bo sung:"; Flags: unchecked

[Files]
; Copy TOAN BO thu muc dist\HaiVanQuangTri\ (exe + _internal\ + moi thu
; PyInstaller da dong goi san) vao thu muc cai dat.
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Go bo {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Chay {#MyAppName} ngay"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Xoa luon du lieu tai (song/dong chay/khi tuong) va bao cao da tao ra
; khi go cai dat, vi config.py luu chung vao thu muc cai dat (BASE_DIR).
; Bo dong nay neu muon GIU LAI du lieu/bao cao cu sau khi go cai.
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\output"
