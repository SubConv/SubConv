"""Tests for subconv.converter.registry.NameRegistry deduplication."""

from subconv.converter.registry import NameRegistry


def test_first_registration_returns_name_unchanged(registry):
    assert registry.register("HK-Node") == "HK-Node"


def test_duplicate_names_get_zero_padded_suffixes(registry):
    assert registry.register("HK") == "HK"
    assert registry.register("HK") == "HK-01"
    assert registry.register("HK") == "HK-02"
    assert registry.register("HK") == "HK-03"


def test_distinct_names_are_independent(registry):
    assert registry.register("JP") == "JP"
    assert registry.register("HK") == "HK"
    assert registry.register("JP") == "JP-01"
    assert registry.register("HK") == "HK-01"


def test_empty_name_is_tracked(registry):
    assert registry.register("") == ""
    assert registry.register("") == "-01"


def test_registries_do_not_share_state():
    first = NameRegistry()
    second = NameRegistry()
    first.register("Node")
    assert second.register("Node") == "Node"


def test_generated_suffixes_cannot_collide_with_original_names(registry):
    names = [registry.register(name) for name in ["HK", "HK", "HK-01", "HK", "HK-02"]]
    assert len(set(names)) == len(names)
