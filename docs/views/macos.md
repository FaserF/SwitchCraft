# macOS Packager

While SwitchCraft is Windows-centric, the **macOS Packager** assists in preparing `.pkg` or `.dmg` apps for deployment to Mac devices via Intune.

## Workflow
1.  **Input**: Select a `.app` bundle or a raw script.
2.  **Signing**: (Optional) Sign the package with an Apple Developer ID Installer certificate (required for Gatekeeper/Intune deployment without prompts).
    *   *Requires `productsign` tool available (on Mac agents) or cloud signing service integration.*
3.  **Wrapper**: Can wrap simple `.app` bundles into a standardized install PKG that moves the app to `/Applications`.
4.  **Intune Wrapping**: Converts the final `.pkg` into `.intunemac` (using the Intune App Wrapping Tool for macOS, which must be installed).

## Limitations
*   Unlike Windows apps, macOS packaging is heavily dependent on Apple's toolchain. Some features may require running SwitchCraft on a Mac or having a remote Mac build agent configured.
