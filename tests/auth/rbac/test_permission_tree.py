
from server.auth.rbac import PermissionTree


def build_tree(patterns: list[str]) -> PermissionTree:
    tree = PermissionTree()
    for pattern in patterns:
        tree.add(pattern)
    return tree


def test_deep_exact_path_does_not_grant_prefixes_or_children():
    tree = build_tree([
        "read/tenant/acme/env/prod/service/billing/resource/invoice",
    ])

    assert tree.allows("read/tenant/acme/env/prod/service/billing/resource/invoice")
    assert not tree.allows("read/tenant/acme/env/prod/service/billing/resource")
    assert not tree.allows("read/tenant/acme/env/prod/service/billing/resource/invoice/items")
    assert not tree.allows("read/tenant/acme/env/staging/service/billing/resource/invoice")
    assert not tree.allows("write/tenant/acme/env/prod/service/billing/resource/invoice")


def test_overlapping_exact_and_single_segment_wildcards():
    tree = build_tree([
        "read/tenant/acme/env/prod/service/billing/resource/invoice",
        "list/tenant/acme/env/prod/service/billing/resource/*",
        "read/tenant/acme/env/*/service/analytics/resource/report",
    ])

    assert tree.allows("read/tenant/acme/env/prod/service/billing/resource/invoice")
    assert tree.allows("list/tenant/acme/env/prod/service/billing/resource/customer")
    assert tree.allows("read/tenant/acme/env/staging/service/analytics/resource/report")

    assert not tree.allows("read/tenant/acme/env/prod/service/billing/resource/customer")
    assert not tree.allows("list/tenant/acme/env/prod/service/billing/resource/customer/profile")
    assert not tree.allows("read/tenant/acme/env/staging/service/billing/resource/invoice")
    assert not tree.allows("write/tenant/acme/env/prod/service/billing/resource/invoice")


def test_deep_wildcard_grants_whole_object_subtree_for_one_action_only():
    tree = build_tree([
        "manage/tenant/acme/env/prod/service/control/**",
        "read/tenant/acme/env/prod/service/billing/resource/invoice",
    ])

    assert tree.allows("manage/tenant/acme/env/prod/service/control")
    assert tree.allows("manage/tenant/acme/env/prod/service/control/users")
    assert tree.allows("manage/tenant/acme/env/prod/service/control/users/123/groups")
    assert tree.allows("read/tenant/acme/env/prod/service/billing/resource/invoice")

    assert not tree.allows("write/tenant/acme/env/prod/service/control/users/123/groups")
    assert not tree.allows("read/tenant/acme/env/prod/service/billing/resource/invoice/items")
    assert not tree.allows("manage/tenant/acme/env/prod/service/controller/users")
    assert not tree.allows("manage/tenant/acme/env/staging/service/control/users")


def test_many_sibling_branches_do_not_bleed_into_each_other():
    tree = build_tree([
        "read/org/*/project/*/dataset/*",
        "export/org/*/project/*/dataset/*/csv",
        "write/org/acme/project/payroll/dataset/salaries",
        "manage/org/acme/project/platform/**",
        "read/org/umbrella/project/research/dataset/cells",
    ])

    assert tree.allows("read/org/acme/project/payroll/dataset/salaries")
    assert tree.allows("write/org/acme/project/payroll/dataset/salaries")
    assert tree.allows("export/org/acme/project/payroll/dataset/salaries/csv")
    assert tree.allows("manage/org/acme/project/platform/incidents/2026")
    assert tree.allows("read/org/umbrella/project/research/dataset/cells")

    assert not tree.allows("export/org/acme/project/payroll/dataset/salaries/json")
    assert not tree.allows("remove/org/acme/project/payroll/dataset/salaries")
    assert not tree.allows("write/org/umbrella/project/research/dataset/cells")
    assert not tree.allows("manage/org/umbrella/project/platform/incidents/2026")


def test_wildcard_object_path_depth_is_strict_after_action():
    tree = build_tree([
        "read/users/*",
        "read/teams/*/members/*",
    ])

    assert tree.allows("read/users/123")
    assert tree.allows("read/teams/eng/members/456")

    assert not tree.allows("read/users/123/profile")
    assert not tree.allows("read/users")
    assert not tree.allows("read/teams/eng/members")
    assert not tree.allows("read/teams/eng/members/456/profile")
    assert not tree.allows("write/users/123")


def test_deep_wildcard_can_coexist_with_more_specific_sibling_rules():
    tree = build_tree([
        "read/system/audit/**",
        "read/system/config",
        "read/system/config/values/*",
    ])

    assert tree.allows("read/system/audit")
    assert tree.allows("read/system/audit/events/2026/07/06")
    assert tree.allows("read/system/config")
    assert tree.allows("read/system/config/values/database")

    assert not tree.allows("write/system/config")
    assert not tree.allows("write/system/config/values/database")
    assert not tree.allows("read/system/config/values/database/detail")


def test_order_of_inserted_patterns_does_not_change_results():
    patterns = [
        "read/a/b/c/d/e/f/g/h/i/j",
        "list/a/b/*/d/*/f/*/h/*/j",
        "remove/a/b/c/d/e/f/g/**",
        "manage/x/**",
        "read/x/y/z/exact",
    ]

    forward = build_tree(patterns)
    reverse = build_tree(list(reversed(patterns)))

    allowed = [
        "read/a/b/c/d/e/f/g/h/i/j",
        "list/a/b/other/d/other/f/other/h/other/j",
        "remove/a/b/c/d/e/f/g/h/i/j",
        "manage/x",
        "manage/x/y/z/anything",
    ]
    denied = [
        "read/a/b/c/d/e/f",
        "list/a/b/other/d/other/f/other/h/other/j/extra",
        "read/a/b/other/d/other/f/other/h/other/j",
        "manage/y/x/z/anything",
    ]

    for path in allowed:
        assert forward.allows(path)
        assert reverse.allows(path)

    for path in denied:
        assert not forward.allows(path)
        assert not reverse.allows(path)
