from fastapi.testclient import TestClient

import app as app_module


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None):
        self.fetchone_result = fetchone_result
        self.fetchall_result = fetchall_result or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.last_query = query
        self.last_params = params

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


def test_health_endpoint():
    client = TestClient(app_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_course_returns_404_when_missing(monkeypatch):
    fake_conn = FakeConn(FakeCursor(fetchone_result=None))
    monkeypatch.setattr(app_module, "get_conn", lambda: fake_conn)
    client = TestClient(app_module.app)

    response = client.get("/courses/DOES 999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"


def test_graph_returns_404_when_builder_raises(monkeypatch):
    class FakeBuilder:
        def __init__(self, conn, max_depth, include_coreqs):
            self.conn = conn
            self.max_depth = max_depth
            self.include_coreqs = include_coreqs

        def build_from_code(self, code):
            raise ValueError("not found")

        def build_dependency_from_code(self, code):
            raise ValueError("not found")

    monkeypatch.setattr(app_module, "GraphBuilder", FakeBuilder)
    monkeypatch.setattr(app_module, "get_conn", lambda: FakeConn(FakeCursor()))

    client = TestClient(app_module.app)
    response = client.get("/graph/DOES 999?view=prereq")

    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found"


def test_graph_dependency_view_calls_dependency_builder(monkeypatch):
    class FakeBuilder:
        def __init__(self, conn, max_depth, include_coreqs):
            self.conn = conn
            self.max_depth = max_depth
            self.include_coreqs = include_coreqs

        def build_from_code(self, code):
            return {"mode": "prereq", "code": code}

        def build_dependency_from_code(self, code):
            return {"mode": "dependency", "code": code}

    monkeypatch.setattr(app_module, "GraphBuilder", FakeBuilder)
    monkeypatch.setattr(app_module, "get_conn", lambda: FakeConn(FakeCursor()))

    client = TestClient(app_module.app)
    response = client.get("/graph/CMPUT 174?view=dependency")

    assert response.status_code == 200
    assert response.json() == {"mode": "dependency", "code": "CMPUT 174"}
