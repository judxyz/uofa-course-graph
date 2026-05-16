from parse_requirements import ParsedGroup, normalize_parsed_groups


def test_normalize_converts_standalone_all_of_to_prereq():
    groups = [
        ParsedGroup(
            group_type="ALL_OF",
            relation_type="PREREQ",
            course_codes=["CMPUT 174", "CMPUT 175"],
            requirement_texts=[],
            display_label="ALL_OF",
            raw_fragment="CMPUT 174 and CMPUT 175",
            visual_style="and",
        )
    ]

    normalized = normalize_parsed_groups(groups)

    assert len(normalized) == 1
    assert normalized[0].group_type == "PREREQ"
    assert normalized[0].display_label == "PREREQ"
    assert normalized[0].visual_style is None


def test_normalize_keeps_all_of_when_nested_under_any_of():
    groups = [
        ParsedGroup(
            group_type="ANY_OF",
            relation_type="PREREQ",
            course_codes=[],
            requirement_texts=[],
            display_label="ANY_OF",
            raw_fragment="(CMPUT 174 and CMPUT 175) or CMPUT 274",
            visual_style="or",
            group_key="root-any",
            parent_group_key=None,
        ),
        ParsedGroup(
            group_type="ALL_OF",
            relation_type="PREREQ",
            course_codes=["CMPUT 174", "CMPUT 175"],
            requirement_texts=[],
            display_label="ALL_OF",
            raw_fragment="CMPUT 174 and CMPUT 175",
            visual_style="and",
            group_key="left-all",
            parent_group_key="root-any",
        ),
        ParsedGroup(
            group_type="PREREQ",
            relation_type="PREREQ",
            course_codes=["CMPUT 274"],
            requirement_texts=[],
            display_label="PREREQ",
            raw_fragment="CMPUT 274",
            visual_style="single",
            group_key="right",
            parent_group_key="root-any",
        ),
    ]

    normalized = normalize_parsed_groups(groups)
    nested = next(group for group in normalized if group.group_key == "left-all")
    assert nested.group_type == "ALL_OF"


def test_normalize_drops_structural_all_of_and_reparents_children():
    groups = [
        ParsedGroup(
            group_type="ALL_OF",
            relation_type="PREREQ",
            course_codes=[],
            requirement_texts=[],
            display_label="ALL_OF",
            raw_fragment="A or B, C",
            visual_style="and",
            group_key="wrapper",
            parent_group_key=None,
        ),
        ParsedGroup(
            group_type="ANY_OF",
            relation_type="PREREQ",
            course_codes=["CMPUT 174", "CMPUT 274"],
            requirement_texts=[],
            display_label="ANY_OF",
            raw_fragment="CMPUT 174 or CMPUT 274",
            visual_style="or",
            group_key="left",
            parent_group_key="wrapper",
        ),
        ParsedGroup(
            group_type="PREREQ",
            relation_type="PREREQ",
            course_codes=["CMPUT 204"],
            requirement_texts=[],
            display_label="PREREQ",
            raw_fragment="CMPUT 204",
            visual_style="single",
            group_key="right",
            parent_group_key="wrapper",
        ),
    ]

    normalized = normalize_parsed_groups(groups)

    assert all(group.group_key != "wrapper" for group in normalized)
    left = next(group for group in normalized if group.group_key == "left")
    right = next(group for group in normalized if group.group_key == "right")
    assert left.parent_group_key is None
    assert right.parent_group_key is None
