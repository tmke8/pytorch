import json
import os
from pathlib import Path
from typing import Any, cast, Dict, List, Set
from warnings import warn

from tools.stats.import_test_stats import ADDITIONAL_CI_FILES_FOLDER, TD_HEURISTIC_PREVIOUSLY_FAILED

from tools.testing.target_determination.heuristics.interface import (
    HeuristicInterface,
    TestPrioritizations,
)
from tools.testing.target_determination.heuristics.utils import (
    python_test_file_to_test_name,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


class PreviouslyFailedInPR(HeuristicInterface):
    def __init__(self, **kwargs: Dict[str, Any]):
        super().__init__(**kwargs)

    def get_test_priorities(self, tests: List[str]) -> TestPrioritizations:
        # Tests must always be returned in a deterministic order.
        # Otherwise it breaks our test sharding logic
        critical_tests = sorted(get_previous_failures())
        test_rankings = TestPrioritizations(
            tests_being_ranked=tests, high_relevance=critical_tests
        )

        return test_rankings

    def get_prediction_confidence(self, tests: List[str]) -> Dict[str, float]:
        critical_tests = get_previous_failures()
        return {test: 1 for test in critical_tests if test in tests}


def get_previous_failures() -> List[str]:
    path = REPO_ROOT / ADDITIONAL_CI_FILES_FOLDER / TD_HEURISTIC_PREVIOUSLY_FAILED
    if not os.path.exists(path):
        print(f"could not find path {path}")
        return []
    with open(path) as f:
        return _parse_prev_failing_test_files(json.load(f))


def _get_previously_failing_tests() -> Set[str]:
    PYTEST_FAILED_TESTS_CACHE_FILE_PATH = Path(".pytest_cache/v/cache/lastfailed")

    if not PYTEST_FAILED_TESTS_CACHE_FILE_PATH.exists():
        warn(
            f"No pytorch cache found at {PYTEST_FAILED_TESTS_CACHE_FILE_PATH.absolute()}"
        )
        return set()

    with open(PYTEST_FAILED_TESTS_CACHE_FILE_PATH) as f:
        last_failed_tests = json.load(f)

    prioritized_tests = _parse_prev_failing_test_files(last_failed_tests)

    return python_test_file_to_test_name(prioritized_tests)


def _parse_prev_failing_test_files(last_failed_tests: Dict[str, bool]) -> Set[str]:
    prioritized_tests = set()

    # The keys are formatted as "test_file.py::test_class::test_method[params]"
    # We just need the test_file part
    for test in last_failed_tests:
        parts = test.split("::")
        if len(parts) > 1:
            test_file = parts[0]
            prioritized_tests.add(test_file)

    return prioritized_tests
