####################################################################
# PowerShell API 測試腳本 - aai.cych.org.tw
####################################################################

$BaseUrl = "http://aai.cych.org.tw:8080"

####################################################################
# API 1: POST /getPatientList/
####################################################################

function Test-GetPatientList {
    param(
        [string]$Station = "6D",
        [string]$AdmitDate = "2026-05-01",
        [string]$SystemKind = "01"
    )
    
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "API 1: POST /getPatientList/" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    
    $url = "$BaseUrl/getPatientList/"
    $body = @{
        station = $Station
        admitDateTime = $AdmitDate
        systemKind = $SystemKind
    } | ConvertTo-Json
    
    Write-Host "`n[REQUEST]"
    Write-Host "URL: POST $url"
    Write-Host "Header: Content-Type: application/json"
    Write-Host "Body:`n$body`n"
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
        
        Write-Host "[RESPONSE]" -ForegroundColor Green
        Write-Host "Success: $($response.success)"
        Write-Host "Message: $($response.message)"
        Write-Host "Patient Count: $($response.data.Count)"
        Write-Host "`nPatient List:`n$(($response.data | ConvertTo-Json -Depth 2))"
        
        return $response.data
        
    }
    catch {
        Write-Host "[ERROR]" -ForegroundColor Red
        Write-Host $_.Exception.Message
        return $null
    }
}

####################################################################
# API 2: POST /fetchData/
####################################################################

function Test-FetchData {
    param(
        [string]$SystemKind = "01",
        [array]$FetchIds = @("69f3c41756710a4b96064f3b", "69f3e0c756710a4b96064f3d")
    )
    
    Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "API 2: POST /fetchData/" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    
    $url = "$BaseUrl/fetchData/"
    $body = @{
        systemKind = $SystemKind
        fetchId = $FetchIds
    } | ConvertTo-Json
    
    Write-Host "`n[REQUEST]"
    Write-Host "URL: POST $url"
    Write-Host "Header: Content-Type: application/json"
    Write-Host "Body:`n$body`n"
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
        
        Write-Host "[RESPONSE]" -ForegroundColor Green
        Write-Host "Success: $($response.success)"
        Write-Host "Message: $($response.message)"
        Write-Host "Data Count: $($response.data.Count)"
        
        if ($response.data.Count -gt 0) {
            Write-Host "`nFirst Record (Preview):"
            $firstRecord = $response.data[0] | ConvertTo-Json -Depth 3
            Write-Host $firstRecord
        }
        
        return $response.data
        
    }
    catch {
        Write-Host "[ERROR]" -ForegroundColor Red
        Write-Host $_.Exception.Message
        return $null
    }
}

####################################################################
# 完整測試流程
####################################################################

function Test-FullFlow {
    Write-Host "`n`n" 
    Write-Host "████████████████████████████████████████████████████████████" -ForegroundColor Yellow
    Write-Host "完整測試流程：先查詢病人，再取得詳細資料" -ForegroundColor Yellow
    Write-Host "████████████████████████████████████████████████████████████" -ForegroundColor Yellow
    
    # 步驟 1: 查詢病人
    $patients = Test-GetPatientList -Station "6D" -AdmitDate "2026-05-01" -SystemKind "01"
    
    if ($patients -and $patients.Count -gt 0) {
        Write-Host "`n✓ 成功取得 $($patients.Count) 筆病人資料" -ForegroundColor Green
        
        # 步驟 2: 取得詳細資料
        $mongoIds = $patients | ForEach-Object { $_.mongoDbId }
        Write-Host "MongoDB IDs: $($mongoIds -join ', ')" -ForegroundColor Cyan
        
        $medicalData = Test-FetchData -SystemKind "01" -FetchIds $mongoIds
        
        if ($medicalData) {
            Write-Host "`n✓ 成功取得 $($medicalData.Count) 筆詳細資料" -ForegroundColor Green
        }
    } else {
        Write-Host "`n✗ 無法取得病人資料" -ForegroundColor Red
    }
    
    Write-Host "`n`n████████████████████████████████████████████████████████████" -ForegroundColor Yellow
    Write-Host "測試完成" -ForegroundColor Yellow
    Write-Host "████████████████████████████████████████████████████████████" -ForegroundColor Yellow
}

# 執行測試
Test-FullFlow
