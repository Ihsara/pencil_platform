#!/usr/bin/env python3
"""
Quick script to inspect the contents of a VAR file
Usage: python inspect_var.py <path_to_run_directory> [var_number]
Example: python inspect_var.py g:/proj/oikotie/shocktube_phase1/run_name 0
"""

import sys
from pathlib import Path

# Add Pencil Code Python library to path
# Adjust this path to match your setup
PLATFORM_ROOT = Path(__file__).parent
PENCIL_CODE_PYTHON_PATH = PLATFORM_ROOT.parent / "pencil-code" / "python"
if str(PENCIL_CODE_PYTHON_PATH) not in sys.path:
    sys.path.insert(0, str(PENCIL_CODE_PYTHON_PATH))

import pencil.read as read
import numpy as np

def inspect_var(run_path: str, var_num: int = 0):
    """Inspect a VAR file and show all available data."""
    run_path = Path(run_path)
    data_dir = run_path / "data"
    
    # Check if proc0 exists (multi-processor run)
    proc_dir = data_dir / "proc0" if (data_dir / "proc0").is_dir() else data_dir
    
    var_file = f"VAR{var_num}"
    
    print("=" * 80)
    print(f"INSPECTING VAR FILE: {var_file}")
    print(f"Run directory: {run_path}")
    print(f"Data directory: {proc_dir}")
    print("=" * 80)
    
    # Read VAR file
    print(f"\n📂 Loading {var_file}...")
    var = read.var(var_file, datadir=str(data_dir), quiet=True, trimall=True)
    
    # Read params
    print(f"📂 Loading params...")
    params = read.param(datadir=str(data_dir), quiet=True, conflicts_quiet=True)
    
    # Read grid
    print(f"📂 Loading grid...")
    grid = read.grid(datadir=str(data_dir), quiet=True, trim=True)
    
    # Read dim
    print(f"📂 Loading dim...")
    dim = read.dim(str(data_dir), proc=-1)
    
    print("\n" + "=" * 80)
    print("VAR OBJECT ATTRIBUTES")
    print("=" * 80)
    
    # List all attributes
    var_attrs = [attr for attr in dir(var) if not attr.startswith('_')]
    
    print(f"\nTotal attributes: {len(var_attrs)}\n")
    
    # Categorize attributes
    scalar_attrs = []
    array_attrs = []
    other_attrs = []
    
    for attr in var_attrs:
        val = getattr(var, attr)
        if isinstance(val, (int, float, np.integer, np.floating)):
            scalar_attrs.append((attr, val, type(val).__name__))
        elif isinstance(val, np.ndarray):
            array_attrs.append((attr, val.shape, val.dtype))
        else:
            other_attrs.append((attr, type(val).__name__))
    
    # Print scalar values
    print("SCALAR VALUES:")
    print("-" * 80)
    for name, value, dtype in sorted(scalar_attrs):
        print(f"  {name:20s} = {value:20.6e}  ({dtype})")
    
    # Print array shapes
    print("\nARRAY VARIABLES:")
    print("-" * 80)
    for name, shape, dtype in sorted(array_attrs):
        print(f"  {name:20s} : shape={str(shape):20s} dtype={dtype}")
    
    # Print other attributes
    if other_attrs:
        print("\nOTHER ATTRIBUTES:")
        print("-" * 80)
        for name, dtype in sorted(other_attrs):
            print(f"  {name:20s} : {dtype}")
    
    # Check for dt specifically
    print("\n" + "=" * 80)
    print("TIMESTEP INFORMATION")
    print("=" * 80)
    
    if hasattr(var, 'dt'):
        print(f"✓ var.dt exists: {var.dt:.6e}")
    else:
        print("✗ var.dt does NOT exist in VAR file")
    
    if hasattr(var, 't'):
        print(f"✓ var.t (simulation time) exists: {var.t:.6e}")
    else:
        print("✗ var.t does NOT exist")
    
    if hasattr(var, 'it'):
        print(f"✓ var.it (iteration number) exists: {var.it}")
    
    # Check params for dt
    print("\n" + "=" * 80)
    print("PARAMS OBJECT - UNIT INFORMATION")
    print("=" * 80)
    
    unit_attrs = ['unit_length', 'unit_velocity', 'unit_density', 
                  'unit_temperature', 'unit_time', 'unit_mass',
                  'dt', 'it1', 'nt', 'cdt', 'cdtv', 'cdn', 'gamma', 'cp', 'cv']
    
    for attr in unit_attrs:
        if hasattr(params, attr):
            val = getattr(params, attr)
            print(f"  params.{attr:20s} = {val}")
        else:
            print(f"  params.{attr:20s} = NOT FOUND")
    
    # Grid information
    print("\n" + "=" * 80)
    print("GRID INFORMATION")
    print("=" * 80)
    print(f"  x: min={grid.x.min():.6e}, max={grid.x.max():.6e}, shape={grid.x.shape}")
    print(f"  y: min={grid.y.min():.6e}, max={grid.y.max():.6e}, shape={grid.y.shape}")
    print(f"  z: min={grid.z.min():.6e}, max={grid.z.max():.6e}, shape={grid.z.shape}")
    print(f"  dx: {grid.dx:.6e}")
    print(f"  dy: {grid.dy:.6e}")
    print(f"  dz: {grid.dz:.6e}")
    
    # Dimension information
    print("\n" + "=" * 80)
    print("DIMENSION INFORMATION")
    print("=" * 80)
    print(f"  nx: {dim.nx}")
    print(f"  ny: {dim.ny}")
    print(f"  nz: {dim.nz}")
    print(f"  nxgrid: {dim.nxgrid}")
    print(f"  nygrid: {dim.nygrid}")
    print(f"  nzgrid: {dim.nzgrid}")
    
    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_var.py <path_to_run_directory> [var_number]")
        print("\nFor HPC data, provide the full HPC path from your plan file:")
        print("Example: python inspect_var.py /scratch/project/oikotie/shocktube_phase1/run_name 0")
        print("\nOr you can check the path in your config:")
        print("  config/<experiment>/plan/sweep.yaml -> hpc.run_base_dir")
        sys.exit(1)
    
    run_path = sys.argv[1]
    var_num = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    
    inspect_var(run_path, var_num)
