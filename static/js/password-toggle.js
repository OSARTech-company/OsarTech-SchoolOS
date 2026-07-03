(function () {
  const STYLE_ID = 'password-toggle-helper-styles';
  const READY_ATTR = 'data-password-toggle-ready';
  const WRAPPER_CLASS = 'password-toggle-wrapper';
  const BUTTON_CLASS = 'password-toggle';

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) {
      return;
    }

    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .${WRAPPER_CLASS} {
        position: relative;
        display: block;
        width: 100%;
      }

      .${WRAPPER_CLASS} input[type="password"],
      .${WRAPPER_CLASS} input[type="text"] {
        width: 100%;
        box-sizing: border-box;
        padding-right: 52px !important;
      }

      .${BUTTON_CLASS} {
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        width: 36px;
        height: 36px;
        border: none;
        border-radius: 999px;
        background: transparent;
        color: #0f4c81;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        padding: 0;
      }

      .${BUTTON_CLASS}:hover,
      .${BUTTON_CLASS}:focus-visible {
        background: rgba(15, 76, 129, 0.08);
        color: #0a2c57;
        outline: none;
      }
    `;
    document.head.appendChild(style);
  }

  function setButtonState(input, button, isVisible) {
    input.type = isVisible ? 'text' : 'password';
    button.setAttribute('aria-pressed', isVisible ? 'true' : 'false');
    button.setAttribute('aria-label', isVisible ? 'Hide password' : 'Show password');
    button.title = isVisible ? 'Hide password' : 'Show password';
    button.innerHTML = isVisible
      ? '<i class="fas fa-eye-slash" aria-hidden="true"></i>'
      : '<i class="fas fa-eye" aria-hidden="true"></i>';
  }

  function enhanceInput(input) {
    if (!input || input.getAttribute(READY_ATTR) === '1') {
      return;
    }

    const existingWrapper = input.closest('.password-toggle-wrapper, .password-wrapper');
    const wrapper = existingWrapper || document.createElement('div');

    if (!existingWrapper) {
      wrapper.className = WRAPPER_CLASS;
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
    } else {
      wrapper.classList.add(WRAPPER_CLASS);
    }

    if (wrapper.querySelector(`.${BUTTON_CLASS}`)) {
      input.setAttribute(READY_ATTR, '1');
      return;
    }

    const button = document.createElement('button');
    button.type = 'button';
    button.className = BUTTON_CLASS;
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', 'Show password');
    button.title = 'Show password';
    button.innerHTML = '<i class="fas fa-eye" aria-hidden="true"></i>';
    button.addEventListener('click', function () {
      const show = input.type === 'password';
      setButtonState(input, button, show);
    });

    wrapper.appendChild(button);
    input.setAttribute(READY_ATTR, '1');
  }

  document.addEventListener('DOMContentLoaded', function () {
    ensureStyles();
    document.querySelectorAll('input[type="password"][data-password-toggle]').forEach(enhanceInput);
  });
})();
