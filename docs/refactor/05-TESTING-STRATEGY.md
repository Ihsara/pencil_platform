# Testing Strategy: Side-by-Side Comparison

**Version**: 2.0  
**Last Updated**: 2025-11-14

This document outlines the side-by-side comparison testing strategy for the refactoring work. All refactor work will be done on a separate branch and tested against the working norm branch.

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Two-Directory Setup](#two-directory-setup)
3. [Comparison Testing Workflow](#comparison-testing-workflow)
4. [What to Compare](#what-to-compare)
5. [Test Execution](#test-execution)
6. [Success Criteria](#success-criteria)

---

## Testing Philosophy

### NO UNITTEST - Direct Comparison Only

```
┌─────────────────────────────────────────┐
│  NORM BRANCH (Benchmark/Working)        │
│  Directory: platform/                   │
│  Branch: norm                           │
│  Status: Known working state            │
└─────────────────────────────────────────┘
              ↓
         COMPARISON
              ↓
┌─────────────────────────────────────────┐
│  REFACTOR BRANCH (New Implementation)   │
│  Directory: platform_refactor/          │
│  Branch: refactor                       │
│  Status: Under development              │
└─────────────────────────────────────────┘
```

### Key Principles

1. **Real Execution**: Run actual workflows, not mocked tests
2. **Side-by-Side**: Compare outputs from norm vs refactor branches
3. **Same Inputs**: Use identical configuration (shocktube_phase1)
4. **Observable Outputs**: Compare logs, terminal output, generated files
5. **No Mocking**: Test the actual system behavior

### Why This Approach?

**PROBLEM with unittest**:
- Mocks don't reflect real behavior
- False confidence from passing tests
- Doesn't validate actual system integration
- Refactoring breaks tests unnecessarily

**SOLUTION with side-by-side comparison**:
- ✅ Tests REAL system behavior
- ✅ Validates actual outputs
- ✅ Catches integration issues
- ✅ Shows exactly where behavior differs
- ✅ No test maintenance overhead

---

## Two-Directory Setup

### Directory Structure

```
G:/study/bachelor/thesis/
├── platform/                    # NORM BRANCH (benchmark)
│   ├── .git/
│   ├── main.py
│   ├── src/
│   ├── config/
│   ├── logs/
│   └── runs/
│
└── platform_refactor/           # REFACTOR BRANCH (testing)
    ├── .git/
    ├── main.py
    ├── src/
    ├── config/
    ├── logs/
    └── runs/
```

### Setup Commands

```powershell
# Navigate to parent directory
cd G:/study/bachelor/thesis/

# Clone repository for refactor work
git clone git@github.com:Ihsara/pencil_platform.git platform_refactor

# Switch refactor directory to refactor branch
cd platform_refactor
git checkout refactor

# Verify setup
cd ..
ls -la
# Should see both platform/ and platform_refactor/
```

### Branch Verification

```powershell
# Check norm branch
cd platform
git branch  # Should show: * norm

# Check refactor branch  
cd ../platform_refactor
git branch  # Should show: * refactor
```

---

## Comparison Testing Workflow

### Complete Testing Cycle

```
1. RUN on NORM branch
   └─> python main.py shocktube_phase1 -mw
       └─> Capture: logs, terminal output, artifacts

2. RUN on REFACTOR branch
   └─> python main.py shocktube_phase1 -mw
       └─> Capture: logs, terminal output, artifacts

3. COMPARE outputs
   └─> Side-by-side analysis
       ├─> Terminal output format
       ├─> Log file contents
       ├─> Generated file structure
       ├─> Execution behavior
       └─> Error handling

4. VALIDATE changes
   └─> Are differences intentional?
   └─> Does refactor improve behavior?
   └─> Are there regressions?
```

### Manual Comparison Process

#### Step 1: Run NORM Branch

```powershell
# Terminal 1: NORM branch
cd G:/study/bachelor/thesis/platform
git checkout norm
git pull origin norm

# Clear old data
Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue

# Run workflow
python main.py shocktube_phase1 -mw 2>&1 | Tee-Object -FilePath "comparison_norm_output.txt"

# Terminal output is saved to: comparison_norm_output.txt
# Logs are in: logs/submission/shocktube_phase1/
```

#### Step 2: Run REFACTOR Branch

```powershell
# Terminal 2: REFACTOR branch
cd G:/study/bachelor/thesis/platform_refactor
git checkout refactor
git pull origin refactor

# Clear old data
Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue

# Run workflow (same command)
python main.py shocktube_phase1 -mw 2>&1 | Tee-Object -FilePath "comparison_refactor_output.txt"

# Terminal output is saved to: comparison_refactor_output.txt
# Logs are in: logs/submission/shocktube_phase1/
```

#### Step 3: Compare Outputs

```powershell
# Compare terminal outputs side by side
code --diff platform/comparison_norm_output.txt platform_refactor/comparison_refactor_output.txt

# Compare log directories
code --diff platform/logs/submission/shocktube_phase1 platform_refactor/logs/submission/shocktube_phase1

# Compare generated run directories
code --diff platform/runs/shocktube_phase1 platform_refactor/runs/shocktube_phase1
```

---

## What to Compare

### 1. Terminal Output

**What to check**:
- Console formatting and display
- Progress indicators
- Warning/error messages
- Status updates
- Final summary

**Example comparison**:
```
NORM:                              REFACTOR:
═══ STARTING WORKFLOW ═══          ═══ STARTING WORKFLOW ═══
→ Generating runs...               → Generating runs...
  [1/2] 50%                          [1/2] 50% 
  [2/2] 100%                         [2/2] 100%
✓ Complete                         ✓ Complete
```

**Questions to ask**:
- Is the output more clear/readable in refactor?
- Are all necessary messages present?
- Are errors properly displayed?

### 2. Log Files

**What to check**:
```
logs/submission/shocktube_phase1/
├── sub_YYYYMMDDHHMMSS/
│   ├── submission.log          # Job submission logs
│   ├── generation.log          # Run generation logs
│   └── [job_id]/
│       ├── pc_build.log        # Build logs
│       ├── pc_start.log        # Start logs
│       └── pc_run.log          # Execution logs
```

**Comparison checklist**:
- [ ] Log files created in same locations
- [ ] Log content captures same information
- [ ] Timestamps reasonable
- [ ] Error messages clear and actionable
- [ ] No missing log entries

### 3. Generated Artifacts

**What to check**:
```
runs/shocktube_phase1/
├── res400_nohyper_..._nu0p1_chi0p1_diffrho0p1/
│   ├── run.in
│   ├── start.in
│   ├── print.in
│   ├── src/
│   └── ...
├── res400_nohyper_..._nu0p5_chi0p5_diffrho0p5/
│   └── ...
```

**Comparison checklist**:
- [ ] Same number of run directories created
- [ ] Directory naming matches pattern
- [ ] File contents are correct
- [ ] Parameter values properly substituted
- [ ] No missing or extra files

### 4. Execution Behavior

**What to check**:
- Execution speed (should be similar)
- Memory usage (should be similar)
- Error handling (should be improved or same)
- Recovery from failures
- Clean termination

### 5. Configuration Parsing

**What to check**:
- Config files loaded correctly
- Parameter sweeps interpreted properly
- Paths resolved correctly
- Environment detection works
- Module loading sequences

---

## Test Execution

### Daily Development Workflow

```powershell
# Morning: Sync both branches
cd G:/study/bachelor/thesis/platform
git pull origin norm

cd G:/study/bachelor/thesis/platform_refactor
git pull origin refactor

# Make changes in refactor branch
cd G:/study/bachelor/thesis/platform_refactor
# ... edit files ...
git add .
git commit -m "Refactor: describe changes"
git push origin refactor

# Test changes
./test_comparison.ps1  # See script below
```

### Automated Comparison Script

Create `test_comparison.ps1` in parent directory:

```powershell
# test_comparison.ps1
# Side-by-side comparison test for refactor work

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$comparison_dir = "comparisons/run_$timestamp"

Write-Host "═══ Starting Comparison Test ═══" -ForegroundColor Cyan
Write-Host "Timestamp: $timestamp" -ForegroundColor Gray

# Create comparison directory
New-Item -ItemType Directory -Path $comparison_dir -Force | Out-Null

# Test NORM branch
Write-Host "`n→ Testing NORM branch..." -ForegroundColor Yellow
cd platform
git checkout norm 2>&1 | Out-Null

# Clean and run
Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue

$norm_start = Get-Date
python main.py shocktube_phase1 -mw 2>&1 | Tee-Object -FilePath "../$comparison_dir/norm_output.txt"
$norm_duration = (Get-Date) - $norm_start

# Copy logs
Copy-Item -Path "logs/submission/shocktube_phase1" -Destination "../$comparison_dir/norm_logs" -Recurse -Force -ErrorAction SilentlyContinue

# Test REFACTOR branch
Write-Host "`n→ Testing REFACTOR branch..." -ForegroundColor Yellow
cd ../platform_refactor
git checkout refactor 2>&1 | Out-Null

# Clean and run
Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force -ErrorAction SilentlyContinue

$refactor_start = Get-Date
python main.py shocktube_phase1 -mw 2>&1 | Tee-Object -FilePath "../$comparison_dir/refactor_output.txt"
$refactor_duration = (Get-Date) - $refactor_start

# Copy logs
Copy-Item -Path "logs/submission/shocktube_phase1" -Destination "../$comparison_dir/refactor_logs" -Recurse -Force -ErrorAction SilentlyContinue

# Generate comparison report
cd ..
$report = @"
═══════════════════════════════════════════════════════════
COMPARISON TEST REPORT
═══════════════════════════════════════════════════════════
Timestamp: $timestamp

EXECUTION TIME:
  NORM:     $($norm_duration.TotalSeconds)s
  REFACTOR: $($refactor_duration.TotalSeconds)s
  Diff:     $([math]::Round($refactor_duration.TotalSeconds - $norm_duration.TotalSeconds, 2))s

OUTPUTS SAVED TO:
  Terminal outputs:
    - $comparison_dir/norm_output.txt
    - $comparison_dir/refactor_output.txt
  
  Logs:
    - $comparison_dir/norm_logs/
    - $comparison_dir/refactor_logs/

NEXT STEPS:
  1. Review terminal outputs side by side
  2. Compare log files
  3. Verify generated artifacts
  4. Document any differences

To view diffs:
  code --diff $comparison_dir/norm_output.txt $comparison_dir/refactor_output.txt
  
═══════════════════════════════════════════════════════════
"@

$report | Tee-Object -FilePath "$comparison_dir/REPORT.txt"

Write-Host "`n✓ Comparison complete!" -ForegroundColor Green
Write-Host "Results saved to: $comparison_dir" -ForegroundColor Gray
```

### Running Comparisons

```powershell
# Run full comparison
./test_comparison.ps1

# Review results
cd comparisons/run_YYYYMMDD_HHMMSS/
cat REPORT.txt

# Visual diff of outputs
code --diff norm_output.txt refactor_output.txt

# Compare logs
code --diff norm_logs/ refactor_logs/
```

---

## Success Criteria

### Refactor is Successful When:

1. **Functional Equivalence**
   - [ ] Same runs generated
   - [ ] Same parameters configured
   - [ ] Same job submissions
   - [ ] Same artifacts created

2. **Output Quality**
   - [ ] Terminal output clear and informative
   - [ ] Logs complete and structured
   - [ ] Error messages actionable
   - [ ] Progress tracking visible

3. **Performance**
   - [ ] Execution time within 10% of norm
   - [ ] Memory usage reasonable
   - [ ] No unnecessary file I/O
   - [ ] Efficient config loading

4. **Code Quality**
   - [ ] Better abstraction and modularity
   - [ ] Clearer separation of concerns
   - [ ] More maintainable structure
   - [ ] Improved error handling

5. **Backwards Compatibility**
   - [ ] Same CLI interface
   - [ ] Same configuration files work
   - [ ] Same directory structure
   - [ ] No breaking changes for users

### Red Flags (Must Fix)

❌ **BLOCKING ISSUES**:
- Different number of runs generated
- Missing or corrupted artifacts
- Crashes or unhandled exceptions
- Wrong parameter values
- Missing log entries
- Significantly slower execution (>20%)

⚠️ **WARNING ISSUES** (Should fix but not blocking):
- Different log formatting
- Changed terminal colors/layout
- Different info/debug message wording
- Minor timing differences

✅ **ACCEPTABLE DIFFERENCES**:
- Improved error messages
- Better progress display
- More informative logging
- Clearer terminal output
- Better structured code

---

## Example Comparison Session

### Scenario: Testing Communication Refactor

```powershell
# 1. Run comparison
./test_comparison.ps1

# Output shows:
# ═══ Starting Comparison Test ═══
# → Testing NORM branch...
# → Testing REFACTOR branch...
# ✓ Comparison complete!

# 2. Review report
cd comparisons/run_20251114_132400/
cat REPORT.txt

# Shows:
# EXECUTION TIME:
#   NORM:     45.3s
#   REFACTOR: 46.1s
#   Diff:     +0.8s

# 3. Compare terminal outputs
code --diff norm_output.txt refactor_output.txt

# Visual diff shows:
# NORM:                          REFACTOR:
# INFO: Generating runs...        ═══ GENERATING RUNS ═══
#                                → Processing sweep...
#                                  [1/2] 50%
#                                  [2/2] 100%
#                                ✓ Generated 2 runs

# 4. Check logs
diff norm_logs/submission.log refactor_logs/submission.log

# 5. Verify artifacts
diff -r ../platform/runs/shocktube_phase1 ../platform_refactor/runs/shocktube_phase1

# 6. Decision
# ✅ APPROVED: Refactor improves terminal output clarity
#              No functional changes
#              Acceptable +0.8s timing difference
```

---

## Documentation Requirements

### For Each Refactor Commit

Document in commit message:
```
Refactor: [Brief description]

Changes:
- What was changed
- Why it was changed
- Impact on behavior

Testing:
- Comparison test timestamp: YYYYMMDD_HHMMSS
- Result: PASS/FAIL
- Notable differences: [if any]

Regression Check:
- [ ] Same functionality
- [ ] Performance acceptable
- [ ] Logs complete
- [ ] Artifacts correct
```

### Comparison Test Log

Maintain `docs/refactor/COMPARISON_LOG.md`:

```markdown
# Refactor Comparison Test Log

## 2025-11-14: Communication Architecture Refactor

**Branch**: refactor
**Commit**: abc123def
**Test Run**: comparisons/run_20251114_132400/

**Changes**: Reorganized communication layer into subfolder

**Results**:
- ✅ Functional equivalence confirmed
- ✅ Terminal output improved
- ✅ Performance: +0.8s (acceptable)
- ✅ All artifacts match

**Decision**: APPROVED for merge

---

## [Next refactor session]
...
```

---

## Final Checklist Before Merge

Before merging refactor branch to norm:

- [ ] Run full comparison test
- [ ] Review all differences
- [ ] Verify no regressions
- [ ] Check performance impact
- [ ] Update documentation
- [ ] Test on HPC (if applicable)
- [ ] Get peer review of comparison results
- [ ] Document changes in COMPARISON_LOG.md

---

## Summary

**NO UNITTEST. Only side-by-side comparison.**

This approach:
- ✅ Tests real system behavior
- ✅ Validates actual integration
- ✅ Shows exact differences
- ✅ No test maintenance
- ✅ Clear success criteria
- ✅ Fast feedback loop

Always test with: `python main.py shocktube_phase1 -mw`

Compare everything: terminal output, logs, artifacts, behavior.

**Completion**: Testing strategy updated for side-by-side comparison approach!
