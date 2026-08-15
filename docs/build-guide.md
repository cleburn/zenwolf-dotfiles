# Zenwolf build guide

Zenwolf is a reusable desktop configuration, not a one-click Linux installer.
You can install the whole desktop or borrow individual pieces. This guide keeps
the choices that can erase a disk, break boot, or target the wrong GPU in your
hands.

If you are new to Arch, keep the official [Arch installation guide][arch-install]
open beside this document. Follow it until you have a booting system, working
network, non-root user, and `sudo`. Zenwolf starts there.

Anything in `<ANGLE_BRACKETS>` is a placeholder. Replace the complete token
with a value confirmed on your machine and do not type the brackets. Shell
variables such as `$HOME` and `$PWD` are literal references and should be typed
exactly as shown. Public files ending in `.example` use explicit `CHANGE_ME`
sentinels inside the file; replace those exact sentinels before installation.

## Contents

1. [Know what you are installing](#scope)
2. [Install the desktop packages](#packages)
3. [Inspect the repository](#inspect)
4. [Describe your hardware](#hardware)
5. [Deploy the user configuration](#deploy)
6. [Install and apply the themes](#themes)
7. [Start the desktop](#desktop)
8. [Add application integrations](#integrations)
9. [Optional system modules](#system)
10. [Validate the result](#validate)
11. [Change or remove Zenwolf](#change)

<a id="scope"></a>

## 1. Know what you are installing

The repository has four practical boundaries:

```text
assets/     screenshots and the wallpapers used by the themes
games/      standalone Python games
home/       files that map below your home directory
system/     reviewed root-owned examples; never deploy blindly
```

The complete theme transaction coordinates Waybar, Ghostty, Rofi, Thunar,
Hyprpaper, Hyprlock, btop, Cava, Firefox, Spotify, and the local startpage. You
can also copy only one component.

Important assumptions:

- the tracked compositor configuration uses Hyprland's Lua interface from
  Hyprland 0.55 or newer;
- the full GPU lifecycle is designed for an AMD display GPU plus an optional
  NVIDIA discrete GPU;
- the ordinary desktop is systemd-user managed;
- the root-owned GPU, suspend, SSH, and ESP examples are optional.

Hyprland loads Lua from `~/.config/hypr/hyprland.lua`; older Hyprland releases
used a different configuration language. See the current [Hyprland
configuration guide][hypr-config].

<a id="packages"></a>

## 2. Install the desktop packages

Update first, then install the desktop, utilities, and included games:

```bash
sudo pacman -Syu --needed \
  bash git rsync python python-pygame jq ripgrep nano cmark-gfm pciutils \
  hyprland hyprlock hyprpaper hyprpolkitagent \
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk \
  ghostty rofi waybar starship fastfetch \
  pipewire pipewire-audio pipewire-alsa pipewire-pulse wireplumber \
  brightnessctl playerctl bluez bluez-utils \
  grim slurp satty wf-recorder wl-clipboard libnotify \
  thunar tumbler ffmpegthumbnailer gvfs file-roller \
  thunar-archive-plugin thunar-volman udisks2 \
  yazi mpv swayimg zathura zathura-pdf-mupdf \
  btop htop cava firefox spotify-launcher cloudflare-speed-cli \
  xdg-user-dirs desktop-file-utils \
  noto-fonts noto-fonts-emoji ttf-jetbrains-mono-nerd otf-font-awesome
```

Useful optional applications:

```bash
sudo pacman -S --needed neovim steam
```

Steam requires Arch's multilib repository. NVIDIA gaming requires the driver
appropriate for your GPU and kernel; do not copy another machine's driver or
module choice.

Enable Bluetooth only if you use it:

```bash
sudo systemctl enable --now bluetooth.service
```

<a id="inspect"></a>

## 3. Inspect the repository

Enter the repository and make sure you are looking at the expected tree:

```bash
cd zenwolf-dotfiles
git status --short
find home/.config -maxdepth 2 -type f | sort
find home/.local/bin -maxdepth 1 \( -type f -o -type l \) | sort
```

A fresh checkout should be clean. Read a file before copying it. In particular,
do not install anything below `system/` until section 9 explains its boundary.

<a id="hardware"></a>

## 4. Describe your hardware

Zenwolf refuses to guess GPU identities. Inspect your system:

```bash
id -un
lspci -Dnnk | rg -i 'vga|3d|display' -A3
ls -l /dev/dri/by-path/
cat /sys/firmware/acpi/platform_profile_choices 2>/dev/null || true
```

Create the local hardware file from the public example:

```bash
sudo install -d -m 755 /etc/zenwolf
sudo install -m 644 \
  system/etc/zenwolf/hardware.conf.example \
  /etc/zenwolf/hardware.conf
sudoedit /etc/zenwolf/hardware.conf
sudo chown root:root /etc/zenwolf/hardware.conf
sudo chmod 644 /etc/zenwolf/hardware.conf
```

Replace every `CHANGE_ME` value:

- `ZENWOLF_SESSION_USER` is the output of `id -un`.
- `ZENWOLF_DESKTOP_DRM` is the symlink ending in `-card` for the GPU that owns
  your displays.
- `ZENWOLF_NVIDIA_PCI_ID` is the domain-qualified NVIDIA address from `lspci
  -D`, without the `/sys/bus/pci/devices/` prefix.
- `ZENWOLF_NVIDIA_RENDER` is that NVIDIA device's symlink ending in `-render`.
- `ZENWOLF_GAMING_PLATFORM_PROFILE` is a real value printed by
  `platform_profile_choices`.

If you do not have an AMD/NVIDIA hybrid laptop, keep the visual desktop but
adapt or remove the GPU-specific wrappers before launch:

```text
~/.local/bin/start-zenwolf-desktop
~/.local/bin/start-zenwolf-gaming
~/.local/bin/steam
~/.local/bin/mpv
~/.local/bin/satty
~/.local/bin/zenwolf-record
~/.local/bin/zenwolf-nvidia-game
```

Intel and single-GPU users normally do not need Zenwolf's explicit Vulkan and
NVIDIA lifecycle boundaries.

<a id="deploy"></a>

## 5. Deploy the user configuration

Dry-run the literal home-directory mapping:

```bash
rsync -avni home/ "$HOME/"
```

Review every proposed path. Deploy without deletion:

```bash
rsync -avi home/ "$HOME/"
```

If the dry run shows a file you already customized, back it up or copy only the
Zenwolf components you want.

Do not add `--delete`; your browser state, credentials, downloads, and other
personal files are not represented by this repository.

Install the wallpapers where the profiles expect them:

```bash
install -d -m 755 ~/.local/share/zenwolf/wallpapers
install -m 644 assets/wallpapers/* ~/.local/share/zenwolf/wallpapers/
```

Refresh desktop metadata and the lowercase XDG directories:

```bash
xdg-user-dirs-update
update-desktop-database ~/.local/share/applications
systemctl --user daemon-reload
```

Log out and back in once if `~/.local/bin` was not already on your `PATH`:

```bash
command -v zenwolf-theme
command -v zenwolf-theme-build
command -v start-zenwolf-desktop
```

All three should resolve below your home directory.

<a id="themes"></a>

## 6. Install and apply the themes

Validate the durable profiles against their generated files:

```bash
zenwolf-theme-build check
zenwolf-theme-build list
```

Apply one complete profile:

```bash
zenwolf-theme elements
zenwolf-theme status
zenwolf-theme-select list
```

The selector uses local thumbnail-cache entries and does not add derived
thumbnails to Git. Open it with:

```bash
zenwolf-theme-select
```

Edit a theme in two layers:

```text
~/.config/zenwolf/themes/<THEME>/profile.json  palette and appearance
~/.config/zenwolf/templates/                 consumer file structure
```

Then regenerate and reapply:

```bash
zenwolf-theme-build build <THEME>
zenwolf-theme-build check <THEME>
zenwolf-theme <THEME>
```

<a id="desktop"></a>

## 7. Start the desktop

Check the configuration before entering Hyprland:

```bash
Hyprland --verify-config --config ~/.config/hypr/hyprland.lua
```

Start the guarded desktop from a TTY:

```bash
start-zenwolf-desktop
```

The default layout has two floating-first workspaces and one tiling-first
workspace. `Super+Space` opens Rofi, `Super+Return` opens a tiled Ghostty on
workspace 3, and `Super+Shift+W` opens the theme selector. The complete shortcut
table is in [the cheatsheet](cheatsheet.md).

The monitor rule is deliberately generic. If you need a fixed mode, scale,
position, or multiple-monitor layout, edit the first `hl.monitor()` call in
`~/.config/hypr/hyprland.lua` after checking `hyprctl monitors`.

<a id="integrations"></a>

## 8. Add application integrations

### Firefox

The repository contains authored startpage files and generated color files. It
does not contain or copy Firefox logins, cookies, history, sessions, Sync data,
encryption keys, or profile databases.

Open Firefox once, close it, then generate local HTML copies of the build guide
and cheatsheet and install the managed homepage block:

```bash
ZENWOLF_DOTFILES_ROOT="$PWD" zenwolf-startpage refresh
zenwolf-startpage install
zenwolf-startpage status
```

The helper discovers the local default profile and edits only the lines between
its two `ZENWOLF STARTPAGE` markers in `user.js`. It never copies the profile
into the repository.

For adaptive browser chrome, install [Pywalfox][pywalfox], its Firefox add-on,
and use its Theme API mode. A theme change calls `pywalfox update` best-effort;
Firefox failure never rolls back the rest of the desktop.

### Spotify

Install and open `spotify-launcher` once before configuring the optional
Spicetify layer:

```bash
zenwolf-spicetify setup
zenwolf-spicetify status
```

After a Spotify update:

```bash
zenwolf-spicetify repair
```

Use `zenwolf-spicetify restore` to remove the patch. See the official
[Spicetify Linux instructions][spicetify].

### Matrix terminal effect

The `matrix` launcher supplies Zenwolf's preset to the upstream
[UniMatrix][unimatrix] program without bundling that program. Clone it to the
path the launcher expects:

```bash
install -d -m 755 ~/.local/share/zenwolf/vendor
git clone https://github.com/will8211/unimatrix.git \
  ~/.local/share/zenwolf/vendor/unimatrix
matrix
```

<a id="system"></a>

## 9. Optional system modules

Everything in this section is opt-in. Read every source file first, and stage
anything that needs editing in `/tmp`. Install only the named files with root
ownership. Never recursively copy `system/` over `/`.

### NVIDIA gaming lifecycle

Use this only after confirming compatible NVIDIA hardware, drivers,
`nvidia-powerd`, DRM modesetting, a valid render node, and a supported platform
profile. The root helper refuses missing or malformed hardware values.

Before installing the sudoers example, replace `change_me_user` and validate
the staged file:

```bash
cp system/etc/sudoers.d/zenwolf-nvidia-gaming.example /tmp/zenwolf-gaming.sudoers
nano /tmp/zenwolf-gaming.sudoers
sudo visudo -cf /tmp/zenwolf-gaming.sudoers
```

Install the reviewed helper, service, and sudoers fragment:

```bash
sudo install -d -m 755 /usr/local/libexec
sudo install -m 755 \
  system/usr/local/libexec/zenwolf-nvidia-gaming \
  /usr/local/libexec/zenwolf-nvidia-gaming
sudo install -m 644 \
  system/etc/systemd/system/zenwolf-nvidia-gaming.service \
  /etc/systemd/system/zenwolf-nvidia-gaming.service
sudo install -m 440 \
  /tmp/zenwolf-gaming.sudoers \
  /etc/sudoers.d/zenwolf-nvidia-gaming
sudo systemctl daemon-reload
sudo systemctl start zenwolf-nvidia-gaming.service
sudo systemctl stop zenwolf-nvidia-gaming.service
```

Both transitions must succeed before using `gamer`.

### Locked-resume helper

The suspend drop-in restarts Hyprlock only when it was already active. It reads
`ZENWOLF_SESSION_USER` from `/etc/zenwolf/hardware.conf`. Install the helper and
drop-in only if you can test lock, suspend, resume, and unlock locally:

```bash
sudo install -d -m 755 \
  /usr/local/libexec \
  /etc/systemd/system/systemd-suspend.service.d
sudo install -m 755 \
  system/usr/local/libexec/zenwolf-hyprlock-resume \
  /usr/local/libexec/zenwolf-hyprlock-resume
sudo install -m 644 \
  system/etc/systemd/system/systemd-suspend.service.d/20-zenwolf-hyprlock-resume.conf \
  /etc/systemd/system/systemd-suspend.service.d/20-zenwolf-hyprlock-resume.conf
sudo systemctl daemon-reload
```

### SSH hardening

The SSH fragment disables remote password and root login. Install it only after
key-based login works in a second session. Keep the first session open while
you install and validate it:

```bash
sudo pacman -S --needed openssh
sudo install -d -m 755 /etc/ssh/sshd_config.d
sudo install -m 644 \
  system/etc/ssh/sshd_config.d/90-zenwolf-hardening.conf \
  /etc/ssh/sshd_config.d/90-zenwolf-hardening.conf
sudo sshd -t
sudo systemctl reload sshd.service
```

Prove a new key-based connection before closing the original session.

### ESP mirror hooks

The Pacman hooks assume `/boot` is the live ESP and `/.bootbackup` is a durable
directory inside the snapshotted root. They are not generic backup hooks. Do
not install them unless your mount and snapshot topology matches that design.
After confirming it does, create the initial mirror before installing the
hooks:

```bash
findmnt /boot
findmnt /
sudo install -d -m 700 /.bootbackup
sudo rsync -a --delete --omit-dir-times \
  --exclude=/loader/random-seed /boot/ /.bootbackup/
sudo install -m 644 system/etc/pacman.d/hooks/*.hook /etc/pacman.d/hooks/
sudo rsync -ani --delete --omit-dir-times \
  --exclude=/loader/random-seed /boot/ /.bootbackup/
```

The final comparison should be silent. Investigate any listed path before the
next package transaction.

<a id="validate"></a>

## 10. Validate the result

Run the inexpensive checks first:

```bash
Hyprland --verify-config --config ~/.config/hypr/hyprland.lua
zenwolf-theme-build check
zenwolf-theme-select list
systemctl --user --failed
python3 -B -m unittest -v tests/test_netspeed.py tests/test_bluetooth.py
```

Inside the desktop, verify:

- Rofi opens and launches an application;
- all three workspaces can be focused;
- a floating window can move, resize, and rise above another;
- `Super+Return` creates a tiled Ghostty on workspace 3;
- the selector changes the wallpaper and all visible consumers;
- screenshots land below the XDG Pictures directory;
- Firefox and Spotify either update or fail without breaking the theme change.

If you installed a GPU module, also prove that ordinary desktop use stays on
the intended display GPU and that the discrete GPU returns to its expected
idle state after gaming.

<a id="change"></a>

## 11. Change or remove Zenwolf

Make personal changes in your own clone, not directly in generated theme files.
Keep one small commit per accepted change.

To preview removal from the home directory, compare the repository tree first:

```bash
rsync -avni home/ "$HOME/"
```

Remove only files you have confirmed came from Zenwolf. Root-owned optional
modules must be disabled and removed individually. Never use a recursive delete
against your home directory or `/`.

[arch-install]: https://wiki.archlinux.org/title/Installation_guide
[hypr-config]: https://wiki.hypr.land/Configuring/Start/
[pywalfox]: https://github.com/Frewacom/pywalfox
[spicetify]: https://spicetify.app/docs/getting-started
[unimatrix]: https://github.com/will8211/unimatrix
