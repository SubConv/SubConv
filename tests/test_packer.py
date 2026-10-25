import asyncio
import re

import pytest

import yaml

from subconv import config, packer, subscription
from subconv.filters import compile_group_filter, filter_names


NODE = {'name': 'HK', 'type': 'trojan', 'server': 'proxy.example', 'port': 443, 'password': 'pw'}


@pytest.mark.parametrize('source', ['(?P<region>HK)', '(?<region>HK)'])
def test_named_group_filters_are_normalized_for_both_engines(source):
    patterns, output = compile_group_filter(source)
    assert filter_names(patterns, ['HK', 'JP']) == ['HK']
    assert output == '(?i)(?<region>HK)'


def test_backtick_filters_preserve_priority_and_deduplicate_nodes():
    patterns, output = compile_group_filter('JP`HK`JP')
    assert output == '(?i)JP`(?i)HK`(?i)JP'
    assert filter_names(patterns, ['HK', 'JP']) == ['JP', 'HK']


@pytest.mark.parametrize('source', [r'\(\?P<region>', r'[(?P<]', r'[^^](?<region>HK)', '(?x)HK # (?P<ignored>'])
def test_filter_normalization_respects_literals_classes_and_comments(source):
    patterns, output = compile_group_filter(source)
    assert patterns and output


@pytest.mark.parametrize('source', [r'(?a:HK)', r'(?u)HK', r'\U0001F1ED', r'\N{LATIN CAPITAL LETTER H}', r'H++K', r'(H)\1', r'(H)?(?(1)K|J)', r'[a-z-[aeiou]]', '('])
def test_incompatible_filters_fail_during_template_validation(source):
    with pytest.raises(ValueError):
        config.Group(name='region', type='select', regex=source)


def test_packer_omits_empty_groups_without_regex():
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='auto', type='select', rule=False),
        config.Group(name='manual', type='select', rule=False, manual=True),
    ])
    result = yaml.safe_load(pack(template, urlstandalone=None, urlstandbystandalone=[NODE]))
    assert [group['name'] for group in result['proxy-groups']] == ['🚀 节点选择', 'manual']


def pack(template=None, **kwargs):
    arguments = dict(url=None, urlstandalone=[NODE], urlstandby=None,
                     urlstandbystandalone=None, provider_names=[], interval=1800,
                     domain='converter.example', short=None, notproxyrule=None,
                     base_url='https://converter.example/', template_name='general',
                     template_config=template or config.TemplateConfig())
    arguments.update(kwargs)
    return asyncio.run(packer.pack(**arguments))


def test_main_and_standby_names_are_unique_and_references_follow_renames():
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='manual', type='select', rule=False, manual=True),
        config.Group(name='auto', type='select', rule=False),
    ])
    result = yaml.safe_load(pack(template, urlstandbystandalone=[NODE]))
    assert [node['name'] for node in result['proxies']] == ['HK', 'HK-01']
    groups = {group['name']: group for group in result['proxy-groups']}
    assert groups['manual']['proxies'] == ['HK', 'HK-01']
    assert groups['auto']['proxies'] == ['HK']
    assert NODE['name'] == 'HK'


def test_inline_rules_remain_complete_and_ordered():
    template = config.TemplateConfig(RULESET=[
        ('DIRECT', '[]IP-CIDR,10.0.0.0/8'),
        ('DIRECT', '[]DOMAIN-SUFFIX,example.com'),
        ('DIRECT', '[]FINAL'),
    ])
    result = yaml.safe_load(pack(template))
    assert result['rules'][1:] == ['IP-CIDR,10.0.0.0/8,DIRECT', 'DOMAIN-SUFFIX,example.com,DIRECT', 'MATCH,DIRECT']
    assert result['rule-providers'] == {}


def test_type_first_subscription_retains_default_groups():
    raw = 'proxies:\n- type: trojan\n  name: HK-node\n  server: proxy.example\n  port: 443\n  password: pw\n'
    nodes = asyncio.run(subscription.parse_nodes(raw))
    result = yaml.safe_load(pack(config.load_template('zju'), url=['https://provider.example'], urlstandalone=None, provider_names=[node["name"] for node in nodes]))
    names = {group['name'] for group in result['proxy-groups']}
    assert {'♻️ 自动选择', '🇭🇰 香港节点'} <= names


def test_manual_regex_uses_node_names_and_keeps_unknown_standby_providers():
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='manual-HK', type='select', rule=False, manual=True, regex='HK'),
    ])
    result = yaml.safe_load(pack(template, url=['https://provider.example'], urlstandalone=None,
                                 provider_names=['HK-node']))
    group = result['proxy-groups'][1]
    assert group['name'] == 'manual-HK'
    assert group['use'] == ['subscription0']
    result = yaml.safe_load(pack(template, urlstandalone=None, urlstandby=['https://standby.example']))
    assert result['proxy-groups'][1]['use'] == ['subscriptionsub0']


def test_packing_does_not_change_global_yaml_alias_behavior():
    shared = ['a', 'b']
    before = yaml.safe_dump({'a': shared, 'b': shared})
    pack()
    assert yaml.safe_dump({'a': shared, 'b': shared}) == before


def test_duplicate_remote_ruleset_names_are_stable():
    template = config.TemplateConfig(RULESET=[
        ('DIRECT', 'https://a.example/foo.list'), ('DIRECT', 'https://b.example/foo.list'),
    ])
    first = pack(template)
    assert first == pack(template)
    assert list(yaml.safe_load(first)['rule-providers']) == ['foo', 'foo-1']


def test_inline_rule_options_follow_policy():
    template = config.TemplateConfig(RULESET=[
        ('DIRECT', '[]IP-CIDR,10.0.0.0/8,no-resolve,src'),
        ('DIRECT', '[]DOMAIN,src'),
    ])
    result = yaml.safe_load(pack(template))
    assert result['rules'][1:] == [
        'IP-CIDR,10.0.0.0/8,DIRECT,no-resolve,src', 'DOMAIN,src,DIRECT',
    ]


@pytest.mark.parametrize('regex', ['(?x)HK # Hong Kong', '(?x)HK # comment\n | JP', '(?-i:HK)|jp'])
def test_group_filter_remains_valid_with_inline_regex_flags_and_comments(regex):
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='region', type='select', rule=False, regex=regex),
    ])
    result = yaml.safe_load(pack(template))
    group = next(group for group in result['proxy-groups'] if group['name'] == 'region')
    assert re.compile(group['filter']).search('HK')
    assert group['proxies'] == ['HK']


@pytest.mark.parametrize('kind', ['DOMAIN-REGEX', 'PROCESS-NAME-REGEX', 'PROCESS-PATH-REGEX'])
@pytest.mark.parametrize('ending', ['src', 'no-resolve'])
def test_regex_rule_payload_is_not_reinterpreted_as_options(kind, ending):
    raw_rule = f'{kind},my,{ending}'
    template = config.TemplateConfig(RULESET=[('DIRECT', '[]' + raw_rule)])
    result = yaml.safe_load(pack(template))
    assert result['rules'][1] == raw_rule + ',DIRECT'


def test_pass_rule_builtin_name_is_reserved_and_references_follow_renames():
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='manual', type='select', rule=False, manual=True),
    ])
    node = {**NODE, 'name': 'PASS-RULE'}
    result = yaml.safe_load(pack(template, urlstandalone=[node], urlstandbystandalone=[node]))
    assert [proxy['name'] for proxy in result['proxies']] == ['PASS-RULE-01', 'PASS-RULE-02']
    assert result['proxy-groups'][1]['proxies'] == ['PASS-RULE-01', 'PASS-RULE-02']


@pytest.mark.parametrize('source', ['a{2147483648}', 'a{0,2147483648}', 'a{,2}', '(?P<é>a)', 'a{' + '9' * 5000 + '}'])
def test_filters_reject_regexp2_incompatible_groups_and_quantifier_limits(source):
    with pytest.raises(ValueError):
        config.Group(name='region', type='select', regex=source)


def test_non_ascii_digits_in_braces_remain_literal():
    patterns, output = compile_group_filter('a{,٢}')
    assert output == '(?i)a{,٢}'
    assert patterns[0].search('a{,٢}')


@pytest.mark.parametrize('regex,name', [('^[^ς]$', 'σ'), ('^[^ı]$', 'i'), (r'^[^\u0131]$', 'i'), (r'^\S$', '\x1c')])
def test_direct_nodes_follow_subconv_unicode_matching(regex, name):
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='region', type='select', rule=False, regex=regex),
    ])
    result = yaml.safe_load(pack(template, urlstandalone=[{**NODE, 'name': name}]))
    assert [group['name'] for group in result['proxy-groups']] == ['🚀 节点选择']


def test_default_regions_filter_direct_nodes_instead_of_deferring_to_client():
    result = yaml.safe_load(pack(config.load_template('zju'), urlstandalone=[NODE, {**NODE, 'name': 'JP'}]))
    groups = {group['name']: group for group in result['proxy-groups']}
    assert groups['🇭🇰 香港节点']['proxies'] == ['HK']
    assert groups['🇯🇵 日本节点']['proxies'] == ['JP']
    assert '🇺🇸 美国节点' not in groups
    assert not groups['🇭🇰 香港节点'].get('use')


def test_manual_unicode_filter_keeps_only_matching_primary_and_standby_nodes():
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='auto', type='select', rule=False, regex='香港'),
        config.Group(name='manual', type='select', rule=False, manual=True, regex='香港'),
    ])
    result = yaml.safe_load(pack(template, urlstandalone=[{**NODE, 'name': '香港主'}, {**NODE, 'name': '日本'}],
                                 urlstandbystandalone=[{**NODE, 'name': '香港备'}]))
    groups = {group['name']: group for group in result['proxy-groups']}
    assert groups['auto']['proxies'] == ['香港主']
    assert groups['manual']['proxies'] == ['香港主', '香港备']


def test_uncertain_remote_unicode_names_remain_available_for_client_filtering():
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='region', type='select', rule=False, regex='^[^ς]$'),
    ])
    result = yaml.safe_load(pack(template, url=['https://provider.example'], urlstandalone=None, provider_names=['σ']))
    assert result['proxy-groups'][1]['use'] == ['subscription0']
    assert 'proxies' not in result['proxy-groups'][1]


@pytest.mark.parametrize('source,output,name', [(r'\_', '(?i)_', '_a'), (r'\é', '(?i)é', 'é'), (r'(?#a\))a', '(?i)a', 'a')])
def test_python_literal_escapes_and_comments_produce_valid_remote_syntax(source, output, name):
    patterns, remote = compile_group_filter(source)
    assert remote == output
    assert filter_names(patterns, [name]) == [name]


def test_strict_python_end_anchor_is_preserved_for_direct_nodes():
    patterns, output = compile_group_filter(r'HK\Z')
    assert filter_names(patterns, ['HK', 'HK\n']) == ['HK']
    assert output == r'(?i)HK\z'
    template = config.TemplateConfig(CUSTOM_PROXY_GROUP=[
        config.Group(name='region', type='select', rule=False, regex=r'HK\Z'),
    ])
    result = yaml.safe_load(pack(template, urlstandalone=[NODE, {**NODE, 'name': 'HK\n'}]))
    assert result['proxy-groups'][1]['proxies'] == ['HK']
