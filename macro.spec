block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pynput._util.win32',
        'pynput._util.win32_vks',
        'pystray._win32',
        'six',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'pynput.keyboard._darwin', 'pynput.keyboard._xorg',
        'pynput.mouse._darwin', 'pynput.mouse._xorg',
        'pystray._darwin', 'pystray._gtk', 'pystray._xorg',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MacroApp',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MacroApp',
)
