from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backup_runner import services
from backup_runner.errors import BackupError, ConfigError
from backup_runner.services import Service, StopConfig


def write_catalog(root: Path, items: list[dict[str, object]]) -> Path:
    path = root / "services.json"
    path.write_text(json.dumps({"version": 1, "services": items}), encoding="utf-8")
    return path


class CatalogValidationTests(unittest.TestCase):
    def test_loads_actual_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            catalog = write_catalog(
                root,
                [
                    {
                        "name": "actual",
                        "description": "Actual Budget server data",
                        "sources": [str(data)],
                        "optional_sources": [str(root / ".env")],
                        "stop": {"project": "actual", "services": ["actual_server"]},
                    }
                ],
            )
            loaded = services.load_services(catalog)
        self.assertEqual(set(loaded), {"actual"})
        self.assertEqual(loaded["actual"].sources, (data,))
        self.assertEqual(loaded["actual"].optional_sources, (root / ".env",))
        self.assertEqual(loaded["actual"].stop, StopConfig("actual", ("actual_server",)))

    def test_production_catalog_contains_only_actual(self) -> None:
        catalog = Path(__file__).resolve().parents[1] / "services.json"
        loaded = services.load_services(catalog)
        self.assertEqual(set(loaded), {"actual"})
        self.assertEqual(loaded["actual"].description, "Actual Budget server data")

    def test_rejects_top_level_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "services.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ConfigError):
                services.load_services(path)

    def test_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = write_catalog(
                Path(temp),
                [{"name": "actual", "sources": ["/tmp/data"], "unexpected": True}],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_rejects_invalid_and_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = write_catalog(root, [{"name": "Bad Name", "sources": ["/tmp/data"]}])
            with self.assertRaises(ConfigError):
                services.load_services(catalog)
            catalog = write_catalog(
                root,
                [
                    {"name": "actual", "sources": ["/tmp/a"]},
                    {"name": "actual", "sources": ["/tmp/b"]},
                ],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_requires_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = write_catalog(Path(temp), [{"name": "actual", "description": "Actual"}])
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_parses_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = write_catalog(
                Path(temp),
                [
                    {
                        "name": "actual",
                        "sources": ["/cookbook/actual/data"],
                        "stop": {"project": "actual", "services": ["actual_server"]},
                    }
                ],
            )
            loaded = services.load_services(catalog)
        self.assertEqual(loaded["actual"].sources, (Path("/cookbook/actual/data"),))
        self.assertEqual(loaded["actual"].stop, StopConfig("actual", ("actual_server",)))

    def test_missing_catalog_raises(self) -> None:
        with self.assertRaises(ConfigError):
            services.load_services(Path(tempfile.gettempdir()) / "does-not-exist.json")


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {"actual": Service("actual", "Actual")}

    def test_preserves_actual_and_removes_duplicates(self) -> None:
        selected = services.selected_services(self.config, raw="actual actual")
        self.assertEqual([service.name for service in selected], ["actual"])

    def test_empty_requires_value(self) -> None:
        with self.assertRaises(ConfigError):
            services.selected_services(self.config, raw="")
        self.assertEqual(services.selected_services(self.config, raw="", require=False), [])

    def test_unknown_service_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            services.selected_services(self.config, raw="actual nope")


class SourceResolutionTests(unittest.TestCase):
    def test_resolves_required_and_optional_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            required = root / "data"
            optional = root / ".env"
            required.mkdir()
            optional.write_text("A=B", encoding="utf-8")
            service = Service(
                "actual",
                "Actual",
                sources=(required,),
                optional_sources=(optional, root / "missing"),
            )
            self.assertEqual(services.resolve_sources(service), [required, optional])

    def test_missing_required_source_raises(self) -> None:
        service = Service("actual", "Actual", sources=(Path("/missing"),))
        with self.assertRaises(BackupError):
            services.resolve_sources(service)

    def test_no_sources_raises(self) -> None:
        service = Service("actual", "Actual")
        with self.assertRaises(BackupError):
            services.resolve_sources(service)
