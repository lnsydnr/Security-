# Bundling the app

To create a standalone executable for the Security+ app, you can use PyInstaller. Below are the steps to bundle the app:

```sh
pyi-makespec.exe --onefile --windowed --name="security-plus-app" --add-data "assets/app_icon.png;assets" src/security_app.py
```

This command generates a .spec file with the necessary configuration to bundle the app, including the app icon and assets.

```sh
pyinstaller security-plus-app.spec
```

After running the above command, PyInstaller will create a `dist` directory containing the bundled executable. You can find the `security-plus-app.exe` file inside the `dist` folder, which you can run on any compatible Windows system without needing to install Python or dependencies separately.