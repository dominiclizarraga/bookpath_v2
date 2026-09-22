"""Keep ordinary tests offline: external commands must be mocked explicitly."""

import subprocess

import pytest


@pytest.fixture(autouse=True)
def block_external_commands(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("Unexpected external command. Mock it instead of calling BigQuery.")

    monkeypatch.setattr(subprocess, "run", blocked)
