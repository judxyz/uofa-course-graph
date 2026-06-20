from graph_builder import normalize_course_code


def test_normalize_course_code_uppercase_and_trim():
    assert normalize_course_code("  cmput 174  ") == "CMPUT 174"


def test_normalize_course_code_replaces_hyphen_with_space():
    assert normalize_course_code("math-114") == "MATH 114"
