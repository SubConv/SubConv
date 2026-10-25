"""Bound YAML work while preserving ordinary anchors, aliases and merge keys."""

import re

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

MAX_CONTENT_BYTES = 10 * 1024 * 1024
MAX_YAML_NODES = 100_000
MAX_YAML_DEPTH = 32


class LimitedSafeLoader(yaml.SafeLoader):
    # yaml.v3 retains on/off/yes/no as strings in untyped mappings. Keep this
    # resolver change local; templates/settings and third-party loaders retain
    # their own resolver tables.
    yaml_implicit_resolvers = {
        key: [(tag, pattern) for tag, pattern in values if tag != "tag:yaml.org,2002:bool"]
        for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    _typed_scalar_tags = {
        f"tag:yaml.org,2002:{kind}"
        for kind in ("bool", "int", "float", "timestamp", "binary")
    }

    def __init__(self, stream):
        super().__init__(stream)
        self.node_count = 0
        self.node_depth = 0

    def compose_node(self, parent, index):
        self.node_count += 1
        self.node_depth += 1
        try:
            if self.node_count > MAX_YAML_NODES or self.node_depth > MAX_YAML_DEPTH:
                raise yaml.YAMLError("YAML exceeds structure limits")
            return super().compose_node(parent, index)
        finally:
            self.node_depth -= 1

    def construct_object(self, node, deep=False):
        try:
            return super().construct_object(node, deep=deep)
        except (ValueError, AttributeError, KeyError, IndexError, OverflowError) as exc:
            # PyYAML's built-in typed scalar constructors do not consistently
            # wrap malformed values in YAMLError. Normalize only this boundary;
            # unrelated construction/programming errors must still propagate.
            if isinstance(node, ScalarNode) and node.tag in self._typed_scalar_tags:
                raise yaml.constructor.ConstructorError(
                    None, None, "Invalid YAML scalar", node.start_mark
                ) from exc
            raise


LimitedSafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def dump_yaml(value) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def _utf8_size(value: str) -> int:
    try:
        return len(value.encode("utf-8"))
    except UnicodeError as exc:
        raise yaml.YAMLError("Invalid Unicode in YAML") from exc


def load_yaml(content: str):
    if _utf8_size(content) > MAX_CONTENT_BYTES:
        raise yaml.YAMLError("YAML exceeds size limit")
    loader = LimitedSafeLoader(content)
    try:
        node = loader.get_single_node()
        if node is None:
            return None
        costs = {}
        visiting = set()

        def cost(current, depth):
            if depth > MAX_YAML_DEPTH or current in visiting:
                raise yaml.YAMLError("Recursive or excessively deep YAML aliases")
            if current in costs:
                size, height, byte_size = costs[current]
                if depth + height > MAX_YAML_DEPTH:
                    raise yaml.YAMLError("YAML exceeds depth limit")
                return size, height, byte_size
            visiting.add(current)
            if isinstance(current, ScalarNode):
                children = []
            elif isinstance(current, SequenceNode):
                children = current.value
            elif isinstance(current, MappingNode):
                children = [item for pair in current.value for item in pair]
            else:
                raise yaml.YAMLError("Unsupported YAML node")
            size, height = 1, 0
            byte_size = _utf8_size(current.value) if isinstance(current, ScalarNode) else 0
            for child in children:
                child_size, child_height, child_bytes = cost(child, depth + 1)
                size += child_size
                byte_size += child_bytes
                if byte_size > MAX_CONTENT_BYTES:
                    raise yaml.YAMLError("YAML aliases exceed expanded size limit")
                height = max(height, child_height + 1)
                if size > MAX_YAML_NODES:
                    raise yaml.YAMLError("YAML aliases exceed expansion limit")
            visiting.remove(current)
            costs[current] = size, height, byte_size
            return size, height, byte_size

        # Merge keys can copy mappings, so check before constructing objects.
        cost(node, 0)
        return loader.construct_document(node)
    finally:
        loader.dispose()
