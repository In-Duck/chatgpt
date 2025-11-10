# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 포함할 이미지 데이터
datas = [
    ('images/*.png', 'images'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=False,          # ✅ onefile일 땐 False로 해야 함
    name='instargram',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                   # ✅ 콘솔창 숨기기
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='instargram.ico',           # ✅ 아이콘 지정
    # ✅ 여기 추가: onefile 모드
    onefile=True,
    # ✅ 추가: 실행 중 압축 풀 경로 자동 생성
    runtime_tmpdir=None
)
