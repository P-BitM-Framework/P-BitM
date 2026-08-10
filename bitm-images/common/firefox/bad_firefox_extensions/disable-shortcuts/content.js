document.addEventListener("keydown", function(e) {
    const isCtrl = e.ctrlKey;   // Ctrl su Win/Linux, Cmd su macOS
    const isAlt  = e.altKey;                 // Alt (Option su macOS)
    const key    = e.key.toLowerCase();

    // ----- COMBINAZIONI CONSENTITE -----
    const allowedCtrl = ["a", "c", "v", "x"];    // Ctrl/Cmd + A C V

    const isDeleteCombo =
        (isCtrl && key === "delete") ||
        (isAlt && key === "delete") ||
        (e.metaKey && key === "delete");

    const isAllowedCtrlCombo = isCtrl && allowedCtrl.includes(key);

    if (isAllowedCtrlCombo || isDeleteCombo) {
        return true; // Non bloccare
    }

    // ----- COMBINAZIONI NON CONSENTITE -----

    // Blocca qualsiasi combinazione con Ctrl/Alt/Cmd NON nelle whitelist
    if (isCtrl || isAlt || e.metaKey) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }

    // Blocca F1, F2, F3, ecc.
    if (/^f\d+$/i.test(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }

}, true); // Capture mode
