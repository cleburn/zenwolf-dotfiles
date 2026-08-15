# Zenwolf cheatsheet

Daily controls first, configuration locations second. The [build
guide](build-guide.md) has installation details and safety boundaries.

Anything in `<ANGLE_BRACKETS>` is a placeholder. Replace the complete token
with a confirmed value and do not type the brackets. Shell variables such as
`$HOME` are literal references and should be typed exactly as shown.

## Desktop shortcuts

| Shortcut | Action |
|---|---|
| `Super+Space` | Open Rofi |
| `Super+Return` | Open a tiled Ghostty on workspace 3 |
| `Super+Q` | Close the focused window |
| `Super+F` | Open Firefox |
| `Super+S` | Open Spotify |
| `Super+L` | Lock |
| `Super+Backspace` | Power menu |
| `Super+Shift+Backspace` | Zen/Game session menu |
| `Super+B` | Toggle or recover Waybar |
| `Super+W` | Cycle themes |
| `Super+Shift+W` | Open the theme selector |
| `Super+M` | Launch, show, or hide btop |
| `Super+A` | Launch, show, or hide Cava |
| `Super+Tab` | Raise the next window |
| `Super+Shift+Tab` | Raise the previous window |
| `Super+Arrow` | Focus a window |
| `Super+Shift+Arrow` | Swap a tiled window with its neighbor |
| `Super+Alt+Arrow` | Move a floating window |
| `Super+Ctrl+Arrow` | Resize a floating window |
| `Super+left-drag` | Move a floating window with a pointer |
| `Super+right-drag` | Resize a floating window with a pointer |
| `Super+Z` | Toggle a zoomed window while keeping Waybar visible |
| `Super+Shift+F` | Toggle true fullscreen |
| `Super+P` | Toggle pseudotiling |
| `Super+1/2/3` | Focus workspace λ, β, or δ |
| `Super+Shift+1/2/3` | Move the focused window and follow it |
| `Print` | Full screenshot |
| `Shift+Print` | Region screenshot |
| `Super+Print` | Screenshot and recording menu |
| `Super+Shift+Q` | Exit Hyprland cleanly |

Workspaces 1 and 2 are floating-first. Workspace 3 is tiling-first. Rofi
Ghostty windows remain floating; `Super+Return` deliberately creates tiled
terminals.

## Theme commands

```bash
zenwolf-theme status
zenwolf-theme toggle
zenwolf-theme elements
zenwolf-theme-select
zenwolf-theme-select list
zenwolf-theme-build check
```

After editing a profile or template:

```bash
zenwolf-theme-build build <THEME>
zenwolf-theme-build check <THEME>
zenwolf-theme <THEME>
```

## Where to change things

| What | File or directory |
|---|---|
| Hyprland behavior and shortcuts | `~/.config/hypr/hyprland.lua` |
| Hyprlock base configuration | `~/.config/hypr/hyprlock.conf` |
| Waybar modules | `~/.config/waybar/config.jsonc` |
| Waybar base structure | `~/.config/waybar/base.css` |
| Rofi application menu | `~/.config/rofi/config.rasi` |
| Rofi theme selector | `~/.config/rofi/zenwolf-theme-selector.rasi` |
| Ghostty | `~/.config/ghostty/config` |
| Fastfetch | `~/.config/fastfetch/config.jsonc` |
| Theme palettes and appearance | `~/.config/zenwolf/themes/<THEME>/profile.json` |
| Shared theme templates | `~/.config/zenwolf/templates/` |
| Active generated theme | `~/.config/zenwolf/current` |
| Firefox startpage links | `~/.local/share/zenwolf/startpage/app.js` |
| Firefox startpage layout | `~/.local/share/zenwolf/startpage/{index.html,base.css}` |
| Bash startup and aliases | `~/.bashrc` |
| Zenwolf terminal commands | `~/.local/bin/` |
| XDG folder names | `~/.config/user-dirs.dirs` |
| Hardware identities | `/etc/zenwolf/hardware.conf` |

Profiles are durable inputs. Generated theme files are outputs; edit the
profile or template and rebuild instead of patching an output permanently.

## Firefox and Spotify

```bash
zenwolf-startpage status
zenwolf-startpage homepage
pywalfox update

zenwolf-spicetify status
zenwolf-spicetify repair
zenwolf-spicetify restore
```

The repository never contains Firefox profile data. The startpage helper owns
only its marked homepage block inside the local profile's `user.js`.

## Files, media, and capture

```bash
yazi
thunar
matrix
cava
netspeed
bluetooth
```

The capture helpers use the authoritative XDG paths:

```bash
xdg-user-dir PICTURES
xdg-user-dir VIDEOS
```

Screenshots go below `pictures/screenshots`; recordings go below
`videos/recordings` with the repository's lowercase XDG policy. New recordings
are H.264 MP4 files and open directly on macOS. Renaming an old MKV does not
convert it; remux it without quality loss:

```bash
ffmpeg -i '<INPUT_RECORDING>.mkv' -map 0:v:0 -c:v copy -tag:v avc1 \
  -movflags +faststart -an '<OUTPUT_RECORDING>.mp4'
```

## Services and health

```bash
systemctl --failed
systemctl --user --failed
systemctl --user status zenwolf-waybar.service
systemctl --user status zenwolf-hyprpaper.service
journalctl --user -u zenwolf-waybar.service -b
journalctl --user -u zenwolf-hyprpaper.service -b
```

Validate the desktop and themes:

```bash
Hyprland --verify-config --config ~/.config/hypr/hyprland.lua
zenwolf-theme-build check
zenwolf-theme-select list
```

Update Arch normally:

```bash
sudo pacman -Syu
pacman -Qdtq
```

Read package output before removing anything.

## Optional GPU lifecycle

Only use these commands after adapting and validating the hardware configuration:

```bash
gamer
systemctl status zenwolf-nvidia-gaming.service
cat /sys/firmware/acpi/platform_profile
```

Start gaming mode from a TTY, exit Hyprland to tear it down, and verify the
service becomes inactive. The [build guide's optional system
section](build-guide.md#system) explains the boundary.

## First-line troubleshooting

- **Theme drift:** run `zenwolf-theme-build check`, rebuild the named profile,
  then reapply it.
- **Selector shows a missing wallpaper:** compare the profile path with
  `~/.local/share/zenwolf/wallpapers/` and verify its SHA-256 value.
- **Waybar is gone:** press `Super+B`, then inspect its user journal.
- **Thunar kept the old interior colors:** close every Thunar process and reopen
  it; GTK reads that stylesheet at process start.
- **Firefox missed a palette:** run `pywalfox update`. Do not copy or delete the
  Firefox profile.
- **Spotify lost styling:** quit Spotify, run `zenwolf-spicetify repair`, and
  reopen it.
- **A screenshot used the wrong folder:** inspect `xdg-user-dir PICTURES` and
  `~/.config/user-dirs.dirs`.
- **Hyprland refuses the config:** run the verification command from a TTY and
  fix the first reported Lua error.
- **GPU mode fails:** stop. Recheck `/etc/zenwolf/hardware.conf`, PCI identities,
  render nodes, drivers, and the service journal before retrying.

For installation, hardware adaptation, optional root modules, and safe removal,
use the [build guide](build-guide.md).
