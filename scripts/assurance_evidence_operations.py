"""Fixed operations for the assurance master; no arbitrary command or path input."""
from pathlib import Path
import json
import os
import shutil
import subprocess

import assurance_evidence_core as c
import assurance_evidence_extension as ex

POLICY = Path('docs/implementation/assurance-evidence-master/operations/allowlist.json')
RULES = POLICY.parent/'allow.rules'
INSTALL = Path('/home/chakwong/.codex/rules/legalmath-assurance-evidence.rules')
ACTIONS = ('ops-preflight', 'ops-install-rules', 'ops-freeze', 'ops-run', 'ops-status')


def expected_commands(root):
    return [prefix+[action] for prefix in (ex.PREFIX,
        [str(root/'.venv/bin/python'), str(root/'scripts/assurance_evidence_master.py')]) for action in ACTIONS]


def rules_text(root):
    return '# Fixed LegalMath assurance operations; the launcher rejects extra arguments.\n'+''.join(
        'prefix_rule(pattern='+json.dumps(command)+', decision="allow")\n' for command in expected_commands(root))


def preflight(root):
    policy = c.read(root/POLICY)
    if policy['commands'] != expected_commands(root) or (root/RULES).read_text() != rules_text(root):
        c.fail('E_INTEGRITY', 'Operations allowlist differs from the reviewed fixed commands')
    codex = shutil.which('codex')
    if codex is None:
        c.fail('E_DEPENDENCY', 'Installed Codex rule checker required')
    checks = []
    for command in expected_commands(root):
        result = subprocess.run([codex, 'execpolicy', 'check', '--rules', str(root/RULES), *command],
            capture_output=True, text=True, timeout=30)
        if result.returncode:
            c.fail('E_INTEGRITY', 'Rule checker failed: '+result.stderr[:1000])
        value = json.loads(result.stdout)
        if value.get('decision') != 'allow':
            c.fail('E_AUTHORITY', 'Exact master command was not allowed: '+str(value))
        checks.append({'command': command, 'decision': value['decision']})
    report = {'status': 'COMMAND_PREFLIGHT_PASSED', 'commands': checks, 'provider_calls': 0,
        'rule_file': c.receipt(root/RULES, root), 'policy': c.receipt(root/POLICY, root),
        'scope': 'Fixed master actions only. No arbitrary shell/interpreter command, global sandbox change or numerical authorization.'}
    c.save(root/POLICY.parent/'preflight.json', report)
    return report


def install(root):
    report = preflight(root)
    content = (root/RULES).read_text()
    if INSTALL.exists() and INSTALL.read_text() != content:
        c.fail('E_INTEGRITY', 'Dedicated rule file already contains different instructions')
    if not INSTALL.exists():
        c.write_text(INSTALL, content)
        os.chmod(INSTALL, 0o600)
    if INSTALL.read_text() != content:
        c.fail('E_INTEGRITY', 'Installed rule bytes differ')
    return {**report, 'status': 'DEDICATED_RULES_INSTALLED', 'installed_path': str(INSTALL)}


def entry(root, code, action):
    if action not in ACTIONS:
        c.fail('E_AUTHORITY', 'Unknown fixed operations action')
    ex.master.check_command(c.read(root/POLICY), ex.PREFIX+[action])
    if action == 'ops-preflight':
        ex.master.output(preflight(root))
    elif action == 'ops-install-rules':
        ex.master.output(install(root))
    else:
        mapped = {'ops-freeze': 'extend-repair', 'ops-run': 'extend', 'ops-status': 'extend-status'}[action]
        ex.entry(root, code, mapped)
