# Kali Linux on VMware Fusion (Apple silicon)

This is an **instructions-only adaptation** for this fork, not a conversion of Zenwolf's Arch-specific system modules or a tested Kali image. It focuses on Kali ARM64 in VMware Fusion on an Apple-silicon Mac. Keep the original [Arch build guide](build-guide.md) for the upstream setup; do not run its Pacman or hardware-specific instructions in Kali.

## Compatibility and safety

- Use a Kali **ARM64/aarch64** installer image and create an ARM virtual machine in Fusion. An amd64 image is not the right guest architecture for Apple silicon.
- The tracked compositor config uses Hyprland's Lua API and requires **Hyprland 0.55 or newer**. Kali's candidate version may be older or some packages may be unavailable. Check before installing; if the requirement is not met, use Kali's supported desktop and do not launch the tracked Hyprland config.
- VMware's virtual graphics device is not the AMD/NVIDIA hybrid hardware this setup was designed for. Do not install Zenwolf's NVIDIA, GPU lifecycle, suspend, or ESP modules in this VM.
- Hyprland under Fusion is experimental. 3D acceleration and display behavior depend on Fusion, guest tools, and the Kali release. Prefer Kali's supported desktop (commonly Xfce) if Wayland or the virtual display is unreliable.
- Back up the VM before changing desktop or display settings. Commands below affect the Kali guest only.

## 1. Prepare Kali and VMware guest tools

Create a Kali ARM64 VM in Fusion, install Kali, create a non-root user, and confirm networking. Then install basic tools and the VMware guest utilities:

```bash
sudo apt update
sudo apt install --no-install-recommends \
  git rsync python3 python3-pygame jq ripgrep nano pciutils \
  open-vm-tools open-vm-tools-desktop
```

Reboot after guest-tools installation. In Fusion, enable the available display acceleration and guest display resizing options. Names and availability vary by Fusion version. Confirm window resizing, pointer movement, clipboard, and networking from Kali before trying another desktop.

## 2. Install a minimal desktop only if packages qualify

Check the configured Kali repositories and candidate versions first:

```bash
apt-cache policy hyprland hyprpaper hyprlock waybar rofi \
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk
```

Proceed only if `hyprland` has a candidate version of **0.55 or newer**, and the required companion packages have candidates. If a package is unavailable or the version is too old, stop here; do not add a random Debian repository or install packages from a different Kali/Debian release to force the setup.

Review APT's proposed changes before confirming this minimal set:

```bash
sudo apt install \
  hyprland hyprpaper hyprlock waybar rofi \
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk \
  pipewire pipewire-audio pipewire-pulse wireplumber pavucontrol \
  grim slurp wl-clipboard libnotify \
  xdg-user-dirs desktop-file-utils \
  fonts-noto fonts-noto-color-emoji fonts-font-awesome
```

If APT cannot locate a listed package, do not continue with a partial Hyprland setup: use Kali's supported desktop, or separately adapt and test the configuration for the packages available in your Kali release. Check optional applications individually before installing them:

```bash
apt-cache policy thunar tumbler ffmpegthumbnailer gvfs file-roller \
  mpv firefox-esr cava btop
```

Ghostty, Satty, Yazi, Spotify Launcher, Cloudflare Speed, and several other upstream applications may require separate installation methods or may not be suitable for this guest. The dotfiles' shortcuts and integrations expect specific program names, so missing applications will make those features unavailable. Do not add repositories or run third-party install scripts without reviewing and trusting their source.

## 3. Clone the fork and preview deployment

```bash
git clone --branch kali-vmware-m4 \
  https://github.com/heikojan2010/zenwolf-dotfiles.git
cd zenwolf-dotfiles
rsync -avni home/ "$HOME/"
```

Review the preview and back up any existing files you may overwrite. Deploy only the pieces you want, without `--delete`:

```bash
rsync -avi home/ "$HOME/"
install -d -m 755 ~/.local/share/zenwolf/wallpapers
install -m 644 assets/wallpapers/* ~/.local/share/zenwolf/wallpapers/
xdg-user-dirs-update
update-desktop-database ~/.local/share/applications
systemctl --user daemon-reload
export PATH="$HOME/.local/bin:$PATH"
```

Do **not** copy `system/` into the guest root. Its examples target Arch and specific physical hardware; this VM does not need them. Do not create `/etc/zenwolf/hardware.conf` from the AMD/NVIDIA example.

## 4. Validate before starting Hyprland

The supplied configuration selects a Mac keyboard variant and uses generic monitor defaults, but VMware output names and input behavior can differ. If Hyprland is running, inspect outputs with `hyprctl monitors` and adjust your own clone's `home/.config/hypr/hyprland.lua` as needed.

Confirm the installed compositor version and check the config before launching the desktop:

```bash
Hyprland --version
Hyprland --verify-config --config ~/.config/hypr/hyprland.lua
zenwolf-theme-build check
```

Only start the desktop if the version requirement is met and config verification passes. Start from a VM console/TTY and keep a way back to Kali's original desktop. Test display resizing, keyboard layout, pointer, clipboard, audio, screenshots, logout, and recovery before relying on the VM. Do not expect gaming or GPU-acceleration behavior to match a physical machine.

## VMware/Kali troubleshooting

- **No resize or unexpected resolution:** shut down the guest and review Fusion's display/resize options; verify `open-vm-tools-desktop` is installed and the guest was rebooted. Test using Kali's default desktop before debugging Hyprland.
- **Black screen, compositor crash, or broken redraw:** return to Kali's default desktop from the VM console. Disable the Fusion graphics acceleration option if available, or abandon Hyprland in this VM. Do not keep changing system modules to address virtual graphics problems.
- **Config verification fails or Hyprland is too old:** do not launch Zenwolf's compositor config. Check `apt-cache policy hyprland`; use the supported Kali desktop or independently port the config to a compatible release.
- **Missing app or integration:** check the package name with `apt-cache policy <package>` and the command with `command -v <program>`. Disable or adapt only that integration; do not mix packages from unrelated releases.
- **No audio or clipboard integration:** verify VMware guest tools, Kali's audio service, and Fusion's guest settings from the default desktop first. These features are not guaranteed by the dotfiles.

Kali is intended for authorized security work. Keep it updated through its configured Kali repositories and use it only in environments where you have permission.
