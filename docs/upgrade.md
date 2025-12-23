# Upgrade Notes

## Code Signing Certificate Configuration

When configuring code signing, the `SigningService` resolves the certificate in the following order of precedence:

1.  **Thumbprint**: Explicit thumbprint configuration.
2.  **`CodeSigningCertPath`**: Path to the certificate file (Pfx).
3.  **`CertPath`**: Legacy configuration path.

If `CodeSigningCertPath` is not configured, the service will check `CertPath` for compatibility. Users migrating from setups where only `CertPath` was used should be aware of this fallback.
