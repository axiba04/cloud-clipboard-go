"""Verify AEA signatures and compare downloaded shortcut actions on a macOS runner."""

import plistlib
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args, data=None):
    return subprocess.run(args, input=data, check=True, capture_output=True).stdout


directory = Path(sys.argv[1]).resolve()
for name in ("Cloud-Clipboard-Send", "Cloud-Clipboard-Receive"):
    signed = directory / f"{name}.shortcut"
    blob = signed.read_bytes()
    assert blob[:4] == b"AEA1"
    profile, auth_size = struct.unpack_from("<II", blob, 4)
    assert profile == 0, "Expected sign-only AEA profile"
    auth = plistlib.loads(blob[12:12 + auth_size])
    leaf = auth["SigningCertificateChain"][0]
    pem = run("openssl", "x509", "-inform", "DER", "-pubkey", "-noout", data=leaf)
    der = run("openssl", "pkey", "-pubin", "-outform", "DER", data=pem)
    public_key = der[-65:]
    assert public_key[0] == 4, "Expected uncompressed P-256 public key"
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        key = scratch / "public-key.txt"
        key.write_text("hex:" + public_key.hex())
        archive = scratch / "payload.aa"
        run("aea", "decrypt", "-i", str(signed), "-o", str(archive), "-sign-pub", str(key))
        extracted = scratch / "extracted"
        extracted.mkdir()
        run("aa", "extract", "-i", str(archive), "-d", str(extracted))
        workflows = list(extracted.glob("*.wflow"))
        assert len(workflows) == 1
        received = plistlib.loads(workflows[0].read_bytes())
    original = plistlib.loads((directory / "source" / f"{name}.plist").read_bytes())
    expected_actions = original["WFWorkflowActions"]
    actual_actions = received["WFWorkflowActions"]
    prefix_count = len(actual_actions) - len(expected_actions)
    print(f"{name}: verified AEA signature; {len(actual_actions)} signed actions; {prefix_count} prefix actions", flush=True)
    assert prefix_count >= 0
    for action in actual_actions[:prefix_count]:
        print("Signing service prefix:", action, flush=True)
        assert action["WFWorkflowActionIdentifier"] in (
            "is.workflow.actions.output", "is.workflow.actions.comment"
        ), "Unexpected action inserted by signing service"
    assert actual_actions[prefix_count:] == expected_actions, "Signing service changed shortcut actions"
    assert received.get("WFWorkflowImportQuestions") == original["WFWorkflowImportQuestions"]
    print("Import questions correctly target configuration actions 0, 2 and 4", flush=True)
