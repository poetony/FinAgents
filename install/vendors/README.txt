Place offline Windows vendor archives here to include them into the portable release.

Expected files (examples):
- mongodb-windows-x86_64-8.0.13.zip
- redis-7.2.4.zip
- nginx-1.29.3.zip

How to use:
1) Put the zip files above into this folder.
2) Run the assembly script:
   powershell -ExecutionPolicy Bypass -File scripts/deployment/assemble_portable_release.ps1 -ReleaseDir .\release\TradingAgentsCN-portable
   The script will stage these zip bundles into release\vendors.

Notes:
- End users will NOT need to download anything; the portable package will include ready-to-run binaries.
- These archives are only needed by maintainers at build time.