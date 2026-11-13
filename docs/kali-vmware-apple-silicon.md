# Kali Linux on VMware Fusion (Apple silicon)

This is an **instructions-only adaptation** for the `heikojan2010/zenwolf-dotfiles` fork. It does not convert the Arch-specific system modules or promise that every upstream desktop component works in a Kali VM. The original [Arch build guide](build-guide.md) remains the reference for the upstream setup.

## Compatibility first

- Create an **ARM64/aarch64 Kali guest** for an Apple-silicon Mac. Do not install an amd64 guest image under the assumption that Fusion will translate it.
- Hyprland's tracked config uses its Lua API and assumes Hyprland **0.55 or newer**. Kali package versions change; check the candidate version before installing. If Kali does not provide the required version, stop before deploying the Hyprland config. Do not assume a package from another Debian release or an unofficial repository is safe.
- VMware's virtual graphics device is not the AMD/NVIDIA hybrid hardware this configuration was designed for. Do not install the optional GPU, NVIDIA, suspend, or ESP modules described in the Arch guide.
- A VM can have limited or absent 3D acceleration. Treat Hyprland as an experiment; use Kali's supported desktop (such as Xfce) if the virtual display, compositor, or performance is unreliable.
- The commands below install packages inside the guest only. Back up the VM before changing its desktop or display configuration.

## 1. Prepare the guest

In VMware Fusion, create a new Linux virtual machine using Kali's ARM64 installer image. Install Kali normally, create a non-root user, and ensure networking works. Install VMware guest tools and basic utilities:

```bash
sudo apt update
sudo apt install --no-install-recommends \
  git rsync python3 python3-pygame jq ripgrep nano pciutils \
  open-vm-tools open-vm-tools-desktop
```

Reboot the guest after installing guest tools. In Fusion, enable the available display acceleration and adjust the VM's display/resize settings. The exact options depend on Fusion and Kali versions. Verify clipboard, window resizing, and pointer behavior before proceeding.

## 2. Check Kali package availability

First inspect what the configured Kali repositories offer; do not assume Arch package names map one-for-one to Debian package names:

```bash
apt-cache policy hyprland hyprpaper hyprlock waybar rofi \
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk
```

For this repository's compositor config, the available Hyprland version must satisfy the Lua API requirement above. The package list below is a starting point only. Install only packages for which `apt-cache policy` shows a candidate, and read the proposed APT changes before confirming:

```bash
sudo apt install \
  hyprland hyprpaper hyprlock waybar rofi \
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk \
  pipewire pipewire-audio pipewire-pulse wireplumber pavucontrol \
  grim slurp wl-clipboard libnotify \
  thunar tumbler ffmpegthumbnailer gvfs file-roller \
  xdg-user-dirs desktop-file-utils \
  fonts-noto fonts-noto-color-emoji fonts-font-awesome
```

If APT reports unavailable packages, omit or replace those individual applications rather than adding an unrelated repository. Some upstream applications in the Arch instructions (including Ghostty, Satty, Yazi, Spotify Launcher, and Cloudflare Speed) may need a separate, reviewed installation method or may not be appropriate in this guest. The current configs expect particular applications and utilities; missing commands can make their corresponding shortcuts or integrations fail.

For a conservative first trial, use Kali's supported desktop and borrow only shell settings, themes, wallpapers, and standalone games. Add Hyprland and its integrations only after confirming package versions and the guest graphics path.

## 3. Clone and preview

Use the fork, not the upstream author's repository:

```bash
git clone --branch kali-vmware-m4 \
  https://github.com/heikojan2010/zenwolf-dotfiles.git
cd zenwolf-dotfiles
rsync -avni home/ "$HOME/"
```

Review every proposed path. Back up existing files, then deploy only the components you want, without `--delete`:

```bash
rsync -avi home/ "$HOME/"
install -d -m 755 ~/.local/share/zenwolf/wallpapers
install -m 644 assets/wallpapers/* ~/.local/share/zenwolf/wallpapers/
xdg-user-dirs-update
update-desktop-database ~/.local/share/applications
systemctl --user daemon-reload
export PATH="$HOME/.local/bin:$PATH"
```

Do **not** copy `system/` into the guest root. The root-owned examples target specific Arch machines and hardware; this VM does not need them.

## 4. Adapt and validate before starting Hyprland

The supplied configuration selects a Mac keyboard variant and contains monitor defaults, but VMware virtual output names and input behavior can differ. From the running compositor, use `hyprctl monitors` to inspect outputs, then adjust `home/.config/hypr/hyprland.lua` in your clone as needed. Do not copy the upstream AMD/NVIDIA hardware values.

If the installed Hyprland supports the expected Lua interface, validate before launching:

```bash
Hyprland --version
Hyprland --verify-config --config ~/.config/hypr/hyprland.lua
zenwolf-theme-build check
```

If verification reports an unsupported config/API, do not try to work around it by launching the full desktop. Use the supported Kali desktop or separately port and test the config for the installed compositor release.

Once the config validates, start from a VM console/TTY and keep a way back to Kali's original desktop. Test suspend/resume, resizing, clipboard, audio, screenshots, and logout. Avoid relying on gaming or GPU-acceleration behavior in the VM.

## Notes

- Kali is a penetration-testing distribution. Keep it updated and use it only in authorized environments.
- `apt` replaces `pacman`; do not run the Arch package or Pacman-hook instructions from the upstream build guide in Kali.
- This branch documents a practical starting path; it is not an end-to-end tested Kali image or a complete Debian port of Zenwolf.
