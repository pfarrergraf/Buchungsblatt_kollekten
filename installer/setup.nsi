; NSIS Installer-Script für Kollekten-Automation
; Erstellt: setup.nsi
; Build: makensis setup.nsi
; Voraussetzung: PyInstaller-Build unter dist/Kollekten-Automation/ vorhanden

Unicode true

!define APP_NAME      "Kollekten-Automation"
!define APP_VERSION   "1.0.0"
!define APP_PUBLISHER "Ev. Kirchengemeinde"
!define APP_EXE       "Kollekten-Automation.exe"
!define INST_DIR      "$PROGRAMFILES64\Kollekten-Automation"
!define REG_KEY       "Software\Microsoft\Windows\CurrentVersion\Uninstall\KollektenAutomation"

; --- Installer-Metadaten ---
Name              "${APP_NAME} ${APP_VERSION}"
OutFile           "..\Kollekten-Setup-${APP_VERSION}.exe"
InstallDir        "${INST_DIR}"
InstallDirRegKey  HKCU "Software\KollektenAutomation" "InstallPath"
RequestExecutionLevel admin
SetCompressor     lzma

; Moderne UI
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\app.ico"
!define MUI_UNICON "..\assets\app.ico"

; Seiten
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Kollekten-Automation jetzt starten"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "German"

; --- Installation ---
Section "Hauptprogramm" SecMain

  SetOutPath "$INSTDIR"
  File /r "..\dist\Kollekten-Automation\*.*"

  ; Startmenü
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Deinstallieren.lnk" \
                  "$INSTDIR\uninstall.exe"

  ; Desktop-Verknüpfung (optional)
  CreateShortcut  "$DESKTOP\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  ; Uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Registry-Eintrag für Windows-Einstellungen > Apps
  WriteRegStr   HKLM "${REG_KEY}" "DisplayName"      "${APP_NAME}"
  WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"   "${APP_VERSION}"
  WriteRegStr   HKLM "${REG_KEY}" "Publisher"        "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${REG_KEY}" "InstallLocation"  "$INSTDIR"
  WriteRegStr   HKLM "${REG_KEY}" "UninstallString"  "$INSTDIR\uninstall.exe"
  WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"      "$INSTDIR\${APP_EXE}"
  WriteRegDWORD HKLM "${REG_KEY}" "NoModify"         1
  WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"         1

SectionEnd

; --- Deinstallation ---
Section "Uninstall"

  RMDir /r "$INSTDIR"

  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Deinstallieren.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"
  Delete "$DESKTOP\${APP_NAME}.lnk"

  ; Autostart-Eintrag entfernen (falls gesetzt)
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "KollektenAutomation"

  ; Uninstall-Registry aufräumen
  DeleteRegKey HKLM "${REG_KEY}"
  DeleteRegKey HKCU "Software\KollektenAutomation"

SectionEnd
