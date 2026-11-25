$ErrorActionPreference = "Stop"

$nombreTarea = "BiblioEscolar-Vencimientos"
$proyecto = Split-Path -Parent $PSScriptRoot
$ejecutor = Join-Path $PSScriptRoot "ejecutar_vencimientos.ps1"

$carpetaLocal = Join-Path $env:LOCALAPPDATA "BiblioEscolar"
$credencialesPath = Join-Path $carpetaLocal "mysql.credential.xml"

if (-not (Test-Path -LiteralPath $ejecutor)) {
    throw "No se encontro ejecutar_vencimientos.ps1."
}

if (-not (Test-Path -LiteralPath $credencialesPath)) {
    throw "Primero configura las credenciales locales de MySQL."
}

$existente = Get-ScheduledTask `
    -TaskName $nombreTarea `
    -TaskPath "\" `
    -ErrorAction SilentlyContinue

if ($existente) {
    throw "La tarea ya existe. Revisa su configuracion antes de reemplazarla."
}

$powershell = Join-Path $env:SystemRoot `
    "System32\WindowsPowerShell\v1.0\powershell.exe"

$argumentos = (
    '-NoProfile -NonInteractive -WindowStyle Hidden ' +
    '-ExecutionPolicy RemoteSigned -File "' + $ejecutor + '"'
)

$accion = New-ScheduledTaskAction `
    -Execute $powershell `
    -Argument $argumentos `
    -WorkingDirectory $proyecto

$disparador = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(15) `
    -RepetitionInterval (New-TimeSpan -Minutes 15)

$usuarioWindows = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$principal = New-ScheduledTaskPrincipal `
    -UserId $usuarioWindows `
    -LogonType Interactive `
    -RunLevel Limited

$opciones = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$registro = @{
    TaskName = $nombreTarea
    TaskPath = "\"
    Action = $accion
    Trigger = $disparador
    Principal = $principal
    Settings = $opciones
    Description = (
        "Procesa vencimientos, solicitudes, reservas y avisos " +
        "de Biblioteca Escolar cada 15 minutos."
    )
}

Register-ScheduledTask @registro | Out-Null

Write-Output "Tarea registrada: $nombreTarea"
Write-Output "Frecuencia: cada 15 minutos."
Write-Output "Usuario de Windows: $usuarioWindows"