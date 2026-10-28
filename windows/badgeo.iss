; Installateur Badgeo (édition locale Windows) — Inno Setup 6.
; Même Badgeo-Setup.exe pour tous les clients et pour les mises à jour (la licence est liée au poste).
#ifndef Version
  #define Version "1.0"
#endif
#ifndef Paquet
  #define Paquet "construction\Badgeo"
#endif

[Setup]
AppId={{6F1C2E8A-4B7D-4D39-9A51-3E7B8C2D1F40}
AppName=Badgeo
AppVersion={#Version}
AppPublisher=Badgeo
DefaultDirName={autopf}\Badgeo
DefaultGroupName=Badgeo
DisableProgramGroupPage=yes
OutputBaseFilename=Badgeo-Setup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
UninstallDisplayName=Badgeo
CloseApplications=no
SetupLogging=yes
SetupIconFile={#Paquet}\app\frontend_dist\favicon.ico
UninstallDisplayIcon={app}\app\frontend_dist\favicon.ico

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Créer un raccourci sur le bureau"; GroupDescription: "Raccourcis :"
Name: "reseau"; Description: "Autoriser les autres postes à se connecter (pare-feu, port 8000)"; GroupDescription: "Réseau :"

[Dirs]
Name: "{commonappdata}\Badgeo"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{commonappdata}\Badgeo\journaux"; Flags: uninsneveruninstall

[Files]
Source: "{#Paquet}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[INI]
Filename: "{app}\Badgeo.url"; Section: "InternetShortcut"; Key: "URL"; String: "http://localhost:8000/"

[Icons]
Name: "{group}\Badgeo"; Filename: "{app}\Badgeo.url"
Name: "{group}\Données et sauvegardes"; Filename: "{commonappdata}\Badgeo"
Name: "{group}\Désinstaller Badgeo"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Badgeo"; Filename: "{app}\Badgeo.url"; Tasks: bureau

[Run]
Filename: "{app}\badgeo-service.exe"; Parameters: "install"; Flags: runhidden waituntilterminated; StatusMsg: "Installation du service Badgeo…"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Badgeo"""; Flags: runhidden waituntilterminated; Tasks: reseau
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Badgeo"" dir=in action=allow protocol=TCP localport=8000 profile=private,domain"; Flags: runhidden waituntilterminated; Tasks: reseau
Filename: "{app}\badgeo-service.exe"; Parameters: "start"; Flags: runhidden waituntilterminated; StatusMsg: "Démarrage de Badgeo (première fois : environ une minute)…"
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$f=(Get-Date).AddSeconds(150); while((Get-Date) -lt $f){{ try{{ $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8000); $c.Close(); break }}catch{{ Start-Sleep -Seconds 2 }} }}"""; Flags: runhidden waituntilterminated; StatusMsg: "Attente du démarrage de Badgeo…"
Filename: "{app}\Badgeo.url"; Description: "Ouvrir Badgeo"; Flags: postinstall shellexec nowait skipifsilent

[UninstallRun]
Filename: "{app}\badgeo-service.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated; RunOnceId: "ArretService"
Filename: "{app}\badgeo-service.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "SuppressionService"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Badgeo"""; Flags: runhidden waituntilterminated; RunOnceId: "PareFeu"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\python"

[Messages]
fr.FinishedLabel=Badgeo est installé. Il démarre avec l'ordinateur et s'ouvre dans le navigateur à l'adresse http://localhost:8000.%n%nAu premier lancement, Badgeo affiche un code d'installation : communiquez-le à l'éditeur pour recevoir votre clé d'activation. Connexion par défaut : admin / Badgeo@2026 (à changer dès la première connexion).%n%nVos données sont dans C:\ProgramData\Badgeo : elles ne sont jamais effacées, même en cas de désinstallation.

[Code]
// Mise à jour : arrêter et retirer l'ancien service avant de remplacer les fichiers
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
  Service: String;
begin
  Service := ExpandConstant('{app}\badgeo-service.exe');
  if FileExists(Service) then
  begin
    Exec(Service, 'stop', '', SW_HIDE, ewWaitUntilTerminated, Code);
    Exec(Service, 'uninstall', '', SW_HIDE, ewWaitUntilTerminated, Code);
    Sleep(1500);
  end;
  Result := '';
end;
