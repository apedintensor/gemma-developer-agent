"""Offline setup check. Never calls a provider or prints credential values."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-registry', action='store_true',
                        help='Also check local central registry metadata.')
    parser.add_argument('--check-credentials', action='store_true',
                        help='Also load the selected central credential in memory, offline.')
    args = parser.parse_args()
    settings = json.loads((ROOT / 'configs/project.json').read_text(encoding='utf-8'))
    expected = settings['prototype']
    if settings['competition_model'] != 'gemma-4-31b-it-qat-w4a16-ct':
        raise RuntimeError('Unexpected competition model.')
    if expected['model'] != 'gemma-4-31b-it' or expected['service'] != 'gemini':
        raise RuntimeError('Unexpected prototype model or service.')
    if expected['base_url'] != 'https://generativelanguage.googleapis.com':
        raise RuntimeError('Unexpected prototype endpoint.')
    if expected['protocol'] != 'gemini_generate_content':
        raise RuntimeError('Unexpected prototype protocol.')
    print('PASS: public project configuration (offline).')
    print('Competition model: ' + settings['competition_model'])
    print('Prototype model: ' + expected['model'])
    if not (args.check_registry or args.check_credentials):
        print('Local registry not required. Official harness and provider access remain unverified.')
        return
    local_path = ROOT / 'configs/local.json'
    local = json.loads(local_path.read_text(encoding='utf-8')) if local_path.exists() else {}
    registry_path = os.environ.get('AI_REGISTRY_ROOT') or local.get(
        'registry_windows' if os.name == 'nt' else 'registry_wsl')
    profile_id = os.environ.get('AI_REGISTRY_PROFILE') or local.get('profile')
    if not registry_path or not profile_id:
        raise RuntimeError('Explicit local registry path and profile are required.')
    registry = Path(registry_path)
    if not (registry / 'api_registry.py').is_file():
        raise RuntimeError('Central registry unavailable; check AI_REGISTRY_ROOT.')
    metadata = json.loads((registry / 'registry/api-profiles.json').read_text(encoding='utf-8'))
    profile = metadata['profiles'].get(profile_id)
    if not profile or profile['service'] != expected['service']:
        raise RuntimeError('Selected service/profile does not match central metadata.')
    if profile.get('base_url') != expected['base_url']:
        raise RuntimeError('Endpoint mismatch; review configuration before using this profile.')
    sys.path.insert(0, str(registry))
    loader = importlib.import_module('api_registry')
    if args.check_credentials:
        config = loader.load_api(expected['service'], profile=profile_id)
        if not config.api_key or config.base_url != expected['base_url']:
            raise RuntimeError('Credential missing or runtime endpoint mismatch.')
        print('PASS: selected credential loaded in memory (offline only).')
    print('PASS: central loader, selected profile and endpoint metadata.')
    print('No network requests. Official harness and provider access remain unverified.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Do not echo arbitrary loader exception text: it could include sensitive data.
        print('FAIL: setup check could not complete (' + type(exc).__name__ + ').', file=sys.stderr)
        sys.exit(1)
