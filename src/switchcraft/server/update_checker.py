"""
Docker Update Checker for SwitchCraft Web.
Checks GitHub releases for newer versions.
"""
import logging
import httpx
from packaging import version
from switchcraft import __version__

logger = logging.getLogger(__name__)

GITHUB_RELEASES_URL = "https://api.github.com/repos/FaserF/SwitchCraft/releases/latest"


async def check_for_updates() -> dict:
    """
    Check GitHub for the latest release version.

    Returns:
        dict with keys:
        - has_update: bool
        - current_version: str
        - latest_version: str
        - release_url: str (URL to release page)
        - docker_command: str (docker pull command hint)
        - error: str (if check failed)
    """
    result = {
        "has_update": False,
        "current_version": __version__,
        "latest_version": __version__,
        "release_url": "",
        "docker_command": "",
        "error": None
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                GITHUB_RELEASES_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"SwitchCraft/{__version__}"
                }
            )

            if response.status_code != 200:
                result["error"] = f"GitHub API returned status {response.status_code}"
                return result

            data = response.json()
            latest_tag = data.get("tag_name", "").lstrip("v")

            if not latest_tag:
                result["error"] = "Could not parse latest version"
                return result

            result["latest_version"] = latest_tag
            result["release_url"] = data.get("html_url", "")

            # Compare versions
            try:
                current = version.parse(__version__)
                latest = version.parse(latest_tag)

                if latest > current:
                    result["has_update"] = True
                    result["docker_command"] = "docker pull ghcr.io/faserf/switchcraft:latest"
                    logger.info(f"Update available: {__version__} -> {latest_tag}")
                else:
                    logger.info(f"SwitchCraft is up to date ({__version__})")

            except Exception as e:
                logger.warning(f"Version comparison failed: {e}")
                # Fall back to string comparison
                if latest_tag != __version__:
                    result["has_update"] = True
                    result["docker_command"] = "docker pull ghcr.io/faserf/switchcraft:latest"

    except httpx.TimeoutException:
        result["error"] = "Timeout connecting to GitHub"
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Update check failed: {e}")

    return result


def check_for_updates_sync() -> dict:
    """Synchronous wrapper for update check."""
    import asyncio
    try:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # If we're already in an async context, return a placeholder
                return {
                    "has_update": False,
                    "current_version": __version__,
                    "error": "Cannot run sync check in async context"
                }
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(check_for_updates())

        return loop.run_until_complete(check_for_updates())
    except Exception as e:
        logger.error(f"Sync update check failed: {e}")
        return {
            "has_update": False,
            "current_version": __version__,
            "error": str(e)
        }
