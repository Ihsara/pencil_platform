# test_comparison.ps1
# Side-by-side comparison test for refactor work
# 
# This script runs the same workflow on both the norm branch (benchmark)
# and the refactor branch, capturing outputs for comparison.
#
# Usage: ./test_comparison.ps1
# Location: Should be in G:/study/bachelor/thesis/ (parent directory)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$comparison_dir = "comparisons/run_$timestamp"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "       SIDE-BY-SIDE COMPARISON TEST" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Timestamp: $timestamp" -ForegroundColor Gray
Write-Host ""

# Create comparison directory
New-Item -ItemType Directory -Path $comparison_dir -Force | Out-Null
Write-Host "→ Created comparison directory: $comparison_dir" -ForegroundColor Green

# ============================================================================
# Test NORM branch (benchmark)
# ============================================================================

Write-Host ""
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host "  TESTING NORM BRANCH (Benchmark)" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Yellow

try {
    cd platform
    
    # Verify branch
    $current_branch = git branch --show-current
    if ($current_branch -ne "norm") {
        Write-Host "→ Switching to norm branch..." -ForegroundColor Gray
        git checkout norm 2>&1 | Out-Null
    }
    
    Write-Host "✓ On branch: norm" -ForegroundColor Green
    
    # Pull latest
    Write-Host "→ Pulling latest changes..." -ForegroundColor Gray
    git pull origin norm 2>&1 | Out-Null
    
    # Clean old data
    Write-Host "→ Cleaning old data..." -ForegroundColor Gray
    Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
    
    # Run workflow
    Write-Host "→ Running: python main.py shocktube_phase1 -mw" -ForegroundColor Cyan
    $norm_start = Get-Date
    python main.py shocktube_phase1 -mw 2>&1 | Tee-Object -FilePath "../$comparison_dir/norm_output.txt"
    $norm_duration = (Get-Date) - $norm_start
    
    Write-Host "✓ NORM execution completed in $([math]::Round($norm_duration.TotalSeconds, 2))s" -ForegroundColor Green
    
    # Copy logs
    if (Test-Path "logs/submission/shocktube_phase1") {
        Copy-Item -Path "logs/submission/shocktube_phase1" -Destination "../$comparison_dir/norm_logs" -Recurse -Force
        Write-Host "✓ Logs copied to comparison directory" -ForegroundColor Green
    }
    
    # Copy generated runs (if exist)
    if (Test-Path "runs/shocktube_phase1") {
        Copy-Item -Path "runs/shocktube_phase1" -Destination "../$comparison_dir/norm_runs" -Recurse -Force
        Write-Host "✓ Run artifacts copied to comparison directory" -ForegroundColor Green
    }
    
    cd ..
}
catch {
    Write-Host "✗ ERROR in NORM branch execution: $_" -ForegroundColor Red
    cd ..
    exit 1
}

# ============================================================================
# Test REFACTOR branch
# ============================================================================

Write-Host ""
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host "  TESTING REFACTOR BRANCH (New Implementation)" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Yellow

try {
    # Check if refactor directory exists
    if (-not (Test-Path "platform_refactor")) {
        Write-Host "✗ platform_refactor directory not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please set up the refactor directory first:" -ForegroundColor Yellow
        Write-Host "  cd G:/study/bachelor/thesis/" -ForegroundColor Gray
        Write-Host "  git clone git@github.com:Ihsara/pencil_platform.git platform_refactor" -ForegroundColor Gray
        Write-Host "  cd platform_refactor" -ForegroundColor Gray
        Write-Host "  git checkout refactor" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
    
    cd platform_refactor
    
    # Verify branch
    $current_branch = git branch --show-current
    if ($current_branch -ne "refactor") {
        Write-Host "→ Switching to refactor branch..." -ForegroundColor Gray
        git checkout refactor 2>&1 | Out-Null
    }
    
    Write-Host "✓ On branch: refactor" -ForegroundColor Green
    
    # Pull latest
    Write-Host "→ Pulling latest changes..." -ForegroundColor Gray
    git pull origin refactor 2>&1 | Out-Null
    
    # Clean old data
    Write-Host "→ Cleaning old data..." -ForegroundColor Gray
    Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
    
    # Run workflow
    Write-Host "→ Running: python main.py shocktube_phase1 -mw" -ForegroundColor Cyan
    $refactor_start = Get-Date
    python main.py shocktube_phase1 -mw 2>&1 | Tee-Object -FilePath "../$comparison_dir/refactor_output.txt"
    $refactor_duration = (Get-Date) - $refactor_start
    
    Write-Host "✓ REFACTOR execution completed in $([math]::Round($refactor_duration.TotalSeconds, 2))s" -ForegroundColor Green
    
    # Copy logs
    if (Test-Path "logs/submission/shocktube_phase1") {
        Copy-Item -Path "logs/submission/shocktube_phase1" -Destination "../$comparison_dir/refactor_logs" -Recurse -Force
        Write-Host "✓ Logs copied to comparison directory" -ForegroundColor Green
    }
    
    # Copy generated runs (if exist)
    if (Test-Path "runs/shocktube_phase1") {
        Copy-Item -Path "runs/shocktube_phase1" -Destination "../$comparison_dir/refactor_runs" -Recurse -Force
        Write-Host "✓ Run artifacts copied to comparison directory" -ForegroundColor Green
    }
    
    cd ..
}
catch {
    Write-Host "✗ ERROR in REFACTOR branch execution: $_" -ForegroundColor Red
    cd ..
    exit 1
}

# ============================================================================
# Generate comparison report
# ============================================================================

Write-Host ""
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  GENERATING COMPARISON REPORT" -ForegroundColor Cyan
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Cyan

$time_diff = [math]::Round($refactor_duration.TotalSeconds - $norm_duration.TotalSeconds, 2)
$time_diff_percent = [math]::Round(($time_diff / $norm_duration.TotalSeconds) * 100, 1)

$report = @"
═══════════════════════════════════════════════════════════
           COMPARISON TEST REPORT
═══════════════════════════════════════════════════════════
Timestamp: $timestamp
Test Command: python main.py shocktube_phase1 -mw

───────────────────────────────────────────────────────────
EXECUTION TIME:
───────────────────────────────────────────────────────────
  NORM branch:     $([math]::Round($norm_duration.TotalSeconds, 2))s
  REFACTOR branch: $([math]::Round($refactor_duration.TotalSeconds, 2))s
  
  Difference:      $time_diff s ($time_diff_percent%)
  
  Status: $(if ([math]::Abs($time_diff_percent) -le 10) { "✓ ACCEPTABLE (<10%)" } elseif ([math]::Abs($time_diff_percent) -le 20) { "⚠ WARNING (10-20%)" } else { "✗ CONCERNING (>20%)" })

───────────────────────────────────────────────────────────
OUTPUTS SAVED TO: $comparison_dir/
───────────────────────────────────────────────────────────
  Terminal outputs:
    • norm_output.txt       (NORM branch terminal output)
    • refactor_output.txt   (REFACTOR branch terminal output)
  
  Logs:
    • norm_logs/            (NORM branch logs)
    • refactor_logs/        (REFACTOR branch logs)
  
  Generated artifacts:
    • norm_runs/            (NORM branch run directories)
    • refactor_runs/        (REFACTOR branch run directories)

───────────────────────────────────────────────────────────
NEXT STEPS:
───────────────────────────────────────────────────────────
1. Review terminal outputs side by side:
   code --diff $comparison_dir/norm_output.txt $comparison_dir/refactor_output.txt

2. Compare log contents:
   code --diff $comparison_dir/norm_logs $comparison_dir/refactor_logs

3. Compare generated run directories:
   code --diff $comparison_dir/norm_runs $comparison_dir/refactor_runs

4. Manual checks:
   [ ] Same number of runs generated
   [ ] Same parameter values in run configs
   [ ] Log files complete and correctly formatted
   [ ] Terminal output clear and informative
   [ ] No crashes or errors
   [ ] No missing artifacts

5. Document findings in:
   platform/docs/refactor/COMPARISON_LOG.md

───────────────────────────────────────────────────────────
ACCEPTANCE CRITERIA:
───────────────────────────────────────────────────────────
  Functional Equivalence:
  [ ] Same runs generated
  [ ] Same parameters configured
  [ ] Same job submissions
  [ ] Same artifacts created
  
  Performance:
  [ ] Execution time within 10% of norm
  [ ] No excessive memory usage
  
  Quality:
  [ ] Terminal output clear/improved
  [ ] Logs complete and structured
  [ ] Error messages actionable
  
  Code:
  [ ] Better abstraction
  [ ] Improved maintainability
  [ ] No breaking changes

═══════════════════════════════════════════════════════════
"@

# Save report
$report | Tee-Object -FilePath "$comparison_dir/REPORT.txt"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ COMPARISON TEST COMPLETE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Results saved to: $comparison_dir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick diff view:" -ForegroundColor Yellow
Write-Host "  code --diff $comparison_dir/norm_output.txt $comparison_dir/refactor_output.txt" -ForegroundColor Gray
Write-Host ""
