# SPDX-License-Identifier: GPL-2.0-or-later
"""CPU/CI gates use fixtures only; never install packages or mutate drivers."""
from email.parser import Parser
import importlib.util
from pathlib import Path
import tarfile
import unittest

from inspect_deb import PackageAuditError, audit_independent_file, audit_links, audit_package
import test_qt_only_packaging as fixtures

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".github/scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_cpu = script("check_cpu")
cpu_smoke = script("cpu_smoke")


class IndependentPayloadTests(unittest.TestCase):
    def test_native_payload_rejected_by_magic_even_with_data_extension(self):
        for magic in (b"\x7fELF", b"MZ", b"!<arch>\n", b"!<thin>\n", b"BC\xc0\xde", b"\xcf\xfa\xed\xfe"):
            with self.subTest(magic=magic), self.assertRaises(PackageAuditError):
                audit_independent_file("usr/share/data.bin", magic)

    def test_extensions_cannot_hide_native_or_vendored_packages(self):
        for name in ("module.so", "lib.so.6.10", "old.o", "static.a", "vendored.whl", "code.exe", "lib.dylib"):
            with self.subTest(name=name), self.assertRaises(PackageAuditError):
                audit_independent_file(name, b"not ELF")

    def test_python_assets_and_gettext_are_architecture_independent(self):
        for name, prefix in (("main.py", b"#!/usr/b"), ("icon.png", b"\x89PNG\r\n\x1a\n"),
                             ("locale.mo", b"\xde\x12\x04\x95"), ("manual.gz", b"\x1f\x8b")):
            audit_independent_file(name, prefix)

    def test_writable_package_files_are_rejected(self):
        fixture = fixtures.QtOnlyPackagingTests()
        fixture.setUp()
        for mode in (0o666, 0o775):
            with self.subTest(mode=mode), self.assertRaises(PackageAuditError):
                audit_package(fixture.control, fixture.members + [fixtures.member("usr/share/data", mode)], fixture.scripts)

    def test_public_entry_link_resolves_inside_payload(self):
        link = fixtures.member("usr/bin/app")
        link.type, link.linkname = tarfile.SYMTYPE, "../lib/app/main.py"
        audit_links([link, fixtures.member("usr/lib/app/main.py")])

    def test_posix_symlink_777_is_not_a_writable_regular_file(self):
        fixture = fixtures.QtOnlyPackagingTests()
        fixture.setUp()
        fixture.members[0].type = tarfile.SYMTYPE
        fixture.members[0].mode = 0o777
        fixture.members[0].linkname = "../lib/main.py"
        audit_package(fixture.control, fixture.members, fixture.scripts)

    def test_external_dangling_cycles_and_hardlinks_are_rejected(self):
        for target in ("/usr/bin/python3", "../../../outside", "missing", "app"):
            link = fixtures.member("usr/bin/app")
            link.type, link.linkname = tarfile.SYMTYPE, target
            with self.subTest(target=target), self.assertRaises(PackageAuditError):
                audit_links([link])
        link.type = tarfile.LNKTYPE
        with self.assertRaises(PackageAuditError):
            audit_links([link])


class CpuEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.config = 'APT::Architecture-Variants "";\nAPT::Architectures:: "amd64";\n'
        self.packages = 'python3\tinstalled\tamd64\t\t3.14\napp\tinstalled\tall\t\t1.0~rc1\n'
        self.release = {"ID": "ubuntu", "VERSION_ID": "26.04"}

    def test_baseline_inputs_pass_without_assuming_runner_cpu(self):
        self.assertEqual(check_cpu.environment_errors("amd64", self.config, self.packages, self.release), [])

    def test_amd64v3_variant_is_detected_despite_architecture_amd64(self):
        for status in ("installed", "unpacked", "triggers-pending"):
            with self.subTest(status=status):
                errors = check_cpu.environment_errors("amd64", self.config,
                    self.packages + "libc6\t%s\tamd64\tamd64v3\t2.43\n" % status, self.release)
                self.assertTrue(any("Non-baseline" in error for error in errors))

    def test_variant_configuration_missing_or_enabled_fails(self):
        for config in ('APT::Architectures:: "amd64";\n', self.config + 'APT::Architecture-Variants:: "amd64v3";\n'):
            self.assertTrue(check_cpu.environment_errors("amd64", config, self.packages, self.release))

    def test_wrong_distribution_or_architecture_fails(self):
        self.assertTrue(check_cpu.environment_errors("arm64", self.config, self.packages, self.release))
        self.assertTrue(check_cpu.environment_errors("amd64", self.config, self.packages, {"ID": "ubuntu", "VERSION_ID": "24.04"}))

    def test_needed_notes_are_distinct_from_optional_used_instructions(self):
        self.assertEqual(check_cpu.declared_isa("x86 ISA needed: x86-64-baseline\nx86 ISA used: x86-64-v3"), ["x86-64-baseline"])
        self.assertEqual(check_cpu.declared_isa("No ISA note"), [])
        for notes in ("x86 ISA needed: x86-64-v2", "x86 ISA needed: x86-64-baseline, x86-64-v3", "x86 ISA needed: <unknown: 10>"):
            with self.subTest(notes=notes), self.assertRaises(ValueError):
                check_cpu.declared_isa(notes)

    @staticmethod
    def diagnostics():
        return ("dl_hwcaps_subdirs_active=0x0\n"
                "x86.cpu_features.features[0x0].cpuid[0x3]=0x4000000\n"
                "x86.cpu_features.features[0x0].cpuid[0x2]=0x0\n"
                "x86.cpu_features.features[0x1].cpuid[0x1]=0x0\n"
                "x86.cpu_features.features[0x2].cpuid[0x2]=0x0\n")

    def test_qemu_cpu_evidence_requires_sse2_and_absent_new_features(self):
        cpu_smoke.verify_diagnostics(self.diagnostics())
        for text in (self.diagnostics().replace("active=0x0", "active=0x1"),
                     self.diagnostics().replace("[0x2]=0x0", "[0x2]=0x10000000", 1),
                     self.diagnostics().replace("[0x1]=0x0", "[0x1]=0x20"),
                     self.diagnostics().replace("[0x3]=0x4000000", "[0x3]=0x0"), "layout changed"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                cpu_smoke.verify_diagnostics(text)


class MainuanWorkflowTests(unittest.TestCase):
    def test_workflow_is_pinned_branch_specific_and_not_a_release(self):
        import yaml
        workflow = yaml.load((ROOT / ".github/workflows/build-mainuan-deb.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow["on"]), {"push", "pull_request", "workflow_dispatch"})
        for event in ("push", "pull_request"):
            self.assertEqual(workflow["on"][event]["branches"], ["port/kubuntu-26.04"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["jobs"]), {"build"})
        job = workflow["jobs"]["build"]
        self.assertEqual(job["container"]["options"], "--platform linux/amd64")
        self.assertRegex(job["container"]["image"], r"^ubuntu:26\.04@sha256:[a-f0-9]{64}$")
        for step in job["steps"]:
            if "uses" in step:
                self.assertRegex(step["uses"], r"^actions/(checkout|upload-artifact)@[a-f0-9]{40}$")
        self.assertFalse((ROOT / ".github/workflows/build.yml").exists())

    def test_prepare_variants_before_install_and_build_tests_unprivileged(self):
        import yaml
        job = yaml.load((ROOT / ".github/workflows/build-mainuan-deb.yml").read_text(), Loader=yaml.BaseLoader)["jobs"]["build"]
        prepare = job["steps"][0]["run"]
        self.assertLess(prepare.index('#clear APT::Architecture-Variants'), prepare.index("apt-get update"))
        for step in job["steps"][3:]:
            if "run" in step:
                self.assertIn("runuser -u mainuan-build", step["run"])
                self.assertNotIn("apt-get install", step["run"])
        text = (ROOT / ".github/workflows/build-mainuan-deb.yml").read_text()
        self.assertNotIn("--native", text)
        self.assertNotIn("--report-only", text)
        self.assertIn("sha256sum --check SHA256SUMS", text)
        self.assertNotIn("packagekit_mutation_probe.py", text)

    def test_ci_prepares_all_runtime_dependencies_from_control(self):
        _, binary = [Parser().parsestr(stanza) for stanza in (ROOT / "debian/control").read_text().strip().split("\n\n")]
        workflow = (ROOT / ".github/workflows/build-mainuan-deb.yml").read_text()
        for clause in (binary["Depends"] + "," + binary["Recommends"]).split(","):
            if not clause.strip():
                continue
            name = clause.strip().split()[0]
            if not name.startswith("${"):
                self.assertIn(name, workflow)


if __name__ == "__main__":
    unittest.main()
