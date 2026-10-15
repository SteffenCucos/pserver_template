
from server.auth.rbac import PermissionTree, TreeStore
from server.models.base.id import Id


def test_new_tree_store_has_empty_caches() -> None:
    store = TreeStore()

    assert store.role_ids_by_user_id == {}
    assert store.role_tree_by_role_id == {}


def test_invalidate_user_removes_only_that_users_role_cache() -> None:
    store = TreeStore()
    first_user_id = Id("first-user")
    second_user_id = Id("second-user")
    store.role_ids_by_user_id[first_user_id] = [Id("admin")]
    store.role_ids_by_user_id[second_user_id] = [Id("reader")]

    store.invalidate_user(first_user_id)
    store.invalidate_user(Id("missing-user"))

    assert first_user_id not in store.role_ids_by_user_id
    assert store.role_ids_by_user_id == {second_user_id: [Id("reader")]}


def test_invalidate_role_removes_only_that_roles_permission_tree() -> None:
    store = TreeStore()
    first_role_id = Id("admin")
    second_role_id = Id("reader")
    first_tree = PermissionTree()
    second_tree = PermissionTree()
    store.role_tree_by_role_id[first_role_id] = first_tree
    store.role_tree_by_role_id[second_role_id] = second_tree

    store.invalidate_role(first_role_id)
    store.invalidate_role(Id("missing-role"))

    assert first_role_id not in store.role_tree_by_role_id
    assert store.role_tree_by_role_id == {second_role_id: second_tree}


def test_clear_removes_user_role_and_role_permission_caches() -> None:
    store = TreeStore()
    store.role_ids_by_user_id[Id("user")] = [Id("admin")]
    store.role_tree_by_role_id[Id("admin")] = PermissionTree()

    store.clear()

    assert store.role_ids_by_user_id == {}
    assert store.role_tree_by_role_id == {}
