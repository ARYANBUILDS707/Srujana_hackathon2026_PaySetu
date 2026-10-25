// PaySetu theme bootstrap (DESIGN.md Section 2.3). Loaded synchronously in <head> so the
// saved theme applies before the first paint (no light flash). Reads the preference this
// device saved ("light", "dark" or "system"); nothing is sent anywhere.
(function () {
  var root = document.documentElement;
  var dark = false;
  try {
    var preference = window.localStorage.getItem("paysetu-theme");
    dark =
      preference === "dark" ||
      (preference !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  } catch {
    dark = false;
  }
  root.setAttribute("data-theme", dark ? "dark" : "light");
})();
