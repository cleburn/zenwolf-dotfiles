-- Zenwolf first-session baseline.

local external_output = os.getenv("ZENWOLF_EXTERNAL_OUTPUT")
local internal_output = os.getenv("ZENWOLF_INTERNAL_OUTPUT") or "eDP-1"
if external_output ~= nil and external_output ~= "" then
    hl.monitor({
        output = external_output,
        mode = os.getenv("ZENWOLF_EXTERNAL_MODE") or "preferred",
        position = "0x0",
        scale = tonumber(os.getenv("ZENWOLF_EXTERNAL_SCALE")) or 1,
        vrr = 0,
        bitdepth = 8,
    })
    hl.monitor({
        output = internal_output,
        disabled = true,
    })
else
    hl.monitor({
        output = "",
        mode = "preferred",
        position = "auto",
        scale = 1,
    })
end

hl.config({
    input = {
        kb_layout = "us",
        repeat_rate = 30,
        repeat_delay = 350,
        -- Permit focus to return to ordinary windows if a hidden-storage
        -- special workspace is exposed during recovery or direct inspection.
        special_fallthrough = true,
        touchpad = {
            natural_scroll = true,
        },
    },
    decoration = {
        -- Scratchpads are companion surfaces, not modal dialogs. Keep the
        -- normal workspace at full brightness while btop is visible.
        dim_special = 0,
    },
    misc = {
        -- A long s2idle suspend can leave Hyprlock visible but unable to
        -- accept input. Permit the post-resume helper to replace only that
        -- lock client while Hyprland keeps the underlying session locked.
        allow_session_lock_restore = true,
        -- Hyprpaper owns every visible wallpaper. Never expose Hyprland's
        -- random bottom layer while hyprpaper replaces an image through IPC.
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        force_default_wallpaper = 2,
        background_color = "rgb(0b1017)",
    },
})

-- The active profile owns colors and appearance values. Keep a safe native
-- fallback so a missing or malformed generated module cannot prevent the
-- compositor, terminal binding, or exit binding from loading.
local theme_window = {
    overlay_rounding = 12,
    overlay_border_size = 1,
}
local theme_path = os.getenv("HOME") .. "/.config/zenwolf/current/hyprland.lua"
local theme_loaded, generated_theme = pcall(dofile, theme_path)
if theme_loaded and type(generated_theme) == "table" then
    theme_window = generated_theme
else
    print("Zenwolf theme module was not loaded; using native window fallback")
end

-- Lambda and beta (numeric workspaces 1 and 2) are floating-first. Each window
-- owns its size and position instead of causing the remaining windows to
-- reflow. Delta (workspace 3) retains Hyprland's tiling-first layout.
-- Use the normal single-tile footprint as a consistent starting point instead
-- of accepting application-specific floating geometry or restoring an earlier
-- experimental size.
local floating_window_size = { "(monitor_w-40)", "(monitor_h-86)" }
local floating_window_position = { 20, 66 }

hl.window_rule({
    name = "zenwolf-floating-workspaces",
    match = {
        workspace = "r[1-2]",
    },
    float = true,
    -- Match one ordinary tile: 20px outer gaps plus Waybar's 46px top
    -- reservation. Monitor-relative dimensions keep the rule inspectable and
    -- avoid embedding this laptop's 1920x1080 resolution.
    size = floating_window_size,
    move = floating_window_position,
})

-- Rofi's tracked launcher gives ordinary Ghostty windows this stable initial
-- title. Keep them floating even when intentionally launched from delta.
hl.window_rule({
    name = "zenwolf-floating-terminal",
    match = {
        initial_title = "Zenwolf Floating Terminal",
    },
    float = true,
    size = floating_window_size,
    move = floating_window_position,
})

-- Super+Enter uses a distinct initial title and opens on delta. The explicit
-- tiled state documents the boundary and protects it from future broad rules.
hl.window_rule({
    name = "zenwolf-tiled-terminal",
    match = {
        initial_title = "Zenwolf Tiled Terminal",
    },
    float = false,
})

-- Rofi launches btop and htop through a dedicated Ghostty application ID.
-- Keep those monitors large and floating so another tiled terminal cannot
-- force them below their minimum row/column requirements.
hl.window_rule({
    name = "zenwolf-system-monitor",
    match = {
        class = "zenwolf-monitor",
    },
    float = true,
    size = { "(monitor_w*0.86)", "(monitor_h*0.82)" },
    center = true,
    persistent_size = true,
    rounding = theme_window.overlay_rounding,
    border_size = theme_window.overlay_border_size,
})

-- Ghostty's Wayland app ID can be initialized after its first surface on
-- some launches. The explicit title is therefore a second static identity
-- boundary for the same monitor-window policy.
hl.window_rule({
    name = "zenwolf-system-monitor-title",
    match = {
        initial_title = "(btop|htop)",
    },
    float = true,
    size = { "(monitor_w*0.86)", "(monitor_h*0.82)" },
    center = true,
    persistent_size = true,
    rounding = theme_window.overlay_rounding,
    border_size = theme_window.overlay_border_size,
})

-- Image inspection is a temporary overlay task, not part of the tiled work
-- layout. Keep Swayimg centered and floating so opening an image does not
-- resize terminals or other working windows underneath it.
hl.window_rule({
    name = "zenwolf-image-viewer",
    match = {
        class = "swayimg",
    },
    float = true,
    size = { "(monitor_w*0.80)", "(monitor_h*0.78)" },
    center = true,
    persistent_size = true,
    rounding = theme_window.overlay_rounding,
    border_size = theme_window.overlay_border_size,
})

-- Cava is an ambient audio surface rather than a normal work tile. Create it
-- directly on the numbered workspace; zenwolf-cava uses hidden storage only
-- after a deliberate hide and restores it to the captured numbered workspace.
-- Keep the managed window shallow and near the bottom so it can accompany
-- another application without covering the center. Ghostty's requested
-- class can remain com.mitchellh.ghostty after its first Wayland surface, so
-- match the explicit initial title—the same stable fallback used by the
-- system-monitor windows above. Ordinary Ghostty windows in which the user
-- later runs cava do not have this initial title and remain freely placeable.
hl.window_rule({
    name = "zenwolf-audio-visualizer",
    match = {
        initial_title = "cava",
    },
    float = true,
    size = { "(monitor_w*0.76)", "(monitor_h*0.20)" },
    move = { "(monitor_w*0.12)", "(monitor_h*0.73)" },
    persistent_size = false,
    rounding = theme_window.overlay_rounding,
    border_size = theme_window.overlay_border_size,
})

-- Netspeed is an on-demand result surface launched from either Waybar or an
-- existing terminal. Keep its dedicated Ghostty window compact and separate
-- from the ordinary tiled work layout.
hl.window_rule({
    name = "zenwolf-netspeed",
    match = {
        initial_title = "Zenwolf Netspeed",
    },
    float = true,
    size = { "(monitor_w*0.42)", "(monitor_h*0.35)" },
    center = true,
    persistent_size = true,
    rounding = theme_window.overlay_rounding,
    border_size = theme_window.overlay_border_size,
})

-- Bluetooth management can include a changing device list and interactive
-- BlueZ confirmation prompts. Give its dedicated terminal enough room while
-- keeping it separate from the ordinary tiled work layout.
hl.window_rule({
    name = "zenwolf-bluetooth",
    match = {
        initial_title = "Zenwolf Bluetooth",
    },
    float = true,
    size = { "(monitor_w*0.56)", "(monitor_h*0.64)" },
    center = true,
    persistent_size = true,
    rounding = theme_window.overlay_rounding,
    border_size = theme_window.overlay_border_size,
})

-- If hidden monitor storage is exposed during recovery, close it before an
-- ordinary application launch so new work enters the numbered workspace.
local function hide_active_zenwolf_storage()
    local special = hl.get_active_special_workspace()

    if special == nil then
        return
    end

    if special.name == "special:monitor" then
        hl.dispatch(hl.dsp.workspace.toggle_special("monitor"))
    elseif special.name == "special:audio" then
        hl.dispatch(hl.dsp.workspace.toggle_special("audio"))
    end
end

local function launch_on_numbered_workspace(command)
    hide_active_zenwolf_storage()
    hl.exec_cmd(command)
end

hl.bind("SUPER + Return", function()
    hide_active_zenwolf_storage()
    hl.dispatch(hl.dsp.focus({ workspace = 3 }))
    hl.exec_cmd("ghostty --title='Zenwolf Tiled Terminal'")
end, { description = "Open a tiled terminal on delta" })
hl.bind("SUPER + Space", function()
    launch_on_numbered_workspace("rofi -show drun")
end, { description = "Open the application launcher on the normal workspace" })
hl.bind("SUPER + Q", hl.dsp.window.close())
hl.bind(
    "SUPER + L",
    hl.dsp.exec_cmd("zenwolf-lock"),
    { description = "Lock the Zenwolf session" }
)
hl.bind(
    "SUPER + SHIFT + Q",
    hl.dsp.exec_cmd("zenwolf-exit-desktop"),
    { description = "Stop session services and exit Hyprland" }
)
hl.bind(
    "SUPER + BackSpace",
    hl.dsp.exec_cmd("zenwolf-power"),
    { description = "Open the confirmed Zenwolf power surface" }
)
hl.bind(
    "SUPER + SHIFT + BackSpace",
    hl.dsp.exec_cmd("zenwolf-session menu"),
    { description = "Open the Zen or Game session switcher" }
)
hl.bind("SUPER + B", hl.dsp.exec_cmd("zenwolf-waybar toggle"), { description = "Show, hide, or recover Waybar" })
hl.bind("SUPER + W", hl.dsp.exec_cmd("zenwolf-theme toggle"), { description = "Cycle the coordinated Zenwolf theme" })
hl.bind("SUPER + SHIFT + W", function()
    launch_on_numbered_workspace("zenwolf-theme-select")
end, { description = "Open the coordinated Zenwolf theme selector" })
hl.bind("SUPER + M", hl.dsp.exec_cmd("zenwolf-btop toggle"), { description = "Launch, show, or hide btop" })
hl.bind("SUPER + A", hl.dsp.exec_cmd("zenwolf-cava toggle"), { description = "Show or hide the audio visualizer" })
hl.bind("SUPER + S", function()
    launch_on_numbered_workspace("spotify-launcher")
end, { description = "Open Spotify" })
hl.bind("SUPER + F", function()
    launch_on_numbered_workspace("firefox")
end, { description = "Open Firefox" })

-- Capture mirrors the semantic layers of a dedicated screenshot key: bare
-- Print is immediate, Shift adds region selection, and Super opens the full
-- capture menu without colliding with workspace movement on Super+Shift+1-3.
hl.bind("Print", hl.dsp.exec_cmd("zenwolf-screenshot full"), { description = "Save a full screenshot" })
hl.bind("SHIFT + Print", hl.dsp.exec_cmd("zenwolf-screenshot region"), { description = "Select and save a screenshot region" })
hl.bind("SUPER + Print", hl.dsp.exec_cmd("zenwolf-capture"), { description = "Open the capture menu" })

-- Keyboard-first window controls. Hyprland tiles windows by default; these
-- bindings make the alternative states explicit instead of depending on a
-- mouse. Zoomed retains Waybar, while fullscreen uses the entire panel.
hl.bind("SUPER + Z", hl.dsp.window.fullscreen({
    mode = "maximized",
    action = "toggle",
}), { description = "Toggle zoomed window" })
hl.bind("SUPER + SHIFT + F", hl.dsp.window.fullscreen({
    mode = "fullscreen",
    action = "toggle",
}), { description = "Toggle true fullscreen window" })
-- Pseudotiling keeps a window in the layout tree while allowing its rendered
-- size to be smaller than its assigned tile. This exposes wallpaper without
-- making the remaining tiled windows expand behind it as floating does.
hl.bind("SUPER + P", hl.dsp.window.pseudo({ action = "toggle" }), { description = "Toggle pseudotiled window" })

-- A trackpad presents its normal and secondary clicks as the same pointer
-- buttons as a mouse. Holding Super while click-dragging therefore provides
-- direct movement and resizing without depending on application titlebars.
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Move a window with the trackpad" })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize a window with the trackpad" })

-- Floating windows need both a focus change and a stack-order change. Without
-- the second dispatch, keyboard focus can move to a window that remains hidden
-- beneath another floating surface.
local function cycle_window(next_window)
    hl.dispatch(hl.dsp.window.cycle_next({
        next = next_window,
        visible = true,
    }))
    hl.dispatch(hl.dsp.window.bring_to_top())
end

hl.bind("SUPER + Tab", function()
    cycle_window(true)
end, { description = "Focus and raise the next window" })
hl.bind("SUPER + SHIFT + Tab", function()
    cycle_window(false)
end, { description = "Focus and raise the previous window" })

local directions = {
    { key = "Left",  submap_key = "left",  direction = "l", x = -40, y = 0 },
    { key = "Right", submap_key = "right", direction = "r", x = 40,  y = 0 },
    { key = "Up",    submap_key = "up",    direction = "u", x = 0,   y = -40 },
    { key = "Down",  submap_key = "down",  direction = "d", x = 0,   y = 40 },
}

for _, item in ipairs(directions) do
    hl.bind("SUPER + " .. item.key, hl.dsp.focus({
        direction = item.direction,
    }), { description = "Focus the neighboring window" })

    hl.bind("SUPER + SHIFT + " .. item.key, hl.dsp.window.swap({
        direction = item.direction,
    }), { description = "Swap the tiled window with its neighbor" })

    hl.bind("SUPER + ALT + " .. item.key, hl.dsp.window.move({
        x = item.x,
        y = item.y,
        relative = true,
    }), { repeating = true, description = "Move a floating window" })

    -- Keep resize available directly rather than entering a modal submap. A
    -- forgotten submap makes every unrelated shortcut appear unresponsive.
    hl.bind("SUPER + CTRL + " .. item.key, hl.dsp.window.resize({
        x = item.x,
        y = item.y,
        relative = true,
    }), { repeating = true, description = "Resize the active window" })
end

-- Import this compositor's runtime identifiers before starting Zenwolf's
-- Waybar user service. The service owns the process and its journal without
-- requiring a session manager such as UWSM.
hl.on("hyprland.start", function()
    hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE XDG_CURRENT_DESKTOP AQ_DRM_DEVICES __EGL_VENDOR_LIBRARY_FILENAMES __GLX_VENDOR_LIBRARY_NAME && systemctl --user start zenwolf-hyprpaper.service zenwolf-waybar.service")
end)

hl.on("hyprland.shutdown", function()
    hl.exec_cmd("systemctl --user stop zenwolf-waybar.service zenwolf-hyprpaper.service")
end)

-- Three keyboard-controlled workspaces. Moving a window follows it so the
-- destination remains visible and the window cannot appear to be lost.
for workspace = 1, 3 do
    local workspace_id = workspace
    hl.bind("SUPER + " .. workspace_id, hl.dsp.focus({ workspace = workspace_id }))
    hl.bind("SUPER + SHIFT + " .. workspace_id, hl.dsp.window.move({
        workspace = workspace_id,
        follow = true,
    }))
end

-- Dedicated media keys; no Super-key combinations are consumed.
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true, description = "Raise volume 5%" })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true, description = "Lower volume 5%" })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true, description = "Toggle speaker mute" })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true, description = "Toggle microphone mute" })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true, description = "Play or pause the active media player" })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true, description = "Play the next media item" })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true, description = "Play the previous media item" })
hl.bind("XF86AudioStop", hl.dsp.exec_cmd("playerctl stop"), { locked = true, description = "Stop the active media player" })

-- Use brightnessctl's default backlight device and retain a nonzero floor.
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl set +10%"), { locked = true, repeating = true, description = "Raise brightness 10%" })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl --min-value=1 set 10%-"), { locked = true, repeating = true, description = "Lower brightness 10%, keep a visible floor" })
