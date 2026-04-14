# Patterns & Conventions

This document explains patterns used in this pipeline that may not be obvious
from the code alone. Based on real MonkeyLogic analysis workflows.

---

## 1. Session Caching

**Problem:** Reading and parsing .bhv2 files is slow. Re-processing all historical
sessions on every run wastes time.

**Solution:** Cache parsed trial data as .pkl files.

```python
import pickle
from pathlib import Path

CACHE_DIR = Path("cache")

def get_cached_session(session_id: str) -> Optional[Dict]:
    cache_file = CACHE_DIR / f"{session_id}.pkl"
    if cache_file.exists():
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return None

def cache_session(session_id: str, data: Dict):
    cache_file = CACHE_DIR / f"{session_id}.pkl"
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)
```

**In the watcher loop:**
```python
def analysis_callback(bhv2_file):
    session_id = Path(bhv2_file).stem

    # Check cache first
    cached = get_cached_session(session_id)
    if cached:
        print(f"Using cached data for {session_id}")
        return

    # Otherwise process and cache
    data = process_bhv2(bhv2_file)
    cache_session(session_id, data)
```

**Cache invalidation:** Add a timestamp check if you need to force re-analysis:
```python
def needs_refresh(cache_file, max_age_days=30):
    if not cache_file.exists():
        return True
    age = time.time() - cache_file.stat().st_mtime
    return age > (max_age_days * 86400)
```

---

## 2. Conditions Files

Some MonkeyLogic tasks use a separate **conditions file** (`.txt`) to define
stimulus positions and other trial parameters. This file is NOT in the .bhv2.

**Typical structure** (space or tab-delimited):
```
Condition    Position1    Position2    RewardProb1    RewardProb2
A_vs_B         left         right         0.9           0.5
B_vs_A         right        left          0.5           0.9
```

**Loading:**
```python
def load_conditions_file(filepath: Path) -> Dict:
    """Parse a MonkeyLogic conditions file."""
    conditions = {}
    with open(filepath, 'r') as f:
        header = f.readline().split()  # Skip header
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                cond_name = parts[0]
                conditions[cond_name] = {
                    'position1': parts[1],
                    'position2': parts[2],
                    'reward_prob1': float(parts[3]) if len(parts) > 3 else None,
                    'reward_prob2': float(parts[4]) if len(parts) > 4 else None,
                }
    return conditions
```

**Where to find it:** Same directory as .bhv2 files, often same name base:
```
/data/
  ├── session.bhv2
  └── session_conditions.txt
```

---

## 3. Block Structure

Sessions can have multiple **blocks** (sub-sessions). Each block has its own
stimulus set, reward probabilities, or task rules.

**Common patterns:**

### Pattern A: Reversal Learning
- Block 1: A=90%, B=50% → Block 2: A=50%, B=90% (reversed)

### Pattern B: Multiple Stimulus Sets
- Block 2: Set A (images A-E)
- Block 3: Set B (images F-J)
- Block 4: Set C (images K-O)

**Extracting block info:**
```python
for trial in trial_data:
    block = trial.get('BlockCount', 0)
    # Block 0 is often "practice" or "setup" - ignore it
    if block == 0:
        continue
    # Block >= 1 is real data
```

**Analyzing per-block:**
```python
from collections import defaultdict

block_data = defaultdict(list)
for trial in trials:
    block_data[trial['block']].append(trial)

for block_num, block_trials in block_data.items():
    accuracy = compute_accuracy(block_trials)
    print(f"Block {block_num}: {accuracy:.1%}")
```

---

## 4. Multiple Sessions Per Day

MonkeyLogic names sessions like: `260304`, `260304_2`, `260304_3`...
(base date + optional suffix for 2nd, 3rd, etc. session that day).

**Parsing:**
```python
def parse_session_id(filename: str) -> Dict:
    """Extract date and session number from filename."""
    # Remove extension and path
    base = Path(filename).stem

    # Handle _2, _3 suffixes
    if '_' in base:
        parts = base.rsplit('_', 1)
        date_part = parts[0]
        session_num = int(parts[1])
    else:
        date_part = base
        session_num = 1

    return {
        'date': date_part,      # "260304"
        'session_num': session_num,  # 1, 2, 3...
        'full_id': base         # "260304_2"
    }
```

**Tracking across sessions:**
```python
# Count sessions per day
base_name_counts = {}
for bhv2_file in data_dir.glob("*.bhv2"):
    info = parse_session_id(bhv2_file.name)
    date = info['date']
    base_name_counts[date] = base_name_counts.get(date, 0) + 1
```

---

## 5. Excluding Invalid Trials

MonkeyLogic marks invalid/break trials in the `TrialError` field:
- `0` = success
- Other values = various error types (no response, incorrect, etc.)

**Filtering:**
```python
def get_valid_trials(trial_data: List[Dict]) -> List[Dict]:
    """Filter to only completed/valid trials."""
    return [t for t in trial_data if t.get('TrialError', 0) == 0]

def get_break_trials(trial_data: List[Dict]) -> List[Dict]:
    """Get trials marked as breaks/errors."""
    return [t for t in trial_data if t.get('TrialError', 0) != 0]
```

**Why it matters:**
- Break trials should NOT count toward accuracy
- But you SHOULD report how many breaks occurred
- RT calculations should exclude breaks

---

## 6. Cross-Session Aggregation

Individual sessions vary. For population-level conclusions, aggregate across sessions:

```python
import pandas as pd

def aggregate_sessions(all_session_metrics: List[Dict]) -> pd.DataFrame:
    """Combine metrics from multiple sessions."""
    df = pd.DataFrame(all_session_metrics)

    # Add derived columns
    df['date'] = df['session_id'].apply(lambda x: parse_session_id(x)['date'])

    # Group by date
    daily = df.groupby('date').agg({
        'accuracy': ['mean', 'std'],
        'n_trials': 'sum',
        'mean_rt': 'mean'
    }).reset_index()

    return daily
```

**Plotting aggregation:**
```python
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Learning curve across sessions
axes[0].plot(daily['date'], daily['accuracy_mean'])
axes[0].fill_between(daily['date'],
                     daily['accuracy_mean'] - daily['accuracy_std'],
                     daily['accuracy_mean'] + daily['accuracy_std'],
                     alpha=0.3)

# Trials per session
axes[1].bar(daily['date'], daily['n_trials'])
```

---

## 7. Behavioral Code Reference

Common MonkeyLogic event codes (your task may differ!):

| Code | Name | Usage |
|------|------|-------|
| 36, 37 | Validated L/R | Confirmed response (use for RT) |
| 42, 43 | Raw L/R | Initial response detected |
| 46, 47 | Stim1 L/R position | Which side is stim1 on |
| 50 | Go signal | Stimuli appeared (RT start) |
| 65 | Reward | Reward delivered |
| 90 | Pavlovian trial | S1 only trial type |
| 91 | Instrumental trial | S1+S2 choice trial |
| 98 | Break trial | Trial error/abort |
| 101-105 | Stimulus IDs | Which stimulus (A, B, C...) |
| 121-129 | Probability codes | 10%-90% reward probability |

**Finding YOUR codes:**
```python
# Print all unique codes from a session
all_codes = set()
for trial in trial_data:
    codes = trial['BehavioralCodes']['CodeNumbers']
    all_codes.update(codes)
print(sorted(all_codes))
```

---

## 8. Reaction Time Calculation

RT = time from **go signal** to **validated response**

```python
def compute_rt(trial: Dict) -> Optional[float]:
    """Compute reaction time for a single trial."""
    bc = trial['BehavioralCodes']
    codes = bc['CodeNumbers']
    times = bc['CodeTimes']

    # Build code -> time map
    code_times = dict(zip(codes, times))

    GO = 50
    RESPONSE_VALID_L = 36
    RESPONSE_VALID_R = 37

    if GO not in code_times:
        return None

    go_time = code_times[GO]

    # Find validated response
    for resp_code in [RESPONSE_VALID_L, RESPONSE_VALID_R]:
        if resp_code in code_times:
            return code_times[resp_code] - go_time

    return None
```

**Note:** Raw response codes (42, 43) are earlier but less accurate.
Use validated codes (36, 37) when available.

---

## 9. Hierarchy Analysis (for PIT tasks)

If you're analyzing Pavlovian-Instrumental Transfer or similar tasks with
learned value hierarchies:

```python
from itertools import permutations

def compute_hierarchy_distances(trials: List[Dict], hierarchy: List[str]) -> Dict:
    """
    Compute how close actual choices match expected hierarchy.

    Args:
        trials: List of parsed trials with 'choice' and 'correct' info
        hierarchy: List of stimuli in order of value, e.g. ['A','B','C','D','E']

    Returns:
        Dict with hierarchy name -> accuracy
    """
    n_stim = len(hierarchy)
    all_hierarchies = list(permutations(hierarchy))

    results = {}

    for hier in all_hierarchies:
        # Create lookup: ordered_pair -> expected winner
        expected = {}
        for i in range(n_stim):
            for j in range(i+1, n_stim):
                pair = (hier[i], hier[j])  # e.g., ('A', 'B')
                expected[pair] = hier[i]  # A > B, so A is expected winner

        # Compute accuracy for this hierarchy
        correct = 0
        total = 0

        for trial in trials:
            stim1, stim2 = trial.get('stim1'), trial.get('stim2')
            if stim1 is None or stim2 is None:
                continue

            pair = tuple(sorted([stim1, stim2], key=lambda x: hierarchy.index(x)))

            if pair not in expected:
                continue

            expected_winner = expected[pair]
            actual_winner = trial.get('choice')

            if actual_winner == expected_winner:
                correct += 1
            total += 1

        results[hier] = correct / total if total > 0 else 0

    return results
```

---

## 10. Graceful Shutdown Pattern

For long-running watchers, support clean shutdown via file:

```python
import time
import threading

class WatcherWithShutdown:
    def __init__(self, watch_dir):
        self.watch_dir = Path(watch_dir)
        self.stop_file = self.watch_dir / "watcher.stop"
        self._running = True

    def check_stop(self):
        if self.stop_file.exists():
            self.stop_file.unlink()
            self._running = False
            return True
        return False

    def run(self):
        while self._running:
            self.check_stop()
            if not self._running:
                break

            # Do work...

            time.sleep(10)

        print("Watcher stopped cleanly")
```
