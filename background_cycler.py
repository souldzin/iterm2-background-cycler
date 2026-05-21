#!/usr/bin/env python3
"""
iTerm2 Background Image Cycler
Automatically cycles through a list of background images with UI controls.

Installation:
1. Copy this script to: ~/Library/Application Support/iTerm2/Scripts/AutoLaunch/
2. Make it executable: chmod +x background_cycler.py
3. Restart iTerm2
4. Access via Scripts menu > Background Cycler
"""

import iterm2
import random
from iterm2.profile import LocalWriteOnlyProfile
from iterm2.registration import ContextMenuProviderRPC
from iterm2.app import async_get_app, App
import asyncio
import json
import subprocess
from pathlib import Path

# Configuration file paths
CONFIG_DIR = Path.home() / "Library/Application Support/iTerm2"
CONFIG_FILE = CONFIG_DIR / "background_cycler_config.json"
IMAGES_FILE = CONFIG_DIR / "background_cycler_images.json"

# Default settings
DEFAULT_INTERVAL = 300  # 5 minutes in seconds
DEFAULT_ENABLED = True


def get_unique_id(name: str) -> str:
    return f"com.souldzin.iterm2_background_cycler.{name}"


class BackgroundCycler:
    app: App
    images_persist: list[str]
    images: list[str]
    current_index: int | None
    enabled: bool
    interval: int

    def __init__(self, app: App):
        self.app = app
        self.images_persist = []
        self.images = []
        self.current_index = None
        self.enabled = DEFAULT_ENABLED
        self.interval = DEFAULT_INTERVAL
        self.load_config()
        self.load_images()
        self.load_current_index()

    def load_config(self):
        """Load configuration from file"""
        # TODO: What if config is messed up?
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.enabled = config.get("enabled", DEFAULT_ENABLED)
                    self.interval = config.get("interval", DEFAULT_INTERVAL)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = {"enabled": self.enabled, "interval": self.interval}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    def load_images(self):
        """Load image list from file"""
        if IMAGES_FILE.exists():
            try:
                with open(IMAGES_FILE, "r") as f:
                    self.images_persist = json.load(f)
                    self.images = list(self.images_persist)
            except Exception as e:
                print(f"Error loading images: {e}")

    def load_current_index(self):
        self.current_index = self._get_next_available_index(start_idx=0, direction=1)

    def save_images(self):
        """Save image list to file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(IMAGES_FILE, "w") as f:
            json.dump(self.images_persist, f, indent=2)

    async def refresh_background(self):
        if not self.images or self.current_index is None:
            # Nothing to do
            return

        current_image = self.images[self.current_index]
        await self.set_background(current_image)

    async def set_background(self, image_path: str):
        """Set background image for all sessions"""
        prof = LocalWriteOnlyProfile()
        prof.set_background_image_location(image_path)

        for window in self.app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    try:
                        await session.async_set_profile_properties(prof)
                    except Exception as e:
                        print(f"Error setting background: {e}")

    async def cycle(self):
        """Main cycling loop"""
        while True:
            if self.current_index is not None and self.enabled and self.images:
                current_image = self.images[self.current_index]
                await self.set_background(current_image)

            if self.images:
                start_idx = (
                    self.current_index + 1 if self.current_index is not None else 0
                )
                self.current_index = self._get_next_available_index(
                    start_idx=start_idx, direction=1
                )

            await asyncio.sleep(self.interval)

    async def next_image(self):
        """Manually advance to next image"""
        if not self.images:
            return "No images configured"

        self.current_index = self._get_next_available_index(
            start_idx=self.current_index, direction=1, start_at_next=True
        )

        if self.current_index is not None:
            current_image = self.images[self.current_index]
            await self.set_background(current_image)
            return f"Switched to: {Path(current_image).name}"
        else:
            return f"Could not find available image."

    async def previous_image(self):
        """Manually go to previous image"""
        if not self.images:
            return "No images configured"

        self.current_index = self._get_next_available_index(
            start_idx=self.current_index, direction=-1, start_at_next=True
        )

        if self.current_index is not None:
            current_image = self.images[self.current_index]
            await self.set_background(current_image)
            return f"Switched to: {Path(current_image).name}"
        else:
            return f"Could not find available image."

    def toggle_cycling(self):
        """Enable/disable automatic cycling"""
        self.enabled = not self.enabled
        self.save_config()
        status = "enabled" if self.enabled else "disabled"
        return f"Cycling {status}"

    def set_interval(self, seconds):
        """Change cycling interval"""
        self.interval = max(10, seconds)  # Minimum 10 seconds
        self.save_config()
        minutes = self.interval / 60
        return f"Interval set to {minutes:.1f} minutes"

    async def add_images(self, paths: list[str]) -> int:
        had_images = bool(self.images)
        new_images = [p for p in paths if p not in self.images_persist]
        self.images_persist.extend(new_images)
        self.images.extend(new_images)
        self.save_images()
        if not had_images:
            self.current_index = self._get_next_available_index(start_idx=0)
            await self.refresh_background()
        return len(new_images)

    async def clear_images(self):
        self.images_persist = []
        self.images = []
        self.current_index = None
        self.save_images()
        await self.set_background("")

    async def shuffle(self):
        """Randomize the session image order and reset to the first image"""
        if not self.images:
            return "No images to shuffle"

        random.shuffle(self.images)
        self.current_index = self._get_next_available_index(start_idx=0)
        await self.refresh_background()

        return f"Shuffled {len(self.images)} images"

    def get_status(self):
        """Get current status"""
        status = "enabled" if self.enabled else "disabled"
        current = (
            Path(self.images[self.current_index]).name
            if self.images and self.current_index is not None
            else "None"
        )
        return f"Status: {status}\nImages: {len(self.images)}\nCurrent: {current}\nInterval: {self.interval}s"

    def _get_next_available_index(
        self,
        start_idx: int | None,
        direction: int = 1,
        start_at_next: bool = False,
    ) -> int | None:
        """
        Find the next available image index starting from start_idx.

        Args:
            start_idx: Index to start searching from. If None, starts at 0 if possible.
            direction: 1 for forward, -1 for backward

        Returns:
            The next available index, or None if no images are available.
        """
        if not self.images:
            return None

        if start_idx is None:
            start_idx = 0

        if start_at_next:
            start_idx = (start_idx + direction) % len(self.images)

        for offset in range(len(self.images)):
            idx = (start_idx + offset * direction) % len(self.images)
            if self._is_image_available(self.images[idx]):
                return idx

        return None

    def _is_image_available(self, image_path_str: str):
        image_path = Path(image_path_str)

        return image_path.exists() and image_path.is_file()


async def select_images_ui():
    """Show macOS file picker to select images"""
    applescript = """
    tell application "iTerm2"
        activate
    end tell
    
    set imageFiles to choose file with prompt "Select background images (hold ⌘ for multiple)" ¬
        with multiple selections allowed ¬
        of type {"public.image"}
    
    set imagePaths to {}
    repeat with imageFile in imageFiles
        set end of imagePaths to POSIX path of imageFile
    end repeat
    
    return imagePaths
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse AppleScript list output
            output = result.stdout.strip()
            if output:
                # Remove "alias" prefix and parse paths
                paths = [p.strip() for p in output.split(",")]
                # Clean up AppleScript formatting
                paths = [p.replace("alias ", "").strip() for p in paths]
                return paths
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"Error in file picker: {e}")
        return None


async def prompt_interval_ui():
    """Prompt user for new interval"""
    applescript = """
    tell application "iTerm2"
        activate
        set userInput to text returned of (display dialog "Enter cycling interval in minutes:" default answer "5")
        return userInput
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                minutes = float(result.stdout.strip())
                return int(minutes * 60)  # Convert to seconds
            except ValueError:
                return None
        return None
    except Exception as e:
        print(f"Error in interval dialog: {e}")
        return None


async def show_alert(title, message):
    """Show a macOS alert dialog"""
    applescript = f"""
    tell application "iTerm2"
        activate
        display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"
    end tell
    """

    try:
        subprocess.run(["osascript", "-e", applescript], timeout=60)
    except Exception as e:
        print(f"Error showing alert: {e}")


async def confirm_alert(title, message) -> bool:
    """Show a macOS confirmation dialog, returns True if the user confirmed"""
    applescript = f"""
    tell application "iTerm2"
        activate
        set result to button returned of (display dialog "{message}" with title "{title}" buttons {{"Cancel", "OK"}} default button "Cancel")
        return result
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0 and result.stdout.strip() == "OK"
    except Exception as e:
        print(f"Error showing confirm dialog: {e}")
        return False


async def main(connection):
    app = await async_get_app(connection)
    if not app:
        print(f"ERROR! iTerm2 app not found. Cannot continue.")
        return 1

    cycler = BackgroundCycler(app)

    # Start the cycling loop in the background
    asyncio.create_task(cycler.cycle())

    # RPC: Add more images
    @ContextMenuProviderRPC
    async def add_images():
        paths = await select_images_ui()
        if paths:
            count = await cycler.add_images(paths)
            await show_alert("Success", f"Added {count} new images")
            return f"Added {count} new images"
        return "No images selected"

    # RPC: Clear all images
    @ContextMenuProviderRPC
    async def clear_images():
        confirmed = await confirm_alert(
            "Clear Images",
            "Are you sure? This will remove your settings for all background images.",
        )
        if not confirmed:
            return "Cancelled image clearing"
        await cycler.clear_images()
        return "All images cleared"

    # RPC: Next image
    @ContextMenuProviderRPC
    async def next_image():
        return await cycler.next_image()

    # RPC: Previous image
    @ContextMenuProviderRPC
    async def previous_image():
        return await cycler.previous_image()

    # RPC: Shuffle images
    @ContextMenuProviderRPC
    async def shuffle_images():
        return await cycler.shuffle()

    # Register all RPC calls with display names so they appear in the Scripts menu
    await add_images.async_register(
        connection,
        display_name="Cycler: Add Images",
        unique_identifier=get_unique_id("add_images"),
        timeout=180,
    )
    await clear_images.async_register(
        connection,
        display_name="Cycler: Clear Images",
        unique_identifier=get_unique_id("clear_images"),
    )
    await next_image.async_register(
        connection,
        display_name="Cycler: Next Image",
        unique_identifier=get_unique_id("next_image"),
    )
    await previous_image.async_register(
        connection,
        display_name="Cycler: Previous Image",
        unique_identifier=get_unique_id("previous_image"),
    )
    await shuffle_images.async_register(
        connection,
        display_name="Cycler: Shuffle Images",
        unique_identifier=get_unique_id("shuffle_images"),
    )

    print("Background Cycler started! Access via Scripts > Background Cycler")


# Run the script
iterm2.run_forever(main)
