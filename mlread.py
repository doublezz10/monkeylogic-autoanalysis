"""
mlread.py - Python reader for MonkeyLogic .bhv2 files.

This is a Python translation/adaptation of MATLAB's mlread.m function.
Reads binary MonkeyLogic .bhv2 files and returns structured trial data.

USAGE:
    from mlread import mlread
    
    data, mlconfig, trial_record, filename = mlread("/path/to/session.bhv2")
    
    # data is a list of dicts, one per trial
    # Each trial dict contains:
    #   - BehavioralCodes: dict with CodeNumbers and CodeTimes
    #   - TrialError: error code (0 = success)
    #   - BlockCount: current block number
    #   - Condition: condition number
    #   - etc.

For information on MonkeyLogic event codes, see:
https://monkeylogic.github.io/Code%20Reference_Event%20Codes.html

DEPENDENCIES:
    numpy, struct (standard library)

NOTES:
    This reads the MATLAB v7.3+ format .bhv2 files.
    Older format may not be supported.
"""

import os
import struct
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict, Any


# =============================================================================
# CONSTANTS
# =============================================================================

# File header markers
BHv2_FILE_VERSION = 2
MAX_TRIAL_EVENTS = 1024
MAX_CONDITION_NAME_LENGTH = 256
MAX_DATA_FILE_HEADER_LENGTH = 4096

# MATLAB types for reading
MATHDF_TYPE_DOUBLE = 0
MATHDF_TYPE_CHAR = 1
MATHDF_TYPE_UINT8 = 2
MATHDF_TYPE_UINT16 = 3
MATHDF_TYPE_UINT32 = 4
MATHDF_TYPE_UINT64 = 5
MATHDF_TYPE_INT8 = 6
MATHDF_TYPE_INT16 = 7
MATHDF_TYPE_INT32 = 8
MATHDF_TYPE_INT64 = 9
MATHDF_TYPE_SINGLE = 10
MATHDF_TYPE_STRUCT = 11
MATHDF_TYPE_ARRAY = 12


class MLBhv2Reader:
    """
    Reader for MonkeyLogic .bhv2 binary files.
    
    Handles MATLAB v7.3+ HDF5-based format.
    """
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.filename = self.filepath.name
        
        # Try numpy HDF5 reader first (faster), fall back to manual parsing
        try:
            import h5py
            self._use_h5py = True
        except ImportError:
            self._use_h5py = False
    
    def read(self) -> Tuple[List[Dict], Dict, Dict, str]:
        """
        Read the complete .bhv2 file.
        
        Returns:
            Tuple of (trial_data, mlconfig, trial_record, filename)
        """
        if self._use_h5py:
            return self._read_h5py()
        else:
            return self._read_manual()
    
    def _read_h5py(self) -> Tuple[List[Dict], Dict, Dict, str]:
        """Read using h5py (requires numpy)."""
        import h5py
        
        trial_data = []
        
        with h5py.File(self.filepath, 'r') as f:
            # Read MLConfig
            mlconfig = self._read_mlconfig(f)
            
            # Read TrialRecord
            trial_record = self._read_trial_record(f)
            
            # Read trials
            behavior_codes = f['BehaviorCodes']
            
            for trial_idx in range(trial_record['N_Trials']):
                trial = self._read_trial_h5(f, behavior_codes, trial_idx)
                trial_data.append(trial)
        
        return trial_data, mlconfig, trial_record, self.filename
    
    def _read_mlconfig(self, f) -> Dict:
        """Read MLConfig section."""
        mlconfig = {}
        
        if 'MLConfig' in f:
            for key, value in f['MLConfig'].items():
                try:
                    mlconfig[key] = value[()] if len(value.shape) == 0 else value[()]
                except:
                    mlconfig[key] = str(value)
        
        return mlconfig
    
    def _read_trial_record(self, f) -> Dict:
        """Read TrialRecord section."""
        trial_record = {}
        
        if 'TrialRecord' in f:
            for key, value in f['TrialRecord'].items():
                try:
                    trial_record[key] = value[()] if len(value.shape) == 0 else value[()]
                except:
                    trial_record[key] = str(value)
        
        return trial_record
    
    def _read_trial_h5(self, f, behavior_codes, trial_idx: int) -> Dict:
        """Read a single trial from HDF5 file."""
        trial = {}
        
        # Behavioral codes for this trial
        bc = behavior_codes['BehavioralCodes']
        
        # Get code numbers and times
        try:
            code_nums = bc['CodeNumbers'][trial_idx, :]
            code_times = bc['CodeTimes'][trial_idx, :]
            
            # Find non-zero entries
            valid = code_nums != 0
            codes = code_nums[valid].tolist()
            times = code_times[valid].tolist()
            
            trial['BehavioralCodes'] = {
                'CodeNumbers': codes,
                'CodeTimes': times
            }
        except (KeyError, IndexError):
            trial['BehavioralCodes'] = {'CodeNumbers': [], 'CodeTimes': []}
        
        # Get other trial fields
        for field in ['TrialError', 'BlockCount', 'Condition', 'TrialStartTime', 
                      'TrialEndTime', 'ResponseTime', 'Outcome']:
            try:
                trial[field] = behavior_codes[field][trial_idx]
            except (KeyError, IndexError):
                trial[field] = None
        
        return trial
    
    def _read_manual(self) -> Tuple[List[Dict], Dict, Dict, str]:
        """
        Manual binary parsing (fallback if h5py not available).
        
        This is a simplified implementation - for full support,
        install h5py: pip install h5py
        """
        raise NotImplementedError(
            "Manual .bhv2 parsing not fully implemented. "
            "Install h5py: pip install h5py"
        )


def mlread(filepath: str) -> Tuple[List[Dict], Dict, Dict, str]:
    """
    Read a MonkeyLogic .bhv2 file.
    
    Args:
        filepath: Path to .bhv2 file
    
    Returns:
        Tuple: (trial_data, mlconfig, trial_record, filename)
        
        - trial_data: List of dicts, one per trial
        - mlconfig: Dict with task configuration
        - trial_record: Dict with trial metadata
        - filename: Name of the file
    
    Example:
        >>> data, config, record, fname = mlread("session.bhv2")
        >>> print(f"Got {len(data)} trials")
        >>> print(f"Trial 0 codes: {data[0]['BehavioralCodes']}")
    """
    reader = MLBhv2Reader(filepath)
    return reader.read()


def get_behavioral_codes(trial_data: List[Dict]) -> Dict[int, List[float]]:
    """
    Extract behavioral codes from trial data as a dict.
    
    Args:
        trial_data: List of trial dicts from mlread()
    
    Returns:
        Dict mapping code number -> list of (time, trial_idx) tuples
    """
    codes = {}
    
    for trial_idx, trial in enumerate(trial_data):
        bc = trial.get('BehavioralCodes', {})
        code_nums = bc.get('CodeNumbers', [])
        code_times = bc.get('CodeTimes', [])
        
        for code_num, code_time in zip(code_nums, code_times):
            if code_num not in codes:
                codes[code_num] = []
            codes[code_num].append((code_time, trial_idx))
    
    return codes


def find_code_times(trial_data: List[Dict], code: int) -> List[float]:
    """
    Find all times a specific code occurred across all trials.
    
    Args:
        trial_data: List of trial dicts from mlread()
        code: Code number to search for
    
    Returns:
        List of times when this code occurred
    """
    all_times = []
    
    for trial in trial_data:
        bc = trial.get('BehavioralCodes', {})
        code_nums = bc.get('CodeNumbers', [])
        code_times = bc.get('CodeTimes', [])
        
        for cn, ct in zip(code_nums, code_times):
            if cn == code:
                all_times.append(ct)
    
    return all_times


# =============================================================================
# COMMON MONKEYLOGIC EVENT CODES
# =============================================================================
# Standard MonkeyLogic event codes. Your task may differ!
# See: https://monkeylogic.github.io/Code%20Reference_Event%20Codes.html

EVENT_CODES = {
    # Trial markers
    'TRIAL_START': 1,
    'TRIAL_END': 2,
    'BLOCK_START': 3,
    'BLOCK_END': 4,
    
    # Response keys
    'KEYBOARD_RESPONSE': 18,
    'MOUSE_RESPONSE': 19,
    'JOYSTICK_RESPONSE': 20,
    
    # Coded responses (often customized)
    'RESPONSE_VALID_LEFT': 36,
    'RESPONSE_VALID_RIGHT': 37,
    'RESPONSE_VALID_UP': 38,
    'RESPONSE_VALID_DOWN': 39,
    
    'RESPONSE_LEFT': 42,
    'RESPONSE_RIGHT': 43,
    'RESPONSE_UP': 44,
    'RESPONSE_DOWN': 45,
    
    # Stimulus positions
    'STIM_LEFT': 46,
    'STIM_RIGHT': 47,
    
    # Timing
    'GO_SIGNAL': 50,
    'CUE_OFFSET': 55,
    'REWARD': 65,
    'PUNISHMENT': 66,
    
    # Trial types (often customized)
    'PAVLOVIAN_TRIAL': 90,
    'INSTRUMENTAL_TRIAL': 91,
    
    # Errors
    'BREAK_TRIAL': 98,
    'NO_RESPONSE': 99,
    'INCORRECT': 100,
    
    # Stimulus IDs (typically 101-199 for stim1, 201-299 for stim2)
    'STIM_A': 101,
    'STIM_B': 102,
    'STIM_C': 103,
    'STIM_D': 104,
    'STIM_E': 105,
    
    # Probabilities (often 121-129 for 10%-90%)
    'PROB_10': 121,
    'PROB_20': 122,
    'PROB_30': 123,
    'PROB_40': 124,
    'PROB_50': 125,
    'PROB_60': 126,
    'PROB_70': 127,
    'PROB_80': 128,
    'PROB_90': 129,
}


if __name__ == "__main__":
    # Simple test
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"Reading: {filepath}")
        
        data, config, record, fname = mlread(filepath)
        
        print(f"\nFile: {fname}")
        print(f"Trials: {len(data)}")
        print(f"\nMLConfig keys: {list(config.keys())[:10]}...")
        print(f"TrialRecord keys: {list(record.keys())[:10]}...")
        
        if data:
            print(f"\nTrial 0:")
            print(f"  BehavioralCodes: {data[0].get('BehavioralCodes', {})}")
            print(f"  TrialError: {data[0].get('TrialError')}")
            print(f"  BlockCount: {data[0].get('BlockCount')}")
    else:
        print("Usage: python mlread.py /path/to/session.bhv2")
