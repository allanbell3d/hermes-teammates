"""roster_file: auto — the profile's own teammates.yaml when it exists, otherwise the root Hermes home's."""
import pytest

from test_roster_file import FakeCtx

OWN = 'teammates:\n  mine: {}\n'
SHARED = 'teammates:\n  shared: {}\n'


@pytest.fixture
def homes(monkeypatch, tmp_path):
    """A root Hermes home with one named profile; HERMES_HOME points at the profile."""
    root = tmp_path / 'root'
    profile = root / 'profiles' / 'eva'
    profile.mkdir(parents=True)
    (root / 'config.yaml').write_text('{}\n', encoding='utf-8')  # marks a real Hermes home
    monkeypatch.setenv('HERMES_HOME', str(profile))
    return root, profile


def _config(settings=None):
    from hermes_teammates.teammates_config import parse, read
    from hermes_teammates.teammates_host import load_roster_file
    return parse(read(FakeCtx(settings or {'roster_file': 'auto'}), load_roster_file))


def test_auto_uses_the_profiles_own_file(plugin, homes):
    root, profile = homes
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    (profile / 'teammates.yaml').write_text(OWN, encoding='utf-8')
    config = _config()
    assert set(config['teammates']) == {'mine'} and not config['config_errors']
    assert config['roster_path'] == f"{profile / 'teammates.yaml'} (auto)"


def test_auto_falls_back_to_the_root_file(plugin, homes):
    root, profile = homes
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    config = _config()
    assert set(config['teammates']) == {'shared'} and not config['config_errors']
    assert config['roster_path'] == f"{root / 'teammates.yaml'} (auto)"


def test_auto_follows_adding_and_deleting_the_profile_file(plugin, homes):
    root, profile = homes
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    own = profile / 'teammates.yaml'
    own.write_text(OWN, encoding='utf-8')
    assert set(_config()['teammates']) == {'mine'}
    own.unlink()
    assert set(_config()['teammates']) == {'shared'}


def test_auto_reports_a_broken_profile_file_instead_of_using_the_root(plugin, homes):
    root, profile = homes
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    (profile / 'teammates.yaml').write_text('teammates: {\n', encoding='utf-8')
    config = _config()
    assert config['teammates'] == {} and any('not valid YAML' in e for e in config['config_errors'])


def test_auto_without_any_file_is_an_empty_roster_and_a_problem(plugin, homes):
    root, profile = homes
    config = _config({'roster_file': 'auto', 'teammates': {'scout': {}}})
    assert config['teammates'] == {} and config['roster_path'] == 'auto'
    problem = next(e for e in config['config_errors'] if 'auto found no teammates.yaml' in e)
    assert str(profile) in problem and str(root) in problem


def test_auto_in_the_root_home_checks_only_its_file(plugin, homes, monkeypatch):
    root, _profile = homes
    monkeypatch.setenv('HERMES_HOME', str(root))
    config = _config()
    problem = next(e for e in config['config_errors'] if 'auto found no' in e)
    assert ' or ' not in problem
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    assert set(_config()['teammates']) == {'shared'}


def test_a_file_named_auto_needs_a_path(plugin, homes):
    _root, profile = homes
    (profile / 'auto').write_text(OWN, encoding='utf-8')
    config = _config({'roster_file': './auto'})
    assert set(config['teammates']) == {'mine'} and config['roster_path'].endswith('auto')


def test_auto_without_a_root_helper_uses_the_profile_file_only(plugin, homes, monkeypatch):
    from hermes_teammates import teammates_host
    root, profile = homes
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    def no_root(home):
        raise ImportError('old Hermes')
    monkeypatch.setattr(teammates_host, '_root_home', no_root)
    config = _config()
    assert config['teammates'] == {} and any(f'no teammates.yaml in {profile}' in e for e in config['config_errors'])


def test_slash_command_shows_the_file_auto_picked(rig, homes):
    from hermes_teammates.teammates_config import read
    from hermes_teammates.teammates_host import load_roster_file
    from hermes_teammates.teammates_tools import render_roster
    root, _profile = homes
    (root / 'teammates.yaml').write_text(SHARED, encoding='utf-8')
    rig.service.config_reader = lambda: read(FakeCtx({'roster_file': 'auto'}), load_roster_file)
    assert f"Roster file: {root / 'teammates.yaml'} (auto)" in render_roster(rig.service.roster('s'))
