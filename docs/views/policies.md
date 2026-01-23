# Policies (GPO/Intune)

The **Policies** view helps you troubleshoot why a device behaves a certain way by inspecting the enforced configurations.

## Features
*   **Resultant Set of Policy (RSoP)**: Gathers applied Group Policies (GPO) and Intune Configuration Profiles.
*   **Search**: Filter policies by name (e.g., "Windows Update", "Defender").
*   **Conflict Detection**: Highlights settings where GPO might conflict with Intune (MDM Wins over GPO is a common concern).
*   **Export**: Save the policy report to HTML for documentation/ticketing.

## Use Case
If an app fails to install because "Windows Installer is disabled", look here to find the exact policy object ID (GUID) or GPO name enforcing that restriction.
