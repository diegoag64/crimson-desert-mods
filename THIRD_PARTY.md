# Third-party dependencies

`nativegrid/dependencies.lock.json` pins download URLs and SHA256 hashes. Setup keeps downloaded code and binaries under ignored `.deps`. No third-party implementation is vendored in this repository.

- [MinHook](https://github.com/TsudaKageyu/minhook), version 1.3.4, commit `c3fcafdc10146beb5919319d0683e44e3c30d537`. The runtime compiles its source. [The retained license](nativegrid/licenses/MinHook.txt) includes the MinHook and HDE notices. Include it with any local binary package.
- [Crimson Desert Ultimate Mods Manager](https://github.com/faisalkindi/CrimsonDesert-UltimateModsManager), commit `b5cc8fc40d7f4733adba40f46212d749928350c8`. Setup fetches only `paz_crypto.py` and `hashlittle.py`. The read-only builder uses filename-based archive decryption and checksum helpers. [The retained MIT license](nativegrid/licenses/CDUMM.txt) applies to those helpers.
- [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader), release 10.0.2. Setup verifies the official x64 no-PDB archive and its DLL hash. Its license is pinned at source commit `56fa0b03920f2a71174126e03a05c77d48b74744`. [The retained MIT license](nativegrid/licenses/Ultimate-ASI-Loader.txt) accompanies local packages.
- [python-lz4](https://github.com/python-lz4/python-lz4) 4.4.5 and [cryptography](https://github.com/pyca/cryptography) 50.0.2 are Python build dependencies. Install their published distributions with their included licenses. They are not embedded in the ASI.

NativeGrid's original code and mod changes use the [MIT License](LICENSE). This grant does not cover dependencies, Pearl Abyss game content, or game assets depicted in documentation screenshots. Each dependency retains its own license. Do not redistribute extracted game resources or generated payload headers.

The revision 42 release candidate ZIP includes NativeGrid's MIT notice and the retained MinHook/HDE and CDUMM notices. It does not bundle DMM, an ASI loader, Python, or Python dependencies. The builder's local output still contains loader files and test resources; publish only the separately audited release ZIP after validation.
