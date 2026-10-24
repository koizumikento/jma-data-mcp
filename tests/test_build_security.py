"""Trust bundle checks shared by CI and the Windows release build."""

import ssl
from importlib.metadata import requires, version

import certifi
from packaging.requirements import Requirement
from packaging.version import Version


def test_certifi_security_floor():
    assert Version(version("certifi")) >= Version("2026.10.19")


def test_source_install_requires_updated_certifi():
    requirement = next(
        Requirement(value)
        for value in requires("jma-data-mcp") or []
        if Requirement(value).name == "certifi"
    )
    assert "2026.10.19" in requirement.specifier
    assert "2026.7.22" not in requirement.specifier


def test_certifi_bundle_loads():
    # Use only certifi here; OS/custom CA stores require a separate operator review.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=certifi.where())
    assert context.get_ca_certs()
