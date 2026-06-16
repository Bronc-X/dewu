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
  const primaryNavToggle = document.querySelector("[data-nav-collapse='primary']");
  primaryNavToggle?.addEventListener("click", () => {
    const collapsed = document.body.classList.toggle("primary-nav-collapsed");
    primaryNavToggle.querySelector(".material-symbols-outlined").textContent = collapsed ? "menu" : "menu_open";
  });
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
      themeLibrary: "\u80cc\u666f\u4e3b\u9898",
      backgroundTab: "\u80cc\u666f",
      aiBackgroundsTab: "AI \u80cc\u666f",
      searchBackgrounds: "\u641c\u7d22\u80cc\u666f",
      suggestedBackgrounds: "\u63a8\u8350",
      trendingBackgrounds: "\u70ed\u95e8",
      createBackground: "\u521b\u5efa\u80cc\u666f",
      generateMore: "\u518d\u751f\u6210 2 \u4e2a",
      editorHome: "\u4e3b\u9875",
      resize: "\u8c03\u6574\u5c3a\u5bf8",
      editingCanvas: "\u7f16\u8f91\u753b\u5e03",
      previewArea: "\u9884\u89c8",
      fixedPreview: "\u56fa\u5b9a\u9884\u89c8\u533a",
      generateCandidates: "\u751f\u6210 4 \u4e2a\u5019\u9009",
      regenerateSelected: "\u91cd\u65b0\u751f\u6210\u9009\u4e2d\u5019\u9009",
      applyOne: "\u5e94\u7528\u81f3 1 \u5f20\u56fe\u50cf",
      applied: "\u5df2\u5e94\u7528",
      advancedSettings: "\u9ad8\u7ea7\u8bbe\u7f6e",
      reuseTitle: "\u4e0a\u8f6e\u5df2\u5e94\u7528\u9884\u89c8",
      noReuse: "\u6682\u65e0\u53ef\u590d\u7528\u9884\u89c8\u3002",
      candidateEmpty: "\u70b9\u51fb\u5de6\u4fa7\u80cc\u666f\u4e3b\u9898\u540e\uff0c\u8fd9\u91cc\u4f1a\u4fdd\u7559\u5b8c\u6574\u9884\u89c8\u56fe\u3002",
      candidateLoading: "\u6b63\u5728\u751f\u6210\u9884\u89c8...",
      candidateReady: "\u5019\u9009\u5df2\u751f\u6210\uff0c\u70b9\u51fb\u53ef\u9009\u4e2d\u3002",
      candidateApplied: "\u5df2\u5e94\u7528\u8be5\u9884\u89c8\u914d\u7f6e\uff0c\u65b0\u56fe\u53ef\u7ee7\u7eed\u590d\u7528\u3002",
      reuseApplied: "\u5df2\u5957\u7528\u4e0a\u8f6e\u9884\u89c8\u7684 prompt \u548c seed\u3002",
      seedLabel: "Seed",
      selectedTheme: "\u5df2\u9009\u4e3b\u9898",
      themeGroups: [
        {
          group: "Mood",
          items: [
            ["Wood", "a warm wood studio interior with natural wooden surfaces, soft daylight, realistic ground contact, premium ecommerce portrait background"],
            ["Minimalist", "a minimalist premium studio with warm neutral walls, subtle tonal gradient, soft floor shadow, uncluttered ecommerce campaign background"],
            ["Snow", "a clean snowy outdoor lifestyle scene with soft overcast light, gentle snow texture, realistic standing contact shadow, fashion ecommerce background"],
            ["Monstera", "a bright botanical interior with monstera leaves, warm daylight, soft wall shadows, realistic floor contact, premium lifestyle background"],
          ],
        },
        {
          group: "Countertop",
          items: [
            ["Stone countertop", "a refined stone countertop and warm wall studio scene, soft daylight, realistic contact shadow, product photography background"],
            ["Kitchen countertop", "a modern kitchen countertop scene with muted cabinets, natural daylight, realistic surface perspective, ecommerce product background"],
            ["Wood countertop", "a warm wood countertop scene with clean wall, soft side light, realistic surface contact and shadow, premium catalog background"],
          ],
        },
        {
          group: "Plant",
          items: [
            ["Indoor plant", "a sunlit indoor plant studio with potted greenery, cream wall, soft floor shadow, realistic portrait-scale lifestyle background"],
            ["Greenhouse", "a calm greenhouse lifestyle scene with layered plants, diffused daylight, realistic depth and ground contact, premium fashion background"],
            ["Plant corner", "a minimal plant corner with warm neutral wall, soft leaves shadows, natural floor contact, clean ecommerce background"],
          ],
        },
        {
          group: "Texture",
          items: [
            ["Soil", "an earthy textured studio scene with soil-toned backdrop, natural warm light, soft grounded shadow, premium editorial background"],
            ["Marble", "a soft marble studio background with subtle veining, controlled daylight, realistic contact shadow, refined ecommerce visual"],
          ],
        },
        {
          group: "Mountain",
          items: [
            ["Sand dunes", "a soft sand dunes landscape with warm natural light, shallow depth, realistic standing contact, outdoor lifestyle fashion background"],
            ["Mountain sunset", "a mountain sunset lifestyle scene with warm rim light, slightly blurred distance, grounded subject area, premium campaign background"],
          ],
        },
        {
          group: "Flower",
          items: [
            ["Tulip studio", "a bright flower studio with tulips and soft cream wall, natural daylight, realistic floor contact, fresh fashion ecommerce background"],
            ["Garden flowers", "a refined garden flower lifestyle scene with soft depth of field, warm daylight, natural ground contact, premium campaign background"],
            ["Floral wall", "a subtle floral wall studio background with gentle color accents, soft shadow, clean subject space, ecommerce portrait background"],
          ],
        },
        {
          group: "Creative",
          items: [
            ["Graffiti", "a tasteful urban graffiti wall with realistic concrete ground, natural street light, grounded shadow, streetwear ecommerce background"],
          ],
        },
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
      themeLibrary: "Background Themes",
      backgroundTab: "Background",
      aiBackgroundsTab: "AI Backgrounds",
      searchBackgrounds: "Search for backgrounds",
      suggestedBackgrounds: "Suggested",
      trendingBackgrounds: "Trending",
      createBackground: "Create a background",
      generateMore: "Generate 2 more",
      editorHome: "Home",
      resize: "Resize",
      editingCanvas: "Editing canvas",
      previewArea: "Previews",
      fixedPreview: "Pinned Preview Area",
      generateCandidates: "Generate 4 Candidates",
      regenerateSelected: "Regenerate Selected",
      applyOne: "Apply To 1 Image",
      applied: "Applied",
      advancedSettings: "Advanced Settings",
      reuseTitle: "Previously Applied Preview",
      noReuse: "No reusable preview yet.",
      candidateEmpty: "Click a background theme on the left; generated full-image previews stay here.",
      candidateLoading: "Generating preview...",
      candidateReady: "Candidate generated. Click to select it.",
      candidateApplied: "Applied this preview configuration. It can now be reused on a new image.",
      reuseApplied: "Copied the previous preview prompt and seed.",
      seedLabel: "Seed",
      selectedTheme: "Selected Theme",
      themeGroups: [
        {
          group: "Mood",
          items: [
            ["Wood", "a warm wood studio interior with natural wooden surfaces, soft daylight, realistic ground contact, premium ecommerce portrait background"],
            ["Minimalist", "a minimalist premium studio with warm neutral walls, subtle tonal gradient, soft floor shadow, uncluttered ecommerce campaign background"],
            ["Snow", "a clean snowy outdoor lifestyle scene with soft overcast light, gentle snow texture, realistic standing contact shadow, fashion ecommerce background"],
            ["Monstera", "a bright botanical interior with monstera leaves, warm daylight, soft wall shadows, realistic floor contact, premium lifestyle background"],
          ],
        },
        {
          group: "Countertop",
          items: [
            ["Stone countertop", "a refined stone countertop and warm wall studio scene, soft daylight, realistic contact shadow, product photography background"],
            ["Kitchen countertop", "a modern kitchen countertop scene with muted cabinets, natural daylight, realistic surface perspective, ecommerce product background"],
            ["Wood countertop", "a warm wood countertop scene with clean wall, soft side light, realistic surface contact and shadow, premium catalog background"],
          ],
        },
        {
          group: "Plant",
          items: [
            ["Indoor plant", "a sunlit indoor plant studio with potted greenery, cream wall, soft floor shadow, realistic portrait-scale lifestyle background"],
            ["Greenhouse", "a calm greenhouse lifestyle scene with layered plants, diffused daylight, realistic depth and ground contact, premium fashion background"],
            ["Plant corner", "a minimal plant corner with warm neutral wall, soft leaves shadows, natural floor contact, clean ecommerce background"],
          ],
        },
        {
          group: "Texture",
          items: [
            ["Soil", "an earthy textured studio scene with soil-toned backdrop, natural warm light, soft grounded shadow, premium editorial background"],
            ["Marble", "a soft marble studio background with subtle veining, controlled daylight, realistic contact shadow, refined ecommerce visual"],
          ],
        },
        {
          group: "Mountain",
          items: [
            ["Sand dunes", "a soft sand dunes landscape with warm natural light, shallow depth, realistic standing contact, outdoor lifestyle fashion background"],
            ["Mountain sunset", "a mountain sunset lifestyle scene with warm rim light, slightly blurred distance, grounded subject area, premium campaign background"],
          ],
        },
        {
          group: "Flower",
          items: [
            ["Tulip studio", "a bright flower studio with tulips and soft cream wall, natural daylight, realistic floor contact, fresh fashion ecommerce background"],
            ["Garden flowers", "a refined garden flower lifestyle scene with soft depth of field, warm daylight, natural ground contact, premium campaign background"],
            ["Floral wall", "a subtle floral wall studio background with gentle color accents, soft shadow, clean subject space, ecommerce portrait background"],
          ],
        },
        {
          group: "Creative",
          items: [
            ["Graffiti", "a tasteful urban graffiti wall with realistic concrete ground, natural street light, grounded shadow, streetwear ecommerce background"],
          ],
        },
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
    if (isBackgroundMode) window.scrollTo(0, 0);
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
            <img id="sandbox-result-summary" alt="${copy.aiResult}" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">
            <span>${copy.empty}</span>
          </article>
        </section>
        <section class="photoroom-stage background-stage is-locked" id="photoroom-background-panel" data-background-stage>
          <div class="photoroom-editor-shell">
            <nav class="photoroom-tool-rail" aria-label="${copy.backgroundTab}">
              <button class="photoroom-tool photoroom-rail-collapse" type="button" data-secondary-collapse aria-label="${copy.resize}">
                <span class="material-symbols-outlined">left_panel_close</span>
                <strong></strong>
              </button>
              <button class="photoroom-tool" type="button" data-editor-tool="home">
                <span class="material-symbols-outlined">home</span>
                <strong>${copy.editorHome}</strong>
              </button>
              <button class="photoroom-tool is-active" type="button" data-editor-tool="background">
                <span class="material-symbols-outlined">wallpaper</span>
                <strong>${copy.backgroundTab}</strong>
              </button>
              <button class="photoroom-tool" type="button" data-editor-tool="resize">
                <span class="material-symbols-outlined">crop_free</span>
                <strong>${copy.resize}</strong>
              </button>
            </nav>
            <aside class="photoroom-bg-drawer">
              <div class="photoroom-drawer-view is-active" data-drawer-view="background">
                <div class="photoroom-drawer-head">
                  <strong>${copy.backgroundTab}</strong>
                  <button class="photoroom-drawer-close" type="button" data-editor-tool="home" aria-label="${copy.editorHome}"><span class="material-symbols-outlined">close</span></button>
                </div>
                <div class="photoroom-bg-tabs" role="tablist">
                  <button class="is-active" type="button">${copy.aiBackgroundsTab}</button>
                  <button type="button">${copy.useReference}</button>
                </div>
                <label class="photoroom-search">
                  <span class="material-symbols-outlined">search</span>
                  <input id="api-background-search" type="search" placeholder="${copy.searchBackgrounds}">
                </label>
                <button class="photoroom-create-bg" type="button" data-create-background>
                  <span class="material-symbols-outlined">auto_awesome</span>
                  <strong>${copy.createBackground}</strong>
                </button>
                <section class="photoroom-bg-section">
                  <div class="photoroom-bg-section-title"><strong>${copy.suggestedBackgrounds}</strong></div>
                  <div class="photoroom-bg-list">
                    ${copy.themeGroups.slice(0, 3).flatMap((group) => group.items).slice(0, 8).map(([label, prompt], itemIndex) => `<button class="preset-chip photoroom-bg-preset ${itemIndex === 0 ? "is-active" : ""}" type="button" data-theme="${escapeHtml(label)}" data-prompt="${escapeHtml(prompt)}"><span></span><strong>${escapeHtml(label)}</strong></button>`).join("")}
                  </div>
                </section>
                <section class="photoroom-bg-section">
                  <div class="photoroom-bg-section-title"><strong>${copy.trendingBackgrounds}</strong></div>
                  <div class="photoroom-bg-list">
                    ${copy.themeGroups.slice(3).flatMap((group) => group.items).map(([label, prompt]) => `<button class="preset-chip photoroom-bg-preset" type="button" data-theme="${escapeHtml(label)}" data-prompt="${escapeHtml(prompt)}"><span></span><strong>${escapeHtml(label)}</strong></button>`).join("")}
                  </div>
                </section>
                <section class="photoroom-bg-section">
                  <div class="photoroom-bg-section-title"><strong>${copy.reuseTitle}</strong><span data-reuse-empty>${copy.noReuse}</span></div>
                  <div class="pr-reuse-list" data-reuse-list></div>
                </section>
              </div>
              <div class="photoroom-drawer-view" data-drawer-view="resize">
                <div class="photoroom-drawer-head">
                  <strong>${copy.resize}</strong>
                  <button class="photoroom-drawer-close" type="button" data-editor-tool="home" aria-label="${copy.editorHome}"><span class="material-symbols-outlined">close</span></button>
                </div>
                <section class="photoroom-resize-section">
                  <button class="photoroom-size-option is-active" type="button" data-aspect-ratio="4:5"><strong>4:5</strong><span>${copy.previewArea}</span></button>
                  <button class="photoroom-size-option" type="button" data-aspect-ratio="1:1"><strong>1:1</strong><span>Square</span></button>
                  <button class="photoroom-size-option" type="button" data-aspect-ratio="3:4"><strong>3:4</strong><span>Portrait</span></button>
                  <button class="photoroom-size-option" type="button" data-aspect-ratio="16:9"><strong>16:9</strong><span>Landscape</span></button>
                </section>
                <div class="photoroom-resize-note">${copy.fixedPreview}</div>
                <div class="photoroom-resize-actions">
                  <button class="primary-pill compact" type="button" data-editor-tool="background"><span class="material-symbols-outlined">wallpaper</span>${copy.backgroundTab}</button>
                </div>
              </div>
            </aside>
            <main class="photoroom-canvas-shell">
              <div class="photoroom-canvas-topbar">
                <button id="sandbox-bg-submit" class="secondary-pill compact photoroom-hidden-action" type="button" disabled><span class="material-symbols-outlined">auto_awesome</span>${copy.generateCandidates}</button>
                <span>${copy.editingCanvas}</span>
                <div class="photoroom-canvas-actions">
                  <button id="sandbox-generate-more" class="secondary-pill compact" type="button" disabled><span class="material-symbols-outlined">add_photo_alternate</span>${copy.generateMore}</button>
                  <a id="sandbox-download-top" class="secondary-pill compact disabled" href="#" download><span class="material-symbols-outlined">download</span>${copy.download}</a>
                </div>
              </div>
              <div class="photoroom-canvas-stage">
                <div class="photoroom-page">
                  <img id="sandbox-result" alt="${copy.aiResult}" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E">
                  <div class="photoroom-canvas-placeholder">
                    <span class="material-symbols-outlined">wallpaper</span>
                    <strong>${copy.candidateEmpty}</strong>
                  </div>
                </div>
              </div>
              <div class="photoroom-variation-strip" data-candidate-grid></div>
              <div class="photoroom-apply-dock">
                <span>${copy.selectedTheme}: <em data-selected-theme>${escapeHtml(copy.themeGroups[0].items[0][0])}</em></span>
                <button id="sandbox-apply-selected" class="primary-pill" type="button" disabled><span class="material-symbols-outlined">done</span>${copy.applyOne}</button>
              </div>
            </main>
          </div>
          <details class="photoroom-advanced">
            <summary>${copy.advancedSettings}</summary>
            <div class="api-form-grid sandbox-fields">
              <label><span>${copy.prompt}</span><input id="api-background-prompt" type="text" value="${escapeHtml(copy.themeGroups[0].items[0][1])}" placeholder="${copy.promptPlaceholder}"></label>
              <label><span>${copy.lighting}</span><select id="api-lighting-mode"><option value="ai.auto">${copy.lightAuto}</option><option value="">${copy.keepOff}</option></select></label>
              <label><span>${copy.shadow}</span><select id="api-shadow-mode"><option value="">${copy.keepOff}</option><option value="ai.soft">${copy.shadowSoft}</option><option value="ai.hard">${copy.shadowHard}</option><option value="ai.floating">${copy.shadowFloating}</option></select></label>
            </div>
            <div class="photoroom-actions">
              <button id="sandbox-regenerate-selected" class="secondary-pill" type="button" disabled><span class="material-symbols-outlined">refresh</span>${copy.regenerateSelected}</button>
              <button id="sandbox-static-submit" class="secondary-pill" type="button" disabled><span class="material-symbols-outlined">wallpaper</span>${copy.useReference}</button>
              <a id="sandbox-download" class="secondary-pill disabled" href="#" download><span class="material-symbols-outlined">download</span>${copy.download}</a>
            </div>
          </details>
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
    const sandboxGenerateMoreButton = apiWorkbench.querySelector("#sandbox-generate-more");
    const sandboxRegenerateButton = apiWorkbench.querySelector("#sandbox-regenerate-selected");
    const sandboxApplyButton = apiWorkbench.querySelector("#sandbox-apply-selected");
    const sandboxStaticButton = apiWorkbench.querySelector("#sandbox-static-submit");
    const sandboxDownload = apiWorkbench.querySelector("#sandbox-download");
    const sandboxDownloadTop = apiWorkbench.querySelector("#sandbox-download-top");
    const apiBackgroundPrompt = apiWorkbench.querySelector("#api-background-prompt");
    const apiLightingMode = apiWorkbench.querySelector("#api-lighting-mode");
    const apiShadowMode = apiWorkbench.querySelector("#api-shadow-mode");
    const backgroundStage = apiWorkbench.querySelector("[data-background-stage]");
    const toolRailButtons = Array.from(apiWorkbench.querySelectorAll(".photoroom-tool[data-editor-tool]"));
    const editorToolTriggers = Array.from(apiWorkbench.querySelectorAll("[data-editor-tool]"));
    const secondaryCollapseButton = apiWorkbench.querySelector("[data-secondary-collapse]");
    const drawerViews = Array.from(apiWorkbench.querySelectorAll("[data-drawer-view]"));
    const resizeButtons = Array.from(apiWorkbench.querySelectorAll("[data-aspect-ratio]"));
    const candidateGrid = apiWorkbench.querySelector("[data-candidate-grid]");
    const reuseList = apiWorkbench.querySelector("[data-reuse-list]");
    const reuseEmpty = apiWorkbench.querySelector("[data-reuse-empty]");
    const selectedThemeLabel = apiWorkbench.querySelector("[data-selected-theme]");
    const stageDots = Array.from(apiWorkbench.querySelectorAll("[data-stage]"));
    const presetChips = Array.from(apiWorkbench.querySelectorAll("[data-prompt]"));
    const previewSeeds = [117879368, 55994449, 48672244, 65080068];
    const reuseStorageKey = "photoroom.appliedPreviewConfigs";
    const state = {
      batchId: `photoroom_batch_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`,
      originalFile: null,
      originalPreviewUrl: "",
      cutoutUrl: "",
      finalUrl: "",
      stage: "upload",
      selectedTheme: copy.themeGroups[0].items[0][0],
      candidates: previewSeeds.map((seed, index) => ({
        id: `candidate_${index + 1}`,
        label: `${index + 1}`,
        seed,
        theme: copy.themeGroups[0].items[0][0],
        prompt: copy.themeGroups[0].items[0][1],
        url: "",
        status: "empty",
      })),
      selectedCandidateId: "candidate_1",
      appliedConfig: null,
      isGenerating: false,
      activeTool: "background",
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
      sandboxCutoutButton.disabled = !hasImage || state.isGenerating;
      sandboxNextButton.disabled = !hasCutout || state.isGenerating;
      sandboxBgButton.disabled = !hasCutout || state.isGenerating;
      if (sandboxGenerateMoreButton) sandboxGenerateMoreButton.disabled = !hasCutout || state.isGenerating;
      if (sandboxRegenerateButton) sandboxRegenerateButton.disabled = !hasCutout || !selectedCandidate() || state.isGenerating;
      if (sandboxApplyButton) sandboxApplyButton.disabled = !selectedCandidate()?.url || state.isGenerating;
      sandboxStaticButton.disabled = !hasCutout || !hasBackgroundFile || state.isGenerating;
      backgroundStage?.classList.toggle("is-locked", !hasCutout);
      sandboxDownload?.classList.toggle("disabled", !state.finalUrl);
      if (sandboxDownload && state.finalUrl) sandboxDownload.href = state.finalUrl;
      sandboxDownloadTop?.classList.toggle("disabled", !state.finalUrl);
      if (sandboxDownloadTop && state.finalUrl) sandboxDownloadTop.href = state.finalUrl;
      apiWorkbench.classList.toggle("is-background-mode", workbenchMode === "ai_background");
      apiWorkbench.classList.toggle("is-cutout-mode", workbenchMode !== "ai_background");
    }

    function setActiveTool(tool) {
      state.activeTool = tool;
      toolRailButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.editorTool === tool);
      });
      drawerViews.forEach((view) => {
        view.classList.toggle("is-active", view.dataset.drawerView === tool);
      });
      apiWorkbench.classList.toggle("is-resize-mode", tool === "resize");
      apiWorkbench.classList.toggle("is-background-drawer", tool === "background");
    }

    function setSecondaryNavCollapsed(collapsed) {
      document.body.classList.toggle("secondary-nav-collapsed", collapsed);
      if (secondaryCollapseButton) {
        secondaryCollapseButton.querySelector(".material-symbols-outlined").textContent = collapsed ? "left_panel_open" : "left_panel_close";
      }
    }

    function resetResults() {
      state.cutoutUrl = "";
      state.finalUrl = "";
      state.isGenerating = false;
      state.appliedConfig = null;
      resetCandidates();
      setImageSource(sandboxCutout, "");
      setImageSource(sandboxResult, "");
      setStage("upload");
      updateControls();
    }

    function selectedCandidate() {
      return state.candidates.find((candidate) => candidate.id === state.selectedCandidateId) || state.candidates[0];
    }

    function resetCandidates() {
      state.candidates = previewSeeds.map((seed, index) => ({
        id: `candidate_${index + 1}`,
        label: `${index + 1}`,
        seed,
        theme: state.selectedTheme,
        prompt: apiBackgroundPrompt?.value.trim() || "",
        url: "",
        status: "empty",
      }));
      state.selectedCandidateId = state.candidates[0]?.id || "";
      renderCandidates();
    }

    function readReuseConfigs() {
      try {
        const payload = JSON.parse(window.localStorage?.getItem(reuseStorageKey) || "[]");
        return Array.isArray(payload) ? payload.filter((item) => item && item.prompt && item.seed).slice(0, 12) : [];
      } catch (_) {
        return [];
      }
    }

    function writeReuseConfig(config) {
      const configs = readReuseConfigs().filter((item) => `${item.theme}-${item.seed}-${item.prompt}` !== `${config.theme}-${config.seed}-${config.prompt}`);
      configs.unshift({ ...config, savedAt: new Date().toISOString() });
      window.localStorage?.setItem(reuseStorageKey, JSON.stringify(configs.slice(0, 12)));
      renderReuseConfigs();
    }

    function renderCandidates() {
      if (!candidateGrid) return;
      candidateGrid.innerHTML = state.candidates.map((candidate) => {
        const selected = candidate.id === state.selectedCandidateId;
        const image = candidate.url
          ? `<img src="${escapeHtml(candidate.url)}" alt="${escapeHtml(candidate.theme)} ${copy.seedLabel} ${candidate.seed}">`
          : `<div class="pr-candidate-empty ${candidate.status === "running" ? "is-loading" : ""}"><span class="material-symbols-outlined">${candidate.status === "running" ? "hourglass_empty" : "image"}</span><em>${candidate.status === "running" ? copy.candidateLoading : copy.candidateEmpty}</em></div>`;
        const status = candidate.status === "running" ? copy.candidateLoading : candidate.url ? copy.candidateReady : `${copy.seedLabel} ${candidate.seed}`;
        return `
          <button class="pr-candidate-card ${selected ? "is-selected" : ""} ${candidate.url ? "has-result" : ""}" type="button" data-candidate-id="${escapeHtml(candidate.id)}">
            ${image}
            <strong>${escapeHtml(candidate.theme)} / ${escapeHtml(candidate.label)}</strong>
            <span>${escapeHtml(status)}</span>
          </button>
        `;
      }).join("");
      candidateGrid.querySelectorAll("[data-candidate-id]").forEach((card) => {
        card.addEventListener("click", () => {
          state.selectedCandidateId = card.dataset.candidateId || state.selectedCandidateId;
          const candidate = selectedCandidate();
          if (candidate?.url) {
            state.finalUrl = candidate.url;
            setImageSource(sandboxResult, candidate.url);
            if (sandboxDownload) sandboxDownload.href = candidate.url;
            if (sandboxDownloadTop) sandboxDownloadTop.href = candidate.url;
          } else if (state.cutoutUrl && !state.isGenerating) {
            generateCandidate(candidate);
          }
          renderCandidates();
          updateControls();
        });
      });
    }

    function renderReuseConfigs() {
      if (!reuseList) return;
      const configs = readReuseConfigs();
      if (reuseEmpty) reuseEmpty.hidden = configs.length > 0;
      reuseList.innerHTML = configs.map((config, index) => `
        <button class="pr-reuse-card" type="button" data-reuse-index="${index}">
          ${config.url ? `<img src="${escapeHtml(config.url)}" alt="${escapeHtml(config.theme || copy.reuseTitle)}">` : ""}
          <strong>${escapeHtml(config.theme || copy.reuseTitle)}</strong>
          <span>${copy.seedLabel} ${escapeHtml(config.seed)}</span>
        </button>
      `).join("");
      reuseList.querySelectorAll("[data-reuse-index]").forEach((card) => {
        card.addEventListener("click", () => {
          const config = configs[Number(card.dataset.reuseIndex || 0)];
          if (!config) return;
          state.selectedTheme = config.theme || state.selectedTheme;
          if (selectedThemeLabel) selectedThemeLabel.textContent = state.selectedTheme;
          if (apiBackgroundPrompt) apiBackgroundPrompt.value = config.prompt || "";
          state.candidates = previewSeeds.map((seed, index) => ({
            id: `candidate_${index + 1}`,
            label: `${index + 1}`,
            seed,
            theme: state.selectedTheme,
            prompt: apiBackgroundPrompt?.value.trim() || "",
            url: "",
            status: "empty",
          }));
          const matched = state.candidates.find((candidate) => candidate.seed === Number(config.seed));
          state.selectedCandidateId = matched?.id || state.candidates[0]?.id || "";
          state.finalUrl = "";
          setImageSource(sandboxResult, "");
          presetChips.forEach((chip) => chip.classList.toggle("is-active", chip.dataset.theme === state.selectedTheme));
          renderCandidates();
          updateControls();
          setStatus(copy.reuseApplied, "ok");
          if (state.cutoutUrl && !state.isGenerating) {
            generateCandidate(selectedCandidate());
          }
        });
      });
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

    async function callPhotoRoomSandbox(mode, options = {}) {
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
      if (options.seed) formData.append("background_seed", String(options.seed));
      formData.append("background_theme", options.theme || state.selectedTheme || "");
      formData.append("candidate_label", options.label || "");
      formData.append("lighting_mode", apiLightingMode?.value || "");
      formData.append("shadow_mode", apiShadowMode?.value || "");
      if (sandboxBackgroundImage?.files?.[0]) {
        formData.append("background_image", sandboxBackgroundImage.files[0]);
      }

      const isCutout = mode === "remove_background";
      const activeButton = isCutout ? sandboxCutoutButton : mode === "background_image" ? sandboxStaticButton : sandboxBgButton;
      const activeText = isCutout ? copy.runningCutout : copy.runningBackground;
      state.isGenerating = true;
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
          if (options.candidateId) {
            const candidate = state.candidates.find((item) => item.id === options.candidateId);
            if (candidate) {
              candidate.url = versionedUrl;
              candidate.status = "generated";
              candidate.prompt = apiBackgroundPrompt?.value.trim() || candidate.prompt;
              candidate.theme = state.selectedTheme;
              candidate.seed = options.seed || candidate.seed;
              state.selectedCandidateId = candidate.id;
              renderCandidates();
            }
          }
        }
      } catch (error) {
        setApiResult({ ok: false, error: String(error) });
        setStatus(String(error), "error");
      } finally {
        state.isGenerating = false;
        sandboxCutoutButton.innerHTML = `<span class="material-symbols-outlined">layers_clear</span>${copy.startCutout}`;
        sandboxBgButton.innerHTML = `<span class="material-symbols-outlined">auto_awesome</span>${copy.generateCandidates}`;
        if (sandboxGenerateMoreButton) sandboxGenerateMoreButton.innerHTML = `<span class="material-symbols-outlined">add_photo_alternate</span>${copy.generateMore}`;
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
        state.selectedTheme = chip.dataset.theme || chip.textContent.trim();
        if (selectedThemeLabel) selectedThemeLabel.textContent = state.selectedTheme;
        apiBackgroundPrompt.value = chip.dataset.prompt || "";
        resetCandidates();
        if (state.cutoutUrl && !state.isGenerating) {
          generateAllCandidates();
        }
      });
    });

    async function generateCandidate(candidate) {
      if (!candidate) return;
      candidate.status = "running";
      candidate.prompt = apiBackgroundPrompt?.value.trim() || candidate.prompt;
      candidate.theme = state.selectedTheme;
      state.selectedCandidateId = candidate.id;
      renderCandidates();
      await callPhotoRoomSandbox("ai_background", {
        candidateId: candidate.id,
        seed: candidate.seed,
        theme: candidate.theme,
        label: candidate.label,
      });
      if (!candidate.url) {
        candidate.status = "empty";
        renderCandidates();
      }
    }

    async function generateAllCandidates() {
      for (const candidate of state.candidates) {
        await generateCandidate(candidate);
        if (!candidate.url) break;
      }
    }

    function applySelectedCandidate() {
      const candidate = selectedCandidate();
      if (!candidate?.url) return;
      state.finalUrl = candidate.url;
      state.appliedConfig = {
        theme: candidate.theme,
        prompt: candidate.prompt || apiBackgroundPrompt?.value.trim() || "",
        seed: candidate.seed,
        label: candidate.label,
        url: candidate.url,
        lightingMode: apiLightingMode?.value || "",
        shadowMode: apiShadowMode?.value || "",
      };
      setImageSource(sandboxResult, candidate.url);
      if (sandboxDownloadTop) sandboxDownloadTop.href = candidate.url;
      setStage("final");
      writeReuseConfig(state.appliedConfig);
      setStatus(copy.candidateApplied, "ok");
      updateControls();
    }

    sandboxCutoutButton?.addEventListener("click", () => callPhotoRoomSandbox("remove_background"));
    sandboxLatestButton?.addEventListener("click", loadLatestCutout);
    sandboxNextButton?.addEventListener("click", () => {
      setStage("background");
      backgroundStage?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    sandboxBgButton?.addEventListener("click", generateAllCandidates);
    sandboxGenerateMoreButton?.addEventListener("click", async () => {
      const startIndex = Math.max(0, state.candidates.findIndex((candidate) => !candidate.url));
      const targets = state.candidates.slice(startIndex, startIndex + 2);
      for (const candidate of targets.length ? targets : state.candidates.slice(0, 2)) {
        await generateCandidate(candidate);
      }
    });
    sandboxRegenerateButton?.addEventListener("click", () => generateCandidate(selectedCandidate()));
    sandboxApplyButton?.addEventListener("click", applySelectedCandidate);
    sandboxStaticButton?.addEventListener("click", () => callPhotoRoomSandbox("background_image"));
    sandboxForm?.addEventListener("submit", (event) => event.preventDefault());
    providerRefresh?.addEventListener("click", refreshProviderStatus);
    secondaryCollapseButton?.addEventListener("click", () => {
      setSecondaryNavCollapsed(!document.body.classList.contains("secondary-nav-collapsed"));
    });
    editorToolTriggers.forEach((button) => {
      button.addEventListener("click", () => {
        const tool = button.dataset.editorTool || "background";
        if (tool === "home") {
          window.location.href = `/?lang=${lang}`;
          return;
        }
        if (document.body.classList.contains("secondary-nav-collapsed")) {
          setSecondaryNavCollapsed(false);
        }
        setActiveTool(tool);
        if (tool === "background") {
          backgroundStage?.classList.remove("is-resize-focus");
        }
      });
    });
    resizeButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const ratio = button.dataset.aspectRatio || "4:5";
        resizeButtons.forEach((item) => item.classList.toggle("is-active", item === button));
        const [width, height] = ratio.split(":").map(Number);
        const safeWidth = Number.isFinite(width) && width > 0 ? width : 4;
        const safeHeight = Number.isFinite(height) && height > 0 ? height : 5;
        const aspect = `${safeWidth} / ${safeHeight}`;
        const page = apiWorkbench.querySelector(".photoroom-page");
        if (page) page.style.aspectRatio = aspect;
        setStatus(`${copy.resize}: ${ratio}`, "ok");
      });
    });

    refreshProviderStatus();
    renderCandidates();
    renderReuseConfigs();
    updateControls();

    if (workbenchMode === "ai_background") {
      setActiveTool("background");
      setStage("background");
      loadLatestCutout();
    } else if (location.hash === "#photoroom-background") {
      setActiveTool("background");
      setStage("background");
      backgroundStage?.scrollIntoView({ behavior: "smooth", block: "center" });
    } else if (location.hash === "#photoroom-cutout") {
      setActiveTool("background");
      setStage("cutout");
      apiWorkbench.querySelector("#photoroom-cutout-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      setActiveTool("background");
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
