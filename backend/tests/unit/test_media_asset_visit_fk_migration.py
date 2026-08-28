from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest


@pytest.fixture
def migration() -> ModuleType:
    path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "20260828_0000_0015_media_assets_visit_fk.py"
    )
    spec = spec_from_file_location("migration_0015", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_aborts_without_ddl_when_orphans_exist(
    migration: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = Mock()
    result.scalar_one.return_value = 2
    bind = Mock()
    bind.execute.return_value = result
    create_foreign_key = Mock()
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "create_foreign_key", create_foreign_key)

    with pytest.raises(RuntimeError, match="found 2 orphaned row"):
        migration.upgrade()

    create_foreign_key.assert_not_called()


def test_upgrade_and_downgrade_manage_only_the_named_constraint(
    migration: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = Mock()
    result.scalar_one.return_value = 0
    bind = Mock()
    bind.execute.return_value = result
    create_foreign_key = Mock()
    drop_constraint = Mock()
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "create_foreign_key", create_foreign_key)
    monkeypatch.setattr(migration.op, "drop_constraint", drop_constraint)

    migration.upgrade()
    migration.downgrade()

    create_foreign_key.assert_called_once_with(
        "fk_media_assets_visit_id_visits",
        "media_assets",
        "visits",
        ["visit_id"],
        ["id"],
        source_schema="operations",
        referent_schema="operations",
        ondelete="NO ACTION",
    )
    drop_constraint.assert_called_once_with(
        "fk_media_assets_visit_id_visits",
        "media_assets",
        schema="operations",
        type_="foreignkey",
    )
