# Simulation Diagnostic Script
# Tests the stop simulation fix and diagnoses data flow issues

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Simulation Diagnostic Test Suite" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$API_BASE = "http://localhost:8000"

# Function to make API call and format output
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET"
    )

    Write-Host "Testing: $Name" -ForegroundColor Yellow
    Write-Host "URL: $Url" -ForegroundColor Gray

    try {
        if ($Method -eq "POST") {
            $response = Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json"
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method Get
        }

        Write-Host "✅ SUCCESS" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 5 | Write-Host
        return $response
    }
    catch {
        Write-Host "❌ FAILED" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        return $null
    }

    Write-Host ""
}

# Test 1: Check backend is running
Write-Host "`n=== Test 1: Backend Health Check ===" -ForegroundColor Cyan
$health = Test-Endpoint -Name "Health Check" -Url "$API_BASE/api/health"
if (-not $health) {
    Write-Host "❌ Backend is not running! Start it with:" -ForegroundColor Red
    Write-Host "   cd masfro-backend" -ForegroundColor Yellow
    Write-Host "   uv run uvicorn app.main:app --reload --log-level debug" -ForegroundColor Yellow
    exit 1
}

# Test 2: Start simulation
Write-Host "`n=== Test 2: Start Simulation ===" -ForegroundColor Cyan
$start = Test-Endpoint -Name "Start Simulation (Medium Mode)" -Url "$API_BASE/api/simulation/start?mode=medium" -Method "POST"
if (-not $start -or $start.state -ne "running") {
    Write-Host "❌ Failed to start simulation" -ForegroundColor Red
    exit 1
}

Write-Host "`nWaiting 10 seconds for events to process..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Test 3: Check simulation status
Write-Host "`n=== Test 3: Simulation Status ===" -ForegroundColor Cyan
$status = Test-Endpoint -Name "Simulation Status" -Url "$API_BASE/api/simulation/status"
if ($status) {
    Write-Host "State: $($status.state)" -ForegroundColor $(if ($status.state -eq "running") { "Green" } else { "Red" })
    Write-Host "Tick Count: $($status.tick_count)" -ForegroundColor Gray
    Write-Host "Time Step: $($status.time_step)" -ForegroundColor Gray
}

# Test 4: Check hazard cache
Write-Host "`n=== Test 4: HazardAgent Cache ===" -ForegroundColor Cyan
$cache = Test-Endpoint -Name "Hazard Cache Debug" -Url "$API_BASE/api/debug/hazard-cache"
if ($cache) {
    Write-Host "`nCache Sizes:" -ForegroundColor Yellow
    Write-Host "  Flood Data: $($cache.cache_sizes.flood)" -ForegroundColor $(if ($cache.cache_sizes.flood -gt 0) { "Green" } else { "Red" })
    Write-Host "  Scout Reports: $($cache.cache_sizes.scout)" -ForegroundColor $(if ($cache.cache_sizes.scout -gt 0) { "Green" } else { "Yellow" })
    Write-Host "`nSimulation Clock: $($cache.simulation_manager_state.simulation_clock)s" -ForegroundColor Gray

    if ($cache.cache_sizes.scout -eq 0) {
        Write-Host "`n⚠️  WARNING: No scout reports in cache yet" -ForegroundColor Yellow
        Write-Host "   Scout events start at 5s. Current clock: $($cache.simulation_manager_state.simulation_clock)s" -ForegroundColor Gray
        Write-Host "   If clock > 5s and still no reports, check backend logs for 'Scout report collected' messages" -ForegroundColor Gray
    }
}

# Test 5: Check scout reports endpoint
Write-Host "`n=== Test 5: Scout Reports API ===" -ForegroundColor Cyan
$reports = Test-Endpoint -Name "Scout Reports" -Url "$API_BASE/api/agents/scout/reports?limit=50&hours=24"
if ($reports) {
    Write-Host "`nTotal Reports: $($reports.total_reports)" -ForegroundColor $(if ($reports.total_reports -gt 0) { "Green" } else { "Red" })

    if ($reports.total_reports -gt 0) {
        Write-Host "`nSample Reports:" -ForegroundColor Yellow
        $reports.reports | Select-Object -First 3 | ForEach-Object {
            Write-Host "  - $($_.location): Severity $($_.severity) - $($_.text.Substring(0, [Math]::Min(50, $_.text.Length)))..." -ForegroundColor Gray
        }
    } else {
        Write-Host "`n❌ No reports available" -ForegroundColor Red
        Write-Host "   Possible causes:" -ForegroundColor Yellow
        Write-Host "   1. Events not reaching their time_offset yet (wait longer)" -ForegroundColor Gray
        Write-Host "   2. CSV scenario file not loaded" -ForegroundColor Gray
        Write-Host "   3. Data flow issue in HazardAgent" -ForegroundColor Gray
    }
}

# Test 6: Check event queue
Write-Host "`n=== Test 6: Event Queue ===" -ForegroundColor Cyan
$events = Test-Endpoint -Name "Simulation Events Debug" -Url "$API_BASE/api/debug/simulation-events"
if ($events) {
    Write-Host "`nEvents Remaining: $($events.total_events_remaining)" -ForegroundColor Gray
    Write-Host "Upcoming Scout Events:" -ForegroundColor Yellow
    $events.upcoming_events | Where-Object { $_.agent -eq "scout_agent" } | Select-Object -First 3 | ForEach-Object {
        Write-Host "  - Time: $($_.time_offset)s, Location: $($_.payload.location)" -ForegroundColor Gray
    }
}

# Test 7: Test STOP simulation fix (the critical fix)
Write-Host "`n=== Test 7: Stop Simulation (Critical Fix Test) ===" -ForegroundColor Cyan
$stop = Test-Endpoint -Name "Stop Simulation" -Url "$API_BASE/api/simulation/stop" -Method "POST"
if ($stop -and $stop.state -eq "paused") {
    Write-Host "✅ STOP FIX WORKING! Simulation stopped successfully" -ForegroundColor Green
} else {
    Write-Host "❌ STOP FIX FAILED!" -ForegroundColor Red
}

# Test 8: Verify stopped state
Write-Host "`n=== Test 8: Verify Stopped State ===" -ForegroundColor Cyan
$finalStatus = Test-Endpoint -Name "Final Status Check" -Url "$API_BASE/api/simulation/status"
if ($finalStatus) {
    Write-Host "Final State: $($finalStatus.state)" -ForegroundColor $(if ($finalStatus.state -eq "paused") { "Green" } else { "Red" })
}

# Summary
Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

$stopWorking = $stop -and $stop.state -eq "paused"
$dataFlowing = $reports -and $reports.total_reports -gt 0

Write-Host "`n✅ Stop Simulation Fix: $(if ($stopWorking) { 'WORKING' } else { 'FAILED' })" -ForegroundColor $(if ($stopWorking) { "Green" } else { "Red" })
Write-Host "$(if ($dataFlowing) { '✅' } else { '❌' }) Scout Data Flow: $(if ($dataFlowing) { 'WORKING' } else { 'NO DATA' })" -ForegroundColor $(if ($dataFlowing) { "Green" } else { "Red" })

if (-not $dataFlowing) {
    Write-Host "`n⚠️  Data Flow Issue Detected" -ForegroundColor Yellow
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Check backend terminal logs for 'Scout report collected' messages" -ForegroundColor Gray
    Write-Host "2. Verify medium_scenario.csv exists in masfro-backend/app/data/simulation_scenarios/" -ForegroundColor Gray
    Write-Host "3. Check simulation clock is advancing (current: $($cache.simulation_manager_state.simulation_clock)s)" -ForegroundColor Gray
    Write-Host "4. Review SIMULATION_CRITICAL_FIXES.md for detailed troubleshooting" -ForegroundColor Gray
}

Write-Host "`nTest completed at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
