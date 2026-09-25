from concurrent.futures import ThreadPoolExecutor
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import Allowance, CodexProvider


def test_shared_allowance_last_slot_is_atomic_and_never_refunded(tmp_path):
    budget=Allowance(tmp_path/'budget.json',1)
    def reserve(_):
        try:return budget.reserve('a'*64)
        except LegalMathError:return 'BLOCKED'
    with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(reserve,range(2)))
    assert sorted(map(str,results))==['1','BLOCKED']
    with pytest.raises(LegalMathError):Allowance(tmp_path/'budget.json',1).reserve('b'*64)
    with pytest.raises(LegalMathError):Allowance(tmp_path/'budget.json',2).reserve('c'*64)


def test_codex_command_is_fresh_readonly_and_ignores_inherited_context(tmp_path):
    provider=CodexProvider();command=provider.command(tmp_path,tmp_path/'schema',tmp_path/'output')
    assert 'resume' not in command and '--ephemeral' in command and '--ignore-user-config' in command
    assert command[command.index('--sandbox')+1]=='read-only'
    assert 'features.shell_tool=false' in command and 'features.apps=false' in command
    assert 'web_search="disabled"' in command


def test_only_provider_routing_survives_config_isolation(tmp_path):
    path=tmp_path/'config.toml'
    path.write_text('model="test-model"\nmodel_provider="corporate"\ndeveloper_instructions="LEAK"\n'
        '[model_providers.corporate]\nname="Corporate"\nbase_url="https://configured.example/v1"\n'
        'wire_api="responses"\nrequires_openai_auth=true\n[mcp_servers.untrusted]\ncommand="LEAK"\n')
    p=CodexProvider(routing_file=path);cmd=p.command(tmp_path,tmp_path/'schema',tmp_path/'out')
    assert '--ignore-user-config' in cmd and 'LEAK' not in ' '.join(cmd)
    assert 'model_provider="corporate"' in cmd
    assert 'model_providers.corporate.base_url="https://configured.example/v1"' in cmd
    assert 'model_providers.corporate.stream_max_retries=0' in cmd


def test_live_provider_cannot_dispatch_without_a_persistent_allowance():
    from legalmath.interpretation.search.models import Settings
    with pytest.raises(LegalMathError):CodexProvider().complete({'task':'GENERATE'},{},Settings())
