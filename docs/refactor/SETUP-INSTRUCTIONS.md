# Refactor Testing Setup Instructions

This document provides step-by-step instructions for setting up the side-by-side comparison testing environment.

---

## Overview

The refactor testing strategy uses two separate directories:
- `platform/` - The **norm** branch (benchmark/working version)
- `platform_refactor/` - The **refactor** branch (new implementation under development)

Both directories are clones of the same repository but track different branches.

---

## Prerequisites

- Git configured with SSH access to the repository
- Python 3.11+ installed
- PowerShell (for running the comparison script)
- Visual Studio Code (optional, for diff viewing)

---

## Step 1: Verify Current Setup

First, check your current platform directory:

```powershell
cd G:/study/bachelor/thesis/platform

# Verify you're on the norm branch
git branch
# Should show: * norm

# Check that the refactor branch exists
git branch -a
# Should show: refactor and remotes/origin/refactor
```

---

## Step 2: Clone Repository for Refactor Work

Navigate to the parent directory and clone a second copy:

```powershell
# Go to parent directory
cd G:/study/bachelor/thesis/

# Clone the repository with a different name
git clone git@github.com:Ihsara/pencil_platform.git platform_refactor

# Expected output:
# Cloning into 'platform_refactor'...
# remote: Enumerating objects: ...
# Receiving objects: 100% ...
# Resolving deltas: 100% ...
```

---

## Step 3: Switch Refactor Directory to Refactor Branch

```powershell
cd platform_refactor

# Checkout the refactor branch
git checkout refactor

# Verify
git branch
# Should show: * refactor

# Pull latest changes
git pull origin refactor
```

---

## Step 4: Verify Directory Structure

Your directory structure should now look like this:

```
G:/study/bachelor/thesis/
├── platform/                    # NORM branch (benchmark)
│   ├── .git/
│   ├── main.py
│   ├── src/
│   ├── config/
│   ├── docs/
│   ├── test_comparison.ps1     # ← Comparison script should be HERE
│   └── ...
│
├── platform_refactor/           # REFACTOR branch (development)
│   ├── .git/
│   ├── main.py
│   ├── src/
│   ├── config/
│   ├── docs/
│   └── ...
│
└── comparisons/                 # Will be created automatically
    └── run_YYYYMMDD_HHMMSS/    # Comparison test results
```

---

## Step 5: Copy the Comparison Script

The `test_comparison.ps1` script should be in the **platform** directory (norm branch):

```powershell
# Make sure you're in the platform directory
cd G:/study/bachelor/thesis/platform

# Verify the script exists
ls test_comparison.ps1

# If it doesn't exist, it will be created when you commit the current changes
```

**Important**: The script expects to be run from the **parent directory** and will look for:
- `platform/` (norm branch)
- `platform_refactor/` (refactor branch)

---

## Step 6: Test the Setup

Run a quick verification:

```powershell
# From the parent directory
cd G:/study/bachelor/thesis/

# Check both directories exist
ls -d platform, platform_refactor

# Check branches
cd platform
git branch --show-current  # Should be: norm

cd ../platform_refactor
git branch --show-current  # Should be: refactor

cd ..
```

---

## Step 7: Run Your First Comparison Test

**NOTE**: The comparison script should be run from the **current platform directory**, not the parent directory!

```powershell
# Make sure you're in the platform directory
cd G:/study/bachelor/thesis/platform

# Run the comparison test
./test_comparison.ps1
```

The script will:
1. Test the norm branch (from `platform/`)
2. Test the refactor branch (from `../platform_refactor/`)
3. Generate a comparison report in `comparisons/run_YYYYMMDD_HHMMSS/`

---

## Daily Workflow

### Morning Setup

```powershell
# Sync both branches
cd G:/study/bachelor/thesis/platform
git pull origin norm

cd ../platform_refactor
git pull origin refactor
```

### Making Changes

All refactor work happens in `platform_refactor/`:

```powershell
cd G:/study/bachelor/thesis/platform_refactor

# Make your changes
# Edit files...

# Commit changes
git add .
git commit -m "Refactor: [description of changes]"
git push origin refactor
```

### Testing Changes

After making changes, run a comparison test:

```powershell
# From the platform directory (norm branch)
cd G:/study/bachelor/thesis/platform
./test_comparison.ps1

# Review results
cd comparisons/run_YYYYMMDD_HHMMSS/
cat REPORT.txt

# View diffs
code --diff norm_output.txt refactor_output.txt
```

### Documenting Results

After each comparison test, document the results:

```powershell
# Edit the comparison log
cd G:/study/bachelor/thesis/platform
code docs/refactor/COMPARISON_LOG.md

# Add an entry following the template
```

---

## Script Location Note

⚠️ **IMPORTANT**: The `test_comparison.ps1` script is located in the `platform/` directory but internally adjusts paths to work correctly. When you run it, it:

1. Runs tests in `platform/` (current directory)
2. Runs tests in `../platform_refactor/` (sibling directory)
3. Creates comparison results in `comparisons/` (subdirectory of platform)

This means you should always run the script from within the `platform/` directory:

```powershell
# ✓ CORRECT
cd G:/study/bachelor/thesis/platform
./test_comparison.ps1

# ✗ WRONG
cd G:/study/bachelor/thesis/
./test_comparison.ps1  # Won't work - script not in parent dir
```

---

## Troubleshooting

### "platform_refactor directory not found"

**Problem**: The script can't find the refactor directory.

**Solution**:
```powershell
cd G:/study/bachelor/thesis/
ls -d platform, platform_refactor

# If platform_refactor is missing:
git clone git@github.com:Ihsara/pencil_platform.git platform_refactor
cd platform_refactor
git checkout refactor
```

### "Not on correct branch"

**Problem**: One directory is on the wrong branch.

**Solution**:
```powershell
# For norm branch
cd G:/study/bachelor/thesis/platform
git checkout norm

# For refactor branch
cd G:/study/bachelor/thesis/platform_refactor
git checkout refactor
```

### "Cannot read remote repository"

**Problem**: SSH key not configured or access denied.

**Solution**:
```powershell
# Test SSH connection
ssh -T git@github.com

# If fails, check SSH keys:
ls ~/.ssh/
# Should have: id_ecdsa, id_ecdsa.pub (or id_rsa, id_rsa.pub)
```

### "Python not found"

**Problem**: Python not in PATH.

**Solution**:
```powershell
# Check Python installation
python --version

# If not found, check Python is installed and add to PATH
```

---

## Best Practices

### 1. Keep Branches Synced

Always pull latest changes before testing:

```powershell
cd platform
git pull origin norm

cd ../platform_refactor
git pull origin refactor
```

### 2. Clean State Testing

The script automatically cleans old data, but you can also manually clean:

```powershell
# Clean norm branch
cd platform
Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force
Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force

# Clean refactor branch
cd ../platform_refactor
Remove-Item -Path "logs/submission/shocktube_phase1/*" -Recurse -Force
Remove-Item -Path "runs/shocktube_phase1/*" -Recurse -Force
```

### 3. Document Everything

After each comparison test:
- Review the REPORT.txt
- Document findings in COMPARISON_LOG.md
- Note any intentional vs. unintentional differences
- Record performance metrics

### 4. Small, Incremental Changes

Make small changes in refactor branch and test frequently:
- Change one component at a time
- Test after each change
- Document each test
- Only merge when all tests pass

---

## Testing Checklist

Before considering a refactor complete:

- [ ] Comparison test executed
- [ ] No functional regressions
- [ ] Performance within 10% of norm
- [ ] Same number of artifacts generated
- [ ] Same parameter values in configs
- [ ] Terminal output clear and informative
- [ ] Logs complete and structured
- [ ] No crashes or errors
- [ ] Results documented in COMPARISON_LOG.md
- [ ] Code reviewed for quality

---

## Next Steps

1. Complete the setup following steps 1-7
2. Run your first comparison test
3. Begin refactor work on the refactor branch
4. Test frequently using `./test_comparison.ps1`
5. Document all changes in COMPARISON_LOG.md

---

## Summary

**Setup**: Two directories, same repo, different branches  
**Testing**: Run `./test_comparison.ps1` from platform directory  
**Command**: Always test with `python main.py shocktube_phase1 -mw`  
**Documentation**: Log all tests in docs/refactor/COMPARISON_LOG.md  

**Remember**: NO UNITTEST - only side-by-side comparison!
