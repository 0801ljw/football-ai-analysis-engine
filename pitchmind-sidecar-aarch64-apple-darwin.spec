# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('app')


a = Analysis(
    ['/Users/ljw/projects/worldcup-ai-content-engine/desktop/sidecar_main.py'],
    pathex=['/Users/ljw/projects/worldcup-ai-content-engine'],
    binaries=[],
    datas=[('/Users/ljw/projects/worldcup-ai-content-engine/app/templates', 'app/templates'), ('/Users/ljw/projects/worldcup-ai-content-engine/app/static', 'app/static'), ('/Users/ljw/projects/worldcup-ai-content-engine/data/demo_matches.json', 'data'), ('/Users/ljw/projects/worldcup-ai-content-engine/app/main.py', 'app'), ('/Users/ljw/projects/worldcup-ai-content-engine/scripts/start.sh', 'scripts'), ('/Users/ljw/projects/worldcup-ai-content-engine/scripts/smoke.sh', 'scripts'), ('/Users/ljw/projects/worldcup-ai-content-engine/scripts/setup.sh', 'scripts'), ('/Users/ljw/projects/worldcup-ai-content-engine/scripts/package_release.sh', 'scripts'), ('/Users/ljw/projects/worldcup-ai-content-engine/scripts/external_trial_smoke.py', 'scripts'), ('/Users/ljw/projects/worldcup-ai-content-engine/pyproject.toml', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pitchmind-sidecar-aarch64-apple-darwin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
