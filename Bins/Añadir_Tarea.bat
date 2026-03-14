@Echo off

schtasks /create /tn "GitWinSeek Refresh" ^
 /tr "\"D:\GitWinTool\GitWinSeek\GitWinSeek.exe\" refresh-all" ^
 /sc minute /mo 1

Echo Tarea Añadida.