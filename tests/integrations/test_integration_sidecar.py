"""Tests for SidecarIntegration."""

import json

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest

from .test_integration_base_skills import SkillsIntegrationTests


class TestSidecarIntegration(SkillsIntegrationTests):
    KEY = "sidecar"
    FOLDER = ".sidecar/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".sidecar/skills"

    def test_options_include_skills_flag(self):
        """Not applicable to Sidecar — it is always skills-based."""
        pytest.skip("Sidecar is always skills-based and does not expose a --skills option")

    def test_options_do_not_include_skills_flag(self):
        i = get_integration(self.KEY)
        assert i is not None
        assert not [o for o in i.options() if o.name == "--skills"]


class TestSidecarCommandInvocation:
    """Sidecar invokes skills by at-mention; its slash commands are built-in only."""

    def test_core_command_renders_at_mention(self):
        i = get_integration("sidecar")

        invocation = i.build_command_invocation("speckit.plan", "ship it")

        assert invocation == "@speckit-plan ship it"

    def test_extension_command_renders_hyphenated_at_mention(self):
        i = get_integration("sidecar")

        invocation = i.build_command_invocation("speckit.git.commit")

        assert invocation == "@speckit-git-commit"


class TestSidecarBuildExecArgs:
    """Sidecar's one-shot mode is ``sidecar --prompt=<prompt>``."""

    def _impl(self):
        from specify_cli.integrations.sidecar import SidecarIntegration

        return SidecarIntegration()

    def test_returns_one_shot_prompt_args(self):
        args = self._impl().build_exec_args("@speckit-specify build photo albums")

        assert args == ["sidecar", "--prompt=@speckit-specify build photo albums"]

    def test_output_json_and_model_do_not_change_command_line(self):
        impl = self._impl()

        base = impl.build_exec_args("hello")

        assert impl.build_exec_args("hello", output_json=False) == base
        assert impl.build_exec_args("hello", model="gpt-oss") == base

    def test_prompt_starting_with_dash_stays_one_token(self):
        args = self._impl().build_exec_args("--help")

        assert args == ["sidecar", "--prompt=--help"]

    def test_runtime_options_add_profile_and_advised_mode(self):
        args = self._impl().build_exec_args(
            "@speckit-implement",
            integration_options={"profile": "work.toml", "advised": True},
        )

        assert args == ["sidecar", "-c", "work.toml", "--advised", "--prompt=@speckit-implement"]

    def test_advised_false_omits_flag(self):
        args = self._impl().build_exec_args("hi", integration_options={"advised": False})

        assert args == ["sidecar", "--prompt=hi"]

    def test_extra_args_precede_prompt(self, monkeypatch):
        monkeypatch.setenv("SPECKIT_INTEGRATION_SIDECAR_EXTRA_ARGS", "--resume abc")

        args = self._impl().build_exec_args("@speckit-plan")

        assert args == ["sidecar", "--resume", "abc", "--prompt=@speckit-plan"]

    def test_integration_args_are_rejected(self):
        with pytest.raises(ValueError, match="integration_args"):
            self._impl().build_exec_args("hi", integration_args=["--advised"])

    def test_unknown_runtime_option_is_rejected(self):
        with pytest.raises(ValueError, match="model"):
            self._impl().build_exec_args("hi", integration_options={"model": "x"})

    def test_non_boolean_advised_is_rejected(self):
        with pytest.raises(ValueError, match="advised"):
            self._impl().build_exec_args("hi", integration_options={"advised": "yes"})

    def test_blank_profile_is_rejected(self):
        with pytest.raises(ValueError, match="profile"):
            self._impl().build_exec_args("hi", integration_options={"profile": " "})


class TestSidecarInitFlow:
    def test_integration_sidecar_creates_skills(self, tmp_path):
        target = tmp_path / "test-proj"

        result = CliRunner().invoke(
            app,
            ["init", str(target), "--integration", "sidecar", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --integration sidecar failed: {result.output}"
        assert (target / ".sidecar" / "skills" / "speckit-plan" / "SKILL.md").exists()


class TestSidecarSkillCompatibility:
    """Sidecar reads ``name`` and ``description`` from one-level-deep SKILL.md
    bundles and substitutes ``$ARGUMENTS`` with the at-mention's trailing text."""

    def _setup_skills(self, tmp_path):
        integration = get_integration("sidecar")
        manifest = IntegrationManifest("sidecar", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")
        return tmp_path / ".sidecar" / "skills"

    def test_skill_frontmatter_name_matches_directory(self, tmp_path):
        import yaml

        skills_dir = self._setup_skills(tmp_path)

        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)
            close = next(i for i in range(1, len(lines)) if lines[i].rstrip() == "---")
            frontmatter = yaml.safe_load("".join(lines[1:close]))
            assert frontmatter.get("name") == skill_dir.name
            assert frontmatter.get("description", "").strip()

    def test_specify_skill_receives_arguments(self, tmp_path):
        skills_dir = self._setup_skills(tmp_path)

        content = (skills_dir / "speckit-specify" / "SKILL.md").read_text(encoding="utf-8")

        assert "$ARGUMENTS" in content


class TestSidecarAtMentionReferences:
    """Generated text must point at ``@speckit-<name>``: ``/speckit-<name>``
    is not a Sidecar slash command and would be rejected as unknown."""

    def test_skill_bodies_reference_commands_by_at_mention(self, tmp_path):
        integration = get_integration("sidecar")
        integration.setup(tmp_path, IntegrationManifest("sidecar", tmp_path), script_type="sh")

        content = (tmp_path / ".sidecar" / "skills" / "speckit-implement" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        assert "@speckit-tasks" in content
        assert "/speckit-tasks" not in content

    def test_hooks_render_at_mention_invocation(self, tmp_path):
        from specify_cli.extensions import HookExecutor

        init_options = tmp_path / ".specify" / "init-options.json"
        init_options.parent.mkdir(parents=True)
        init_options.write_text(json.dumps({"ai": "sidecar", "ai_skills": True}))

        message = HookExecutor(tmp_path).format_hook_message(
            "before_plan",
            [{"extension": "test-ext", "command": "speckit.plan", "optional": False}],
        )

        assert "EXECUTE_COMMAND_INVOCATION: @speckit-plan" in message


class TestSidecarMultiInstallSafe:
    def test_multi_install_safe_is_true(self):
        assert get_integration("sidecar").multi_install_safe is True

    def test_sidecar_root_does_not_overlap_other_safe_integrations(self):
        from pathlib import PurePosixPath

        from specify_cli.integrations import INTEGRATION_REGISTRY

        sidecar_root = PurePosixPath(".sidecar")
        for key, integration in INTEGRATION_REGISTRY.items():
            if key == "sidecar" or not integration.multi_install_safe:
                continue
            folder = (integration.config or {}).get("folder")
            if not folder:
                continue
            other = PurePosixPath(str(folder).rstrip("/"))
            for left, right in ((sidecar_root, other), (other, sidecar_root)):
                try:
                    left.relative_to(right)
                except ValueError:
                    continue
                raise AssertionError(f"sidecar root overlaps {key!r} root {other}")
