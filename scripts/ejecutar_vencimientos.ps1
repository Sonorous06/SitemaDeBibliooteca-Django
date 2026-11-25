$ErrorActionPreference = "Stop"

$proyecto = Split-Path -Parent $PSScriptRoot
$python = Join-Path $proyecto ".venv\Scripts\python.exe"

$carpetaLocal = Join-Path $env:LOCALAPPDATA "BiblioEscolar"
$credencialesPath = Join-Path $carpetaLocal "mysql.credential.xml"
$carpetaLogs = Join-Path $carpetaLocal "logs"

$codigoSalida = 1

try {
    New-Item -ItemType Directory -Path $carpetaLogs -Force | Out-Null

    if (-not (Test-Path -LiteralPath $python)) {
        throw "No se encontro el Python del entorno virtual."
    }

    if (-not (Test-Path -LiteralPath $credencialesPath)) {
        throw "Primero configura las credenciales locales de MySQL."
    }

    $credencial = Import-Clixml -LiteralPath $credencialesPath

    $env:DB_USER = $credencial.UserName
    $env:DB_PASSWORD = $credencial.GetNetworkCredential().Password
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"

    $marca = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $salidaPath = Join-Path $carpetaLogs "$marca-salida.log"
    $errorPath = Join-Path $carpetaLogs "$marca-error.log"

    $parametros = @{
        FilePath = $python
        ArgumentList = @(
            "manage.py",
            "procesar_vencimientos",
            "--no-color"
        )
        WorkingDirectory = $proyecto
        RedirectStandardOutput = $salidaPath
        RedirectStandardError = $errorPath
        NoNewWindow = $true
        Wait = $true
        PassThru = $true
    }

    $proceso = Start-Process @parametros
    $codigoSalida = $proceso.ExitCode

    $resumenPath = Join-Path $carpetaLogs "ejecuciones.log"

    "$(Get-Date -Format s) Codigo=$codigoSalida Salida=$salidaPath Error=$errorPath" |
        Add-Content -LiteralPath $resumenPath -Encoding UTF8

    if ($codigoSalida -eq 0) {
        Write-Output "Proceso completado correctamente."
        Get-Content -LiteralPath $salidaPath -Encoding UTF8
    }
    else {
        Write-Output "El comando fallo. Revisa: $errorPath"
    }

    Write-Output "Registros: $carpetaLogs"
}
catch {
    Write-Output "No se pudo completar la ejecucion."
    Write-Output $_.Exception.Message
    $codigoSalida = 1
}
finally {
    Remove-Item Env:DB_PASSWORD -ErrorAction SilentlyContinue
}

exit $codigoSalida