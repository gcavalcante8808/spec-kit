# Sidecar

Install [Sidecar](https://github.com/sidecloud/sidecar) before setup.
The integration key is `sidecar`.

## Multi-Install Safety

This integration is declared multi-install safe. See the
[shared multi-install rules](cli.md#can-i-install-multiple-integrations-in-the-same-project).

## Setup

```bash
specify init my-project --integration sidecar
```

For an existing Spec Kit project, use `specify integration install sidecar`.
See [integration management](cli.md) for activation, upgrades, and removal.

## Installed Skills

Skills are installed as `.sidecar/skills/speckit-<command>/SKILL.md`.
Sidecar invokes skills with an at-mention at the start of a message, not a
slash command, for example `@speckit-specify build photo albums`.

## Workflow Dispatch

Workflow steps use `sidecar --prompt=<prompt>`, which runs one turn, prints
the final reply as plain text, and exits non-zero on failure. The adapter
ignores the workflow `model` and structured-output requests; the Sidecar
profile selects the model.

Supported per-step `integration_options`:

| Option | Type | Effect |
|---|---|---|
| `profile` | string | Passes `-c <profile>` to use an explicit profile TOML |
| `advised` | boolean | Passes `--advised`: the configured advisor must approve before mutating tools run and must accept the step's ending |

```yaml
- id: implement
  command: speckit.implement
  integration: sidecar
  integration_options:
    advised: true
  input:
    args: "{{ inputs.spec }}"
```

`integration_args` is not supported. `SPECKIT_INTEGRATION_SIDECAR_EXTRA_ARGS`
appends extra flags before the prompt.
