// Set default homepage (or the page to load in kiosk mode)
user_pref("browser.startup.homepage", "https://google.com");
user_pref("browser.newtab.url", "https://google.com");


// Disable the Bookmarks Toolbar
user_pref("browser.toolbars.bookmarks.visibility", "never");

// Disable full-screen warning
user_pref("full-screen-api.warning.timeout", 0);
user_pref("full-screen-api.transition-duration.enter", "0 0");
user_pref("full-screen-api.transition-duration.leave", "0 0");

// Disable context menu (right-click)
user_pref("dom.event.contextmenu.enabled", false);

// Disable developer tools shortcut (optional)
user_pref("devtools.policy.disabled", true);

// Prevent session restore popup
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.sessionstore.resume_session_once", false);

// Disable Firefox Studies (optional)
user_pref("app.normandy.enabled", false);
user_pref("app.shield.optoutstudies.enabled", false);

// Disable Firefox Sync or Account prompts
user_pref("identity.fxaccounts.enabled", false);

// Disable the "What's New" and privacy information page
user_pref("browser.startup.homepage_override.mstone", "ignore");


user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

user_pref("extensions.pocket.enabled", false);

// Disable Alt-based menu shortcut (like Alt+F, Alt+E, etc.)
user_pref("ui.key.menuAccessKey", 0);  // Disables the menu access key

// Disable the Quit shortcut (Ctrl+Q)
user_pref("browser.quitShortcut.disabled", true);
user_pref("browser.tabs.closeWindowWithLastTab", false);

// Reopen closed tabs and windows
user_pref("browser.sessionstore.max_tabs_undo", 0);
user_pref("browser.sessionstore.max_windows_undo", 0);

user_pref("xpinstall.signatures.required", false);

user_pref("ui.systemUsesDarkTheme", THEME);

user_pref("browser.ml.chat.enabled", false);
user_pref("browser.ml.chat.shortcuts.enabled", false);
user_pref("browser.ml.chat.sidebar", false);
user_pref("browser.ml.chat.activations", 0);

// Disable Shortcuts
user_pref("browser.newtabpage.enabled", false);
user_pref("browser.tabs.closeWindowWithLastTab", false);
user_pref("browser.tabs.warnOnClose", true);

// Public browsing leaves through the campaign-scoped filtered egress proxy.
// Local collection on 127.0.0.1:8080 deliberately bypasses it.
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", "p-bitm-egress-CAMPAIGN_ID");
user_pref("network.proxy.http_port", 3128);
user_pref("network.proxy.ssl", "p-bitm-egress-CAMPAIGN_ID");
user_pref("network.proxy.ssl_port", 3128);
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1");
user_pref("network.proxy.socks_remote_dns", true);
