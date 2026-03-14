


# 1. Crear Tarea:

```Bash
schtasks /create /tn "GitWinSeek Refresh" ^
 /tr "\"D:\JUAN CARLOS\8 - JC_GitTools\GitWinSeek.exe\" refresh-all" ^
 /sc minute /mo 2
```

## Esto significa:

nombre de la tarea → GitWinSeek Refresh

programa → GitWinSeek

comando → refresh-all

frecuencia → cada 2 minutos
- Si prefieres cada 5 minutos:

```Bash
    /sc minute /mo 5
```

# 2. Verificar que la tarea existe

Puedes comprobarlo con:
```Bash
schtasks /query /tn "GitWinSeek Refresh"
```

# 3. Probar la tarea manualmente

Puedes ejecutarla al instante con:
```Bash
schtasks /run /tn "GitWinSeek Refresh"
```
Esto sirve para probar que realmente refresca los iconos.

# 4. Si algún día quieres borrarla

```Bash
schtasks /delete /tn "GitWinSeek Refresh" /f
```