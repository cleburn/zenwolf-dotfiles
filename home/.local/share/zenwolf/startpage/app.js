"use strict";

// Edit this one array to change section labels, link titles, or destinations.
const SECTIONS = [
  {
    label: "Daily",
    links: [
      ["YT", "YouTube", "https://www.youtube.com/"],
      ["X", "X", "https://x.com/"],
      ["RD", "Reddit", "https://www.reddit.com/"],
    ],
  },
  {
    label: "Zenwolf",
    links: [
      ["BG", "Build guide", "docs/build-guide.html"],
      ["CS", "Daily cheatsheet", "docs/cheatsheet.html"],
      ["GH", "GitHub", "https://github.com/"],
      ["AW", "ArchWiki", "https://wiki.archlinux.org/"],
      ["HY", "Hyprland Wiki", "https://wiki.hypr.land/"],
    ],
  },
  {
    label: "Play",
    links: [
      ["ST", "Steam", "https://store.steampowered.com/"],
      ["PD", "ProtonDB", "https://www.protondb.com/"],
      ["DB", "SteamDB", "https://steamdb.info/"],
      ["PW", "PCGamingWiki", "https://www.pcgamingwiki.com/"],
    ],
  },
];

const search = document.querySelector("#search-query");
const sections = document.querySelector("#link-sections");
const elementTones = ["water", "earth", "fire", "air"];
let linkIndex = 0;

function linkCard([mark, name, href]) {
  const link = document.createElement("a");
  link.className = "link-card";
  link.href = href;
  link.dataset.element = elementTones[linkIndex % elementTones.length];
  linkIndex += 1;

  const markNode = document.createElement("span");
  markNode.className = "link-mark";
  markNode.textContent = mark;

  const copy = document.createElement("span");
  copy.className = "link-copy";
  const title = document.createElement("strong");
  title.textContent = name;
  copy.append(title);

  const arrow = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  arrow.setAttribute("viewBox", "0 0 24 24");
  arrow.setAttribute("aria-hidden", "true");
  arrow.innerHTML = '<path d="M7 17 17 7M9 7h8v8"></path>';

  link.append(markNode, copy, arrow);
  return link;
}

function linkSection(data) {
  const section = document.createElement("section");
  section.className = "link-section";

  const heading = document.createElement("header");
  heading.className = "section-heading";
  const copy = document.createElement("div");
  const title = document.createElement("h2");
  title.textContent = data.label;
  copy.append(title);
  heading.append(copy);

  const grid = document.createElement("div");
  grid.className = "link-grid";
  grid.append(...data.links.map(linkCard));
  section.append(heading, grid);
  return section;
}

document.addEventListener("keydown", (event) => {
  const editing = event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement;

  if (!editing && event.key === "/") {
    event.preventDefault();
    search.focus();
    return;
  }

  if (event.key === "Escape") {
    search.value = "";
    search.blur();
  }
});

sections.replaceChildren(...SECTIONS.map(linkSection));
