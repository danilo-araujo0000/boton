from cx_Freeze import setup, Executable

setup(
    name="botao de enviar",
    version="1.0",
    description="botao de enviar , codigo violeta 32 bits",
    options={
        'build_exe': {
            'include_files': ['C:/Windows/System32/api-ms-win-core-path-l1-1-0.dll'],
            'packages': ['unicodedata', 'zipfile'],
        }
    },
    executables=[Executable("botao de enviar.py")],
)
