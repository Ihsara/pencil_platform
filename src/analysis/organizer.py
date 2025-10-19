# src/analysis_organizer.py

"""
Module for organizing analysis outputs into a structured folder hierarchy.
Automatically identifies best performers and creates modular "best" folders.
"""

import shutil
from pathlib import Path
from loguru import logger
from typing import Dict, List, Tuple
import json


class AnalysisOrganizer:
    """
    Organizes analysis outputs into a clean, hierarchical structure.
    
    Folder Structure:
    analysis/{experiment_name}/
    ├── error/
    │   ├── evolution/        (error evolution GIFs)
    │   ├── frames/           (error evolution frames)
    │   └── norms/            (error norms analysis)
    ├── var/
    │   ├── evolution/        (var evolution GIFs)
    │   └── frames/           (var evolution frames)
    └── best/
        └── evolution/
            ├── L1/           (best performers by L1 metric)
            ├── L2/           (best performers by L2 metric)
            ├── LINF/         (best performers by L∞ metric)
            └── Combined/     (best performers by combined score)
    """
    
    def __init__(self, experiment_name: str, analysis_base_dir: Path):
        """
        Initialize the organizer.
        
        Args:
            experiment_name: Name of the experiment
            analysis_base_dir: Base analysis directory (e.g., analysis/{experiment_name})
        """
        self.experiment_name = experiment_name
        self.base_dir = analysis_base_dir
        
        # Define new structure
        self.error_dir = self.base_dir / "error"
        self.error_evolution_dir = self.error_dir / "evolution"
        self.error_frames_dir = self.error_dir / "frames"
        self.error_norms_dir = self.error_dir / "norms"
        
        self.var_dir = self.base_dir / "var"
        self.var_evolution_dir = self.var_dir / "evolution"
        
        self.best_dir = self.base_dir / "best"
        self.best_evolution_dir = self.best_dir / "evolution"
        
    def create_structure(self):
        """Create the organized folder structure."""
        logger.info("Creating organized folder structure...")
        
        # Create main folders
        self.error_evolution_dir.mkdir(parents=True, exist_ok=True)
        self.error_frames_dir.mkdir(parents=True, exist_ok=True)
        self.error_norms_dir.mkdir(parents=True, exist_ok=True)
        
        self.var_evolution_dir.mkdir(parents=True, exist_ok=True)
        
        self.best_evolution_dir.mkdir(parents=True, exist_ok=True)
        
        logger.success("✓ Created organized folder structure")
    
    def migrate_existing_files(self):
        """
        Migrate files from old structure to new structure.
        
        Old structure:
        - error_evolution/
        - error_frames/
        - error_norms/
        - var_evolution/
        
        New structure:
        - error/evolution/
        - error/frames/
        - error/norms/
        - var/evolution/
        """
        logger.info("Migrating existing files to new structure...")
        
        # Map old directories to new directories
        migrations = {
            self.base_dir / "error_evolution": self.error_evolution_dir,
            self.base_dir / "error_frames": self.error_frames_dir,
            self.base_dir / "error_norms": self.error_norms_dir,
            self.base_dir / "var_evolution": self.var_evolution_dir,
        }
        
        for old_dir, new_dir in migrations.items():
            if old_dir.exists() and old_dir != new_dir:
                logger.info(f"  ├─ Migrating {old_dir.name}/ → {new_dir.relative_to(self.base_dir)}/")
                
                # Move all files from old to new
                for item in old_dir.iterdir():
                    dest = new_dir / item.name
                    if item.is_file():
                        shutil.move(str(item), str(dest))
                    elif item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.move(str(item), str(dest))
                
                # Remove old directory
                if old_dir.exists() and not any(old_dir.iterdir()):
                    old_dir.rmdir()
                    logger.info(f"     └─ Removed old directory: {old_dir.name}/")
        
        logger.success("✓ Migration complete")
    
    def create_best_performers_structure(self, error_norms_cache: Dict, 
                                        combined_scores: Dict,
                                        metrics: List[str] = ['l1', 'l2', 'linf']):
        """
        Create 'best' folder structure with top performers for each metric.
        
        Args:
            error_norms_cache: Dictionary with error norms for each run
            combined_scores: Dictionary with combined scores for each run
            metrics: List of metrics to create best folders for
        """
        logger.info("Creating best performers structure...")
        
        # Create metric-specific folders
        metric_folders = {}
        for metric in metrics:
            metric_upper = metric.upper()
            metric_folder = self.best_evolution_dir / metric_upper
            metric_folder.mkdir(parents=True, exist_ok=True)
            metric_folders[metric] = metric_folder
        
        # Create Combined folder
        combined_folder = self.best_evolution_dir / "Combined"
        combined_folder.mkdir(parents=True, exist_ok=True)
        metric_folders['combined'] = combined_folder
        
        logger.success("✓ Created best performers folder structure")
        
        return metric_folders
    
    def populate_best_performers(self, error_norms_cache: Dict,
                                 combined_scores: Dict,
                                 top_n: int = 3,
                                 metrics: List[str] = ['l1', 'l2', 'linf']):
        """
        Copy best performer files to the 'best' folders.
        
        For each metric, identifies top N performers and copies their:
        - Error evolution GIFs
        - Error evolution frames
        
        Args:
            error_norms_cache: Dictionary with error norms for each run
            combined_scores: Dictionary with combined scores for each run
            top_n: Number of top performers to include (default: 3)
            metrics: List of metrics to evaluate
        """
        logger.info(f"Populating best performers (top {top_n} for each metric)...")
        
        # Create folder structure
        metric_folders = self.create_best_performers_structure(
            error_norms_cache, combined_scores, metrics
        )
        
        # For each metric, find top N performers
        for metric in metrics:
            logger.info(f"  ├─ Processing {metric.upper()} metric...")
            
            # Calculate score for this metric using ONLY DENSITY (rho)
            metric_scores = {}
            for run_name, cached in error_norms_cache.items():
                error_norms = cached['error_norms']
                
                # Use ONLY density error for scoring
                if 'rho' in error_norms and metric in error_norms['rho']:
                    mean_val = error_norms['rho'][metric]['mean']
                    if mean_val is not None and not (isinstance(mean_val, float) and (mean_val != mean_val or mean_val == float('inf'))):  # Check for NaN and inf
                        metric_scores[run_name] = mean_val
            
            # Sort and get top N
            sorted_runs = sorted(metric_scores.items(), key=lambda x: x[1])
            top_runs = sorted_runs[:top_n]
            
            # Copy files for top performers
            metric_folder = metric_folders[metric]
            for rank, (run_name, score) in enumerate(top_runs, 1):
                logger.info(f"     ├─ #{rank}: {run_name} (score: {score:.6e})")
                
                # Copy error evolution GIF
                src_gif = self.error_evolution_dir / f"{run_name}_error_evolution.gif"
                if src_gif.exists():
                    dest_gif = metric_folder / f"#{rank}_{run_name}_error_evolution.gif"
                    shutil.copy2(src_gif, dest_gif)
                
                # Copy error evolution frames folder
                src_frames = self.error_frames_dir / run_name
                if src_frames.exists():
                    dest_frames = metric_folder / f"#{rank}_{run_name}"
                    if dest_frames.exists():
                        shutil.rmtree(dest_frames)
                    shutil.copytree(src_frames, dest_frames)
            
            logger.info(f"     └─ ✓ Copied top {len(top_runs)} performers for {metric.upper()}")
        
        # Process Combined scores
        logger.info(f"  ├─ Processing Combined scores...")
        sorted_combined = sorted(combined_scores.items(), key=lambda x: x[1]['combined'])
        top_combined = sorted_combined[:top_n]
        
        combined_folder = metric_folders['combined']
        for rank, (run_name, scores) in enumerate(top_combined, 1):
            logger.info(f"     ├─ #{rank}: {run_name} (score: {scores['combined']:.6e})")
            
            # Copy error evolution GIF
            src_gif = self.error_evolution_dir / f"{run_name}_error_evolution.gif"
            if src_gif.exists():
                dest_gif = combined_folder / f"#{rank}_{run_name}_error_evolution.gif"
                shutil.copy2(src_gif, dest_gif)
            
            # Copy error evolution frames folder
            src_frames = self.error_frames_dir / run_name
            if src_frames.exists():
                dest_frames = combined_folder / f"#{rank}_{run_name}"
                if dest_frames.exists():
                    shutil.rmtree(dest_frames)
                shutil.copytree(src_frames, dest_frames)
        
        logger.info(f"     └─ ✓ Copied top {len(top_combined)} performers for Combined")
        
        # Create summary JSON for each metric folder
        self._create_best_summaries(metric_folders, top_n, metrics, 
                                    error_norms_cache, combined_scores)
        
        logger.success("✓ Best performers populated")
    
    def _create_best_summaries(self, metric_folders: Dict, top_n: int,
                              metrics: List[str], error_norms_cache: Dict,
                              combined_scores: Dict):
        """Create summary JSON files for each best performers folder."""
        import numpy as np
        
        # For each metric
        for metric in metrics:
            metric_folder = metric_folders[metric]
            
            # Calculate scores
            metric_scores = {}
            for run_name, cached in error_norms_cache.items():
                error_norms = cached['error_norms']
                
                scores = []
                for var in ['rho', 'ux', 'pp', 'ee']:
                    if var in error_norms and metric in error_norms[var]:
                        mean_val = error_norms[var][metric]['mean']
                        if mean_val is not None and not (isinstance(mean_val, float) and (mean_val != mean_val or mean_val == float('inf'))):
                            scores.append(mean_val)
                
                if scores:
                    metric_scores[run_name] = np.mean(scores)
            
            sorted_runs = sorted(metric_scores.items(), key=lambda x: x[1])
            top_runs = sorted_runs[:top_n]
            
            # Create summary
            summary = {
                'metric': metric.upper(),
                'top_performers': [
                    {
                        'rank': rank,
                        'run_name': run_name,
                        'score': float(score)
                    }
                    for rank, (run_name, score) in enumerate(top_runs, 1)
                ]
            }
            
            summary_file = metric_folder / f"best_{metric}_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
        
        # For Combined
        combined_folder = metric_folders['combined']
        sorted_combined = sorted(combined_scores.items(), key=lambda x: x[1]['combined'])
        top_combined = sorted_combined[:top_n]
        
        summary = {
            'metric': 'Combined',
            'top_performers': [
                {
                    'rank': rank,
                    'run_name': run_name,
                    'combined_score': float(scores['combined']),
                    'per_metric_scores': {k: float(v) for k, v in scores['per_metric'].items()}
                }
                for rank, (run_name, scores) in enumerate(top_combined, 1)
            ]
        }
        
        summary_file = combined_folder / "best_combined_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def organize(self):
        """
        Complete organization workflow:
        1. Create new structure
        2. Migrate existing files
        """
        logger.info("=" * 80)
        logger.info("ORGANIZING ANALYSIS FOLDER STRUCTURE")
        logger.info("=" * 80)
        
        self.create_structure()
        self.migrate_existing_files()
        
        logger.success("=" * 80)
        logger.success("FOLDER ORGANIZATION COMPLETE")
        logger.success("=" * 80)
