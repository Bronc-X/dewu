(() => {
  const fileInput = document.getElementById("file-input");
  const uploadZone = document.getElementById("upload-zone");
  const fileSummary = document.getElementById("file-summary");
  const fileList = document.getElementById("file-list");
  const form = document.getElementById("upload-form");
  const submitButton = document.getElementById("submit-button");
  const minImages = Number(document.body.dataset.minImages || 1);
  const maxImages = Number(document.body.dataset.maxImages || 8);
  const lang = document.body.dataset.lang === "en" ? "en" : "zh";
  const copy = {
    zh: {
      none: "\u5c1a\u672a\u9009\u62e9\u56fe\u7247\u3002",
      selected: (count) => `\u5df2\u9009\u62e9 ${count} \u5f20\u56fe\u7247\uff0c\u53ef\u4e0a\u4f20 ${minImages} \u5230 ${maxImages} \u5f20\u3002`,
      invalid: (count) => `\u5f53\u524d\u9009\u62e9 ${count} \u5f20\uff0c\u8bf7\u4e0a\u4f20 ${minImages} \u5230 ${maxImages} \u5f20\u56fe\u7247\u3002`,
      uploading: "\u6b63\u5728\u4e0a\u4f20\u5e76\u542f\u52a8\u751f\u6210",
      progress: (done, total, progress) => `> \u8fdb\u5ea6\u66f4\u65b0\uff1a${done}/${total} \u5f20\uff0c${progress}%`,
      configured: "\u5df2\u914d\u7f6e",
      unconfigured: "\u672a\u914d\u7f6e",
      apiTitle: "PhotoRoom \u5206\u6b65\u5de5\u4f5c\u53f0",
      apiHint: "\u5bfc\u5165\u540e\u5148\u62a0\u56fe\uff0c\u770b\u8fc7\u4e3b\u4f53\u8fb9\u7f18\u540e\u518d\u751f\u6210 AI \u80cc\u666f\u3002",
      cutoutTitle: "PhotoRoom \u62a0\u56fe\u5de5\u4f5c\u53f0",
      cutoutHint: "\u8fd9\u91cc\u53ea\u505a\u7b2c\u4e00\u6b65\uff1a\u4e0a\u4f20\u5546\u54c1\u56fe\uff0c\u8fd4\u56de\u900f\u660e\u80cc\u666f\u4e3b\u4f53\u3002",
      backgroundTitle: "AI \u667a\u80fd\u80cc\u666f\u5de5\u4f5c\u53f0",
      backgroundHint: "\u8fd9\u91cc\u505a\u7b2c\u4e8c\u6b65\uff1a\u4f7f\u7528\u5df2\u62a0\u597d\u7684\u4e3b\u4f53\uff0c\u751f\u6210\u65b0\u80cc\u666f\u3002",
      useLatestCutout: "\u4f7f\u7528\u6700\u8fd1\u62a0\u56fe",
      refresh: "\u5237\u65b0\u72b6\u6001",
      status: "\u63a5\u53e3\u72b6\u6001",
      upload: "\u5bfc\u5165",
      cutout: "\u62a0\u56fe",
      background: "AI \u80cc\u666f",
      final: "\u7ed3\u679c",
      uploadImage: "\u4e0a\u4f20\u539f\u56fe",
      chooseImage: "\u70b9\u51fb\u6216\u62d6\u5165\u5546\u54c1\u56fe",
      bgImage: "\u53c2\u8003\u80cc\u666f",
      bgImageHint: "\u53ef\u9009\uff1a\u624b\u52a8\u6307\u5b9a\u80cc\u666f",
      startCutout: "\u5f00\u59cb\u62a0\u56fe",
      nextBackground: "\u8fdb\u5165 AI \u80cc\u666f",
      generateBackground: "\u751f\u6210 AI \u80cc\u666f",
      useReference: "\u4f7f\u7528\u53c2\u8003\u80cc\u666f",
      download: "\u4e0b\u8f7d\u7ed3\u679c",
      original: "\u539f\u56fe",
      cutoutResult: "\u62a0\u56fe\u7ed3\u679c",
      aiResult: "AI \u80cc\u666f\u7ed3\u679c",
      empty: "\u7b49\u5f85\u7ed3\u679c",
      prompt: "\u80cc\u666f\u65b9\u5411",
      promptPlaceholder: "\u4f8b\uff1aclean premium ecommerce studio background, matching product angle and lighting",
      lighting: "\u8c03\u5149",
      shadow: "\u9634\u5f71",
      keepOff: "\u4e0d\u542f\u7528",
      lightAuto: "\u81ea\u52a8\u8c03\u5149",
      shadowSoft: "\u67d4\u548c\u9634\u5f71",
      shadowHard: "\u786c\u9634\u5f71",
      shadowFloating: "\u6d6e\u7a7a\u9634\u5f71",
      debug: "API \u8c03\u7528\u8be6\u60c5",
      missingImage: "\u8bf7\u5148\u9009\u62e9\u4e00\u5f20\u5546\u54c1\u56fe\u3002",
      missingCutout: "\u8bf7\u5148\u5b8c\u6210\u62a0\u56fe\uff0c\u518d\u751f\u6210\u80cc\u666f\u3002",
      missingBackground: "\u4f7f\u7528\u53c2\u8003\u80cc\u666f\u65f6\uff0c\u9700\u8981\u518d\u9009\u4e00\u5f20\u80cc\u666f\u56fe\u3002",
      runningCutout: "\u6b63\u5728\u62a0\u56fe...",
      runningBackground: "\u6b63\u5728\u751f\u6210 AI \u80cc\u666f...",
      cutoutDone: "\u62a0\u56fe\u5b8c\u6210\uff0c\u8bf7\u5728\u4e2d\u95f4\u9884\u89c8\u533a\u68c0\u67e5\u8fb9\u7f18\u3002",
      backgroundDone: "\u80cc\u666f\u5df2\u751f\u6210\uff0c\u7ed3\u679c\u5728\u53f3\u4fa7\u3002",
      latestCutoutLoaded: "\u5df2\u8f7d\u5165\u6700\u8fd1\u4e00\u5f20\u62a0\u56fe\uff0c\u53ef\u4ee5\u76f4\u63a5\u751f\u6210\u80cc\u666f\u3002",
      noLatestCutout: "\u6682\u65e0\u6700\u8fd1\u62a0\u56fe\uff0c\u8bf7\u5148\u5230 PhotoRoom \u62a0\u56fe\u5b8c\u6210\u4e00\u6b21\u3002",
      presets: [
        ["\u7535\u5546\u767d\u5e95", "clean white ecommerce studio background, soft product shadow, catalog-ready"],
        ["\u8857\u5934\u6c34\u6ce5", "urban concrete streetwear background, natural daylight, realistic ground contact"],
        ["\u81ea\u7136\u6237\u5916", "natural outdoor lifestyle background, soft sunlight, premium retail campaign"],
        ["\u5ba4\u5185\u68da\u62cd", "minimal indoor studio set, softbox lighting, matching product angle"],
        ["\u6697\u8c03\u9ad8\u7ea7", "dark luxury editorial background, controlled highlights, premium shadows"],
        ["\u5976\u6cb9\u67d4\u5149", "warm cream soft-light studio background, gentle shadows, refined ecommerce style"],
      ],
    },
    en: {
      none: "No images selected.",
      selected: (count) => `Selected ${count} images. Upload ${minImages} to ${maxImages}.`,
      invalid: (count) => `Selected ${count}. Please upload ${minImages} to ${maxImages} images.`,
      uploading: "Uploading and starting generation",
      progress: (done, total, progress) => `> Progress updated: ${done}/${total} assets, ${progress}%`,
      configured: "Configured",
      unconfigured: "Not Configured",
      apiTitle: "PhotoRoom Step Workbench",
      apiHint: "Upload, remove the background, review the cutout, then generate the AI background.",
      cutoutTitle: "PhotoRoom Cutout Workbench",
      cutoutHint: "This page only handles step one: upload a product image and return a transparent-background subject.",
      backgroundTitle: "AI Background Workbench",
      backgroundHint: "This page handles step two: use a completed cutout, then generate a new background.",
      useLatestCutout: "Use Latest Cutout",
      refresh: "Refresh Status",
      status: "API Status",
      upload: "Import",
      cutout: "Cutout",
      background: "AI Background",
      final: "Result",
      uploadImage: "Upload Original",
      chooseImage: "Click or drop a product image",
      bgImage: "Reference Background",
      bgImageHint: "Optional manual background",
      startCutout: "Remove Background",
      nextBackground: "Go To AI Background",
      generateBackground: "Generate AI Background",
      useReference: "Use Reference Background",
      download: "Download Result",
      original: "Original",
      cutoutResult: "Cutout Result",
      aiResult: "AI Background Result",
      empty: "Waiting for result",
      prompt: "Background Direction",
      promptPlaceholder: "Example: clean premium ecommerce studio background, matching product angle and lighting",
      lighting: "Relight",
      shadow: "Shadow",
      keepOff: "Off",
      lightAuto: "AI Auto",
      shadowSoft: "AI Soft",
      shadowHard: "AI Hard",
      shadowFloating: "AI Floating",
      debug: "API Details",
      missingImage: "Choose a product image first.",
      missingCutout: "Run cutout first, then generate the background.",
      missingBackground: "Reference background mode needs a second background image.",
      runningCutout: "Removing background...",
      runningBackground: "Generating AI background...",
      cutoutDone: "Cutout complete. Review the subject edges in the middle preview.",
      backgroundDone: "Background generated. The result is on the right.",
      latestCutoutLoaded: "Loaded the latest cutout. You can generate the background now.",
      noLatestCutout: "No recent cutout yet. Run PhotoRoom Cutout first.",
      presets: [
        ["White studio", "clean white ecommerce studio background, soft product shadow, catalog-ready"],
        ["Concrete street", "urban concrete streetwear background, natural daylight, realistic ground contact"],
        ["Outdoor lifestyle", "natural outdoor lifestyle background, soft sunlight, premium retail campaign"],
        ["Indoor studio", "minimal indoor studio set, softbox lighting, matching product angle"],
        ["Dark premium", "dark luxury editorial background, controlled highlights, premium shadows"],
        ["Cream soft light", "warm cream soft-light studio background, gentle shadows, refined ecommerce style"],
      ],
    },
  }[lang];

  function renderFileList() {
    if (!fileInput || !fileSummary || !fileList) return;
    const files = Array.from(fileInput.files || []);
    fileList.innerHTML = "";
    fileSummary.textContent = files.length ? copy.selected(files.length) : copy.none;
    files.forEach((file, index) => {
      const item = document.createElement("li");
      item.textContent = `${String(index + 1).padStart(2, "0")} / ${file.name}`;
      fileList.appendChild(item);
    });
  }

  if (uploadZone && fileInput) {
    uploadZone.addEventListener("dragover", (event) => {
      event.preventDefault();
      uploadZone.classList.add("is-dragover");
    });
    uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("is-dragover"));
    uploadZone.addEventListener("drop", (event) => {
      event.preventDefault();
      uploadZone.classList.remove("is-dragover");
      fileInput.files = event.dataTransfer.files;
      renderFileList();
    });
    fileInput.addEventListener("change", renderFileList);
  }

  if (form && fileInput && submitButton && fileSummary) {
    form.addEventListener("submit", (event) => {
      const count = (fileInput.files || []).length;
      if (count < minImages || count > maxImages) {
        event.preventDefault();
        fileSummary.textContent = copy.invalid(count);
        return;
      }
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="material-symbols-outlined">hourglass_empty</span>' + copy.uploading;
    });
  }

  const apiWorkbench = document.querySelector("[data-api-workbench]");
  const workbenchMode = apiWorkbench?.dataset.mode === "ai_background" ? "ai_background" : "cutout";

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function setImageSource(image, url) {
    if (!image) return;
    image.src = url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E";
    image.classList.toggle("has-image", Boolean(url));
  }

  function normalizePreviewUrl(url) {
    if (!url || url.startsWith("data:image/svg+xml")) return "";
    return url;
  }

  function isImageHref(url) {
    if (!url) return false;
    return /\.(png|jpe?g|webp|gif|avif)(?:[?#].*)?$/i.test(url);
  }

  function ensureImageLightbox() {
    let lightbox = document.querySelector("[data-image-lightbox]");
    if (lightbox) return lightbox;
    lightbox = document.createElement("div");
    lightbox.className = "image-lightbox";
    lightbox.dataset.imageLightbox = "true";
    lightbox.hidden = true;
    lightbox.innerHTML = `
      <div class="image-lightbox__backdrop" data-lightbox-close></div>
      <section class="image-lightbox__card" role="dialog" aria-modal="true" aria-label="${lang === "en" ? "Image preview" : "\u56fe\u7247\u9884\u89c8"}">
        <button class="image-lightbox__close" type="button" data-lightbox-close aria-label="${lang === "en" ? "Close preview" : "\u5173\u95ed\u9884\u89c8"}"><span class="material-symbols-outlined">close</span></button>
        <div class="image-lightbox__stage"><img alt=""></div>
        <footer><strong data-lightbox-title></strong><a class="secondary-pill compact" data-lightbox-download href="#" download><span class="material-symbols-outlined">download</span>${lang === "en" ? "Download" : "\u4e0b\u8f7d\u56fe\u7247"}</a></footer>
      </section>
    `;
    document.body.appendChild(lightbox);
    lightbox.addEventListener("click", (event) => {
      if (event.target.closest("[data-lightbox-close]")) closeImageLightbox();
    });
    return lightbox;
  }

  function openImageLightbox(url, title = "") {
    const previewUrl = normalizePreviewUrl(url);
    if (!previewUrl) return;
    const lightbox = ensureImageLightbox();
    const image = lightbox.querySelector("img");
    const titleEl = lightbox.querySelector("[data-lightbox-title]");
    const download = lightbox.querySelector("[data-lightbox-download]");
    image.src = previewUrl;
    image.alt = title || (lang === "en" ? "Image preview" : "\u56fe\u7247\u9884\u89c8");
    titleEl.textContent = title || image.alt;
    download.href = previewUrl;
    lightbox.hidden = false;
    document.body.classList.add("has-image-lightbox");
    lightbox.querySelector(".image-lightbox__close")?.focus();
  }

  function closeImageLightbox() {
    const lightbox = document.querySelector("[data-image-lightbox]");
    if (!lightbox) return;
    lightbox.hidden = true;
    const image = lightbox.querySelector("img");
    if (image) image.src = "";
    document.body.classList.remove("has-image-lightbox");
  }

  document.addEventListener("click", (event) => {
    if (event.target.closest(".image-lightbox")) return;
    const clickable = event.target.closest(".asset-card, .background-card, .history-chip, .review-result-images a, .result-card, .preview-tile, .comparison-view, .thumb, .photoroom-stage-list a");
    if (!clickable) return;
    const directImage = event.target.closest("img");
    if ((clickable.matches(".history-chip, .thumb") || clickable.closest(".photoroom-stage-list")) && !directImage) return;
    const image = directImage || clickable.querySelector("img");
    const href = clickable.getAttribute("href") || "";
    const fallbackUrl = isImageHref(href) ? href : "";
    const url = normalizePreviewUrl(image?.currentSrc || image?.src || fallbackUrl);
    if (!url) return;
    event.preventDefault();
    event.stopPropagation();
    openImageLightbox(url, image?.alt || clickable.textContent.trim());
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeImageLightbox();
  });

  function mountPhotoRoomWorkbench() {
    if (!apiWorkbench) return;
    const isBackgroundMode = workbenchMode === "ai_background";
    const title = isBackgroundMode ? copy.backgroundTitle : copy.cutoutTitle;
    const hint = isBackgroundMode ? copy.backgroundHint : copy.cutoutHint;
    apiWorkbench.innerHTML = `
      <div class="section-title photoroom-workflow-header">
        <div>
          <h2><span class="material-symbols-outlined">auto_fix_high</span>${title}</h2>
          <p>${hint}</p>
        </div>
        <button class="secondary-pill compact" type="button" data-provider-refresh>${copy.refresh}</button>
      </div>
      <div class="api-status-line"><span>${copy.status}</span><strong data-provider-status>${copy.unconfigured}</strong></div>
      <form id="photoroom-sandbox-form" class="sandbox-form photoroom-wizard">
        <div class="workflow-stage-rail" aria-label="${copy.apiTitle}">
          <button class="stage-dot is-active" type="button" data-stage="upload"><span>01</span><strong>${copy.upload}</strong></button>
          <button class="stage-dot" type="button" data-stage="cutout"><span>02</span><strong>${copy.cutout}</strong></button>
          <button class="stage-dot" type="button" data-stage="background"><span>03</span><strong>${copy.background}</strong></button>
          <button class="stage-dot" type="button" data-stage="final"><span>04</span><strong>${copy.final}</strong></button>
        </div>
        <section class="photoroom-stage" id="photoroom-cutout-panel">
          <div class="sandbox-upload-grid">
            <label class="sandbox-file">
              <span class="material-symbols-outlined">add_photo_alternate</span>
              <strong>${copy.uploadImage}</strong>
              <small data-sandbox-image-name>${copy.chooseImage}</small>
              <input id="sandbox-image" type="file" accept=".png,.jpg,.jpeg,.webp" required>
            </label>
            <label class="sandbox-file optional-bg">
              <span class="material-symbols-outlined">wallpaper</span>
              <strong>${copy.bgImage}</strong>
              <small data-sandbox-bg-name>${copy.bgImageHint}</small>
              <input id="sandbox-background-image" type="file" accept=".png,.jpg,.jpeg,.webp">
            </label>
          </div>
        <div class="photoroom-actions">
          <button id="sandbox-cutout" class="primary-pill" type="button" disabled><span class="material-symbols-outlined">layers_clear</span>${copy.startCutout}</button>
          <button id="sandbox-next-background" class="secondary-pill" type="button" disabled><span class="material-symbols-outlined">arrow_forward</span>${copy.nextBackground}</button>
          <button id="sandbox-latest-cutout" class="secondary-pill" type="button"><span class="material-symbols-outlined">history</span>${copy.useLatestCutout}</button>
        </div>
      </section>
        <section class="photoroom-result-grid" aria-live="polite">
          <article class="result-card">
            <strong>${copy.original}</strong>
            <img id="sandbox-original" alt="${copy.original}" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">
            <span>${copy.empty}</span>
          </article>
          <article class="result-card">
            <strong>${copy.cutoutResult}</strong>
            <img id="sandbox-cutout-result" alt="${copy.cutoutResult}" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">
            <span>${copy.empty}</span>
          </article>
          <article class="result-card">
            <strong>${copy.aiResult}</strong>
            <img id="sandbox-result" alt="${copy.aiResult}" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">
            <span>${copy.empty}</span>
          </article>
        </section>
        <section class="photoroom-stage background-stage is-locked" id="photoroom-background-panel" data-background-stage>
          <div class="prompt-presets">
            ${copy.presets.map(([label, prompt], index) => `<button class="preset-chip ${index === 0 ? "is-active" : ""}" type="button" data-prompt="${escapeHtml(prompt)}">${escapeHtml(label)}</button>`).join("")}
          </div>
          <div class="api-form-grid sandbox-fields">
            <label><span>${copy.prompt}</span><input id="api-background-prompt" type="text" value="${escapeHtml(copy.presets[0][1])}" placeholder="${copy.promptPlaceholder}"></label>
            <label><span>${copy.lighting}</span><select id="api-lighting-mode"><option value="ai.auto">${copy.lightAuto}</option><option value="">${copy.keepOff}</option></select></label>
            <label><span>${copy.shadow}</span><select id="api-shadow-mode"><option value="ai.soft">${copy.shadowSoft}</option><option value="ai.hard">${copy.shadowHard}</option><option value="ai.floating">${copy.shadowFloating}</option><option value="">${copy.keepOff}</option></select></label>
          </div>
          <div class="photoroom-actions">
            <button id="sandbox-bg-submit" class="primary-pill" type="button" disabled><span class="material-symbols-outlined">auto_awesome</span>${copy.generateBackground}</button>
            <button id="sandbox-static-submit" class="secondary-pill" type="button" disabled><span class="material-symbols-outlined">wallpaper</span>${copy.useReference}</button>
            <a id="sandbox-download" class="secondary-pill disabled" href="#" download><span class="material-symbols-outlined">download</span>${copy.download}</a>
          </div>
        </section>
      </form>
      <div id="api-status-message" class="result-state">${copy.chooseImage}</div>
      <details class="sandbox-debug">
        <summary>${copy.debug}</summary>
        <pre id="api-result" class="api-result"></pre>
      </details>
    `;

    const providerStatus = apiWorkbench.querySelector("[data-provider-status]");
    const providerRefresh = apiWorkbench.querySelector("[data-provider-refresh]");
    const apiResult = apiWorkbench.querySelector("#api-result");
    const statusMessage = apiWorkbench.querySelector("#api-status-message");
    const sandboxForm = apiWorkbench.querySelector("#photoroom-sandbox-form");
    const sandboxImage = apiWorkbench.querySelector("#sandbox-image");
    const sandboxBackgroundImage = apiWorkbench.querySelector("#sandbox-background-image");
    const sandboxImageName = apiWorkbench.querySelector("[data-sandbox-image-name]");
    const sandboxBgName = apiWorkbench.querySelector("[data-sandbox-bg-name]");
    const sandboxOriginal = apiWorkbench.querySelector("#sandbox-original");
    const sandboxCutout = apiWorkbench.querySelector("#sandbox-cutout-result");
    const sandboxResult = apiWorkbench.querySelector("#sandbox-result");
    const sandboxCutoutButton = apiWorkbench.querySelector("#sandbox-cutout");
    const sandboxNextButton = apiWorkbench.querySelector("#sandbox-next-background");
    const sandboxLatestButton = apiWorkbench.querySelector("#sandbox-latest-cutout");
    const sandboxBgButton = apiWorkbench.querySelector("#sandbox-bg-submit");
    const sandboxStaticButton = apiWorkbench.querySelector("#sandbox-static-submit");
    const sandboxDownload = apiWorkbench.querySelector("#sandbox-download");
    const apiBackgroundPrompt = apiWorkbench.querySelector("#api-background-prompt");
    const apiLightingMode = apiWorkbench.querySelector("#api-lighting-mode");
    const apiShadowMode = apiWorkbench.querySelector("#api-shadow-mode");
    const backgroundStage = apiWorkbench.querySelector("[data-background-stage]");
    const stageDots = Array.from(apiWorkbench.querySelectorAll("[data-stage]"));
    const presetChips = Array.from(apiWorkbench.querySelectorAll("[data-prompt]"));
    const state = {
      batchId: `photoroom_batch_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`,
      originalFile: null,
      originalPreviewUrl: "",
      cutoutUrl: "",
      finalUrl: "",
      stage: "upload",
    };

    function setApiResult(payload) {
      if (!apiResult) return;
      apiResult.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    }

    function setStatus(message, tone = "") {
      if (!statusMessage) return;
      statusMessage.textContent = message;
      statusMessage.dataset.tone = tone;
    }

    function setStage(stage) {
      state.stage = stage;
      const stageOrder = ["upload", "cutout", "background", "final"];
      const currentIndex = stageOrder.indexOf(stage);
      stageDots.forEach((dot) => {
        const index = stageOrder.indexOf(dot.dataset.stage || "");
        dot.classList.toggle("is-active", index === currentIndex);
        dot.classList.toggle("is-complete", index >= 0 && index < currentIndex);
      });
    }

    function updateControls() {
      const hasImage = Boolean(state.originalFile);
      const hasCutout = Boolean(state.cutoutUrl);
      const hasBackgroundFile = Boolean(sandboxBackgroundImage?.files?.[0]);
      sandboxCutoutButton.disabled = !hasImage;
      sandboxNextButton.disabled = !hasCutout;
      sandboxBgButton.disabled = !hasCutout;
      sandboxStaticButton.disabled = !hasCutout || !hasBackgroundFile;
      backgroundStage?.classList.toggle("is-locked", !hasCutout);
      sandboxDownload?.classList.toggle("disabled", !state.finalUrl);
      if (sandboxDownload && state.finalUrl) sandboxDownload.href = state.finalUrl;
      apiWorkbench.classList.toggle("is-background-mode", workbenchMode === "ai_background");
      apiWorkbench.classList.toggle("is-cutout-mode", workbenchMode !== "ai_background");
    }

    function resetResults() {
      state.cutoutUrl = "";
      state.finalUrl = "";
      setImageSource(sandboxCutout, "");
      setImageSource(sandboxResult, "");
      setStage("upload");
      updateControls();
    }

    async function refreshProviderStatus() {
      try {
        const response = await fetch("/api/providers/status", { headers: { accept: "application/json" } });
        const payload = await response.json();
        const photoroom = (payload.providers || []).find((provider) => provider.provider === "photoroom");
        if (providerStatus && photoroom) {
          providerStatus.textContent = photoroom.configured ? copy.configured : copy.unconfigured;
          providerStatus.dataset.configured = photoroom.configured ? "true" : "false";
        }
        setApiResult(payload);
      } catch (error) {
        setApiResult({ ok: false, error: String(error) });
      }
    }

    async function imageFileForBackground() {
      if (!state.cutoutUrl) return state.originalFile;
      const response = await fetch(state.cutoutUrl, { cache: "no-store" });
      const blob = await response.blob();
      return new File([blob], "photoroom-cutout.png", { type: blob.type || "image/png" });
    }

    async function loadLatestCutout() {
      try {
        const response = await fetch(`/api/tools/photoroom/history?mode=remove_background&limit=1&lang=${lang}`, {
          headers: { accept: "application/json" },
        });
        const payload = await response.json();
        const latest = payload.items?.[0];
        if (!latest?.result_url) {
          setStatus(copy.noLatestCutout, "error");
          return;
        }
        state.batchId = latest.batch_id || state.batchId;
        state.cutoutUrl = latest.result_url;
        state.finalUrl = "";
        setImageSource(sandboxCutout, `${latest.result_url}?t=${Date.now()}`);
        if (latest.input_url) setImageSource(sandboxOriginal, `${latest.input_url}?t=${Date.now()}`);
        setImageSource(sandboxResult, "");
        setStage("background");
        setStatus(copy.latestCutoutLoaded, "ok");
        updateControls();
      } catch (error) {
        setStatus(String(error), "error");
      }
    }

    async function callPhotoRoomSandbox(mode) {
      const sourceFile = mode === "remove_background" ? state.originalFile : await imageFileForBackground();
      if (!sourceFile) {
        setStatus(copy.missingImage, "error");
        return;
      }
      if (mode !== "remove_background" && !state.cutoutUrl) {
        setStatus(copy.missingCutout, "error");
        return;
      }
      if (mode === "background_image" && !sandboxBackgroundImage?.files?.[0]) {
        setStatus(copy.missingBackground, "error");
        return;
      }

      const formData = new FormData();
      formData.append("image", sourceFile);
      formData.append("mode", mode);
      formData.append("batch_id", state.batchId);
      formData.append("background_prompt", apiBackgroundPrompt?.value.trim() || "");
      formData.append("lighting_mode", apiLightingMode?.value || "");
      formData.append("shadow_mode", apiShadowMode?.value || "");
      if (sandboxBackgroundImage?.files?.[0]) {
        formData.append("background_image", sandboxBackgroundImage.files[0]);
      }

      const isCutout = mode === "remove_background";
      const activeButton = isCutout ? sandboxCutoutButton : mode === "background_image" ? sandboxStaticButton : sandboxBgButton;
      const activeText = isCutout ? copy.runningCutout : copy.runningBackground;
      activeButton.disabled = true;
      activeButton.innerHTML = `<span class="material-symbols-outlined">hourglass_empty</span>${activeText}`;
      setStatus(activeText);
      setApiResult(activeText);

      try {
        const response = await fetch("/api/tools/photoroom/sandbox", {
          method: "POST",
          headers: { accept: "application/json" },
          body: formData,
        });
        const payload = await response.json();
        setApiResult(payload);
        if (!payload.ok || !payload.result?.url) {
          setStatus(payload.detail || payload.error || "PhotoRoom request failed.", "error");
          return;
        }
        const versionedUrl = `${payload.result.url}?t=${Date.now()}`;
        if (isCutout) {
          state.batchId = payload.history?.batch_id || state.batchId;
          state.cutoutUrl = payload.result.url;
          window.localStorage?.setItem("photoroom.latestCutoutUrl", payload.result.url);
          setImageSource(sandboxCutout, versionedUrl);
          setStage("background");
          setStatus(copy.cutoutDone, "ok");
          backgroundStage?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else {
          state.finalUrl = versionedUrl;
          setImageSource(sandboxResult, versionedUrl);
          setStage("final");
          setStatus(copy.backgroundDone, "ok");
        }
      } catch (error) {
        setApiResult({ ok: false, error: String(error) });
        setStatus(String(error), "error");
      } finally {
        sandboxCutoutButton.innerHTML = `<span class="material-symbols-outlined">layers_clear</span>${copy.startCutout}`;
        sandboxBgButton.innerHTML = `<span class="material-symbols-outlined">auto_awesome</span>${copy.generateBackground}`;
        sandboxStaticButton.innerHTML = `<span class="material-symbols-outlined">wallpaper</span>${copy.useReference}`;
        updateControls();
      }
    }

    sandboxImage?.addEventListener("change", () => {
      const file = sandboxImage.files?.[0] || null;
      state.originalFile = file;
      sandboxImageName.textContent = file ? file.name : copy.chooseImage;
      if (state.originalPreviewUrl) URL.revokeObjectURL(state.originalPreviewUrl);
      state.originalPreviewUrl = file ? URL.createObjectURL(file) : "";
      setImageSource(sandboxOriginal, state.originalPreviewUrl);
      resetResults();
      setStatus(file ? copy.startCutout : copy.chooseImage);
      updateControls();
    });

    sandboxBackgroundImage?.addEventListener("change", () => {
      const file = sandboxBackgroundImage.files?.[0] || null;
      sandboxBgName.textContent = file ? file.name : copy.bgImageHint;
      updateControls();
    });

    presetChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        presetChips.forEach((item) => item.classList.remove("is-active"));
        chip.classList.add("is-active");
        apiBackgroundPrompt.value = chip.dataset.prompt || "";
      });
    });

    sandboxCutoutButton?.addEventListener("click", () => callPhotoRoomSandbox("remove_background"));
    sandboxLatestButton?.addEventListener("click", loadLatestCutout);
    sandboxNextButton?.addEventListener("click", () => {
      setStage("background");
      backgroundStage?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    sandboxBgButton?.addEventListener("click", () => callPhotoRoomSandbox("ai_background"));
    sandboxStaticButton?.addEventListener("click", () => callPhotoRoomSandbox("background_image"));
    sandboxForm?.addEventListener("submit", (event) => event.preventDefault());
    providerRefresh?.addEventListener("click", refreshProviderStatus);

    refreshProviderStatus();
    updateControls();

    if (workbenchMode === "ai_background") {
      setStage("background");
      loadLatestCutout();
      backgroundStage?.scrollIntoView({ behavior: "smooth", block: "center" });
    } else if (location.hash === "#photoroom-background") {
      setStage("background");
      backgroundStage?.scrollIntoView({ behavior: "smooth", block: "center" });
    } else if (location.hash === "#photoroom-cutout") {
      setStage("cutout");
      apiWorkbench.querySelector("#photoroom-cutout-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  mountPhotoRoomWorkbench();

  const sliderContainer = document.getElementById("comparisonSlider");
  const sliderHandle = document.getElementById("sliderHandle");
  const overlayImage = document.getElementById("overlayImage");
  const overlayImgTag = overlayImage ? overlayImage.querySelector("img") : null;
  let isDragging = false;

  function setSlider(clientX) {
    if (!sliderContainer || !sliderHandle || !overlayImage || !overlayImgTag) return;
    const rect = sliderContainer.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const percentage = (x / rect.width) * 100;
    sliderHandle.style.left = `${percentage}%`;
    overlayImage.style.width = `${percentage}%`;
    overlayImgTag.style.width = `${rect.width}px`;
    overlayImage.style.setProperty("--slider-width", `${rect.width}px`);
  }

  if (sliderContainer && sliderHandle) {
    sliderHandle.addEventListener("mousedown", () => { isDragging = true; });
    sliderHandle.addEventListener("touchstart", () => { isDragging = true; }, { passive: true });
    window.addEventListener("mouseup", () => { isDragging = false; });
    window.addEventListener("touchend", () => { isDragging = false; });
    window.addEventListener("mousemove", (event) => { if (isDragging) setSlider(event.clientX); });
    window.addEventListener("touchmove", (event) => {
      if (!isDragging) return;
      event.preventDefault();
      setSlider(event.touches[0].clientX);
    }, { passive: false });
    window.addEventListener("resize", () => setSlider(sliderContainer.getBoundingClientRect().left + sliderContainer.getBoundingClientRect().width / 2));
    requestAnimationFrame(() => setSlider(sliderContainer.getBoundingClientRect().left + sliderContainer.getBoundingClientRect().width / 2));
  }

  const batchId = document.body.dataset.batchId;
  if (batchId && document.querySelector(".generation-monitor")) {
    const progressNumber = document.getElementById("progress-number");
    const orbProgress = document.getElementById("orb-progress");
    const itemsDone = document.getElementById("items-done");
    const orb = document.querySelector(".liquid-orb");
    const nodes = document.querySelector(".pipeline-nodes");
    const logContainer = document.getElementById("log-container");
    let lastDone = -1;

    async function refreshBatch() {
      try {
        const response = await fetch(`/api/batches/${batchId}`, { headers: { accept: "application/json" } });
        if (!response.ok) return;
        const payload = await response.json();
        const progress = payload.progress || 0;
        const total = payload.report.total || 0;
        const done = payload.items_done || 0;
        if (progressNumber) progressNumber.textContent = `${progress}%`;
        if (orbProgress) orbProgress.innerHTML = `${progress}<span>%</span>`;
        if (orb) orb.style.setProperty("--progress", `${progress}%`);
        if (nodes) nodes.style.setProperty("--progress", `${progress}%`);
        if (itemsDone) itemsDone.innerHTML = `${done}<span>/${total}</span>`;
        if (logContainer && done !== lastDone) {
          lastDone = done;
          const div = document.createElement("p");
          div.className = "is-live";
          div.textContent = copy.progress(done, total, progress);
          logContainer.appendChild(div);
          logContainer.scrollTop = logContainer.scrollHeight;
        }
        if (["completed", "failed"].includes(payload.report.status)) {
          window.setTimeout(() => window.location.reload(), 800);
        }
      } catch (_) {
        // The meta refresh still keeps the page honest if polling fails.
      }
    }
    window.setInterval(refreshBatch, 5000);
  }
})();
