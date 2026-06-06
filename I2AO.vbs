' ============================================================
'  I2AO.vbs  —  Lanceur silencieux (pas de fenetre console)
'  Double-cliquer pour demarrer I2AO
' ============================================================

Dim ROOT, launcher, shell
ROOT    = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
launcher = ROOT & "lancer.bat"

Set shell = CreateObject("WScript.Shell")

' Lance lancer.bat sans fenetre console (0 = hidden)
shell.Run "cmd /c """ & launcher & """", 0, False

Set shell = Nothing
