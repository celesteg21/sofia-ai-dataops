"""Harness de evaluacion offline: precision del clasificador de incidentes.

Objetivo: verificar que el clasificador (keyword fallback o LLM) supera el umbral
de precision definido sobre los 20 fixtures etiquetados. No hace llamadas HTTP reales.

Corre con:
    make eval

NO corre con `make test` (excluido via marker -m "not eval" en pytest config).
"""

import json
from pathlib import Path

import pytest

from sofia_ai_dataops.agents.nodes.classify import make_classify_incident_node

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

_FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "eval_incidents.jsonl"
_ACCURACY_THRESHOLD = 0.80  # 80% minimo para pasar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixtures() -> list[dict]:  # type: ignore[type-arg]
    fixtures = []
    with _FIXTURES_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


def _build_state(fixture: dict) -> dict:  # type: ignore[type-arg]
    return {
        "dag_id": fixture.get("dag_id", "unknown_dag"),
        "task_id": fixture.get("task_id", "unknown_task"),
        "run_id": "eval__run",
        "logs": fixture["logs"],
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Tests de precision
# ---------------------------------------------------------------------------


@pytest.mark.eval
class TestClassificationAccuracy:
    """Evalua la precision del clasificador sobre los fixtures etiquetados."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        # Usa keyword fallback (sin LLM) — reproducible en CI sin API key.
        self.classifier = make_classify_incident_node(chat_client=None)
        self.fixtures = _load_fixtures()
        assert len(self.fixtures) >= 20, "Se requieren al menos 20 fixtures de evaluacion."

    def test_failure_type_accuracy_above_threshold(self) -> None:
        """La precision de failure_type debe superar el 80%."""
        correct = 0
        errors = []

        for fixture in self.fixtures:
            state = _build_state(fixture)
            result = self.classifier(state)  # type: ignore[arg-type]
            predicted = result.get("failure_type", "unknown")
            expected = fixture["expected_failure_type"]

            if predicted == expected:
                correct += 1
            else:
                errors.append(
                    {
                        "id": fixture["id"],
                        "expected": expected,
                        "predicted": predicted,
                        "logs_snippet": fixture["logs"][:80],
                    }
                )

        total = len(self.fixtures)
        accuracy = correct / total
        failure_report = "\n".join(
            f"  [{e['id']}] expected={e['expected']} got={e['predicted']} | {e['logs_snippet']}"
            for e in errors
        )

        assert accuracy >= _ACCURACY_THRESHOLD, (
            f"Precision de failure_type: {accuracy:.0%} ({correct}/{total}) — "
            f"por debajo del umbral {_ACCURACY_THRESHOLD:.0%}.\n"
            f"Errores:\n{failure_report}"
        )

    def test_severity_accuracy_above_threshold(self) -> None:
        """La precision de severity debe superar el 80%."""
        correct = 0
        errors = []

        for fixture in self.fixtures:
            state = _build_state(fixture)
            result = self.classifier(state)  # type: ignore[arg-type]
            predicted = result.get("severity", "medium")
            expected = fixture["expected_severity"]

            if predicted == expected:
                correct += 1
            else:
                errors.append(
                    {
                        "id": fixture["id"],
                        "expected": expected,
                        "predicted": predicted,
                        "logs_snippet": fixture["logs"][:80],
                    }
                )

        total = len(self.fixtures)
        accuracy = correct / total
        failure_report = "\n".join(
            f"  [{e['id']}] expected={e['expected']} got={e['predicted']} | {e['logs_snippet']}"
            for e in errors
        )

        assert accuracy >= _ACCURACY_THRESHOLD, (
            f"Precision de severity: {accuracy:.0%} ({correct}/{total}) — "
            f"por debajo del umbral {_ACCURACY_THRESHOLD:.0%}.\n"
            f"Errores:\n{failure_report}"
        )

    def test_all_failure_types_represented(self) -> None:
        """Los 5 tipos de falla deben estar representados en los fixtures."""
        types_present = {f["expected_failure_type"] for f in self.fixtures}
        expected_types = {"connectivity", "permissions", "infrastructure", "upstream", "unknown"}
        assert expected_types.issubset(types_present), (
            f"Tipos faltantes en fixtures: {expected_types - types_present}"
        )

    def test_fixture_count(self) -> None:
        """Deben existir al menos 20 fixtures de evaluacion."""
        assert len(self.fixtures) >= 20, (
            f"Solo hay {len(self.fixtures)} fixtures. El minimo requerido es 20."
        )

    def test_no_fixture_missing_required_fields(self) -> None:
        """Todos los fixtures deben tener logs, expected_failure_type y expected_severity."""
        for fixture in self.fixtures:
            assert "logs" in fixture, f"Fixture {fixture.get('id')} sin campo 'logs'"
            assert "expected_failure_type" in fixture, (
                f"Fixture {fixture.get('id')} sin campo 'expected_failure_type'"
            )
            assert "expected_severity" in fixture, (
                f"Fixture {fixture.get('id')} sin campo 'expected_severity'"
            )
