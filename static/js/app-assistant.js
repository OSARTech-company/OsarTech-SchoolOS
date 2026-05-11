(function () {
    function normalizeGlobalFooter() {
        var footers = Array.prototype.slice.call(document.querySelectorAll('.app-global-footer'));
        if (!footers.length) return;
        var keep = footers[0];
        for (var i = 1; i < footers.length; i++) {
            var node = footers[i];
            if (node && node.parentNode) node.parentNode.removeChild(node);
        }
        if (keep.parentNode !== document.body) {
            document.body.appendChild(keep);
        }
    }

    function createMessage(container, text, isUser) {
        var node = document.createElement('div');
        node.className = isUser ? 'app-ai-user-msg' : 'app-ai-bot-msg';
        node.textContent = text;
        container.appendChild(node);
        container.scrollTop = container.scrollHeight;
        return node;
    }

    function createTypingMessage(container) {
        var node = document.createElement('div');
        node.className = 'app-ai-bot-msg app-ai-typing';
        node.textContent = 'Thinking';
        container.appendChild(node);
        container.scrollTop = container.scrollHeight;
        return node;
    }

    function createStreamedBotMessage(container, text, onDone) {
        var node = document.createElement('div');
        node.className = 'app-ai-bot-msg app-ai-streaming';
        node.textContent = '';
        container.appendChild(node);
        container.scrollTop = container.scrollHeight;

        var fullText = String(text || '');
        var index = 0;

        function tick() {
            var speedBoost = Math.min(8, Math.floor(index / 150));
            index = Math.min(fullText.length, index + 2 + speedBoost);
            node.textContent = fullText.slice(0, index);
            container.scrollTop = container.scrollHeight;
            if (index < fullText.length) {
                window.setTimeout(tick, 14);
                return;
            }
            node.classList.remove('app-ai-streaming');
            if (typeof onDone === 'function') onDone(node);
        }

        tick();
        return node;
    }

    function sendFeedback(csrfToken, helpful, questionText, answerText) {
        var payload = new URLSearchParams();
        payload.set('helpful', helpful ? '1' : '0');
        payload.set('question', String(questionText || '').trim().slice(0, 500));
        payload.set('answer', String(answerText || '').trim().slice(0, 1200));
        payload.set('page', window.location.pathname || '/');
        if (csrfToken) payload.set('csrf_token', csrfToken);
        fetch('/assistant/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: payload.toString()
        }).catch(function () {});
    }

    function buildPageContext(root) {
        var parts = [];
        try {
            var path = String(window.location.pathname || '/').trim();
            if (path) parts.push('path: ' + path);

            var heading = document.querySelector('.header h1, .header h2, .stack-head h1, .stack-head h2');
            if (heading && heading.textContent) {
                parts.push('page: ' + String(heading.textContent || '').trim().slice(0, 90));
            }

            var activeLink = document.querySelector('.side-link.active span');
            if (activeLink && activeLink.textContent) {
                parts.push('active menu: ' + String(activeLink.textContent || '').trim().slice(0, 60));
            }

            var role = String((root && root.getAttribute('data-role')) || '').trim().toLowerCase();
            if (role === 'parent') {
                var selectedChild = '';
                var params = new URLSearchParams(window.location.search || '');
                var key = String(params.get('student_key') || '').trim();
                var studentGroups = Array.prototype.slice.call(document.querySelectorAll('details.side-group[data-student-key]'));
                if (key) {
                    studentGroups.some(function (node) {
                        var nodeKey = String((node.getAttribute('data-student-key') || '')).trim();
                        if (nodeKey !== key) return false;
                        var label = node.querySelector('summary.side-group-toggle span');
                        selectedChild = String((label && label.textContent) || '').trim();
                        return !!selectedChild;
                    });
                }
                if (!selectedChild) {
                    var openGroupLabel = document.querySelector('details.side-group[data-student-key][open] summary.side-group-toggle span');
                    if (openGroupLabel && openGroupLabel.textContent) {
                        selectedChild = String(openGroupLabel.textContent || '').trim();
                    }
                }
                if (selectedChild) {
                    parts.push('selected child: ' + selectedChild.slice(0, 90));
                } else if (studentGroups.length) {
                    parts.push('linked children: ' + String(studentGroups.length));
                }
            }
        } catch (_err) {
            // Ignore context parsing errors.
        }
        return parts.join(' | ').slice(0, 260);
    }

    function renderFeedbackControls(csrfToken, hostNode, questionText, answerText) {
        if (!hostNode) return;
        var wrap = document.createElement('div');
        wrap.className = 'app-ai-feedback';
        var up = document.createElement('button');
        up.type = 'button';
        up.className = 'app-ai-feedback-btn';
        up.textContent = 'Helpful';
        var down = document.createElement('button');
        down.type = 'button';
        down.className = 'app-ai-feedback-btn';
        down.textContent = 'Not helpful';
        function applyChoice(isHelpful) {
            sendFeedback(csrfToken, isHelpful, questionText, answerText);
            up.disabled = true;
            down.disabled = true;
            if (isHelpful) up.classList.add('active');
            else down.classList.add('active');
        }
        up.addEventListener('click', function () { applyChoice(true); });
        down.addEventListener('click', function () { applyChoice(false); });
        wrap.appendChild(up);
        wrap.appendChild(down);
        hostNode.appendChild(wrap);
        hostNode.parentNode.scrollTop = hostNode.parentNode.scrollHeight;
    }

    function renderSmartLinks(hostNode, links) {
        if (!hostNode || !Array.isArray(links) || !links.length) return;
        var wrap = document.createElement('div');
        wrap.className = 'app-ai-smart-links';
        links.slice(0, 3).forEach(function (item) {
            if (!item || !item.url || !item.label) return;
            var link = document.createElement('a');
            link.href = String(item.url);
            link.textContent = String(item.label);
            link.className = 'app-ai-smart-link';
            wrap.appendChild(link);
        });
        if (wrap.childNodes.length) hostNode.appendChild(wrap);
    }

    function renderFixSnippet(hostNode, snippetText) {
        if (!hostNode) return;
        var text = String(snippetText || '').trim();
        if (!text) return;
        var wrap = document.createElement('div');
        wrap.className = 'app-ai-fix-snippet';
        var pre = document.createElement('pre');
        pre.textContent = text;
        var copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'app-ai-fix-copy';
        copyBtn.textContent = 'Copy Fix Snippet';
        copyBtn.addEventListener('click', function () {
            var done = function () {
                copyBtn.textContent = 'Copied';
                window.setTimeout(function () { copyBtn.textContent = 'Copy Fix Snippet'; }, 1300);
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(done).catch(function () {});
            }
        });
        wrap.appendChild(pre);
        wrap.appendChild(copyBtn);
        hostNode.appendChild(wrap);
    }

    function renderQuickPrompts(container, prompts, onPick) {
        if (!container) return;
        while (container.firstChild) container.removeChild(container.firstChild);
        var rows = Array.isArray(prompts) ? prompts : [];
        if (!rows.length) return;
        var label = document.createElement('div');
        label.className = 'app-ai-quick-label';
        label.textContent = 'Tap To Ask';
        container.appendChild(label);
        rows.slice(0, 8).forEach(function (item) {
            var text = String(item || '').trim();
            if (!text) return;
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = text;
            btn.addEventListener('click', function () {
                if (typeof onPick === 'function') onPick(text);
            });
            container.appendChild(btn);
        });
    }

    function parseMaybeJsonResponse(resp) {
        return resp.text().then(function (text) {
            var raw = String(text || '');
            var contentType = String(resp.headers.get('content-type') || '').toLowerCase();
            var looksJson = contentType.indexOf('application/json') >= 0 || contentType.indexOf('+json') >= 0;
            if (!looksJson) {
                var trimmed = raw.trim();
                if (trimmed && trimmed.charAt(0) === '{') {
                    looksJson = true;
                }
            }
            if (!looksJson) {
                var plain = raw.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
                if (!plain) {
                    plain = 'Assistant request failed.';
                } else if (plain.length > 220) {
                    plain = plain.slice(0, 220);
                }
                throw new Error(plain);
            }
            try {
                return JSON.parse(raw || '{}');
            } catch (_err) {
                throw new Error('Assistant request returned an invalid JSON payload.');
            }
        });
    }

    function initAssistant(root) {
        if (!root || root.dataset.bound === '1') return;
        root.dataset.bound = '1';

        var panel = root.querySelector('.app-ai-panel');
        var toggle = root.querySelector('.app-ai-toggle');
        var closeBtn = root.querySelector('.app-ai-close');
        var clearBtn = root.querySelector('.app-ai-clear');
        var form = root.querySelector('.app-ai-form');
        var input = form ? form.querySelector('input[name=\"question\"]') : null;
        var modeSelect = form ? form.querySelector('select[name=\"response_mode\"]') : null;
        var submitBtn = form ? form.querySelector('button[type=\"submit\"]') : null;
        var messages = root.querySelector('.app-ai-messages');
        var quickWrap = root.querySelector('.app-ai-quick');
        var csrfToken = (root.querySelector('.app-ai-csrf') || {}).value || '';
        var defaultMode = String(root.getAttribute('data-preferred-mode') || 'standard').trim().toLowerCase();
        var defaultIntro = String((messages && messages.getAttribute('data-intro')) || '').trim();
        var defaultQuickPrompts = [];
        var history = [];
        var isBusy = false;

        if (!panel || !toggle || !closeBtn || !form || !input || !messages) return;
        if (quickWrap) {
            try {
                defaultQuickPrompts = JSON.parse(String(quickWrap.getAttribute('data-default-prompts') || '[]'));
            } catch (_e) {
                defaultQuickPrompts = [];
            }
        }

        try {
            var savedMode = window.localStorage.getItem('app_ai_response_mode_v1') || '';
            var chosenMode = (savedMode || defaultMode || 'standard').trim().toLowerCase();
            if (modeSelect && chosenMode) modeSelect.value = chosenMode;
        } catch (e) {}

        try {
            var pulseKey = 'app_ai_seen_pulse_v1';
            if (!window.localStorage.getItem(pulseKey)) {
                toggle.classList.add('app-ai-pulse');
                window.localStorage.setItem(pulseKey, '1');
                window.setTimeout(function () {
                    toggle.classList.remove('app-ai-pulse');
                }, 7600);
            }
        } catch (e) {}

        function openPanel() {
            panel.hidden = false;
            toggle.setAttribute('aria-expanded', 'true');
            input.focus();
        }

        function closePanel() {
            panel.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        }

        function setBusy(flag) {
            isBusy = !!flag;
            input.disabled = isBusy;
            if (modeSelect) modeSelect.disabled = isBusy;
            if (submitBtn) submitBtn.disabled = isBusy;
            if (clearBtn) clearBtn.disabled = isBusy;
        }

        function resetConversation(extraText) {
            history = [];
            while (messages.firstChild) messages.removeChild(messages.firstChild);
            if (defaultIntro) createMessage(messages, defaultIntro, false);
            if (extraText) createMessage(messages, extraText, false);
            renderQuickPrompts(quickWrap, defaultQuickPrompts, function (picked) { ask(picked); });
        }

        function ask(questionText) {
            if (isBusy) return;
            var text = String(questionText || '').trim();
            if (!text) {
                createMessage(messages, 'Type a question first. You can also paste an error message.', false);
                return;
            }
            if (text.length > 1200) {
                createMessage(messages, 'Message is too long. Keep it under 1200 characters.', false);
                return;
            }
            setBusy(true);
            createMessage(messages, text, true);
            history.push({ role: 'user', text: text });
            history = history.slice(-8);
            var pendingNode = createTypingMessage(messages);

            var payload = new URLSearchParams();
            payload.set('question', text);
            payload.set('page', window.location.pathname || '/');
            var pageContext = buildPageContext(root);
            if (pageContext) payload.set('page_context', pageContext);
            payload.set('history', JSON.stringify(history));
            if (modeSelect && modeSelect.value) payload.set('response_mode', modeSelect.value);
            if (csrfToken) payload.set('csrf_token', csrfToken);

            fetch('/assistant/guide', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: payload.toString()
            }).then(function (resp) {
                if (!resp.ok) {
                    return parseMaybeJsonResponse(resp).then(function (errData) {
                        var msg = (errData && errData.error) ? String(errData.error) : 'Assistant request failed.';
                        throw new Error(msg);
                    });
                }
                return parseMaybeJsonResponse(resp);
            }).then(function (data) {
                if (pendingNode && pendingNode.parentNode) pendingNode.parentNode.removeChild(pendingNode);
                if (!data || !data.ok) {
                    createMessage(messages, 'I could not process that. Try again.', false);
                    setBusy(false);
                    return;
                }
                var lines = [data.answer || 'I could not find a direct answer.'];
                if (data.role_scope) {
                    lines.push(String(data.role_scope));
                }
                if (data.click_path) {
                    lines.push('Click path: ' + String(data.click_path));
                }
                if (Array.isArray(data.steps) && data.steps.length) {
                    data.steps.slice(0, 4).forEach(function (step, idx) {
                        lines.push((idx + 1) + '. ' + step);
                    });
                }
                if (data.guided_checklist && Array.isArray(data.checklist_items) && data.checklist_items.length) {
                    lines.push('Checklist:');
                    data.checklist_items.slice(0, 8).forEach(function (item) {
                        lines.push('- [ ] ' + String(item || '').trim());
                    });
                }
                if (Array.isArray(data.links) && data.links.length) {
                    lines.push('Useful pages: ' + data.links.map(function (item) { return item.label; }).join(', '));
                }
                if (Array.isArray(data.source_hints) && data.source_hints.length) {
                    lines.push('Relevant pages: ' + data.source_hints.join(', '));
                }
                if (typeof data.confidence === 'number') {
                    lines.push('Confidence: ' + Math.round(Math.max(0, Math.min(1, data.confidence)) * 100) + '%');
                }
                if (data.safety_note) {
                    lines.push('Safety: ' + data.safety_note);
                }
                if (data.next_question) {
                    lines.push('Next: ' + data.next_question);
                }
                if (data.answer_version) {
                    lines.push('Answer version: ' + String(data.answer_version));
                }
                var answerText = lines.join('\n');
                createStreamedBotMessage(messages, answerText, function (botNode) {
                    history.push({ role: 'assistant', text: answerText });
                    history = history.slice(-8);
                    renderFeedbackControls(csrfToken, botNode, text, answerText);
                    renderSmartLinks(botNode, data.smart_links || []);
                    renderFixSnippet(botNode, data.fix_snippet || '');
                    var nextPrompts = [];
                    if (Array.isArray(data.quick_prompts) && data.quick_prompts.length) {
                        nextPrompts = data.quick_prompts;
                    } else if (Array.isArray(data.follow_ups) && data.follow_ups.length) {
                        nextPrompts = data.follow_ups;
                    } else {
                        nextPrompts = defaultQuickPrompts;
                    }
                    renderQuickPrompts(quickWrap, nextPrompts, function (picked) { ask(picked); });
                    setBusy(false);
                });
            }).catch(function (err) {
                if (pendingNode && pendingNode.parentNode) pendingNode.parentNode.removeChild(pendingNode);
                var msg = (err && err.message) ? err.message : 'Network or permission issue. Please try again.';
                createMessage(messages, msg, false);
                setBusy(false);
            });
        }

        toggle.addEventListener('click', function () {
            if (panel.hidden) openPanel();
            else closePanel();
        });
        closeBtn.addEventListener('click', closePanel);
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                if (isBusy) return;
                setBusy(true);
                var payload = new URLSearchParams();
                if (csrfToken) payload.set('csrf_token', csrfToken);
                fetch('/assistant/memory/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: payload.toString()
                }).then(function (resp) {
                    if (!resp.ok) {
                        return parseMaybeJsonResponse(resp).then(function (errData) {
                            var msg = (errData && errData.error) ? String(errData.error) : 'Could not clear memory.';
                            throw new Error(msg);
                        });
                    }
                    return parseMaybeJsonResponse(resp);
                }).then(function () {
                    resetConversation('Assistant memory cleared. I will respond from scratch now.');
                    setBusy(false);
                }).catch(function (err) {
                    var msg = (err && err.message) ? err.message : 'Could not clear memory.';
                    createMessage(messages, msg, false);
                    setBusy(false);
                });
            });
        }
        form.addEventListener('submit', function (ev) {
            ev.preventDefault();
            ask(input.value);
            input.value = '';
        });
        if (modeSelect) {
            modeSelect.addEventListener('change', function () {
                try {
                    window.localStorage.setItem('app_ai_response_mode_v1', modeSelect.value || 'standard');
                } catch (e) {}
                var prefPayload = new URLSearchParams();
                prefPayload.set('response_mode', modeSelect.value || 'standard');
                if (csrfToken) prefPayload.set('csrf_token', csrfToken);
                fetch('/assistant/preferences', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: prefPayload.toString()
                }).then(function (resp) {
                    if (!resp.ok) {
                        return parseMaybeJsonResponse(resp).catch(function () { return null; });
                    }
                    return parseMaybeJsonResponse(resp);
                }).catch(function () {});
            });
        }

        renderQuickPrompts(quickWrap, defaultQuickPrompts, function (picked) { ask(picked); });
        // Always start collapsed and open only on user click.
        closePanel();
    }

    function boot() {
        normalizeGlobalFooter();
        var welcomeNode = document.querySelector('.app-welcome-toast');
        if (welcomeNode) {
            window.setTimeout(function () {
                welcomeNode.classList.add('app-welcome-hide');
                window.setTimeout(function () {
                    if (welcomeNode && welcomeNode.parentNode) welcomeNode.parentNode.removeChild(welcomeNode);
                }, 380);
            }, 10000);
        }
        var roots = document.querySelectorAll('.app-ai-assistant');
        roots.forEach(initAssistant);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
