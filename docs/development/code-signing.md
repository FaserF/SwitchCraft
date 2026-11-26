# Windows Code Signing (CI/CD)

SwitchCraft's Windows `.exe` build workflow (`.github/workflows/build.yml`) supports automated Authenticode signing using either **Azure Trusted Signing** or a **PFX Code Signing Certificate**.

When no signing secrets are configured, the signing steps are skipped cleanly with an informational notice so unsigned local/fork builds continue to succeed.

## Option 1: Azure Trusted Signing (Recommended)

Configure the following repository secrets in GitHub (**Settings > Secrets and variables > Actions**):

- `AZURE_SIGNING_ENDPOINT` (e.g. `https://eus.codesigning.azure.net`)
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_SIGNING_ACCOUNT`
- `AZURE_CERT_PROFILE`

The workflow runs `azure/trusted-signing-action@v0` with SHA-256 digests and RFC 3161 timestamping (`http://timestamp.acs.microsoft.com`).

## Option 2: PFX Code Signing Certificate

If you have an EV/OV `.pfx` certificate, configure:

- `WINDOWS_SIGNING_CERT_B64`: Base64-encoded contents of your `.pfx` file.
- `WINDOWS_SIGNING_CERT_PASSWORD`: Certificate password.

The workflow decodes the certificate to `$RUNNER_TEMP`, signs all built `dist/*.exe` binaries via Windows SDK `signtool.exe` with `/fd SHA256 /tr http://timestamp.digicert.com /td SHA256`, and removes the temporary `.pfx` file in an `always()` cleanup step.

## Verifying a Signed Binary

On Windows, verify the signature and timestamp chain with:

```powershell
signtool verify /pa /v dist\SwitchCraft.exe
```
