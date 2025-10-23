# Flag Combinations Reference

This document shows all valid flag combinations and their behavior.

## Standalone Modes (No Submission)

These commands work on already-submitted jobs or existing data:

### Monitoring Commands

```bash
# Quick SLURM status check
python main.py <experiment_name> --check

# Detailed progress monitoring (one-time)
python main.py <experiment_name> -m
python main.py <experiment_name> --monitor

# Wait for already-submitted job to complete
python main.py <experiment_name> -w
python main.py <experiment_name> --wait

# Wait and auto-analyze when done
python main.py <experiment_name> -wa
python main.py <experiment_name> --wait --analyze
```

### Analysis Commands

```bash
# Run video-only analysis
python main.py <experiment_name> -a
python main.py <experiment_name> --analyze

# Run L1/L2 error norm analysis
python main.py <experiment_name> --error-norms
```

### Visualization Commands

```bash
# Visualize all runs
python main.py <experiment_name> --viz

# Visualize specific runs
python main.py <experiment_name> --viz run1 run2

# Interactive visualization
python main.py <experiment_name> --viz ?
```

## Submission Modes

These commands generate configs and submit jobs to SLURM:

### Basic Submission

```bash
# Submit only
python main.py <experiment_name>

# Submit with rebuild
python main.py <experiment_name> --rebuild

# Test mode (no submission)
python main.py <experiment_name> --test
python main.py <experiment_name> --test 5  # Limit to 5 runs
```

### Automated Workflows

```bash
# Submit + Wait
python main.py <experiment_name> -w

# Submit + Wait + Analyze (fully automated!)
python main.py <experiment_name> -wa

# Submit + Wait with monitoring hint + Analyze
python main.py <experiment_name> -mwa
```

## Flag Behavior Summary

| Command | Submits? | Waits? | Analyzes? | Notes |
|---------|----------|--------|-----------|-------|
| `exp` | ✓ | ✗ | ✗ | Submit only |
| `exp --check` | ✗ | ✗ | ✗ | Quick status |
| `exp -m` | ✗ | ✗ | ✗ | Detailed monitoring |
| `exp -w` (standalone) | ✗ | ✓ | ✗ | Wait for existing job |
| `exp -wa` (standalone) | ✗ | ✓ | ✓ | Wait + analyze existing job |
| `exp -a` | ✗ | ✗ | ✓ | Analyze only |
| `exp -w` (submission) | ✓ | ✓ | ✗ | Submit then wait |
| `exp -wa` (submission) | ✓ | ✓ | ✓ | Submit + wait + analyze |
| `exp -mwa` (submission) | ✓ | ✓ | ✓ | Submit + wait + analyze (with monitoring hint) |
| `exp --viz` | ✗ | ✗ | ✗ | Visualize results |
| `exp --error-norms` | ✗ | ✗ | ✗ | Error norm analysis |

## Common Workflows

### Workflow 1: Submit and Come Back Later
```bash
# Submit
python main.py shocktube_phase1

# Later: Check status
python main.py shocktube_phase1 --check

# When ready: Analyze
python main.py shocktube_phase1 -a
```

### Workflow 2: Submit and Monitor
```bash
# Submit
python main.py shocktube_phase1

# Monitor progress (run in another terminal or later)
python main.py shocktube_phase1 -m
```

### Workflow 3: Fully Automated
```bash
# One command does everything!
python main.py shocktube_phase1 -wa
```

### Workflow 4: Test Then Submit
```bash
# Test first (generates 2 runs, no submission)
python main.py shocktube_phase1 --test

# If OK, submit for real
python main.py shocktube_phase1
```

## Advanced Examples

### Monitor Existing Job Continuously
```bash
# Start monitoring
python main.py exp -m

# In a loop (bash)
while true; do 
  python main.py exp -m
  sleep 60
done
```

### Submit Multiple Experiments
```bash
python main.py exp1 -wa &
python main.py exp2 -wa &
python main.py exp3 -wa &
# All submit, wait, and analyze in parallel
```

### Rerun Analysis Only
```bash
# If jobs completed but analysis failed or needs updating
python main.py exp -a
python main.py exp --error-norms
```

## Notes

1. **Context Awareness**: The system detects whether you're working with a standalone command (existing job) or a submission command based on flag combinations.

2. **Short vs Long**: Short flags (`-m`, `-w`, `-a`) can be combined (`-mwa`), while long flags (`--monitor`, `--wait`, `--analyze`) must be separate.

3. **Monitor Flag in Submission**: When using `-mwa` for submission, the `-m` flag serves as a reminder that you can monitor progress, but doesn't actually run continuous monitoring (which would block the wait process).

4. **Test Mode**: Using `--test` prevents actual submission regardless of other flags.
