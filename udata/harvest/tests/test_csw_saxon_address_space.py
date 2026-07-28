"""Saxon must be able to start within the address space of a uwsgi worker.

saxonche 13 reserves 32 GiB of address space when a CSW backend creates its
PySaxonProcessor -- reserved only, never used: RSS stays at 58 MiB. saxonche 12
does not do this at all. The reservation comes from the GraalVM runtime 13 is
built on and cannot be tuned: saxonche exposes no way to size the isolate.

uwsgi caps the *virtual* memory of its workers (`limit-as`, see
docs/installation.md), so the reservation blows past that cap, the isolate cannot
be created and the worker dies on `graal_create_isolate error`. It is a native
exit rather than a Python exception, so nothing can catch it and every in-flight
request on that worker goes down with it. Celery and the CLI are unaffected: only
uwsgi sets `limit-as`.

Nothing else in the test suite runs under a memory limit, which is how the
saxonche 13 upgrade (#3818) passed CI while breaking harvest previews.
"""

import subprocess
import sys
import textwrap

# The lowest `limit-as` we ship, from docs/installation.md and docker-udata.
UWSGI_LIMIT_AS_MB = 1024

START_SAXON_UNDER_LIMITED_ADDRESS_SPACE = textwrap.dedent(f"""
    import resource

    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, ({UWSGI_LIMIT_AS_MB} * 1024 * 1024, hard))

    from udata.harvest.backends.dcat import BaseCswDcatBackend, PySaxonProcessor

    proc = PySaxonProcessor(license=False)
    for feature, value in BaseCswDcatBackend.SAXON_SECURITY_FEATURES.items():
        proc.set_configuration_property(feature, value)

    node = proc.parse_xml(xml_text="<root><child/></root>")
    xpath = proc.new_xpath_processor()
    xpath.set_context(xdm_item=node)
    assert xpath.evaluate("/root/child")
""")


def test_saxon_starts_within_the_uwsgi_address_space_limit():
    result = subprocess.run(
        [sys.executable, "-c", START_SAXON_UNDER_LIMITED_ADDRESS_SPACE],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"Saxon failed to start within {UWSGI_LIMIT_AS_MB} MiB of address space, "
        f"CSW harvesting is broken under uwsgi:\n{result.stdout}{result.stderr}"
    )
