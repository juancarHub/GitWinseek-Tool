@Echo off

schtasks /create /tn "GitWinSeek Refresh" ^
 /tr "\"D:\JUAN CARLOS\8 - JC_GitTools\GitWinSeek.exe\" refresh-all" ^
 /sc minute /mo 2

Echo Tarea Añadida.