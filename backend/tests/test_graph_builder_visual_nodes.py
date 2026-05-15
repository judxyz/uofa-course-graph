"""Tests for omitting pass-through label groups during graph assembly."""

from __future__ import annotations

from graph_builder import (
    GraphBuilder,
    GroupRecord,
    CourseRecord,
    ItemRecord,
    is_relation_label_group,
    is_redundant_root_and_wrapper,
    should_omit_visual_group_node,
)


def _course(course_id: int, code: str) -> CourseRecord:
    subject, number = code.split()
    return CourseRecord(
        id=course_id,
        code=code,
        subject=subject,
        number=int(number),
        title=code,
        description=None,
        other_notes=None,
        raw_prereq_text=None,
        raw_coreq_text=None,
        catalog_url=None,
        parse_status="parsed",
    )


def _group(
    group_id: int,
    course_id: int,
    group_type: str,
    *,
    display_label: str | None = None,
    visual_style: str | None = None,
    parent_group_id: int | None = None,
) -> GroupRecord:
    return GroupRecord(
        id=group_id,
        course_id=course_id,
        group_type=group_type,
        parent_group_id=parent_group_id,
        display_label=display_label,
        visual_style=visual_style,
    )


def _item(
    item_id: int,
    group_id: int,
    required_course_id: int,
    *,
    relation_type: str = "PREREQ",
) -> ItemRecord:
    return ItemRecord(
        id=item_id,
        group_id=group_id,
        required_course_id=required_course_id,
        relation_type=relation_type,
        item_order=1,
        missing_course_code=None,
        requirement_text=None,
        course_code="MATH 114",
        course_subject="MATH",
        course_number=114,
        course_title="Calc",
        course_parse_status="parsed",
    )


class ScenarioGraphBuilder(GraphBuilder):
    """GraphBuilder backed by in-memory scenario data instead of PostgreSQL."""

    def __init__(
        self,
        *,
        root_course: CourseRecord,
        courses: dict[int, CourseRecord] | None = None,
        groups_by_course: dict[int, list[GroupRecord]] | None = None,
        subgroups_by_group: dict[int, list[GroupRecord]] | None = None,
        items_by_group: dict[int, list[ItemRecord]] | None = None,
        max_depth: int = 2,
        include_coreqs: bool = True,
    ):
        self._root_course = root_course
        self._courses = courses or {}
        self._groups_by_course = groups_by_course or {}
        self._subgroups_by_group = subgroups_by_group or {}
        self._items_by_group = items_by_group or {}
        super().__init__(conn=object(), max_depth=max_depth, include_coreqs=include_coreqs)
        self._course_cache = {root_course.id: root_course, **self._courses}

    def _fetch_groups_for_course(self, course_id: int) -> list[GroupRecord]:
        return self._groups_by_course.get(course_id, [])

    def _fetch_subgroups_for_group(self, group_id: int) -> list[GroupRecord]:
        return self._subgroups_by_group.get(group_id, [])

    def _fetch_items_for_group(self, group_id: int) -> list[ItemRecord]:
        return self._items_by_group.get(group_id, [])

    def _fetch_course_by_id(self, course_id: int) -> CourseRecord | None:
        return self._course_cache.get(course_id)


def _expand_root(builder: ScenarioGraphBuilder) -> str:
    root_id = builder._add_course_node(builder._root_course, depth=0)
    builder._expand_course(
        builder._root_course,
        course_node_id=root_id,
        depth=0,
        course_depth=0,
        path={builder._root_course.id},
    )
    return root_id


def test_is_relation_label_group_prereq_resolved_type():
    group = _group(1, 1, "UNKNOWN", display_label="PREREQ")
    assert is_relation_label_group(group, "PREREQ") is True


def test_is_relation_label_group_keeps_styled_coreq_or():
    group = _group(1, 1, "COREQ", display_label="COREQ", visual_style="or")
    assert is_relation_label_group(group, "COREQ") is False


def test_is_redundant_root_and_wrapper_only_at_depth_one():
    group = _group(1, 1, "ALL_OF")
    assert is_redundant_root_and_wrapper(group, 1) is True
    assert is_redundant_root_and_wrapper(group, 2) is False


def test_prereq_label_node_is_omitted_and_edge_is_bridged():
    root = _course(1, "CMPUT 174")
    child = _course(2, "MATH 114")
    prereq_group = _group(11, 1, "UNKNOWN", display_label="PREREQ")
    builder = ScenarioGraphBuilder(
        root_course=root,
        courses={2: child},
        groups_by_course={1: [prereq_group]},
        items_by_group={11: [_item(101, 11, 2)]},
    )
    root_id = _expand_root(builder)

    group_nodes = [node for node in builder.nodes if node["type"] == "group"]
    course_nodes = [node for node in builder.nodes if node["type"] == "course"]

    assert group_nodes == []
    assert len(course_nodes) == 2
    assert len(builder.edges) == 1
    assert builder.edges[0] == {
        "id": builder.edges[0]["id"],
        "source": root_id,
        "target": next(node["id"] for node in course_nodes if node["code"] == "MATH 114"),
        "relationType": "PREREQ",
    }


def test_redundant_root_and_is_omitted_and_children_attach_directly():
    root = _course(1, "CMPUT 204")
    or_group = _group(41, 1, "ANY_OF", display_label="OR")
    child = _course(2, "CMPUT 272")
    top_and = _group(40, 1, "ALL_OF", display_label="AND")
    builder = ScenarioGraphBuilder(
        root_course=root,
        courses={2: child},
        groups_by_course={1: [top_and]},
        subgroups_by_group={40: [or_group]},
        items_by_group={40: [_item(401, 40, 2)]},
    )
    root_id = _expand_root(builder)

    group_nodes = [node for node in builder.nodes if node["type"] == "group"]
    group_labels = {node["label"] for node in group_nodes}

    assert "AND" not in group_labels
    assert "ALL_OF" not in group_labels
    assert "ANY_OF" in group_labels
    assert any(
        edge["source"] == root_id and edge["relationType"] == "PREREQ" for edge in builder.edges
    )


def test_plain_coreq_label_removed_but_styled_or_coreq_kept():
    root = _course(1, "CMPUT 261")
    child = _course(2, "CMPUT 204")
    coreq_label = _group(31, 1, "COREQ", display_label="COREQ")
    coreq_or = _group(32, 1, "COREQ", display_label="COREQ", visual_style="or")
    builder = ScenarioGraphBuilder(
        root_course=root,
        courses={2: child},
        groups_by_course={1: [coreq_label]},
        subgroups_by_group={31: [coreq_or]},
        items_by_group={32: [_item(321, 32, 2, relation_type="COREQ")]},
    )
    _expand_root(builder)

    group_nodes = [node for node in builder.nodes if node["type"] == "group"]
    group_ids = {node["id"] for node in group_nodes}

    assert len(group_nodes) == 1
    assert any(node.get("visualStyle") == "or" for node in group_nodes)
    assert not any("coreq-label" in node_id for node_id in group_ids)
    assert any(edge["relationType"] == "COREQ" for edge in builder.edges)


def test_nested_and_under_or_is_not_omitted():
    root = _course(1, "CMPUT 204")
    child = _course(2, "MATH 144")
    or_top = _group(51, 1, "ANY_OF", display_label="OR")
    and_nested = _group(52, 1, "ALL_OF", display_label="AND", parent_group_id=51)
    builder = ScenarioGraphBuilder(
        root_course=root,
        courses={2: child},
        groups_by_course={1: [or_top]},
        subgroups_by_group={51: [and_nested]},
        items_by_group={52: [_item(521, 52, 2)]},
    )
    _expand_root(builder)

    and_nodes = [node for node in builder.nodes if node["type"] == "group" and node["groupType"] == "ALL_OF"]
    assert len(and_nodes) == 1


def test_parallel_prereq_labels_emit_no_group_nodes():
    root = _course(1, "CMPUT 174")
    child = _course(2, "MATH 114")
    prereq_a = _group(21, 1, "UNKNOWN", display_label="PREREQ")
    prereq_b = _group(22, 1, "UNKNOWN", display_label="PREREQ")
    builder = ScenarioGraphBuilder(
        root_course=root,
        courses={2: child},
        groups_by_course={1: [prereq_a, prereq_b]},
        items_by_group={
            21: [_item(211, 21, 2)],
            22: [_item(221, 22, 2)],
        },
    )
    _expand_root(builder)

    group_nodes = [node for node in builder.nodes if node["type"] == "group"]
    prereq_edges = [edge for edge in builder.edges if edge["relationType"] == "PREREQ"]

    assert group_nodes == []
    assert len(prereq_edges) >= 1
