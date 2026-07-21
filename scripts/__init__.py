# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Mock experiments with realistic wall-clock execution time for workflow testing."""

import sys
from pathlib import Path

# Add demo directory to path for imports
demo_path = Path(__file__).parent.parent / "demo"
if str(demo_path) not in sys.path:
    sys.path.insert(0, str(demo_path))

from resonator_spectroscopy import resonator_spectroscopy
from qubit_spectroscopy import qubit_spectroscopy
from rabi_oscillation import rabi_oscillation
from t1_measurement import t1_measurement
from ramsey_measurement import ramsey_measurement

__all__ = [
    "resonator_spectroscopy",
    "qubit_spectroscopy",
    "rabi_oscillation",
    "t1_measurement",
    "ramsey_measurement",
]
