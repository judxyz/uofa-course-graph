"""Recursive graph builder for frontend prerequisite tree payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_MAX_DEPTH = 1


@dataclass(frozen=True)
class CourseRecord:
    """Normalized course record used by the graph builder."""

    id: int
    code: str
    subject: str
    number: int | str | None
    title: str
    description: str | None
    other_notes: str | None
    raw_prereq_text: str | None
    raw_coreq_text: str | None
    catalog_url: str | None
    parse_status: str | None

@dataclass(frozen=True)
class GroupRecord:
    """Requirement group row."""

    id: int
    course_id: int
    group_type: str
    parent_group_id: int | None
    display_label: str | None
    visual_style: str | None


@dataclass(frozen=True)
class DependencyLinkRecord:
    """Dependency relation from the selected root course to a target course."""

    item_id: int
    relation_type: str
    group_id: int
    target_course_id: int


@dataclass(frozen=True)
class ItemRecord:
    """Requirement item row joined with referenced course metadata."""

    id: int
    group_id: int
    required_course_id: int | None
    relation_type: str
    item_order: int | None
    missing_course_code: str | None
    requirement_text: str | None
    course_code: str | None
    course_subject: str | None
    course_number: int | str | None
    course_title: str | None
    course_parse_status: str | None

def normalize_course_code(code: str) -> str:
    """Normalize course code for lookup."""
    return code.upper().replace("-", " ").strip()


def is_relation_label_group(group: GroupRecord, resolved_group_type: str) -> bool:
    """Return True when a group is only a pass-through PREREQ/COREQ label node."""
    # Real AND/OR logic nodes are never pass-through labels, even when legacy data
    # maps a single-item ALL_OF group to a PREREQ display type.
    if group.group_type in {"ALL_OF", "ANY_OF"}:
        return False

    if resolved_group_type == "PREREQ":
        return True

    visual_style = (group.visual_style or "").strip().lower()
    is_styled_coreq = visual_style in {"and", "or"}

    if resolved_group_type == "COREQ":
        return not is_styled_coreq

    normalized_label = (group.display_label or "").strip().upper()
    if normalized_label == "PREREQ":
        return True

    if normalized_label == "COREQ" and resolved_group_type in {"UNKNOWN", "COREQ"}:
        return not is_styled_coreq

    return False


def is_redundant_root_and_wrapper(group: GroupRecord, visual_depth: int) -> bool:
    """Return True for a root-level ALL_OF wrapper that only fans out to children."""
    return visual_depth == 1 and group.group_type == "ALL_OF"


def should_omit_visual_group_node(
    group: GroupRecord,
    resolved_group_type: str,
    visual_depth: int,
) -> bool:
    """Return True when the group should not be emitted as a visual graph node."""
    return is_relation_label_group(group, resolved_group_type) or is_redundant_root_and_wrapper(
        group, visual_depth
    )


def ensure_requirement_item_schema(conn) -> None:
    """Allow graph reads to include unresolved requirement item codes."""
    with conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE requirement_items
            ADD COLUMN IF NOT EXISTS missing_course_code TEXT
            """
        )
        cur.execute(
            """
            ALTER TABLE requirement_items
            ADD COLUMN IF NOT EXISTS requirement_text TEXT
            """
        )
        cur.execute(
            """
            ALTER TABLE requirement_items
            ALTER COLUMN required_course_id DROP NOT NULL
            """
        )


class GraphBuilder:
    """Build a recursive frontend graph payload for a selected course."""

    def __init__(self, conn, max_depth: int = DEFAULT_MAX_DEPTH, include_coreqs: bool = True):
        self.conn = conn
        # max_depth is course depth: root = 0, first prerequisite courses = 1.
        # Requirement group nodes keep their own visual depth but do not count
        # against this limit.
        self.max_depth = max_depth
        self.include_coreqs = include_coreqs

        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.groups: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []

        self._seen_edge_ids: set[str] = set()
        self._seen_edge_keys: set[tuple[str, str, str]] = set()
        self._seen_group_ids: set[int] = set()
        self._seen_item_ids: set[int] = set()
        self._node_instance_counter = 0
        self._edge_instance_counter = 0

        self._course_cache: dict[int, CourseRecord] = {}
        self._group_cache: dict[int, list[GroupRecord]] = {}
        self._subgroup_cache: dict[int, list[GroupRecord]] = {}
        self._item_cache: dict[int, list[ItemRecord]] = {}
        self._group_by_id_cache: dict[int, GroupRecord] = {}

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def build_from_code(self, code: str) -> dict[str, Any]:
        """Build the full graph payload starting from a course code."""
        normalized_code = normalize_course_code(code)
        root_course = self._fetch_course_by_code(normalized_code)

        if root_course is None:
            raise ValueError("Course not found")

        self._course_cache[root_course.id] = root_course
        self._preload_graph_data(root_course.id)

        root_course_node_id = self._add_course_node(root_course, depth=0)
        self._expand_course(
            root_course,
            course_node_id=root_course_node_id,
            depth=0,
            course_depth=0,
            path={root_course.id},
        )

        return {
            "rootCourse": self._serialize_root_course(root_course),
            "groups": self.groups,
            "items": self.items,
            "nodes": self.nodes,
            "edges": self.edges,
            "rawPrerequisiteText": root_course.raw_prereq_text,
            "rawCorequisiteText": root_course.raw_coreq_text,
            "meta": {
                "maxDepth": self.max_depth,
                "includeCoreqs": self.include_coreqs,
                "viewMode": "prereq",
            },
        }

    def build_dependency_from_code(self, code: str) -> dict[str, Any]:
        """Build a one-level dependency payload (root -> direct prereq dependents)."""
        normalized_code = normalize_course_code(code)
        root_course = self._fetch_course_by_code(normalized_code)

        if root_course is None:
            raise ValueError("Course not found")

        root_course_node_id = self._add_course_node(root_course, depth=0)
        dependent_courses = self._fetch_dependency_courses_for_required_course(root_course.id)

        for dependent_course in dependent_courses:
            dependent_course_node_id = self._add_course_node(dependent_course, depth=1)
            self._add_edge(
                {
                    "id": self._next_edge_id("edge-course-dependent"),
                    "source": root_course_node_id,
                    "target": dependent_course_node_id,
                    "relationType": "PREREQ",
                }
            )

        return {
            "rootCourse": self._serialize_root_course(root_course),
            "groups": [],
            "items": [],
            "nodes": self.nodes,
            "edges": self.edges,
            "rawPrerequisiteText": root_course.raw_prereq_text,
            "rawCorequisiteText": root_course.raw_coreq_text,
            "meta": {
                "maxDepth": 1,
                "includeCoreqs": False,
                "viewMode": "dependency",
            },
        }

    def _fetch_dependency_courses_for_required_course(
        self, required_course_id: int
    ) -> list[CourseRecord]:
        """Fetch direct dependent courses where the root is a prerequisite."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT
                    c.id,
                    c.code,
                    c.subject,
                    c.number,
                    c.title,
                    c.description,
                    c.other_notes,
                    c.raw_prereq_text,
                    c.raw_coreq_text,
                    c.catalog_url,
                    c.parse_status
                FROM requirement_items ri
                JOIN requirement_groups rg
                    ON rg.id = ri.group_id
                JOIN courses c
                    ON c.id = rg.course_id
                WHERE ri.required_course_id = %s
                  AND ri.relation_type = 'PREREQ'
                ORDER BY c.subject, c.number, c.code
                """,
                (required_course_id,),
            )
            rows = cur.fetchall()

        return [CourseRecord(*row) for row in rows]

    # --------------------------------------------------
    # Recursive expansion
    # --------------------------------------------------

    def _expand_course(
        self,
        course: CourseRecord,
        course_node_id: str,
        depth: int,
        course_depth: int,
        path: set[int],
    ) -> None:
        """
        Recursively expand requirement groups/items for a course.

        depth is the actual node depth of the current course node.
        course_depth counts only course-to-course prerequisite hops.

        Node depth pattern:
        - root course: 0
        - its groups: 1
        - direct required courses: 2
        - their groups: 3
        - their required courses: 4
        """
        if course_depth >= self.max_depth:
            return

        group_visual_depth = depth + 1
        groups = self._fetch_groups_for_course(course.id)

        for group in groups:
            if group.group_type == "COREQ" and not self.include_coreqs:
                continue

            items = self._fetch_items_for_group(group.id)
            resolved_group_type = self._resolve_group_type(group, items)

            if should_omit_visual_group_node(group, resolved_group_type, group_visual_depth):
                self._expand_group_children(
                    group=group,
                    attach_node_id=course_node_id,
                    children_depth=group_visual_depth + 1,
                    course_depth=course_depth,
                    path=path,
                )
                continue

            group_node_id = self._add_group_node(
                group, depth=group_visual_depth, group_type=resolved_group_type
            )
            self._add_course_to_group_edge(course_node_id, group_node_id, resolved_group_type)
            self._expand_group_children(
                group=group,
                attach_node_id=group_node_id,
                children_depth=group_visual_depth + 1,
                course_depth=course_depth,
                path=path,
            )

    def _expand_group_children(
        self,
        group: GroupRecord,
        attach_node_id: str,
        children_depth: int,
        course_depth: int,
        path: set[int],
    ) -> None:
        """Recursively expand a group's children: subgroups or direct course items."""
        items = self._fetch_items_for_group(group.id)
        subgroups = self._fetch_subgroups_for_group(group.id)
        child_course_depth = course_depth + 1

        if subgroups:
            for subgroup in subgroups:
                if subgroup.group_type == "COREQ" and not self.include_coreqs:
                    continue
                sub_items = self._fetch_items_for_group(subgroup.id)
                resolved_sub_type = self._resolve_group_type(subgroup, sub_items)
                subgroup_visual_depth = children_depth

                if should_omit_visual_group_node(
                    subgroup, resolved_sub_type, subgroup_visual_depth
                ):
                    self._expand_group_children(
                        group=subgroup,
                        attach_node_id=attach_node_id,
                        children_depth=subgroup_visual_depth + 1,
                        course_depth=course_depth,
                        path=path,
                    )
                    continue

                subgroup_node_id = self._add_group_node(
                    subgroup, depth=subgroup_visual_depth, group_type=resolved_sub_type
                )
                self._add_node_to_node_edge(
                    attach_node_id,
                    subgroup_node_id,
                    self._relation_type_for_group_link(resolved_sub_type),
                )
                self._expand_group_children(
                    group=subgroup,
                    attach_node_id=subgroup_node_id,
                    children_depth=subgroup_visual_depth + 1,
                    course_depth=course_depth,
                    path=path,
                )
        else:
            for item in items:
                if item.relation_type == "COREQ" and not self.include_coreqs:
                    continue
                if child_course_depth > self.max_depth:
                    continue

                if item.required_course_id is None:
                    self._add_item(item)
                    item_node_id = (
                        self._add_requirement_node(item, depth=children_depth)
                        if item.requirement_text
                        else self._add_unavailable_course_node(item, depth=children_depth)
                    )
                    self._add_node_to_node_edge(
                        attach_node_id,
                        item_node_id,
                        item.relation_type,
                    )
                    continue

                child_course = self._fetch_course_by_id(item.required_course_id)
                if child_course is None:
                    continue
                self._add_item(item)
                child_course_node_id = self._add_course_node(child_course, depth=children_depth)
                self._add_node_to_node_edge(
                    attach_node_id,
                    child_course_node_id,
                    item.relation_type,
                )
                if child_course.id in path:
                    continue
                next_path = set(path)
                next_path.add(child_course.id)
                self._expand_course(
                    child_course,
                    course_node_id=child_course_node_id,
                    depth=children_depth,
                    course_depth=child_course_depth,
                    path=next_path,
                )

    # --------------------------------------------------
    # Database fetches
    # --------------------------------------------------

    def _preload_graph_data(self, root_course_id: int) -> None:
        """Batch-load graph rows up to the requested course depth."""
        if self.max_depth <= 0:
            return

        frontier_course_ids = {root_course_id}
        expanded_course_ids: set[int] = set()

        for _course_depth in range(self.max_depth):
            course_ids = frontier_course_ids - expanded_course_ids
            if not course_ids:
                break

            groups = self._preload_groups_for_courses(course_ids)
            items = self._preload_items_for_groups(group.id for group in groups)

            child_course_ids = {
                item.required_course_id
                for item in items
                if item.required_course_id is not None
            }

            self._preload_courses_by_ids(child_course_ids)

            expanded_course_ids.update(course_ids)
            frontier_course_ids = child_course_ids - expanded_course_ids

    def _preload_courses_by_ids(self, course_ids: set[int]) -> None:
        """Fetch missing courses in one query and seed the course cache."""
        missing_course_ids = sorted(course_id for course_id in course_ids if course_id not in self._course_cache)
        if not missing_course_ids:
            return

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    code,
                    subject,
                    number,
                    title,
                    description,
                    other_notes,
                    raw_prereq_text,
                    raw_coreq_text,
                    catalog_url,
                    parse_status
                FROM courses
                WHERE id = ANY(%s)
                """,
                (missing_course_ids,),
            )
            rows = cur.fetchall()

        for row in rows:
            course = CourseRecord(*row)
            self._course_cache[course.id] = course

    def _preload_groups_for_courses(self, course_ids: set[int]) -> list[GroupRecord]:
        """Fetch all requirement groups for courses and seed group lookups."""
        ordered_course_ids = sorted(course_ids)
        if not ordered_course_ids:
            return []

        for course_id in ordered_course_ids:
            self._group_cache.setdefault(course_id, [])

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    course_id,
                    group_type,
                    parent_group_id,
                    display_label,
                    visual_style
                FROM requirement_groups
                WHERE course_id = ANY(%s)
                ORDER BY course_id, parent_group_id NULLS FIRST, id
                """,
                (ordered_course_ids,),
            )
            rows = cur.fetchall()

        groups = [GroupRecord(*row) for row in rows]

        for group in groups:
            self._subgroup_cache.setdefault(group.id, [])

            if group.parent_group_id is None:
                self._group_cache.setdefault(group.course_id, []).append(group)
            else:
                self._subgroup_cache.setdefault(group.parent_group_id, []).append(group)

        return groups

    def _preload_items_for_groups(self, group_ids) -> list[ItemRecord]:
        """Fetch all requirement items for groups and seed item lookups."""
        ordered_group_ids = sorted(set(group_ids))
        if not ordered_group_ids:
            return []

        for group_id in ordered_group_ids:
            self._item_cache.setdefault(group_id, [])

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ri.id,
                    ri.group_id,
                    ri.required_course_id,
                    ri.relation_type,
                    ri.item_order,
                    ri.missing_course_code,
                    ri.requirement_text,
                    c.code,
                    c.subject,
                    c.number,
                    c.title,
                    c.parse_status
                FROM requirement_items ri
                LEFT JOIN courses c
                    ON c.id = ri.required_course_id
                WHERE ri.group_id = ANY(%s)
                ORDER BY ri.group_id, ri.item_order NULLS LAST, ri.id
                """,
                (ordered_group_ids,),
            )
            rows = cur.fetchall()

        items = [ItemRecord(*row) for row in rows]

        for item in items:
            self._item_cache.setdefault(item.group_id, []).append(item)

        return items

    def _fetch_course_by_code(self, normalized_code: str) -> CourseRecord | None:
        """Fetch course by normalized code."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    code,
                    subject,
                    number,
                    title,
                    description,
                    other_notes,
                    raw_prereq_text,
                    raw_coreq_text,
                    catalog_url,
                    parse_status
                FROM courses
                WHERE UPPER(code) = %s
                """,
                (normalized_code,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return CourseRecord(*row)

    def _fetch_course_by_id(self, course_id: int) -> CourseRecord | None:
        """Fetch course by ID with caching."""
        if course_id in self._course_cache:
            return self._course_cache[course_id]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    code,
                    subject,
                    number,
                    title,
                    description,
                    other_notes,
                    raw_prereq_text,
                    raw_coreq_text,
                    catalog_url,
                    parse_status
                FROM courses
                WHERE id = %s
                """,
                (course_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        course = CourseRecord(*row)
        self._course_cache[course_id] = course
        return course

    def _fetch_groups_for_course(self, course_id: int) -> list[GroupRecord]:
        """Fetch top-level requirement groups (no parent) for a course."""
        if course_id in self._group_cache:
            return self._group_cache[course_id]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    course_id,
                    group_type,
                    parent_group_id,
                    display_label,
                    visual_style
                FROM requirement_groups
                WHERE course_id = %s AND parent_group_id IS NULL
                ORDER BY id
                """,
                (course_id,),
            )
            rows = cur.fetchall()

        groups = [GroupRecord(*row) for row in rows]
        self._group_cache[course_id] = groups
        return groups

    def _fetch_subgroups_for_group(self, group_id: int) -> list[GroupRecord]:
        """Fetch child requirement groups for a parent group."""
        if group_id in self._subgroup_cache:
            return self._subgroup_cache[group_id]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    course_id,
                    group_type,
                    parent_group_id,
                    display_label,
                    visual_style
                FROM requirement_groups
                WHERE parent_group_id = %s
                ORDER BY id
                """,
                (group_id,),
            )
            rows = cur.fetchall()

        subgroups = [GroupRecord(*row) for row in rows]
        self._subgroup_cache[group_id] = subgroups
        return subgroups

    def _fetch_group_by_id(self, group_id: int) -> GroupRecord | None:
        """Fetch a requirement group by id with caching."""
        if group_id in self._group_by_id_cache:
            return self._group_by_id_cache[group_id]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    course_id,
                    group_type,
                    parent_group_id,
                    display_label,
                    visual_style
                FROM requirement_groups
                WHERE id = %s
                """,
                (group_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        group = GroupRecord(*row)
        self._group_by_id_cache[group_id] = group
        return group

    def _fetch_group_ancestor_chain(self, group_id: int) -> list[GroupRecord]:
        """Return group lineage from matched group up to top-level parent."""
        chain: list[GroupRecord] = []
        current_group_id: int | None = group_id
        seen_group_ids: set[int] = set()

        while current_group_id is not None and current_group_id not in seen_group_ids:
            seen_group_ids.add(current_group_id)
            group = self._fetch_group_by_id(current_group_id)
            if group is None:
                break
            chain.append(group)
            current_group_id = group.parent_group_id

        return chain

    def _fetch_items_for_group(self, group_id: int) -> list[ItemRecord]:
        """Fetch all items for a requirement group."""
        if group_id in self._item_cache:
            return self._item_cache[group_id]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ri.id,
                    ri.group_id,
                    ri.required_course_id,
                    ri.relation_type,
                    ri.item_order,
                    ri.missing_course_code,
                    ri.requirement_text,
                    c.code,
                    c.subject,
                    c.number,
                    c.title,
                    c.parse_status
                FROM requirement_items ri
                LEFT JOIN courses c
                    ON c.id = ri.required_course_id
                WHERE ri.group_id = %s
                ORDER BY ri.item_order NULLS LAST, ri.id
                """,
                (group_id,),
            )
            rows = cur.fetchall()

        items = [ItemRecord(*row) for row in rows]
        self._item_cache[group_id] = items
        return items

    # --------------------------------------------------
    # Serializers
    # --------------------------------------------------

    def _serialize_root_course(self, course: CourseRecord) -> dict[str, Any]:
        """Serialize root course payload."""
        return {
            "id": course.id,
            "code": course.code,
            "subject": course.subject,
            "number": course.number,
            "title": course.title,
            "description": course.description,
            "otherNotes": course.other_notes,
            "catalogUrl": course.catalog_url,
            "parseStatus": course.parse_status,
        }

    def _next_node_id(self, prefix: str, entity_id: int) -> str:
        """Create a unique node instance id for each occurrence in the graph."""
        self._node_instance_counter += 1
        return f"{prefix}-{entity_id}-instance-{self._node_instance_counter}"

    def _next_edge_id(self, prefix: str) -> str:
        """Create a unique edge instance id for each occurrence in the graph."""
        self._edge_instance_counter += 1
        return f"{prefix}-{self._edge_instance_counter}"

    def _make_course_node(self, course: CourseRecord, depth: int, node_id: str) -> dict[str, Any]:
        """Create frontend course node."""
        return {
            "id": node_id,
            "type": "course",
            "courseId": course.id,
            "code": course.code,
            "title": course.title,
            "subject": course.subject,
            "number": course.number,
            "parseStatus": course.parse_status,
            "depth": depth,
        }

    def _make_unavailable_course_node(self, item: ItemRecord, depth: int, node_id: str) -> dict[str, Any]:
        """Create frontend node for a referenced course missing from the catalog."""
        code = item.missing_course_code or "Unavailable course"
        subject, _, number = code.partition(" ")

        return {
            "id": node_id,
            "type": "course",
            "courseId": None,
            "code": code,
            "title": "Course unavailable",
            "subject": subject,
            "number": number or None,
            "parseStatus": None,
            "isAvailable": False,
            "depth": depth,
        }

    def _make_requirement_node(self, item: ItemRecord, depth: int, node_id: str) -> dict[str, Any]:
        """Create frontend node for generic non-course requirements."""
        return {
            "id": node_id,
            "type": "requirement",
            "requirementId": item.id,
            "label": item.requirement_text,
            "depth": depth,
        }

    def _make_group_node(self, group: GroupRecord, depth: int, node_id: str) -> dict[str, Any]:
        """Create frontend group node."""
        return {
            "id": node_id,
            "type": "group",
            "groupId": group.id,
            "groupType": group.group_type,
            "label": group.display_label,
            "displayLabel": group.display_label,
            "visualStyle": group.visual_style,
            "depth": depth,
        }

    # --------------------------------------------------
    # Graph assembly helpers
    # --------------------------------------------------

    def _resolve_group_type(self, group: GroupRecord, items: list[ItemRecord]) -> str:
        """Map stored group types to the frontend-visible group type."""
        return group.group_type

    def _resolve_group_label(self, group: GroupRecord, group_type: str) -> str | None:
        """Normalize emitted labels so legacy data matches current frontend wording."""
        if group_type in {"ALL_OF", "ANY_OF", "PREREQ", "COREQ"}:
            return group_type

        return group.display_label

    @staticmethod
    def _relation_type_for_group_link(resolved_group_type: str) -> str:
        """Map a resolved group type to the edge relation used when linking graph nodes."""
        return "COREQ" if resolved_group_type == "COREQ" else "PREREQ"

    def _add_course_node(self, course: CourseRecord, depth: int) -> str:
        """Add a unique course node instance and return its node id."""
        node_id = self._next_node_id("course", course.id)
        node = self._make_course_node(course, depth, node_id)
        self.nodes.append(node)
        return node_id

    def _add_unavailable_course_node(self, item: ItemRecord, depth: int) -> str:
        """Add a unique unavailable course node instance and return its node id."""
        node_id = self._next_node_id("missing-course", item.id)
        node = self._make_unavailable_course_node(item, depth, node_id)
        self.nodes.append(node)
        return node_id

    def _add_requirement_node(self, item: ItemRecord, depth: int) -> str:
        """Add a unique generic requirement node instance and return its node id."""
        node_id = self._next_node_id("requirement", item.id)
        node = self._make_requirement_node(item, depth, node_id)
        self.nodes.append(node)
        return node_id

    def _add_group_node(self, group: GroupRecord, depth: int, group_type: str) -> str:
        """Add a unique group node instance and return its node id."""
        node_id = self._next_node_id("group", group.id)
        display_label = self._resolve_group_label(group, group_type)

        if group.id not in self._seen_group_ids:
            self.groups.append(
                {
                    "id": group.id,
                    "nodeId": node_id,
                    "courseId": group.course_id,
                    "groupType": group_type,
                    "parentGroupId": group.parent_group_id,
                    "displayLabel": display_label,
                    "label": display_label,
                    "visualStyle": group.visual_style,
                }
            )
            self._seen_group_ids.add(group.id)

        group_node_data = GroupRecord(
            id=group.id,
            course_id=group.course_id,
            group_type=group_type,
            parent_group_id=group.parent_group_id,
            display_label=display_label,
            visual_style=group.visual_style,
        )
        node = self._make_group_node(group_node_data, depth, node_id)
        self.nodes.append(node)
        return node_id


    def _add_item(self, item: ItemRecord) -> None:
        """Add requirement item metadata if not already present."""
        if item.id in self._seen_item_ids:
            return

        self.items.append(
            {
                "id": item.id,
                "groupId": item.group_id,
                "requiredCourseId": item.required_course_id,
                "relationType": item.relation_type,
                "itemOrder": item.item_order,
                "course": {
                    "id": item.required_course_id,
                    "code": item.course_code or item.missing_course_code or "Unavailable course",
                    "subject": item.course_subject,
                    "number": item.course_number,
                    "title": item.course_title or "Course unavailable",
                    "parseStatus": item.course_parse_status,
                    "isAvailable": item.required_course_id is not None,
                    "requirementText": item.requirement_text,
                },
            }
        )
        self._seen_item_ids.add(item.id)

    def _add_edge(self, edge: dict[str, Any]) -> None:
        """Add edge if not already present."""
        source = edge["source"]
        target = edge["target"]
        if source == target:
            return

        edge_key = (source, target, edge["relationType"])
        if edge_key in self._seen_edge_keys:
            return

        edge_id = edge["id"]
        if edge_id in self._seen_edge_ids:
            return

        self.edges.append(edge)
        self._seen_edge_ids.add(edge_id)
        self._seen_edge_keys.add(edge_key)

    def _add_node_to_node_edge(self, source_node_id: str, target_node_id: str, relation_type: str) -> None:
        """Add a deduplicated edge between two graph nodes."""
        self._add_edge(
            {
                "id": self._next_edge_id("edge-node-node"),
                "source": source_node_id,
                "target": target_node_id,
                "relationType": relation_type,
            }
        )

    def _add_course_to_group_edge(self, course_node_id: str, group_node_id: str, group_type: str) -> None:
        """Add root/parent course -> group edge."""
        relation_type = "COREQ" if group_type == "COREQ" else "PREREQ"

        self._add_edge(
            {
                "id": self._next_edge_id("edge-course-group"),
                "source": course_node_id,
                "target": group_node_id,
                "relationType": relation_type,
            }
        )

    def _add_group_to_course_edge(
        self,
        group_node_id: str,
        required_course_node_id: str,
        item_id: int,
        relation_type: str,
    ) -> None:
        """Add group -> required course edge."""
        self._add_edge(
            {
                "id": self._next_edge_id(f"edge-group-course-item-{item_id}"),
                "source": group_node_id,
                "target": required_course_node_id,
                "relationType": relation_type,
            }
        )

    def _add_group_to_subgroup_edge(
        self,
        parent_group_node_id: str,
        child_group_node_id: str,
        child_group_type: str,
    ) -> None:
        """Add parent group -> child subgroup edge."""
        relation_type = "COREQ" if child_group_type == "COREQ" else "PREREQ"
        self._add_edge(
            {
                "id": self._next_edge_id("edge-group-subgroup"),
                "source": parent_group_node_id,
                "target": child_group_node_id,
                "relationType": relation_type,
            }
        )
