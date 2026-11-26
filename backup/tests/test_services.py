from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import services
from backup_runner.errors import BackupError, ConfigError
from backup_runner.services import Service, StopConfig


def write_catalog(root: Path, items: list[dict[str, object]]) -> Path:
    path = root / "services.json"
    path.write_text(json.dumps({"version": 1, "services": items}), encoding="utf-8")
    return path


class CatalogValidationTests(unittest.TestCase):
    def test_loads_valid_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            catalog = write_catalog(
                root,
                [
                    {"name": "configs", "type": "env_configs", "root": str(root)},
                    {"name": "actual", "type": "files", "sources": [str(data)], "databases": []},
                ],
            )
            loaded = services.load_services(catalog)
        self.assertEqual(set(loaded), {"configs", "actual"})
        self.assertEqual(loaded["actual"].sources, (data,))
        self.assertEqual(loaded["actual"].description, "actual")

    def test_production_catalog_loads(self) -> None:
        catalog = Path(__file__).resolve().parents[1] / "services.json"
        loaded = services.load_services(catalog)
        self.assertEqual(len(loaded), 11)
        self.assertIn("immich", loaded)
        self.assertEqual(loaded["configs"].kind, "env_configs")

    def test_rejects_top_level_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "services.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ConfigError):
                services.load_services(path)

    def test_rejects_unknown_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = write_catalog(
                Path(temp),
                [{"name": "actual", "type": "files", "sources": ["/tmp/data"], "unexpected": True}],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_rejects_invalid_and_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = write_catalog(
                root,
                [
                    {"name": "Bad Name", "type": "files", "sources": ["/tmp/data"]},
                ],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)
            catalog = write_catalog(
                root,
                [
                    {"name": "actual", "type": "files", "sources": ["/tmp/a"]},
                    {"name": "actual", "type": "files", "sources": ["/tmp/b"]},
                ],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_rejects_invalid_type_and_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = write_catalog(
                root,
                [{"name": "actual", "type": "unknown", "sources": ["/tmp/data"]}],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)
            catalog = write_catalog(
                root,
                [{"name": "actual", "type": "files", "sources": ["/tmp/data"], "databases": ["bad-name"]}],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_files_requires_sources_or_databases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = write_catalog(Path(temp), [{"name": "actual", "type": "files"}])
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_env_configs_requires_absolute_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = write_catalog(
                Path(temp),
                [{"name": "configs", "type": "env_configs", "root": "relative/path"}],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_env_configs_rejects_file_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = write_catalog(
                root,
                [
                    {
                        "name": "configs",
                        "type": "env_configs",
                        "root": str(root),
                        "sources": [str(root / "data")],
                    }
                ],
            )
            with self.assertRaises(ConfigError):
                services.load_services(catalog)

    def test_parses_stop_config_and_expands_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.dict(os.environ, {"VOL": "volume"}, clear=True):
                catalog = write_catalog(
                    root,
                    [
                        {
                            "name": "actual",
                            "type": "files",
                            "sources": ["/docker-volumes/${VOL}/_data"],
                            "stop": {"project": "actual", "services": ["actual_server"]},
                        }
                    ],
                )
                loaded = services.load_services(catalog)
            self.assertEqual(loaded["actual"].sources, (Path("/docker-volumes/volume/_data"),))
            self.assertEqual(loaded["actual"].stop, StopConfig("actual", ("actual_server",)))

    def test_missing_catalog_raises(self) -> None:
        with self.assertRaises(ConfigError):
            services.load_services(Path(tempfile.gettempdir()) / "does-not-exist.json")


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "actual": Service("actual", "Actual", "files"),
            "immich": Service("immich", "Immich", "files"),
            "configs": Service("configs", "Configs", "env_configs"),
        }

    def test_preserves_order_and_removes_duplicates(self) -> None:
        selected = services.selected_services(self.config, raw="immich actual immich")
        self.assertEqual([service.name for service in selected], ["immich", "actual"])

    def test_empty_requires_value(self) -> None:
        with self.assertRaises(ConfigError):
            services.selected_services(self.config, raw="")
        self.assertEqual(services.selected_services(self.config, raw="", require=False), [])

    def test_unknown_service_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            services.selected_services(self.config, raw="actual nope")


class SourceResolutionTests(unittest.TestCase):
    def test_collects_root_and_child_env_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".env").write_text("A=B", encoding="utf-8")
            (root / "one").mkdir()
            (root / "one" / ".env").write_text("C=D", encoding="utf-8")
            (root / "two").mkdir()
            (root / "two" / ".env").write_text("E=F", encoding="utf-8")
            service = Service(
                "configs",
                "Configs",
                "env_configs",
                root=root,
                env_excludes=(root / "two" / ".env",),
            )
            sources = services.collect_env_sources(service)
        self.assertEqual(sources, [root / ".env", root / "one" / ".env"])

    def test_collects_nothing_when_root_missing(self) -> None:
        service = Service("configs", "Configs", "env_configs", root=Path("/missing"))
        with self.assertRaises(BackupError):
            services.collect_env_sources(service)

    def test_resolves_required_and_optional_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            required = root / "required"
            optional = root / "optional"
            required.mkdir()
            optional.mkdir()
            service = Service(
                "actual",
                "Actual",
                "files",
                sources=(required,),
                optional_sources=(optional, root / "missing"),
            )
            self.assertEqual(services.resolve_sources(service), [required, optional])

    def test_missing_required_source_raises(self) -> None:
        service = Service("actual", "Actual", "files", sources=(Path("/missing"),))
        with self.assertRaises(BackupError):
            services.resolve_sources(service)

    def test_postgres_cluster_has_no_file_sources(self) -> None:
        service = Service("datastore-sql", "DB", "postgres_cluster")
        self.assertEqual(services.resolve_sources(service), [])

    def test_database_only_service_can_have_no_files(self) -> None:
        service = Service("actual", "Actual", "files", databases=("actual",))
        self.assertEqual(services.resolve_sources(service), [])
