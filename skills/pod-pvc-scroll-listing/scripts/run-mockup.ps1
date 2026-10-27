param(
 [Parameter(Mandatory=$true)][ValidateSet('Inspect','Build','Export')][string]$Mode,
 [Parameter(Mandatory=$true)][string]$ConfigPath,
 [ValidateRange(0,3600)][int]$LockTimeoutSeconds=0
)
$ErrorActionPreference='Stop'
$mockupMutex=[Threading.Mutex]::new($false,'Local\Codex-POD-Photoshop')
$mockupLocked=$false;$mockupApp=$null
try{
 try{$mockupLocked=$mockupMutex.WaitOne([TimeSpan]::FromSeconds($LockTimeoutSeconds))}catch [Threading.AbandonedMutexException]{$mockupLocked=$true}
 if(-not $mockupLocked){'{"status":"busy","code":"POD_PS_BUSY","retryable":true}';throw 'POD_PS_BUSY: another managed Photoshop task is running'}
 $mockupConfigFile=(Resolve-Path -LiteralPath $ConfigPath).Path
 $mockupConfig=Get-Content -LiteralPath $mockupConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
 if($Mode -eq 'Export'){foreach($mockupJob in $mockupConfig.jobs){if($mockupJob.template_sha256){$mockupActual=(Get-FileHash -LiteralPath $mockupJob.template -Algorithm SHA256).Hash;if($mockupActual -ne $mockupJob.template_sha256){throw ('Template hash mismatch: '+$mockupJob.id)}}}}
 $mockupPayload=$mockupConfig | ConvertTo-Json -Depth 60 -Compress
 $mockupTools=($PSScriptRoot -replace '\\','/') | ConvertTo-Json -Compress
 $mockupScript=switch($Mode){'Build'{'build-shared-template.jsx'}'Export'{'batch-export.jsx'}'Inspect'{'inspect-shared-template.jsx'}}
 $mockupEntry="var MOCKUP_JOB=$mockupPayload;`nvar MOCKUP_TOOLS=$mockupTools;`n$.evalFile(new File(MOCKUP_TOOLS+'/$mockupScript'));"
 $mockupRunDir=Join-Path (Split-Path -Parent $mockupConfigFile) '运行记录';New-Item -ItemType Directory -Path $mockupRunDir -Force | Out-Null
 $mockupEntryPath=Join-Path $mockupRunDir ($Mode+'-'+[Guid]::NewGuid().ToString('N')+'.jsx')
 [IO.File]::WriteAllText($mockupEntryPath,$mockupEntry,[Text.UTF8Encoding]::new($false))
 $mockupApp=New-Object -ComObject Photoshop.Application
 $mockupResponse=$mockupApp.DoJavaScriptFile($mockupEntryPath);$mockupResult=$mockupResponse | ConvertFrom-Json;$mockupResponse
 if($mockupResult.status -eq 'partial_failure'){throw 'POD_EXPORT_PARTIAL_FAILURE: inspect export-report.json'}
}finally{
 if($null -ne $mockupApp){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($mockupApp)}
 if($mockupLocked){$mockupMutex.ReleaseMutex()};$mockupMutex.Dispose()
}
