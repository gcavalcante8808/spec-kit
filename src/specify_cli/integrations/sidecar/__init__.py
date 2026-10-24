"""Sidecar integration — skills-based agent.

Sidecar discovers project skills from ``.sidecar/skills`` using
``<name>/SKILL.md`` bundles with ``name``/``description`` frontmatter. Skills
are invoked by an at-mention at the start of a message, for example
``@speckit-specify build photo albums``; Sidecar replaces ``$ARGUMENTS`` in
the skill body with the text after the skill name. Slash commands are a
fixed, built-in set in Sidecar, so ``/speckit-<name>`` would not resolve.

See: https://github.com/sidecloud/sidecar
"""

from __future__ import annotations
from pathlib import Path

from collections.abc import Mapping, Sequence
from typing import Any

from ..base import SkillsIntegration


class SidecarIntegration(SkillsIntegration):
    """Integration for the Sidecar coding agent."""

    key = "sidecar"
    config = {
        "name": "Sidecar",
        "folder": ".sidecar/",
        "commands_subdir": "skills",
        "install_url": "https://github.com/sidecloud/sidecar",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".sidecar/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    # ``.sidecar/skills`` is a static agent root that no other integration
    # writes into, so co-installing Sidecar alongside other agents is safe.
    multi_install_safe = True

    _RUNTIME_OPTIONS = frozenset({"advised", "profile"})

    def build_command_invocation(self, command_name: str, args: str = "") -> str:
        """Build Sidecar's at-mention skill invocation, e.g. ``@speckit-plan``."""
        stem = command_name
        if stem.startswith("speckit."):
            stem = stem[len("speckit."):]

        invocation = "@speckit-" + stem.replace(".", "-")
        if args:
            invocation = f"{invocation} {args}"
        return invocation

    def build_exec_args(
        self,
        prompt: str,
        *,
        model: str | None = None,
        output_json: bool = True,
        integration_args: Sequence[str] | None = None,
        integration_options: Mapping[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> list[str] | None:
        """Build non-interactive CLI args for Sidecar.

        Sidecar's one-shot mode is ``sidecar --prompt=<prompt>``: it runs one
        turn, prints the final assistant reply as plain text, and exits
        non-zero on failure. The CLI has no structured-output or model flag
        (the profile selects the model), so ``output_json`` and ``model`` are
        ignored.

        Per-step ``integration_options``:

        * ``profile`` — path to a profile TOML, passed as ``-c <profile>``.
        * ``advised`` — ``true`` runs the step in advised mode, where the
          configured advisor must approve before mutating tools run and must
          accept the step's ending.

        The prompt is passed as ``--prompt=<prompt>`` so a prompt starting
        with ``-`` is never parsed as a flag.
        """
        self.validate_runtime_config(integration_args, integration_options)
        options = integration_options or {}
        args = [self._resolve_executable()]
        self._apply_extra_args_env_var(args)
        if "profile" in options:
            args.extend(["-c", options["profile"]])
        if options.get("advised"):
            args.append("--advised")
        args.append(f"--prompt={prompt}")
        return args

    def validate_runtime_config(
        self,
        integration_args: Sequence[str] | None = None,
        integration_options: Mapping[str, Any] | None = None,
    ) -> None:
        """Accept only the ``advised`` and ``profile`` per-step options."""
        if integration_args:
            raise ValueError(
                "Integration 'sidecar' does not support per-step "
                "'integration_args'; use 'integration_options'."
            )
        options = dict(integration_options or {})
        unknown = sorted(str(name) for name in options if name not in self._RUNTIME_OPTIONS)
        if unknown:
            raise ValueError(
                "Integration 'sidecar' does not support per-step "
                f"'integration_options' ({', '.join(unknown)}); "
                "supported options are 'advised' and 'profile'."
            )
        if "advised" in options and not isinstance(options["advised"], bool):
            raise ValueError("Sidecar 'integration_options.advised' must be a boolean.")
        if "profile" in options:
            profile = options["profile"]
            if not isinstance(profile, str) or not profile.strip():
                raise ValueError(
                    "Sidecar 'integration_options.profile' must be a non-empty path."
                )
