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

"""Tests for prompt asset loading."""

from pathlib import Path

from prompt import KNOWLEDGE_DIR, load_system_prompt


def test_load_system_prompt_reads_packaged_asset():
    """System prompt asset should be present alongside the installed module."""
    prompt_file = KNOWLEDGE_DIR / "system-prompt.md"

    assert prompt_file.exists()
    assert prompt_file.is_file()
    assert prompt_file == Path(__file__).parents[2] / "data" / "knowledge" / "system-prompt.md"

    prompt_text = load_system_prompt()

    assert prompt_text
    assert "{{DATETIME}}" not in prompt_text