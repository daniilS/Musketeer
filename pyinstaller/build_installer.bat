if exist venv (rmdir /s /q .\venv\ || exit /b)
if exist build (rmdir /s /q .\build\ || exit /b)
if exist dist (rmdir /s /q .\dist\ || exit /b)
python -m venv --clear --upgrade-deps venv || exit /b
call venv\Scripts\activate.bat

pip install git+https://github.com/DudeNr33/pyinstaller-versionfile.git
pip install --upgrade --upgrade-strategy=eager wheel pyinstaller  ..

pyivf-make_version --source-format distribution --metadata-source musketeer --outfile version_info.txt

pyinstaller --noconfirm Musketeer.spec || goto cleanup

for /f %%i in ('python -c "import musketeer; print(musketeer.__version__)"') do set musketeer_version=%%i

"C:\Program Files (x86)\Inno Setup 6\iscc.exe" /DMyAppVersion=%musketeer_version% musketeer.iss

:cleanup
deactivate
