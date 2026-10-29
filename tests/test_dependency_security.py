"""Security floors must also apply to installs that do not use uv.lock."""

from importlib.metadata import metadata, requires, version

import dns.exception
import dns.name
import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version


def test_dnspython_security_floor():
    assert Version(version("dnspython")) >= Version("2.9.0")
    requirement = next(
        Requirement(value)
        for value in requires("jma-data-mcp") or []
        if Requirement(value).name == "dnspython"
    )
    assert "2.8.0" not in requirement.specifier
    assert "2.9.0" in requirement.specifier


def test_package_requires_python311():
    supported = SpecifierSet(metadata("jma-data-mcp")["Requires-Python"])
    assert "3.10" not in supported
    assert "3.11" in supported


@pytest.mark.parametrize("pointer_count", [16, 17])
def test_dns_compression_pointer_chain_is_bounded(pointer_count):
    # GHSA-45c3-73f7-pv4m: reject chains over 16 hops, without a timing test
    # or network request. Each pointer goes back to the preceding pointer.
    wire = b"\x00\x00" + b"".join(
        (0xC000 | offset).to_bytes(2, "big") for offset in range(0, pointer_count * 2, 2)
    )
    if pointer_count == 16:
        name, consumed = dns.name.from_wire(wire, len(wire) - 2)
        assert name == dns.name.root
        assert consumed == 2
    else:
        with pytest.raises(dns.exception.FormError, match="pointer chain was too long"):
            dns.name.from_wire(wire, len(wire) - 2)
