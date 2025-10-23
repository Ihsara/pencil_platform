# Job Monitoring Guide

This guide explains how to monitor the progress of submitted HPC jobs using the enhanced monitoring features.

## Overview

The platform now provides detailed monitoring of job progress by examining log files from each stage of the simulation:

1. **Build Stage** (`pc_build.log`) - Code compilation
2. **Start Stage** (`pc_start.log`) - Initial condition setup
3. **Run Stage** (`pc_run.log`) - Main simulation execution with iteration tracking

## Workflow Options

### Option 1: Manual Workflow (Submit, then Monitor Separately)

1. **Submit the job**:
   ```bash
   python main.py <experiment_name>
   ```

2. **Monitor the job** (using one of the commands below)

### Option 2: Automated Workflow (Submit + Wait + Analyze)

Use the convenient `-wa` or `-mwa` shorthand for a fully automated workflow:

```bash
# Submit, wait, and analyze when complete
python main.py <experiment_name> -wa

# Submit, wait with monitoring, and analyze when complete
python main.py <experiment_name> -mwa
```

This is equivalent to:
```bash
python main.py <experiment_name>           # Submit
python main.py <experiment_name> --wait    # Wait
python main.py <experiment_name> --analyze # Analyze
```

## Commands

### Basic Status Check

Check SLURM job status (PENDING, RUNNING, COMPLETED, FAILED):

```bash
python main.py <experiment_name> --check
```

### Detailed Progress Monitoring

Monitor detailed progress including current stage and iteration counts:

```bash
# Long form
python main.py <experiment_name> --monitor

# Short form
python main.py <experiment_name> -m
```

This command shows:
- Current stage for each array task (build/start/run/completed/failed)
- Latest iteration number for running simulations
- Last 5 lines of relevant log files
- Summary counts by stage

### Wait for Completion

Wait for job completion with periodic status updates:

```bash
# Long form
python main.py <experiment_name> --wait

# Short form  
python main.py <experiment_name> -w

# Wait and analyze
python main.py <experiment_name> -wa
```

**Note:** When using `--wait` or `-w` on an already-submitted job, it monitors that job. When used during submission (e.g., `python main.py <experiment_name> -w`), it submits first, then waits.

This will:
- Poll job status every 60 seconds
- Show detailed progress every 3rd poll
- Exit when all jobs complete or fail
- Optionally run analysis automatically with `-a` flag

### Shorthand Combinations

For convenience, flags can be combined:

```bash
# Monitor (standalone - for already submitted jobs)
python main.py <experiment_name> -m

# Submit + Wait
python main.py <experiment_name> -w

# Submit + Wait + Analyze (fully automated!)
python main.py <experiment_name> -wa

# Submit + Wait with detailed monitoring + Analyze
python main.py <experiment_name> -mwa
```

## Log File Structure

Logs are stored in:
```
logs/submission/<experiment_name>/sub_<timestamp>/<job_id>/array_<task_id>/
├── pc_build.log    # Build output (if rebuild mode)
├── pc_start.log    # Initial condition setup
└── pc_run.log      # Main simulation with iterations
```

## Stage Detection Logic

The monitoring system intelligently detects the current stage by:

1. **Checking for errors**: Scans all logs for ERROR/FATAL keywords
2. **Determining stage**: Based on which log files exist
3. **Extracting iterations**: Parses pc_run.log for iteration numbers
4. **Verifying completion**: Looks for success messages

## Example Output

### Monitor Command

```
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Task ┃ Run Name                ┃ Stage    ┃ Iteration ┃ Details                    ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1    │ res4000_nu5p0_chi5p0... │ run      │ 139000    │ Running iteration 139000   │
│ 2    │ res4000_nu1p0_chi1p0... │ run      │ 98000     │ Running iteration 98000    │
│ 3    │ res4000_nu0p5_chi0p5... │ start    │ -         │ Starting simulation        │
│ 4    │ res4000_nu0p1_chi0p1... │ build    │ -         │ Building code              │
└──────┴─────────────────────────┴──────────┴───────────┴────────────────────────────┘

Summary:
  Initializing: 0
  Building: 1
  Starting: 1
  Running: 2
  Completed: 0
  Failed: 0
```

## Troubleshooting

### No logs found

If monitoring shows "No submission logs found yet", the job may be:
- Still queuing (not started yet)
- Using a different job ID than expected
- Logs not created yet

Check basic status: `python main.py <experiment_name> --check`

### Misleading completion status

The old behavior would show "completed" immediately based on SLURM status alone. The new monitoring:
- Verifies actual progress through log files
- Shows accurate iteration counts
- Detects failures in any stage
- Provides real-time progress updates

### Log reading errors

If logs show "reading error", this usually means:
- File is being written to (try again in a few seconds)
- Permissions issue
- Corrupted log file

## Best Practices

1. **Use --monitor for detailed tracking**: Especially useful for long-running jobs
2. **Use --wait for automation**: Combine with --analyze for hands-off operation
3. **Check regularly**: Poll every few minutes during critical phases
4. **Examine failed jobs**: Use the log paths shown in error messages

## Integration with Analysis

After jobs complete, automatically run analysis:

```bash
# Wait and analyze
python main.py <experiment_name> --wait --analyze

# Or run analysis separately
python main.py <experiment_name> --analyze
```

## Performance Considerations

- Log file tailing is efficient (reads only last N lines)
- Monitoring doesn't impact running simulations
- Poll interval is configurable in the code (default: 60s)
- Detailed progress shown every 3rd poll to reduce output
