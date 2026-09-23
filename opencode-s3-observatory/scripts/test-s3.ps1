[CmdletBinding()]
param(
    [string]$FilePath = "",
    [string]$ObjectKey = ""
)

$ErrorActionPreference = "Stop"
$endpoint = "http://localhost:8333"
$bucket = "bigdata"
$accessKey = "admin"
$secretKey = "bigdata-local-secret"
$region = "us-east-1"
$projectRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($FilePath)) {
    $FilePath = Join-Path $projectRoot "samples\exemple.txt"
}

function Invoke-Curl {
    param([string[]]$Arguments)

    & curl.exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "curl a echoue avec le code $LASTEXITCODE."
    }
}

foreach ($command in @("docker", "curl.exe", "python")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "La commande '$command' est introuvable."
    }
}

$resolvedFile = (Resolve-Path -LiteralPath $FilePath).Path
if ([string]::IsNullOrWhiteSpace($ObjectKey)) {
    $ObjectKey = Split-Path -Leaf $resolvedFile
}

$downloadPath = Join-Path $projectRoot "samples\telecharge-$([IO.Path]::GetFileName($ObjectKey))"
$objectUrl = "$endpoint/$bucket/$([Uri]::EscapeDataString($ObjectKey))"

Push-Location $projectRoot
try {
    Write-Host "Demarrage de SeaweedFS..." -ForegroundColor Cyan
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up a echoue."
    }

    Write-Host "Attente de l'API S3..." -ForegroundColor Cyan
    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        & curl.exe --silent --output NUL `
            --aws-sigv4 "aws:amz:${region}:s3" `
            --user "${accessKey}:${secretKey}" `
            "$endpoint/$bucket/"
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw "L'API S3 ne repond pas apres 30 secondes. Lancez 'docker compose logs s3'."
    }

    $form = python "$projectRoot/examples/post-policy.py" `
        --key $ObjectKey `
        --bucket $bucket `
        --access-key $accessKey `
        --secret-key $secretKey `
        --region $region | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "La generation de la signature POST a echoue."
    }

    Write-Host "POST de '$resolvedFile' vers s3://$bucket/$ObjectKey..." -ForegroundColor Cyan
    Invoke-Curl -Arguments @(
        "--fail-with-body", "--silent", "--show-error", "--request", "POST",
        "$endpoint/$bucket/",
        "--form-string", "key=$ObjectKey",
        "--form-string", "x-amz-algorithm=AWS4-HMAC-SHA256",
        "--form-string", "x-amz-credential=$($form.credential)",
        "--form-string", "x-amz-date=$($form.date)",
        "--form-string", "policy=$($form.policy)",
        "--form-string", "x-amz-signature=$($form.signature)",
        "--form-string", "success_action_status=201",
        "--form", "file=@$resolvedFile"
    )

    Write-Host "GET de s3://$bucket/$ObjectKey..." -ForegroundColor Cyan
    Invoke-Curl -Arguments @(
        "--fail-with-body", "--silent", "--show-error",
        "--aws-sigv4", "aws:amz:${region}:s3",
        "--user", "${accessKey}:${secretKey}",
        "--output", $downloadPath,
        $objectUrl
    )

    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedFile).Hash
    $downloadHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $downloadPath).Hash
    if ($sourceHash -ne $downloadHash) {
        throw "Echec : le fichier telecharge est different du fichier envoye."
    }

    Write-Host "Succes : POST et GET fonctionnent, les fichiers sont identiques." -ForegroundColor Green
    Write-Host "Fichier recupere : $downloadPath"
}
finally {
    Pop-Location
}
