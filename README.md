# JC Git Tools


Conjunto de herramientas ligeras para trabajar con repositorios **Git en Windows** de forma visual y rápida.

El sistema está compuesto por dos programas principales que trabajan juntos:

- **Git Win Tool** → interfaz visual para trabajar con repositorios Git
- **GitWinSeek** → sistema de monitorización visual que cambia el icono de las carpetas según el estado del repositorio

El objetivo es disponer de un entorno de trabajo muy ligero que permita ver el estado de los repositorios directamente en el **Explorador de Windows**, sin necesidad de herramientas pesadas ni tocar el shell de windows.

---

# Arquitectura del sistema

La solución se divide en dos componentes independientes pero integrados.

## 1. Git Win Tool

Aplicación gráfica para trabajar con repositorios Git.

Permite:

- abrir repositorios
- ver el estado del repositorio
- ver cambios locales
- hacer commit
- hacer push
- hacer pull
- refrescar estado
- ver sincronización con remoto (ahead / behind)

Cuando se ejecuta una operación que cambia el estado del repositorio, el programa llama automáticamente a **GitWinSeek** para actualizar el icono de la carpeta.

---

## 2. GitWinSeek

**Herramienta que monitoriza repositorios Git y modifica el icono de las carpetas en el Explorador de Windows.**

Funciona utilizando:

- `desktop.ini`
- un pack de iconos
- información del estado del repositorio obtenida mediante `git`

Esto permite ver el estado del repositorio directamente en el sistema de archivos.

### Estados visuales

| Estado | Icono | Significado |
|------|------|------|
| Verde | Repo limpio y sincronizado |
| Naranja | Cambios locales |
| Azul | Commit realizado pero pendiente de push |
| Rojo | Conflictos o error |

De esta forma es posible identificar el estado de cada repositorio **sin abrir ninguna herramienta**.

---

# Funcionamiento

GitWinSeek analiza el estado del repositorio usando comandos Git como:

- `git status`
- `git rev-parse`
- `git branch`

En función del estado detectado:

1. genera o modifica el archivo `desktop.ini`
2. asigna el icono correspondiente
3. fuerza un refresco del Explorador de Windows

---

# Comandos disponibles en GitWinSeek

## ->Inicializar seguimiento visual

```bash
GitWinSeek.exe init "ruta_repo"
```
Configura el repositorio para seguimiento visual.

Esto:

- crea la carpeta .jcgiticon

- copia los iconos necesarios

- crea desktop.ini

- registra el repositorio para seguimiento

## ->Refrescar icono de un repositorio

```bash
GitWinSeek.exe refresh "ruta_repo"
```
Actualiza el icono según el estado actual del repositorio.

## ->Refrescar todos los repositorios registrados
```bash
GitWinSeek.exe refresh-all
```
Revisa todos los repositorios registrados y actualiza su icono.

Este comando se utiliza normalmente en una tarea programada.

## ->Eliminar seguimiento visual
```bash
GitWinSeek.exe remove "ruta_repo"
```
Elimina el sistema de iconos del repositorio.

# Integración con el Explorador de Windows

Se añaden entradas en el menú contextual:
```
Git Tools
 ├─ Abrir Git Win Tool
 ├─ Inicializar icono Git
 ├─ Refrescar icono Git
 ├─ Quitar seguimiento visual
 └─ Refrescar todos los repos GitWinSeek
 ```

Esto permite utilizar las herramientas directamente desde el Explorador.
Ver los Archivos de instalacion y desinstalacion de claves en el registro (.reg).
(**Para usarlos, actualizar las rutas de los programas dentro de ellos.**)

## Refresco automático

Para mantener los iconos actualizados se utiliza **una tarea programada de Windows** que ejecuta:

```bash
GitWinSeek.exe refresh-all
```
cada cierto tiempo (por ejemplo cada 5 minutos).

```bash
schtasks /create /tn "GitWinSeek Refresh" ^
 /tr "\"RUTA AÑ ARCHIVO\GitWinSeek.exe\" refresh-all" ^
 /sc minute /mo 5
```
Esto garantiza que el estado visual siempre esté sincronizado con el repositorio.
y no tocamos el pull de procesos en segundo plano.

### - Verificar que la tarea existe

Puedes comprobarlo con:
```bash
schtasks /query /tn "GitWinSeek Refresh"
```
### - Probar la tarea manualmente, puedes ejecutarla al instante con:
```bash
schtasks /run /tn "GitWinSeek Refresh"
```
Esto sirve para probar que realmente refresca los iconos.

## Para Eliminar la tarea y el auto refresco:
```bash
schtasks /delete /tn "GitWinSeek Refresh" /f
```
