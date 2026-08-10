-- Zenwolf Swayimg ergonomics.
-- Escape is Swayimg's upstream exit key; q is added because it is the
-- conventional quit key used by btop, less, Zathura, and many terminal tools.

local function exit_viewer()
    swayimg.exit()
end

swayimg.viewer.on_key("q", exit_viewer)
swayimg.viewer.on_key("Escape", exit_viewer)
swayimg.slideshow.on_key("q", exit_viewer)
swayimg.slideshow.on_key("Escape", exit_viewer)
swayimg.gallery.on_key("q", exit_viewer)
swayimg.gallery.on_key("Escape", exit_viewer)
