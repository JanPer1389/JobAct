$ErrorActionPreference = "Stop"
$portProbe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$portProbe.Start()
$testPort = ([Net.IPEndPoint]$portProbe.LocalEndpoint).Port
$portProbe.Stop()
$baseUrl = "http://127.0.0.1:$testPort"
$server = $null
$previousPort = $env:PORT
$previousCi = $env:CI

try {
    $env:CI = "true"
    node .\node_modules\next\dist\bin\next build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend production build failed."
    }

    $dockerfile = Get-Content -Raw (Join-Path $PSScriptRoot "..\Dockerfile")
    $cmdMatch = [regex]::Match(
        $dockerfile,
        '(?m)^CMD\s+(?<command>\[[^\r\n]+\])\s*$'
    )
    if (-not $cmdMatch.Success) {
        throw "Dockerfile does not define a JSON-form CMD."
    }
    $configuredCommand = $cmdMatch.Groups["command"].Value | ConvertFrom-Json
    $package = Get-Content -Raw (Join-Path $PSScriptRoot "..\package.json") | ConvertFrom-Json
    $scriptName = $configuredCommand[1]
    $scriptCommand = $package.scripts.$scriptName -split '\s+'
    if ($configuredCommand[0] -ne "pnpm" -or $scriptCommand[0] -ne "next") {
        throw "Smoke test only supports a pnpm script backed by the Next.js CLI."
    }
    $executable = (Get-Command node).Source
    $arguments = @(
        (Resolve-Path (Join-Path $PSScriptRoot "..\node_modules\next\dist\bin\next")),
        $scriptCommand[1]
    )

    $env:PORT = [string]$testPort
    $server = Start-Process `
        -FilePath $executable `
        -ArgumentList $arguments `
        -WorkingDirectory (Resolve-Path (Join-Path $PSScriptRoot "..")) `
        -PassThru `
        -WindowStyle Hidden

    $homeResponse = $null
    for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
        try {
            $homeResponse = Invoke-WebRequest -Uri $baseUrl -UseBasicParsing
            if ($homeResponse.StatusCode -eq 200) { break }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if ($null -eq $homeResponse -or $homeResponse.StatusCode -ne 200) {
        throw "Configured frontend command did not become ready."
    }

    $chunkMatch = [regex]::Match(
        $homeResponse.Content,
        'src="(?<path>/_next/static/chunks/[^"?]+\.js)"'
    )
    if (-not $chunkMatch.Success) {
        throw "Rendered page did not contain a Next.js client chunk."
    }

    $chunk = Invoke-WebRequest `
        -Uri "$baseUrl$($chunkMatch.Groups['path'].Value)" `
        -Headers @{ Origin = "https://jobact.dokploy.gcexp.ru" } `
        -UseBasicParsing `
        -SkipHttpErrorCheck

    if ($chunk.StatusCode -ne 200) {
        throw "Client chunk was blocked for the production origin: HTTP $($chunk.StatusCode)."
    }

    Write-Output "Configured frontend command serves client chunks to the public origin."
} finally {
    if ($null -ne $server -and -not $server.HasExited) {
        taskkill.exe /PID $server.Id /T /F 2>$null | Out-Null
    }
    netstat.exe -ano | Select-String ":$testPort\s+.*LISTENING\s+(?<pid>\d+)$" | ForEach-Object {
        Stop-Process -Id ([int]$_.Matches[0].Groups["pid"].Value) -Force -ErrorAction SilentlyContinue
    }
    $env:PORT = $previousPort
    $env:CI = $previousCi
}
