"""
Tests for CatiaSession connect/reconnect logic, with pycatia mocked out
entirely so this suite runs on any OS without CATIA installed - including
a simulated COM crash-and-recover scenario.
"""

from unittest.mock import MagicMock

import catia.session as session_module
import pytest
from utils.error_handler import CatiaConnectionError


@pytest.fixture(autouse=True)
def reset_singleton():
    session_module.CatiaSession._instance = None
    yield
    session_module.CatiaSession._instance = None


def _make_fake_app():
    app = MagicMock()
    app.documents.count = 0
    return app


def test_get_application_connects_lazily(monkeypatch):
    fake_app = _make_fake_app()
    monkeypatch.setattr(session_module, "PYCATIA_AVAILABLE", True)
    monkeypatch.setattr(session_module, "_catia_factory", lambda: fake_app)

    sess = session_module.CatiaSession.get_instance()
    app = sess.get_application()
    assert app is fake_app


def test_reconnect_after_simulated_crash(monkeypatch):
    fake_app_1 = _make_fake_app()
    fake_app_2 = _make_fake_app()
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return fake_app_1 if calls["n"] == 1 else fake_app_2

    monkeypatch.setattr(session_module, "PYCATIA_AVAILABLE", True)
    monkeypatch.setattr(session_module, "_catia_factory", factory)
    monkeypatch.setattr(session_module.time, "sleep", lambda *_a, **_k: None)

    sess = session_module.CatiaSession.get_instance()
    app1 = sess.get_application()
    assert app1 is fake_app_1

    # Simulate a crash: any attribute access on `documents` now raises,
    # which is exactly how a closed/crashed CATIA COM object behaves.
    type(fake_app_1).documents = property(
        lambda self: (_ for _ in ()).throw(RuntimeError("COM error"))
    )

    app2 = sess.get_application()
    assert app2 is fake_app_2
    assert calls["n"] == 2


def test_offline_mode_raises_clear_error(monkeypatch):
    monkeypatch.setattr(session_module, "PYCATIA_AVAILABLE", False)
    sess = session_module.CatiaSession.get_instance()
    with pytest.raises(CatiaConnectionError):
        sess.get_application()


def test_force_reconnect_always_creates_new_app(monkeypatch):
    fake_app_1 = _make_fake_app()
    fake_app_2 = _make_fake_app()
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return fake_app_1 if calls["n"] == 1 else fake_app_2

    monkeypatch.setattr(session_module, "PYCATIA_AVAILABLE", True)
    monkeypatch.setattr(session_module, "_catia_factory", factory)
    monkeypatch.setattr(session_module.time, "sleep", lambda *_a, **_k: None)

    sess = session_module.CatiaSession.get_instance()
    sess.get_application()
    app2 = sess.force_reconnect()
    assert app2 is fake_app_2
