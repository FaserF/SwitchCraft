# SAP Management Wizard

The **SAP Management Wizard** is a guided tool designed to simplify the lifecycle management of SAP Installation Servers.

![SAP Wizard Screenshot](/docs/public/img/sap_wizard.png)
*Note: Screenshot represents the modern UI layout.*

## View Components

### Server Selection
The first step requires the path to a network share or local folder containing the SAP nwsetupadmin server.

### Update Manager
Allows queuing multiple `.exe` patches for sequential merging.

### Customization Options
- **WebView2 Toggle**: Corresponds to the `UseWebView2` parameter in the SAP configuration.
- **Branding**: Automatically handles the copying and registration of custom logos.

## Best Practices
- Always create a backup of your `Setup` directory before applying customizations.
- Ensure you have administrative privileges on the folder where the installation server is hosted.
- Test the resulting Single-File Installer on a clean machine before wide-scale distribution.
