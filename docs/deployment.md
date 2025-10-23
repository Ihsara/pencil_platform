# Deployment Guide

This guide covers deploying and running the Pencil Code Automated Experiment Manager on HPC systems.

## Overview

The platform is designed to run directly on HPC systems where simulations execute. This architecture ensures:

- Direct access to simulation output files
- Real-time job monitoring capabilities
- Efficient file I/O operations
- Proper log file access

## Prerequisites

- SSH access to your HPC cluster
- Python 3.13+ installed on the cluster
- SLURM workload manager
- Sufficient storage quota for simulation data

## Initial Setup

### 1. Connect to HPC

```bash
ssh username@your-hpc-cluster.edu
```

### 2. Clone Repository

```bash
cd /path/to/your/scratch/space
git clone <repository-url>
cd platform
```

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 4. Configure for Your Cluster

Edit SLURM settings in your experiment's `sweep.yaml`:

```yaml
slurm:
  account: "your_project_account"
  partition: "compute"
  time: "01:00:00"
  nodes: 1
  ntasks_per_node: 40
```

## Running Experiments

### Basic Workflow

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Test configuration (generates 2 runs without submission)
python main.py my_experiment --test

# 3. Review generated files
ls runs/my_experiment/generated_configs/

# 4. Submit full experiment
python main.py my_experiment

# 5. Monitor progress
python main.py my_experiment --monitor

# 6. Check status
python main.py my_experiment --check
```

### Automated Workflow

For fully automated execution:

```bash
# Submit, wait for completion, then analyze
python main.py my_experiment --wait --analyze
```

## Job Monitoring

### Why Run on HPC

The monitoring system requires access to log files created by running jobs:

- **Logs location**: HPC filesystem (`/scratch/project_*/...`)
- **Monitoring reads**: Log files in real-time
- **Job queries**: SLURM commands (`squeue`, `sacct`)

Running from a local machine will cause monitoring to fail because:
- Log files are not accessible remotely
- SLURM commands are not available
- File paths differ between systems

### Monitoring Commands

```bash
# Quick SLURM status
python main.py my_experiment --check

# Detailed progress with iteration counts
python main.py my_experiment --monitor

# Wait for job completion
python main.py my_experiment --wait
```

## File System Layout

### Recommended Structure

```
/scratch/project_XXXXX/username/
├── pencil_platform/          # Platform installation
│   ├── src/
│   ├── config/
│   ├── docs/
│   └── main.py
├── runs/                     # Generated configurations (symlink or subdir)
│   └── my_experiment/
│       ├── generated_configs/
│       └── submit_jobs.sh
└── simulations/              # Actual simulation output
    └── my_experiment/
        ├── run_001/
        ├── run_002/
        └── ...
```

### Storage Considerations

- **Scratch space**: Fast, temporary storage for active simulations
- **Project space**: Long-term storage for results
- **Home directory**: Small quota, use only for code

Configure output paths in `sweep.yaml`:

```yaml
output_base_dir: "/scratch/project_XXXXX/username/simulations/my_experiment"
run_base_dir: "/scratch/project_XXXXX/username/simulations/my_experiment"
```

## Best Practices

### Development Workflow

1. **Edit locally**: Modify code and configurations on your local machine
2. **Commit changes**: Use version control (git)
3. **Push to remote**: Push changes to repository
4. **Pull on HPC**: SSH to HPC and pull latest changes
5. **Run on HPC**: Execute all generation, submission, and monitoring on HPC

### Resource Management

```bash
# Check your quota
quota -s

# Check running jobs
squeue -u $USER

# Check completed jobs
sacct -u $USER --starttime=today

# Cancel jobs if needed
scancel <job_id>
```

### Long-Running Sessions

Use `screen` or `tmux` for persistent sessions:

```bash
# Start screen session
screen -S experiment

# Run your command
python main.py my_experiment --wait --analyze

# Detach: Ctrl+A, then D

# Reattach later
screen -r experiment
```

## Troubleshooting

### "Cannot find SLURM commands"

**Solution**: Ensure you're on a login node or compute node with SLURM access.

```bash
# Test SLURM availability
which sbatch
squeue --version
```

### "Permission denied" for directories

**Solution**: Check directory permissions and ownership.

```bash
# Check permissions
ls -ld /scratch/project_XXXXX/username

# Fix if needed
chmod 755 /path/to/directory
```

### "No space left on device"

**Solution**: Check and clean up storage.

```bash
# Check quota
quota -s

# Find large directories
du -sh /scratch/project_XXXXX/username/* | sort -h

# Clean up old runs
rm -rf runs/old_experiment/
```

### "Module not found" errors

**Solution**: Ensure virtual environment is activated.

```bash
# Verify environment
which python  # Should show .venv/bin/python

# Reinstall if needed
pip install -e . --force-reinstall
```

## Cluster-Specific Configuration

### SLURM Parameters

Common SLURM parameters to adjust:

```yaml
slurm:
  account: "project_account"    # Your allocation
  partition: "standard"          # Queue name
  time: "04:00:00"              # Wall time (HH:MM:SS)
  nodes: 1                       # Number of nodes
  ntasks_per_node: 40           # Tasks per node
  mem_per_cpu: "2G"             # Memory per CPU
  mail_type: "END,FAIL"         # Email notifications
  mail_user: "your@email.com"   # Your email
```

### Common Partition Names

- **debug/test**: Quick turnaround, limited time
- **standard/normal**: General purpose queue
- **large/bigmem**: High memory jobs
- **gpu**: GPU-accelerated jobs
- **long**: Extended wall time

Consult your cluster's documentation for specific partition details.

## Security Considerations

### File Permissions

```bash
# Set appropriate permissions for generated configs
chmod 750 runs/my_experiment/

# Protect sensitive configuration files
chmod 600 config/*/plan/sweep.yaml
```

### SSH Keys

Use SSH keys for authentication:

```bash
# Generate key (if not exists)
ssh-keygen -t ed25519

# Copy to HPC
ssh-copy-id username@your-hpc-cluster.edu
```

## Additional Resources

- [HPC Cluster Documentation](https://your-cluster-docs.edu)
- [SLURM Documentation](https://slurm.schedmd.com/)
- [Job Monitoring Guide](job-monitoring.md)
- [Troubleshooting Guide](troubleshooting.md)

## Quick Reference

| Task | Command |
|------|---------|
| Submit experiment | `python main.py <experiment>` |
| Test configuration | `python main.py <experiment> --test` |
| Check job status | `python main.py <experiment> --check` |
| Monitor progress | `python main.py <experiment> --monitor` |
| Wait for completion | `python main.py <experiment> --wait` |
| Run analysis | `python main.py <experiment> --analyze` |
| Full automation | `python main.py <experiment> --wait --analyze` |
