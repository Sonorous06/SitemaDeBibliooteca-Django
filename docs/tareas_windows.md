# Vencimientos y avisos automáticos en Windows

El comando `procesar_vencimientos` marca préstamos vencidos, expira
solicitudes y reservas, reasigna ejemplares y genera avisos.

## Requisitos

- Proyecto instalado con `.venv` y migraciones aplicadas.
- MySQL iniciado y accesible.
- Windows encendido, sin suspensión y con la sesión del usuario iniciada.
- Mantener el proyecto en la ubicación donde se registra la tarea.

No es necesario mantener abiertos VS Code ni el servidor de Django.

## Configurar las credenciales locales

Desde PowerShell, en la carpeta que contiene `manage.py`:

```powershell
$carpetaLocal = Join-Path $env:LOCALAPPDATA "BiblioEscolar"
New-Item -ItemType Directory -Path $carpetaLocal -Force | Out-Null

$credencialMySQL = Get-Credential -UserName "root" -Message "Credenciales de MySQL para Biblioteca"

$credencialMySQL | Export-Clixml -LiteralPath (Join-Path $carpetaLocal "mysql.credential.xml")
Remove-Variable credencialMySQL
```

Cambiar `root` si se utiliza otro usuario de MySQL.

La contraseña corresponde a MySQL, no a una cuenta de la biblioteca.
Windows protege la credencial para el usuario y equipo que la guardaron.
Cada integrante debe configurar sus propias credenciales.

El ejecutor proporciona las variables `DB_USER` y `DB_PASSWORD`.
La configuración local de Django debe utilizarlas para conectarse.

## Probar el ejecutor

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\ejecutar_vencimientos.ps1
```

Debe mostrar `Proceso completado correctamente`.
Los contadores pueden ser cero si no hay registros que procesar.

## Registrar la tarea

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\configurar_tarea_windows.ps1
```

Se registra `BiblioEscolar-Vencimientos` cada 15 minutos.
No inicia otra instancia de esa tarea si la anterior sigue ejecutándose.
El configurador no reemplaza una tarea existente con el mismo nombre.

## Verificar la ejecución

Para solicitar una ejecución inmediata:

```powershell
Start-ScheduledTask -TaskName "BiblioEscolar-Vencimientos"
```

Después de que termine:

```powershell
Get-ScheduledTaskInfo -TaskName "BiblioEscolar-Vencimientos" |
    Select-Object LastRunTime, LastTaskResult, NextRunTime

Get-Content "$env:LOCALAPPDATA\BiblioEscolar\logs\ejecuciones.log" -Tail 5
```

Un resultado correcto muestra `LastTaskResult` igual a `0` y un registro
con `Codigo=0`.

Para comprobar el disparador automático, esperar a `NextRunTime` sin
iniciar manualmente la tarea y verificar que cambien la última ejecución
y el registro.

## Registros y errores

Los registros están en:

```text
%LOCALAPPDATA%\BiblioEscolar\logs
```

Cada ejecución del comando genera archivos de salida y error.
Si el código no es cero, consultar el archivo de error indicado.

Las credenciales y registros permanecen fuera del repositorio.

## Desactivar o reactivar

```powershell
Disable-ScheduledTask -TaskName "BiblioEscolar-Vencimientos"
Enable-ScheduledTask -TaskName "BiblioEscolar-Vencimientos"
```

Esta configuración corresponde al equipo local. Para ejecutarse sin
una sesión iniciada o en un servidor se requiere otra configuración.