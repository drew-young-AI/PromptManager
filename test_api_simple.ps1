####################################################################
# PowerShell API Test Script for aai.cych.org.tw
####################################################################

$BaseUrl = "http://aai.cych.org.tw:8080"

Write-Host "`n" 
Write-Host "█ API 1: POST /getPatientList/" -ForegroundColor Cyan
Write-Host "█ 需要的 BODY 欄位:" -ForegroundColor Cyan
Write-Host "█   - station (病房代碼, 例: '6D')" -ForegroundColor Cyan
Write-Host "█   - admitDateTime (入院日期, 格式: yyyy-MM-dd)" -ForegroundColor Cyan
Write-Host "█   - systemKind (系統別: 01/02/03/04)" -ForegroundColor Cyan
Write-Host ""

$body1 = @{
    station = "6D"
    admitDateTime = "2026-05-01"
    systemKind = "01"
} | ConvertTo-Json

Write-Host "Request Body JSON:" -ForegroundColor Yellow
Write-Host $body1 -ForegroundColor White
Write-Host ""

$response1 = Invoke-RestMethod -Uri "$BaseUrl/getPatientList/" -Method Post -Body $body1 -ContentType "application/json"
Write-Host "Response: Success=$($response1.success), Count=$($response1.data.Count)" -ForegroundColor Green
Write-Host "Patients: $($response1.data | ConvertTo-Json -Depth 1)" -ForegroundColor White

Write-Host "`n" 
Write-Host "█ API 2: POST /fetchData/" -ForegroundColor Cyan
Write-Host "█ 需要的 BODY 欄位:" -ForegroundColor Cyan
Write-Host "█   - systemKind (系統別: 01/02/03/04)" -ForegroundColor Cyan
Write-Host "█   - fetchId (MongoDB _id 陣列)" -ForegroundColor Cyan
Write-Host ""

$mongoIds = $response1.data | ForEach-Object { $_.mongoDbId }
$body2 = @{
    systemKind = "01"
    fetchId = $mongoIds
} | ConvertTo-Json

Write-Host "Request Body JSON:" -ForegroundColor Yellow
Write-Host $body2 -ForegroundColor White
Write-Host ""

$response2 = Invoke-RestMethod -Uri "$BaseUrl/fetchData/" -Method Post -Body $body2 -ContentType "application/json"
Write-Host "Response: Success=$($response2.success), Count=$($response2.data.Count)" -ForegroundColor Green
Write-Host "Sample Data: $($response2.data[0] | ConvertTo-Json -Depth 2)" -ForegroundColor White
