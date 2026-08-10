// bitm-controller.js
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

    // showSpinner() {
    //   this.hide(this.elements.success);
    //   this.hide(this.elements.wrapper);
    //   this.hideIframe();
    //   this.show(this.elements.spinner);
    // },

    showSuccess() {
      this.hide(this.elements.spinner);
      this.hide(this.elements.wrapper);
      this.hideIframe();
      this.show(this.elements.success);
    },

    showContent() {
      this.hide(this.elements.spinner);
      this.hide(this.elements.success);
      this.hide(this.elements.wrapper);
      this.showIframe();
    },

    // showLanding() {
    //   this.hide(this.elements.spinner);
    //   this.hide(this.elements.success);
    //   this.hideIframe();
    //   this.show(this.elements.wrapper);
    // },

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
      this.elements.iframe.style.opacity = '1';
      this.elements.iframe.style.display = 'block';
    },

    // hideIframe() {
    //   if (!this.elements.iframe) return;
    //   this.elements.iframe.style.visibility = 'hidden';
    //   this.elements.iframe.style.opacity = '0';
    // }
  };

  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.Controller.init());
  } else {
    window.Controller.init();
  }
})();
