"use strict";

// Local file pages do not notice when zenwolf-theme replaces their stylesheet.
// Check one tiny marker while the page is visible, then reload only the two
// theme assets when its revision changes. This has no daemon or network cost.
const themeLink = document.querySelector("link[data-zenwolf-theme]");
const wallpaper = document.querySelector(".wallpaper");
let activeThemeRevision = "";
let stateRequestActive = false;

window.zenwolfThemeState = (revision) => {
  if (!/^[0-9]+$/.test(revision) || revision === activeThemeRevision) {
    return;
  }

  activeThemeRevision = revision;
  if (themeLink) {
    themeLink.href = `theme.css?revision=${revision}`;
  }
  if (wallpaper) {
    wallpaper.style.setProperty(
      "--wallpaper",
      `url("./wallpaper?revision=${revision}")`,
    );
  }
};

function refreshThemeAssets() {
  if (document.visibilityState !== "visible" || stateRequestActive) {
    return;
  }

  stateRequestActive = true;
  const stateScript = document.createElement("script");
  stateScript.src = `theme-state.js?cache=${Date.now()}`;
  stateScript.async = true;
  stateScript.addEventListener("load", finishStateRequest);
  stateScript.addEventListener("error", finishStateRequest);
  document.head.append(stateScript);

  function finishStateRequest() {
    stateScript.remove();
    stateRequestActive = false;
  }
}

document.addEventListener("visibilitychange", refreshThemeAssets);
window.setInterval(refreshThemeAssets, 1500);
refreshThemeAssets();
