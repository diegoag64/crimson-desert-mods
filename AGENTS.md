# Repository workflow

- Use small commits for changes. Keep the verified inventory baseline separate from experimental shop changes. Do not rewrite published history.
- Read `docs/build.md` before build changes and `docs/install.md` before installer changes. The canonical code is under `nativegrid/` and `scripts/`. Historical root-level scratch scripts are untracked and must remain intact for local tests.
- Preserve existing packages and rollback copies. Build into a new ignored output directory. Never install, launch the game, touch saves, or change game files without the user's authorization for that action.
- Keep exact EXE, method, index, and asset guards. A new game hash requires a compatibility audit. Never update pins merely to make a build pass.
- Run relevant native fixtures, Python checks, installer fixtures, and `scripts/audit_publication.py` before committing. Report fixture results separately from live UI evidence. Label shop UI experimental until an active runtime and live test establish its behavior.
- Add source files and documentation images to both `tracked-files.txt` and `.gitignore` by exact path. Stage explicit paths. Keep README and documentation screenshots under `docs/images/`; the publication audit permits PNG, JPEG, and WebP files there up to 8 MiB each. Keep research captures untracked. Never commit extracted game assets, generated headers, executables, logs, research dumps, downloads, tools, secrets, or local configuration.
- Do not select a project license without user authorization. Preserve third-party notices in dependency setup and local packages.
