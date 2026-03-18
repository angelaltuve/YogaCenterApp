import gc
import pytest
from sqlmodel import SQLModel, create_engine, Session
from PyQt6.QtWidgets import QApplication
from database import db

@pytest.fixture(scope="session")
def qapp():
    """Fixture para crear una aplicación Qt"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture(scope="function")
def test_engine():
    """Crea un engine SQLite en memoria."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def test_session(test_engine):
    """Proporciona una sesión de base de datos para pruebas."""
    with Session(test_engine) as session:
        yield session

@pytest.fixture(autouse=True)
def patch_db_engine(monkeypatch, test_engine):
    """Reemplaza el engine global del módulo db por el de prueba."""
    monkeypatch.setattr(db, "engine", test_engine)

@pytest.fixture(autouse=True)
def patch_get_session(monkeypatch, test_session):
    """Parchea get_session para que devuelva la sesión de prueba."""
    monkeypatch.setattr("database.db.get_session", lambda: test_session)

@pytest.fixture(autouse=True)
def force_gc():
    """Fuerza la recolección de basura después de cada prueba."""
    yield
    gc.collect()
