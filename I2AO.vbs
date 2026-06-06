' ============================================================
'  I2AO.vbs  —  Lanceur silencieux (pas de fenetre console)
'  Double-cliquer pour demarrer I2AO
' ============================================================

Dim ROOT, launcher, shell
ROOT     = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
launcher = ROOT & "lancer.bat"

Set shell = CreateObject("WScript.Shell")

' windowStyle = 0  → fenêtre complètement cachée
' bWaitOnReturn = False → le VBS ne bloque pas
shell.Run "cmd /c """ & launcher & """", 0, False

Set shell = Nothing
WScript.Quit
