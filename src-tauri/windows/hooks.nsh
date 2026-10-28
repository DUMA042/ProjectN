; Stop a running Flow instance before files are replaced or removed.
; The host owns the API and PostgreSQL as child processes in a Windows job
; object, so terminating the host is enough to release every file.
; %APPDATA%\Flow is intentionally left untouched by install and uninstall.

!macro FLOW_STOP_RUNNING
  DetailPrint "Stopping Flow if it is running..."
  nsExec::ExecToLog 'taskkill /IM Flow.exe /F /T'
  Pop $0
  nsExec::ExecToLog 'taskkill /IM flow-desktop.exe /F /T'
  Pop $0
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro FLOW_STOP_RUNNING
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro FLOW_STOP_RUNNING
!macroend
