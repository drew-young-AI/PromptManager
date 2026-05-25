(function () {
    const config = JSON.parse(document.getElementById("prompt-manager-config").textContent);
    const channelSuggestions = JSON.parse(
        document.getElementById("prompt-channel-suggestions").textContent
    );
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
    const TREE_PANEL_STORAGE_KEY = "prompt-manager-tree-collapsed";

    const state = {
        tree: { types: [] },
        currentPrompt: null,
        selectedVersion: null,
        treeCollapsed: false,
    };

    const elements = {
        appLayout: document.getElementById("appLayout"),
        catalogPanel: document.getElementById("catalogPanel"),
        treeToggleButton: document.getElementById("treeToggleButton"),
        flashMessage: document.getElementById("flashMessage"),
        promptTree: document.getElementById("promptTree"),
        treeState: document.getElementById("treeState"),
        promptSummary: document.getElementById("promptSummary"),
        selectedPromptPath: document.getElementById("selectedPromptPath"),
        selectedPrompt: document.getElementById("selectedPrompt"),
        latestVersionBadge: document.getElementById("latestVersionBadge"),
        lastSavedAt: document.getElementById("lastSavedAt"),
        contextPromptName: document.getElementById("contextPromptName"),
        contextVersionName: document.getElementById("contextVersionName"),
        contextChannelTarget: document.getElementById("contextChannelTarget"),
        mappingPromptPath: document.getElementById("mappingPromptPath") || document.createElement("strong"),
        mappingVersionSummary:
            document.getElementById("mappingVersionSummary") || document.createElement("p"),
        editorVersionHint: document.getElementById("editorVersionHint"),
        refreshTreeButton: document.getElementById("refreshTreeButton"),
        clearEditorButton: document.getElementById("clearEditorButton"),
        savePromptButton: document.getElementById("savePromptButton"),
        clearFormButton: document.getElementById("clearFormButton"),
        deleteVersionButton: document.getElementById("deleteVersionButton"),
        deletePromptButton: document.getElementById("deletePromptButton"),
        channelInput: document.getElementById("channelInput"),
        assignChannelButton: document.getElementById("assignChannelButton"),
        removeChannelButton: document.getElementById("removeChannelButton"),
        channelList: document.getElementById("channelList"),
        editorVersionSelect: document.getElementById("editorVersionSelect"),
        testVersionSelect: document.getElementById("testVersionSelect"),
        runTestButton: document.getElementById("runTestButton"),
        testCurrentButton: document.getElementById("testCurrentButton"),
        testModeBadge: document.getElementById("testModeBadge"),
        renderedPromptOutput: document.getElementById("renderedPromptOutput"),
        requestPreviewOutput: document.getElementById("requestPreviewOutput"),
        modelOutput: document.getElementById("modelOutput"),
        typeInput: document.getElementById("typeInput"),
        categoryDatalist: document.getElementById("categoryDatalist"),
        categoryInput: document.getElementById("categoryInput"),
        promptNameInput: document.getElementById("promptNameInput"),
        authorInput: document.getElementById("authorInput"),
        descriptionInput: document.getElementById("descriptionInput"),
        roleCharacterInput: document.getElementById("roleCharacterInput"),
        contentInput: document.getElementById("contentInput"),
        notesInput: document.getElementById("notesInput"),
        testInput: document.getElementById("testInput"),
    };

    function setFlash(message, tone) {
        elements.flashMessage.textContent = message;
        elements.flashMessage.dataset.tone = tone || "info";
        elements.flashMessage.classList.toggle("is-visible", Boolean(message));
    }

    function setTextContent(element, value) {
        if (element) {
            element.textContent = value;
        }
    }

    function setControlDisabled(element, disabled) {
        if (element) {
            element.disabled = disabled;
        }
    }

    function resetOutputs() {
        elements.renderedPromptOutput.textContent = "";
        elements.requestPreviewOutput.textContent = "";
        elements.modelOutput.textContent = "";
        elements.testModeBadge.textContent = "預覽模式";
        elements.testModeBadge.className = "chip chip-neutral";
    }

    function toPrettyJson(value) {
        return JSON.stringify(value || {}, null, 2);
    }

    function promptIdentity() {
        return {
            type: elements.typeInput.value.trim(),
            category: elements.categoryInput.value.trim(),
            name: elements.promptNameInput.value.trim(),
        };
    }

    async function loadSubDepartments(departmentName) {
        if (elements.categoryDatalist) {
            elements.categoryDatalist.replaceChildren();
        }
        if (!departmentName) {
            return;
        }
        const params = new URLSearchParams({ department: departmentName });
        const data = await requestJson(config.subDepartmentsUrl + "?" + params.toString());
        (data.sub_departments || []).forEach(function (item) {
            const opt = document.createElement("option");
            opt.value = item.name;
            if (elements.categoryDatalist) {
                elements.categoryDatalist.appendChild(opt);
            }
        });
    }

    function promptPath(prompt) {
        if (!prompt) {
            return "尚未選擇";
        }
        return prompt.type + " / " + prompt.category + " / " + prompt.name;
    }

    function getVersionItem(versionId) {
        if (!state.currentPrompt) {
            return null;
        }
        return (
            state.currentPrompt.versions.find(function (item) {
                return item.id === versionId;
            }) || null
        );
    }

    function currentVersionLabel() {
        if (!state.currentPrompt || !state.selectedVersion) {
            return "新增版本";
        }
        const item = getVersionItem(state.selectedVersion);
        return item ? "v" + String(item.version) : "新增版本";
    }

    function displayChannelName(channelName) {
        const normalized = String(channelName || "").trim().toLowerCase();
        const labels = {
            production: "production（正式）",
            alpha: "alpha（測試）",
            beta: "beta（測試）",
            staging: "staging（預備環境）",
            development: "development（開發環境）",
        };

        if (!normalized) {
            return "尚未選擇";
        }

        return labels[normalized] || channelName;
    }

    function getAssignedVersionForChannel(channelName) {
        if (!state.currentPrompt || !state.currentPrompt.channels) {
            return null;
        }

        const normalized = String(channelName || "").trim().toLowerCase();
        if (!normalized) {
            return null;
        }

        return state.currentPrompt.channels[normalized] ?? null;
    }

    function getVersionItemByChannel(channelName) {
        const assigned = getAssignedVersionForChannel(channelName);
        if (!assigned || !state.currentPrompt) {
            return null;
        }

        const byId = state.currentPrompt.versions.find(function (item) {
            return String(item.id) === String(assigned);
        });
        if (byId) {
            return byId;
        }

        const assignedNumber = Number(assigned);
        if (!Number.isFinite(assignedNumber)) {
            return null;
        }

        return (
            state.currentPrompt.versions.find(function (item) {
                return item.version === assignedNumber;
            }) || null
        );
    }

    function applyTreePanelState(collapsed, persist) {
        const shouldPersist = persist !== false;

        state.treeCollapsed = Boolean(collapsed);

        syncTreePanelForViewport();

        if (shouldPersist) {
            try {
                window.localStorage.setItem(
                    TREE_PANEL_STORAGE_KEY,
                    state.treeCollapsed ? "1" : "0"
                );
            } catch (error) {
                // Ignore storage access issues and keep the in-memory state only.
            }
        }
    }

    function syncTreePanelForViewport() {
        const effectiveCollapsed = window.innerWidth <= 1180 ? false : state.treeCollapsed;

        if (elements.appLayout) {
            elements.appLayout.classList.toggle("tree-collapsed", effectiveCollapsed);
        }

        if (elements.catalogPanel) {
            elements.catalogPanel.classList.toggle("is-collapsed", effectiveCollapsed);
        }

        if (elements.treeToggleButton) {
            const label = effectiveCollapsed ? "展開提示詞樹" : "收合提示詞樹";
            const icon = effectiveCollapsed ? "📁" : "📂";
            elements.treeToggleButton.textContent = icon;
            elements.treeToggleButton.setAttribute("aria-expanded", String(!effectiveCollapsed));
            elements.treeToggleButton.setAttribute("aria-label", label);
            elements.treeToggleButton.setAttribute("title", label);
            elements.treeToggleButton.classList.toggle("is-collapsed", effectiveCollapsed);
        }
    }

    function initializeTreePanelState() {
        let collapsed = false;

        try {
            collapsed = window.localStorage.getItem(TREE_PANEL_STORAGE_KEY) === "1";
        } catch (error) {
            collapsed = false;
        }

        applyTreePanelState(collapsed, false);
    }

    function samePrompt(typeName, categoryName, promptName) {
        if (!state.currentPrompt) {
            return false;
        }

        return (
            state.currentPrompt.type === typeName &&
            state.currentPrompt.category === categoryName &&
            state.currentPrompt.name === promptName
        );
    }

    async function requestJson(url, options) {
        const fetchOptions = Object.assign(
            {
                headers: {
                    Accept: "application/json",
                },
            },
            options || {}
        );

        if (fetchOptions.body) {
            fetchOptions.headers = Object.assign({}, fetchOptions.headers, {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            });
        }

        const response = await fetch(url, fetchOptions);
        const payload = await response.json().catch(function () {
            return {};
        });

        if (!response.ok) {
            throw new Error(payload.error || "請求失敗。");
        }

        return payload;
    }

    function createOption(value, label) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        return option;
    }

    function fillVersionSelect(selectElement, versions, allowBlankLabel) {
        selectElement.replaceChildren();

        if (allowBlankLabel) {
            selectElement.appendChild(createOption("", allowBlankLabel));
        }

        versions.forEach(function (versionItem) {
            const label =
                "v" +
                String(versionItem.version) +
                (versionItem.created_at ? " · " + versionItem.created_at : "");
            selectElement.appendChild(createOption(versionItem.id || String(versionItem.version), label));
        });
    }

    function updateContextBlocks() {
        if (!state.currentPrompt) {
            setTextContent(elements.promptSummary, "建立或調整提示詞版本");
            setTextContent(elements.selectedPromptPath, "目前尚未選擇提示詞");
            setTextContent(elements.selectedPrompt, "目前尚未選擇提示詞");
            setTextContent(elements.latestVersionBadge, "最新版本：尚未選擇");
            setTextContent(elements.lastSavedAt, "目前尚未儲存任何版本。");
            setTextContent(elements.contextPromptName, "尚未選擇");
            setTextContent(elements.contextVersionName, "新增版本");
            setTextContent(elements.contextChannelTarget, "尚未選擇");
            setTextContent(elements.mappingPromptPath, "請先在左側選擇一筆提示詞");
            setTextContent(elements.mappingVersionSummary, "請先在上方選擇測試版本，再設定發布環境。");
            setTextContent(elements.editorVersionHint, "選擇既有版本可先載入內容參考；儲存時會另外建立新版本。");
            setControlDisabled(elements.deleteVersionButton, true);
            setControlDisabled(elements.deletePromptButton, true);
            setControlDisabled(elements.removeChannelButton, true);
            return;
        }

        const selectedVersionItem = getVersionItem(state.selectedVersion);
        const pendingVersionValue = elements.testVersionSelect.value;
        const pendingVersionItem = pendingVersionValue ? getVersionItem(pendingVersionValue) : null;
        const pendingVersionNum = pendingVersionItem ? pendingVersionItem.version : null;
        const channelName = elements.channelInput.value.trim();
        const displayChannel = channelName || "未填寫";
        const assignedVersionValue = getAssignedVersionForChannel(channelName);
        const assignedVersionItem = getVersionItemByChannel(channelName);
        const assignedVersionNum = assignedVersionItem ? assignedVersionItem.version : null;

        setTextContent(elements.promptSummary, state.currentPrompt.name);
        setTextContent(elements.selectedPromptPath, promptPath(state.currentPrompt));
        setTextContent(elements.selectedPrompt, promptPath(state.currentPrompt));
        setTextContent(
            elements.latestVersionBadge,
            "最新版本：v" + String(state.currentPrompt.latest_version || "尚未選擇")
        );
        setTextContent(
            elements.lastSavedAt,
            state.currentPrompt.updated_at
                ? "最近儲存時間：" + state.currentPrompt.updated_at
                : "目前尚未儲存任何版本。"
        );
        setTextContent(elements.contextPromptName, state.currentPrompt.name);
        setTextContent(elements.contextVersionName, currentVersionLabel());
        setTextContent(
            elements.contextChannelTarget,
            assignedVersionValue
                ? displayChannelName(displayChannel) +
                      " → v" +
                      (assignedVersionNum !== null ? assignedVersionNum : "?")
                : channelName
                    ? displayChannelName(displayChannel) + " 尚未指派版本"
                    : "尚未選擇"
        );
        setTextContent(elements.mappingPromptPath, promptPath(state.currentPrompt));
        setTextContent(
            elements.mappingVersionSummary,
            !channelName
                ? "請先選擇發布環境。"
                : !pendingVersionValue
                    ? "請先選擇測試版本，再按下更新發布環境。"
                    : assignedVersionNum !== null && pendingVersionNum !== null && String(assignedVersionNum) === String(pendingVersionNum)
                        ? "目前發布環境「" +
                              displayChannelName(displayChannel) +
                              "」已指向 v" +
                              pendingVersionNum +
                              "。再次按下更新發布環境才會重新套用。"
                        : "目前選擇的是測試版本 v" +
                              (pendingVersionNum !== null ? pendingVersionNum : "?") +
                              "。只有按下更新發布環境，才會套用到「" +
                              displayChannelName(displayChannel) +
                              "」。"
        );

        if (selectedVersionItem) {
            setTextContent(
                elements.editorVersionHint,
                "目前載入 " + currentVersionLabel() + " 作為編輯參考。按下「儲存為新版本」後，會依目前內容新增版本。"
            );
        } else {
            setTextContent(elements.editorVersionHint, "目前是新增版本模式，編輯區內容儲存後會成為新版本。");
        }

        setControlDisabled(
            elements.deleteVersionButton,
            !(state.currentPrompt.versions.length > 1 && Boolean(state.selectedVersion))
        );
        setControlDisabled(elements.deletePromptButton, false);
        setControlDisabled(elements.removeChannelButton, !Boolean(assignedVersionValue));
    }

    function renderChannelList() {
        elements.channelList.replaceChildren();

        if (!state.currentPrompt || !Object.keys(state.currentPrompt.channels).length) {
            const empty = document.createElement("p");
            empty.className = "empty-state";
            empty.textContent = "目前沒有任何發布環境設定。";
            elements.channelList.appendChild(empty);
            return;
        }

        Object.keys(state.currentPrompt.channels).forEach(function (channelName) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "chip chip-action";
            const versionItem = getVersionItemByChannel(channelName);
            const versionLabel = versionItem ? String(versionItem.version) : "?";
            button.textContent =
                displayChannelName(channelName) +
                " → v" +
                versionLabel;
            button.addEventListener("click", function () {
                const version = versionItem ? versionItem.version : "?";
                elements.channelInput.value = channelName;
                if (versionItem) {
                    elements.testVersionSelect.value = versionItem.id;
                }
                updateContextBlocks();
                setFlash(
                    "已選擇發布環境「" + displayChannelName(channelName) + "」，目前指向版本 v" + String(version) + "。",
                    "info"
                );
            });
            elements.channelList.appendChild(button);
        });
    }

    function renderTree() {
        elements.promptTree.replaceChildren();

        if (!state.tree.types.length) {
            const empty = document.createElement("p");
            empty.className = "empty-state";
            empty.textContent = "目前還沒有任何提示詞，請先建立一筆提示詞。";
            elements.promptTree.appendChild(empty);
            return;
        }

        state.tree.types.forEach(function (typeNode) {
            const typeSection = document.createElement("details");
            typeSection.className = "tree-section";
            typeSection.open = true;

            const typeSummary = document.createElement("summary");
            typeSummary.textContent = typeNode.name + "（" + String(typeNode.prompt_count) + "）";
            typeSection.appendChild(typeSummary);

            typeNode.categories.forEach(function (categoryNode) {
                const categorySection = document.createElement("details");
                categorySection.className = "tree-section tree-subsection";

                const categorySummary = document.createElement("summary");
                categorySummary.textContent =
                    categoryNode.name + "（" + String(categoryNode.prompt_count) + "）";
                categorySection.appendChild(categorySummary);

                const promptList = document.createElement("div");
                promptList.className = "tree-prompt-list";

                categoryNode.prompts.forEach(function (promptNode) {
                    const button = document.createElement("button");
                    button.type = "button";
                    button.className = "tree-prompt-button";
                    if (samePrompt(typeNode.name, categoryNode.name, promptNode.name)) {
                        button.classList.add("is-selected");
                    }
                    button.textContent =
                        promptNode.name + " · 最新版本 v" + String(promptNode.latest_version || "-");
                    button.addEventListener("click", function () {
                        loadPrompt(typeNode.name, categoryNode.name, promptNode.name);
                    });
                    promptList.appendChild(button);
                });

                categorySection.appendChild(promptList);
                typeSection.appendChild(categorySection);
            });

            elements.promptTree.appendChild(typeSection);
        });
    }

    function setVersionSelectors(versionId) {
        const versionValue = versionId || "";
        elements.editorVersionSelect.value = versionValue;
        elements.testVersionSelect.value = versionValue;
    }

    function selectVersion(versionId) {
        if (!state.currentPrompt) {
            return;
        }

        const versionItem = getVersionItem(versionId);
        if (!versionItem) {
            return;
        }

        state.selectedVersion = versionId;
        elements.roleCharacterInput.value = versionItem.role_character || "";
        elements.contentInput.value = versionItem.content;
        elements.notesInput.value = versionItem.notes || "";
        elements.authorInput.value = versionItem.created_by || elements.authorInput.value;
        setVersionSelectors(versionId);
        updateContextBlocks();
    }

    async function populatePrompt(prompt) {
        state.currentPrompt = prompt;
        state.selectedVersion = prompt.latest_version;

        elements.typeInput.value = prompt.type;
        await loadSubDepartments(prompt.type);
        elements.categoryInput.value = prompt.category;
        elements.promptNameInput.value = prompt.name;
        elements.descriptionInput.value = prompt.description || "";

        fillVersionSelect(elements.editorVersionSelect, prompt.versions, "新增版本（不載入）");
        fillVersionSelect(elements.testVersionSelect, prompt.versions, "預設使用最新版本");

        if (!elements.channelInput.value) {
            elements.channelInput.value = channelSuggestions[0] || "production";
        }

        renderChannelList();
        selectVersion(prompt.latest_version_id);
        renderTree();
        resetOutputs();
    }

    function clearForm() {
        state.currentPrompt = null;
        state.selectedVersion = null;
        elements.typeInput.value = "";
        if (elements.categoryDatalist) { elements.categoryDatalist.replaceChildren(); }
        elements.categoryInput.value = "";
        elements.promptNameInput.value = "";
        elements.descriptionInput.value = "";
        elements.authorInput.value = "";
        elements.roleCharacterInput.value = "";
        elements.contentInput.value = "";
        elements.notesInput.value = "";
        elements.channelInput.value = channelSuggestions[0] || "production";
        fillVersionSelect(elements.editorVersionSelect, [], "新增版本（不載入）");
        fillVersionSelect(elements.testVersionSelect, [], "預設使用最新版本");
        updateContextBlocks();
        renderChannelList();
        resetOutputs();
        renderTree();
    }

    async function loadTree() {
        elements.treeState.textContent = "正在載入提示詞階層…";
        const payload = await requestJson(config.treeUrl);
        state.tree = payload;
        elements.treeState.textContent = payload.types.length
            ? "已載入 " + String(payload.types.length) + " 個部門群組。"
            : "目前還沒有提示詞資料。";
        renderTree();
    }

    async function loadPrompt(typeName, categoryName, promptName) {
        const params = new URLSearchParams({
            type: typeName,
            category: categoryName,
            name: promptName,
        });
        const prompt = await requestJson(config.detailUrl + "?" + params.toString());
        await populatePrompt(prompt);
    }

    async function refreshTreeAndPrompt(promptReference) {
        await loadTree();

        if (!promptReference) {
            return;
        }

        await loadPrompt(promptReference.type, promptReference.category, promptReference.name);
    }

    async function savePrompt() {
        const identity = promptIdentity();
        const payload = {
            type: identity.type,
            category: identity.category,
            name: identity.name,
            description: elements.descriptionInput.value.trim(),
            author: elements.authorInput.value.trim(),
            role_character: elements.roleCharacterInput.value,
            content: elements.contentInput.value,
            notes: elements.notesInput.value,
        };

        const response = await requestJson(config.saveUrl, {
            method: "POST",
            body: JSON.stringify(payload),
        });

        await refreshTreeAndPrompt(response.prompt);
        setFlash("已儲存為新版本 v" + String(response.prompt.latest_version) + "。", "success");
    }

    async function assignChannel() {
        const identity = promptIdentity();
        const versionValue = elements.testVersionSelect.value;
        if (!versionValue) {
            throw new Error("請先在上方選擇測試版本，才能更新發布環境。");
        }
        const versionItem = getVersionItem(versionValue);
        if (!versionItem) {
            throw new Error("找不到選擇的版本。");
        }

        const payload = {
            type: identity.type,
            category: identity.category,
            name: identity.name,
            channel: elements.channelInput.value.trim(),
            version: versionItem.version,
        };

        const response = await requestJson(config.assignChannelUrl, {
            method: "POST",
            body: JSON.stringify(payload),
        });

        await refreshTreeAndPrompt(response.prompt);
        elements.channelInput.value = payload.channel;
        elements.testVersionSelect.value = versionValue;
        updateContextBlocks();
        setFlash(
            "已將發布環境「" + displayChannelName(payload.channel) + "」指派到版本 v" + String(versionItem.version) + "。",
            "success"
        );
    }

    async function deleteChannel() {
        if (!state.currentPrompt) {
            throw new Error("請先選擇提示詞，再移除發布環境映射。");
        }

        const channelName = elements.channelInput.value.trim();
        if (!channelName) {
            throw new Error("請先輸入或選擇要移除的發布環境名稱。");
        }

        const assignedVersionValue = getAssignedVersionForChannel(channelName);
        if (!assignedVersionValue) {
            throw new Error("目前這個發布環境沒有已存在的版本映射可移除。");
        }

        if (
            !window.confirm(
                "確定要移除發布環境「" +
                    displayChannelName(channelName) +
                    "」目前對應的版本 v" +
                    String(assignedVersionValue) +
                    " 嗎？"
            )
        ) {
            return;
        }

        const payload = {
            type: state.currentPrompt.type,
            category: state.currentPrompt.category,
            name: state.currentPrompt.name,
            channel: channelName,
        };

        const response = await requestJson(config.deleteChannelUrl, {
            method: "POST",
            body: JSON.stringify(payload),
        });

        await refreshTreeAndPrompt(response.prompt);
        elements.channelInput.value = channelName;
        updateContextBlocks();
        setFlash("已移除發布環境「" + displayChannelName(channelName) + "」的版本映射。", "success");
    }

    async function deleteVersion() {
        if (!state.currentPrompt || !state.selectedVersion) {
            throw new Error("請先選擇要刪除的版本。");
        }

        const versionItem = getVersionItem(state.selectedVersion);
        if (!versionItem) {
            throw new Error("找不到選擇的版本。");
        }

        if (!window.confirm("確定要刪除目前版本 " + currentVersionLabel() + " 嗎？此動作無法復原。")) {
            return;
        }

        const response = await requestJson(config.deleteVersionUrl, {
            method: "POST",
            body: JSON.stringify({
                type: state.currentPrompt.type,
                category: state.currentPrompt.category,
                name: state.currentPrompt.name,
                version: versionItem.version,
            }),
        });

        await refreshTreeAndPrompt(response.prompt);
        setFlash("已刪除目前版本。", "success");
    }

    async function deletePrompt() {
        if (!state.currentPrompt) {
            throw new Error("請先選擇要刪除的提示詞。");
        }

        if (!window.confirm("確定要刪除整筆提示詞嗎？該提示詞的所有版本與發布環境設定都會一併移除。")) {
            return;
        }

        await requestJson(config.deletePromptUrl, {
            method: "POST",
            body: JSON.stringify({
                type: state.currentPrompt.type,
                category: state.currentPrompt.category,
                name: state.currentPrompt.name,
            }),
        });

        clearForm();
        await refreshTreeAndPrompt(null);
        setFlash("已刪除整筆提示詞。", "success");
    }

    async function runTest() {
        const identity = promptIdentity();
        const versionValue = elements.testVersionSelect.value;
        const versionItem = versionValue ? getVersionItem(versionValue) : null;
        const payload = {
            type: identity.type,
            category: identity.category,
            name: identity.name,
            version: versionItem ? versionItem.version : null,
            user_input: elements.testInput.value,
        };

        const response = await requestJson(config.testUrl, {
            method: "POST",
            body: JSON.stringify(payload),
        });

        elements.renderedPromptOutput.textContent = response.rendered_prompt || "";
        elements.requestPreviewOutput.textContent = toPrettyJson(response.request_preview || []);
        elements.modelOutput.textContent = response.output || "";
        elements.testModeBadge.textContent =
            response.mode === "live" ? "即時模型結果" : "預覽模式";
        elements.testModeBadge.className =
            response.mode === "live" ? "chip chip-accent" : "chip chip-neutral";
        setFlash("已完成版本 v" + String(response.selected_version) + " 的測試。", "success");
    }

    async function runTestInline() {
        const payload = {
            role_character: elements.roleCharacterInput.value,
            content: elements.contentInput.value,
            user_input: elements.testInput.value,
        };

        const response = await requestJson(config.testInlineUrl, {
            method: "POST",
            body: JSON.stringify(payload),
        });

        elements.renderedPromptOutput.textContent = response.rendered_prompt || "";
        elements.requestPreviewOutput.textContent = toPrettyJson(response.request_preview || []);
        elements.modelOutput.textContent = response.output || "";
        elements.testModeBadge.textContent =
            response.mode === "live" ? "即時模型結果" : "預覽模式";
        elements.testModeBadge.className =
            response.mode === "live" ? "chip chip-accent" : "chip chip-neutral";
        setFlash("已完成目前內容的測試。", "success");
    }

    function handleEditorVersionChange() {
        const value = elements.editorVersionSelect.value;
        if (!value) {
            state.selectedVersion = null;
            elements.authorInput.value = "";
            elements.roleCharacterInput.value = "";
            elements.contentInput.value = "";
            elements.notesInput.value = "";
            updateContextBlocks();
            return;
        }

        selectVersion(value);
    }

    function bindEvents() {
        if (elements.clearEditorButton) {
            elements.clearEditorButton.addEventListener("click", function () {
                clearForm();
                setFlash("已清空所有選擇。", "info");
            });
        }

        elements.refreshTreeButton.addEventListener("click", function () {
            runAction(loadTree);
        });

        if (elements.treeToggleButton) {
            elements.treeToggleButton.addEventListener("click", function () {
                applyTreePanelState(!state.treeCollapsed);
            });
        }

        window.addEventListener("resize", syncTreePanelForViewport);

        elements.savePromptButton.addEventListener("click", function () {
            runAction(savePrompt);
        });

        elements.clearFormButton.addEventListener("click", function () {
            clearForm();
            setFlash("已清除編輯內容。", "info");
        });

        elements.assignChannelButton.addEventListener("click", function () {
            runAction(assignChannel);
        });

        elements.removeChannelButton.addEventListener("click", function () {
            runAction(deleteChannel);
        });

        elements.deleteVersionButton.addEventListener("click", function () {
            runAction(deleteVersion);
        });

        elements.deletePromptButton.addEventListener("click", function () {
            runAction(deletePrompt);
        });

        elements.runTestButton.addEventListener("click", function () {
            runAction(runTest);
        });

        if (elements.testCurrentButton) {
            elements.testCurrentButton.addEventListener("click", function () {
                runAction(runTestInline);
            });
        }

        elements.typeInput.addEventListener("change", function () {
            const dept = elements.typeInput.value;
            if (elements.categoryDatalist) { elements.categoryDatalist.replaceChildren(); }
            elements.categoryInput.value = "";
            if (dept) {
                runAction(function () { return loadSubDepartments(dept); });
            }
        });

        elements.editorVersionSelect.addEventListener("change", handleEditorVersionChange);
        elements.testVersionSelect.addEventListener("change", updateContextBlocks);
        elements.channelInput.addEventListener("change", updateContextBlocks);
    }

    async function runAction(action) {
        try {
            await action();
        } catch (error) {
            setFlash(error.message || "發生未預期的錯誤。", "error");
        }
    }

    async function init() {
        initializeTreePanelState();
        bindEvents();
        clearForm();
        await runAction(function () {
            return refreshTreeAndPrompt(null);
        });
    }

    init();
})();
