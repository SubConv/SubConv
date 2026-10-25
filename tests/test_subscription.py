import asyncio

import pytest
import yaml

from subconv import subscription
from subconv.converter.util import ParseError
from subconv.yaml_utils import load_yaml


@pytest.mark.parametrize('value', ['on', 'off', 'yes', 'no', 'ON', 'NO'])
def test_mihomo_implicit_strings_are_preserved_without_global_loader_changes(value):
    raw = f'proxies: [{{name: {value}, type: trojan, server: {value}, port: 443, password: {value}}}]'
    node = asyncio.run(subscription.parse_nodes(raw))[0]
    assert node['name'] == node['server'] == node['password'] == value
    assert yaml.safe_load(value) in (True, False)


def test_true_false_remain_yaml_booleans():
    loaded = load_yaml('proxies: [{name: A, udp: true, tls: false}]')
    assert loaded['proxies'][0]['udp'] is True
    assert loaded['proxies'][0]['tls'] is False


def test_proxy_budget_applies_to_yaml_subscriptions(monkeypatch):
    from subconv.converter.util import ProxyBudget
    monkeypatch.setattr(subscription, 'ProxyBudget', lambda: ProxyBudget(max_nodes=2))
    with pytest.raises(ParseError, match='node limit'):
        asyncio.run(subscription.parse_nodes('proxies: [{name: A}, {name: B}, {name: C}]'))


def test_names_do_not_depend_on_yaml_key_order_or_quotes():
    raw = 'proxies:\n- type: trojan\n  name: "HK: AI"\n  port: 443\n'
    result = asyncio.run(subscription.parseSubs(raw))
    assert [node['name'] for node in yaml.safe_load(result)['proxies']] == ['HK: AI']


def test_anchors_and_merge_keys_are_supported_and_preserved():
    raw = '''defaults: &defaults
  type: trojan
  server: example.com
  port: 443
  password: pw
proxies:
- <<: *defaults
  name: A
  alpn: &alpn [h2, http/1.1]
- <<: *defaults
  name: B
  alpn: *alpn
'''
    result = asyncio.run(subscription.parseSubs(raw))
    nodes = yaml.safe_load(result)['proxies']
    assert [node['server'] for node in nodes] == ['example.com', 'example.com']
    assert nodes[0]['alpn'] is nodes[1]['alpn']
    assert '&id' in result and '*id' in result


@pytest.mark.parametrize('raw', [
    'proxies: &a [*a]',
    'a: &a [x,x,x,x,x,x]\nb: &b [*a,*a,*a,*a,*a,*a]\nc: &c [*b,*b,*b,*b,*b,*b]\nd: &d [*c,*c,*c,*c,*c,*c]\ne: &e [*d,*d,*d,*d,*d,*d]\nf: &f [*e,*e,*e,*e,*e,*e]\nproxies: [*f,*f,*f,*f,*f,*f]',
    'proxies: [[' + '[' * 40 + 'x' + ']' * 40 + ']]',
])
def test_unsafe_yaml_graphs_are_rejected_before_serializing(raw):
    with pytest.raises(yaml.YAMLError):
        load_yaml(raw)
    with pytest.raises(ParseError):
        asyncio.run(subscription.parseSubs(raw))


@pytest.mark.parametrize('raw', ['proxies: null', 'proxies: []', 'proxies: [[x]]', 'proxies: [{name: 7}]'])
def test_invalid_proxy_shapes_are_rejected(raw):
    with pytest.raises(ParseError):
        asyncio.run(subscription.parseSubs(raw))


@pytest.mark.parametrize('raw', ['{proxies: [', '{other: []}', '[trojan://pw@example.com:443]', 'proxies: [\n  name: missing-bracket'])
def test_malformed_yaml_is_not_reinterpreted_as_share_links(raw):
    with pytest.raises(ParseError):
        asyncio.run(subscription.parseSubs(raw))


def test_repeated_large_scalar_aliases_are_bounded(monkeypatch):
    from subconv import yaml_utils
    monkeypatch.setattr(yaml_utils, 'MAX_CONTENT_BYTES', 1024)
    raw = 'value: &v ' + 'x' * 100 + '\nproxies: [' + ','.join(['*v'] * 20) + ']'
    assert len(raw.encode()) < 1024
    with pytest.raises(yaml.YAMLError, match='expanded size'):
        load_yaml(raw)


def test_invalid_unicode_escape_is_a_parse_error():
    with pytest.raises(ParseError):
        asyncio.run(subscription.parseSubs('proxies: [{name: "\\ud800"}]'))


@pytest.mark.parametrize('value', ['2001-13-01', '!!timestamp invalid', '!!float nope', '!!int nope', "!!int ''", "!!float ''", '!!bool nope'])
def test_malformed_typed_yaml_scalars_are_parse_errors(value):
    raw = 'proxies: [{name: A, extra: ' + value + '}]'
    with pytest.raises(yaml.YAMLError):
        load_yaml(raw)
    with pytest.raises(ParseError):
        asyncio.run(subscription.parseSubs(raw))


def test_unexpected_yaml_constructor_errors_are_not_hidden(monkeypatch):
    from subconv.yaml_utils import LimitedSafeLoader
    def broken_constructor(*args, **kwargs): raise RuntimeError('constructor defect')
    monkeypatch.setattr(LimitedSafeLoader, 'construct_document', broken_constructor)
    with pytest.raises(RuntimeError, match='constructor defect'):
        asyncio.run(subscription.parseSubs('proxies: [{name: A}]'))


def test_unrenderable_yaml_integer_is_a_parse_error():
    raw = 'proxies: [{name: A, type: direct, extra: 0x' + 'f' * 4000 + '}]'
    with pytest.raises(ParseError, match='Integer field'):
        asyncio.run(subscription.parseSubs(raw))
