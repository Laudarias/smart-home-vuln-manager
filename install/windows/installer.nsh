; install/windows/installer.nsh
; ─────────────────────────────────────────────────────────────────────────────
; Hook de NSIS: se ejecuta después de que electron-builder copia los archivos.
; Llama a setup.ps1 para configurar WSL2 y el entorno Python.
; ─────────────────────────────────────────────────────────────────────────────

!macro customInstall
  DetailPrint "Configurando entorno WSL2 (esto puede tardar varios minutos)..."

  ; Ejecutar setup.ps1 como administrador con PowerShell
  nsExec::ExecToLog 'powershell.exe -ExecutionPolicy Bypass -NonInteractive -File "$INSTDIR\resources\installer\setup.ps1"'
  Pop $0  ; código de salida

  ${If} $0 != "0"
    MessageBox MB_ICONEXCLAMATION "La configuración del entorno no se completó correctamente.$\n$\nCódigo: $0$\n$\nRevisa que tu equipo tenga conexión a internet y vuelve a intentarlo."
  ${EndIf}
!macroend

!macro customUnInstall
  ; Al desinstalar, opcional: eliminar el entorno WSL
  ; (comentado por defecto para no borrar datos del usuario)
  ; nsExec::ExecToLog 'wsl.exe --unregister Ubuntu'
!macroend
