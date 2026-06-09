(() => {
  const fileInput = document.getElementById("file-input");
  const uploadZone = document.getElementById("upload-zone");
  const fileSummary = document.getElementById("file-summary");
  const fileList = document.getElementById("file-list");
  const form = document.getElementById("upload-form");
  const submitButton = document.getElementById("submit-button");
  const maxImages = Number(document.body.dataset.maxImages || 8);
  const lang = document.body.dataset.lang === "en" ? "en" : "zh";
  const copy = {
    zh: {
      none: "\u5c1a\u672a\u9009\u62e9\u56fe\u7247\u3002",
      selected: (count) => `\u5df2\u9009\u62e9 ${count} \u5f20\u56fe\u7247\uff0c\u9700\u8981\u6b63\u597d ${maxImages} \u5f20\u3002`,
      invalid: (count) => `\u5f53\u524d\u9009\u62e9 ${count} \u5f20\uff0c\u8bf7\u4e00\u6b21\u4e0a\u4f20 ${maxImages} \u5f20\u56fe\u7247\u3002`,
      uploading: "\u6b63\u5728\u4e0a\u4f20\u5e76\u542f\u52a8\u751f\u6210",
      progress: (done, total, progress) => `> \u8fdb\u5ea6\u66f4\u65b0\uff1a${done}/${total} \u5f20\uff0c${progress}%`,
    },
    en: {
      none: "No images selected.",
      selected: (count) => `Selected ${count} images. Exactly ${maxImages} are required.`,
      invalid: (count) => `Selected ${count}. Please upload exactly ${maxImages} images.`,
      uploading: "Uploading and starting generation",
      progress: (done, total, progress) => `> Progress updated: ${done}/${total} assets, ${progress}%`,
    }
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
      if (count !== maxImages) {
        event.preventDefault();
        fileSummary.textContent = copy.invalid(count);
        return;
      }
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="material-symbols-outlined">hourglass_empty</span>' + copy.uploading;
    });
  }

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
