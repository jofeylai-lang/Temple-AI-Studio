import { platforms } from "./fixtures.js";
import {
  approvePreview,
  buildPreviewPackage,
  createDraftProject,
  pipelineStages,
  prepareExportPackage,
  providerRegistry,
  regenerateScene,
  validateProjectInput
} from "./pipeline.js";
import {
  createProjectId,
  getSelectedProduct,
  loadState,
  resetState,
  saveState
} from "./state.js";

const app = document.querySelector("#app");
const screenTitle = document.querySelector("#screen-title");
const statusStrip = document.querySelector("#status-strip");
const navItems = [...document.querySelectorAll(".nav-item")];

let state = loadState();
let route = normalizeRoute(location.hash.replace("#", "") || "home");
let progressTimer = null;

if (new URLSearchParams(location.search).get("demo") === "generated") {
  ensureGeneratedDemo();
}

render();

window.addEventListener("hashchange", () => {
  route = normalizeRoute(location.hash.replace("#", "") || "home");
  render();
});

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action], [data-route]");
  if (!target) return;

  if (target.dataset.route) {
    navigate(target.dataset.route);
    return;
  }

  handleAction(target.dataset.action, target);
});

document.addEventListener("change", (event) => {
  if (event.target.matches("[data-select-product]")) {
    state.selectedProductId = event.target.value;
    state.lastNotice = "Selected product updated.";
    saveAndRender();
  }
});

function handleAction(action, target) {
  const product = getSelectedProduct(state);

  if (action === "reset-demo") {
    state = resetState();
    navigate("home");
    return;
  }

  if (action === "save-product") {
    const form = target.closest("form");
    const formData = new FormData(form);
    const id = `product-${Date.now()}`;
    state.products = [
      ...state.products,
      {
        id,
        name: formData.get("name").trim(),
        category: formData.get("category").trim(),
        description: formData.get("description").trim(),
        sellingPoint: formData.get("sellingPoint").trim(),
        mainImage: formData.get("mainImage").trim(),
        tags: []
      }
    ];
    state.selectedProductId = id;
    state.lastNotice = "Product saved to library.";
    saveAndRender();
    return;
  }

  if (action === "start-create") {
    navigate("create");
    return;
  }

  if (action === "select-product") {
    state.selectedProductId = target.dataset.productId;
    state.lastNotice = "Product selected.";
    saveState(state);
    navigate("create");
    return;
  }

  if (action === "start-generation") {
    const form = document.querySelector("#create-form");
    const formData = new FormData(form);
    const draft = {
      targetPlatform: formData.get("targetPlatform"),
      tone: formData.get("tone"),
      lengthTarget: formData.get("lengthTarget"),
      materialNotes: formData.get("materialNotes"),
      chineseDescription: formData.get("chineseDescription")
    };
    const validation = validateProjectInput(product, draft);

    if (!validation.ok) {
      renderValidationErrors(validation.errors);
      return;
    }

    state.currentProject = createDraftProject(product, draft, createProjectId());
    state.progressIndex = 0;
    state.exportPackage = null;
    state.lastNotice = "Generation pipeline started.";
    saveState(state);
    navigate("progress");
    startProgress();
    return;
  }

  if (action === "complete-generation") {
    finishGeneration();
    return;
  }

  if (action === "approve-preview") {
    state.currentProject = approvePreview(state.currentProject);
    state.lastNotice = "Preview approved.";
    saveAndRender();
    return;
  }

  if (action === "open-scene") {
    state.selectedSceneId = target.dataset.sceneId;
    saveState(state);
    navigate("scene");
    return;
  }

  if (action === "regenerate-scene") {
    const sceneId = target.dataset.sceneId || state.selectedSceneId;
    state.currentProject = regenerateScene(state.currentProject, sceneId);
    state.selectedSceneId = sceneId;
    state.lastNotice = "Scene regenerated as a placeholder version.";
    saveAndRender();
    return;
  }

  if (action === "prepare-export") {
    const result = prepareExportPackage(state.currentProject);
    if (!result.ok) {
      state.lastNotice = result.reason;
      saveAndRender();
      return;
    }
    state.exportPackage = result.package;
    state.currentProject = {
      ...state.currentProject,
      reviewStatus: "Exported",
      metadata: {
        ...state.currentProject.metadata,
        exportStatus: "Prepared Placeholder"
      }
    };
    state.lastNotice = "Export package prepared.";
    saveAndRender();
  }
}

function startProgress() {
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    state.progressIndex += 1;
    if (state.progressIndex >= pipelineStages.length) {
      clearInterval(progressTimer);
      finishGeneration();
      return;
    }
    saveAndRender();
  }, 650);
}

function finishGeneration() {
  const product = getSelectedProduct(state);
  state.progressIndex = pipelineStages.length;
  state.currentProject = buildPreviewPackage(state.currentProject, product);
  state.lastNotice = "Preview package is ready.";
  saveState(state);
  navigate("preview");
}

function ensureGeneratedDemo() {
  const product = getSelectedProduct(state);
  if (!state.currentProject?.preview) {
    const project = createDraftProject(
      product,
      {
        targetPlatform: "Instagram Reels",
        tone: "Calm, warm, premium",
        lengthTarget: "30 seconds",
        materialNotes: "Main product photo plus optional packaging reference.",
        chineseDescription: "請幫我做一支溫柔、有儀式感的產品短影片，適合社群發布。"
      },
      "tpvg-alpha-demo"
    );
    state.currentProject = buildPreviewPackage(project, product);
    state.progressIndex = pipelineStages.length;
    state.lastNotice = "Generated demo loaded.";
    saveState(state);
  }
}

function render() {
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.route === route));
  screenTitle.textContent = titleForRoute(route);
  statusStrip.innerHTML = renderStatus();

  const screens = {
    home: renderHome,
    library: renderLibrary,
    create: renderCreate,
    progress: renderProgress,
    preview: renderPreview,
    scene: renderSceneDetail,
    export: renderExport
  };

  app.innerHTML = screens[route]();
  app.focus({ preventScroll: true });
}

function renderStatus() {
  const project = state.currentProject;
  return [
    `<span class="pill">Branch: main</span>`,
    `<span class="pill ${project?.reviewStatus === "Exported" ? "ok" : ""}">Status: ${project?.reviewStatus || "No active project"}</span>`,
    `<span class="pill">Project: ${project?.id || "None"}</span>`
  ].join("");
}

function renderHome() {
  const product = getSelectedProduct(state);
  return `
    <section class="grid two">
      <div class="panel">
        <h2>Start one Temple product video</h2>
        <p class="muted">This Alpha converts the approved V1 workflow into a runnable prototype. AI generation is simulated, but navigation, validation, scenes, review, regeneration, and export states are real in the browser.</p>
        <div class="actions">
          <button class="button" data-action="start-create">Start New Product Video</button>
          <button class="button secondary" data-route="library">Open Product Library</button>
          <button class="button secondary" data-route="preview">Review Preview</button>
        </div>
      </div>
      <div class="panel">
        <h3>Current product</h3>
        <p><strong>${escapeHtml(product.name)}</strong></p>
        <p class="muted">${escapeHtml(product.description)}</p>
        <p><strong>Main selling point:</strong> ${escapeHtml(product.sellingPoint)}</p>
      </div>
    </section>
    <section class="grid three" style="margin-top:18px">
      ${renderMetric("Products", state.products.length)}
      ${renderMetric("Scenes", state.currentProject?.scenes?.length || 0)}
      ${renderMetric("Providers Prepared", providerRegistry.length)}
    </section>
  `;
}

function renderLibrary() {
  return `
    <section class="grid two">
      <div class="panel">
        <h2>Product Library</h2>
        <p class="muted">Choose the product identity before creating a video.</p>
        <div class="list">
          ${state.products.map((product) => `
            <article class="list-item">
              <div>
                <h3>${escapeHtml(product.name)}</h3>
                <p class="muted">${escapeHtml(product.category)} - ${escapeHtml(product.description)}</p>
                <p><strong>Selling point:</strong> ${escapeHtml(product.sellingPoint)}</p>
              </div>
              <button class="button secondary" data-action="select-product" data-product-id="${product.id}">Use</button>
            </article>
          `).join("")}
        </div>
      </div>
      <form class="panel form-grid">
        <h2>Add product</h2>
        ${field("Product name", "name", "Temple Ritual Oil")}
        ${field("Category", "category", "Ritual product")}
        ${textarea("Product description", "description", "A product prepared for calm daily ritual.")}
        ${textarea("Main selling point", "sellingPoint", "Makes it easier to create a clear and focused moment.")}
        ${field("Main image reference", "mainImage", "materials/product-main.jpg")}
        <button class="button" type="button" data-action="save-product">Save Product</button>
      </form>
    </section>
  `;
}

function renderCreate() {
  const product = getSelectedProduct(state);
  return `
    <section class="grid two">
      <form id="create-form" class="panel form-grid">
        <h2>Create Video</h2>
        <div class="field">
          <label>Selected product</label>
          <select data-select-product>
            ${state.products.map((item) => `<option value="${item.id}" ${item.id === product.id ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>Target platform</label>
          <select name="targetPlatform">
            ${platforms.map((platform) => `<option>${platform}</option>`).join("")}
          </select>
        </div>
        ${field("Tone", "tone", "Calm, warm, premium")}
        ${field("Length target", "lengthTarget", "30 seconds")}
        ${textarea("Photos / materials notes", "materialNotes", "Use the main product photo and keep product identity stable.")}
        ${textarea("Chinese description", "chineseDescription", "請幫我做一支溫柔、有儀式感的產品短影片，適合社群發布。")}
        <div id="validation-errors"></div>
        <div class="actions">
          <button class="button" type="button" data-action="start-generation">Start Generation</button>
          <button class="button secondary" type="button" data-route="library">Change Product</button>
        </div>
      </form>
      <aside class="panel">
        <h2>Input readiness</h2>
        <table class="table">
          <tbody>
            ${readinessRow("Product name", product.name)}
            ${readinessRow("Description", product.description)}
            ${readinessRow("Selling point", product.sellingPoint)}
            ${readinessRow("Main image", product.mainImage)}
            ${readinessRow("Output format", "Vertical 9:16, manual posting")}
          </tbody>
        </table>
      </aside>
    </section>
  `;
}

function renderProgress() {
  const complete = Math.min(state.progressIndex, pipelineStages.length);
  const percent = Math.round((complete / pipelineStages.length) * 100);
  return `
    <section class="grid two">
      <div class="panel">
        <h2>Generation Progress</h2>
        <p class="muted">The Alpha simulates the V1 reasoning pipeline without calling paid APIs or local AI engines.</p>
        <div class="progress-bar" aria-label="Progress"><span style="width:${percent}%"></span></div>
        <p style="margin-top:12px"><strong>${percent}% complete</strong></p>
        <div class="list">
          ${pipelineStages.map((step, index) => `
            <div class="step ${index < complete ? "done" : ""} ${index === complete ? "active" : ""}">
              <span class="step-index">${index + 1}</span>
              <div>
                <strong>${step.name}</strong>
                <p class="muted">${step.description}</p>
              </div>
            </div>
          `).join("")}
        </div>
        <div class="actions" style="margin-top:16px">
          <button class="button" data-action="complete-generation">Complete Demo Generation</button>
          <button class="button secondary" data-route="create">Back to Create Video</button>
        </div>
      </div>
      <aside class="panel">
        <h2>Provider slots</h2>
        <div class="list">
          ${providerRegistry.map((provider) => `
            <article class="card">
              <h3>${provider.name}</h3>
              <p class="muted">${provider.role}</p>
              <span class="pill warn">${provider.status}</span>
            </article>
          `).join("")}
        </div>
      </aside>
    </section>
  `;
}

function renderPreview() {
  const project = state.currentProject;
  if (!project?.preview) return renderEmpty("No preview yet.", "Create a video first.", "create");

  return `
    <section class="grid two">
      <div class="panel">
        <h2>Preview</h2>
        <div class="placeholder-video">
          <div>
            <strong>${escapeHtml(project.preview.title)}</strong>
            <span>${escapeHtml(project.targetPlatform)} placeholder preview</span>
          </div>
        </div>
      </div>
      <aside class="panel">
        <h2>Review package</h2>
        <p><strong>Caption:</strong> ${escapeHtml(project.preview.caption)}</p>
        <p><strong>Thumbnail:</strong> ${escapeHtml(project.preview.thumbnailSuggestion)}</p>
        <p><strong>Review status:</strong> ${escapeHtml(project.reviewStatus)}</p>
        <div class="actions">
          <button class="button" data-action="approve-preview">Approve Preview</button>
          <button class="button secondary" data-route="export">Go to Export</button>
        </div>
      </aside>
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Scenes</h2>
      <div class="list">
        ${project.scenes.map((scene) => renderSceneRow(scene)).join("")}
      </div>
    </section>
  `;
}

function renderSceneDetail() {
  const project = state.currentProject;
  if (!project?.scenes?.length) return renderEmpty("No scene yet.", "Generate a preview first.", "create");

  const scene = project.scenes.find((item) => item.id === state.selectedSceneId) || project.scenes[0];
  return `
    <section class="grid two">
      <div class="panel">
        <h2>Scene Detail</h2>
        <p class="muted">Scene-level review and regeneration are isolated from the full video.</p>
        <table class="table">
          <tbody>
            <tr><th>Purpose</th><td>${escapeHtml(scene.purpose)}</td></tr>
            <tr><th>Duration</th><td>${scene.duration} seconds</td></tr>
            <tr><th>Version</th><td>${scene.version}</td></tr>
            <tr><th>Status</th><td>${escapeHtml(scene.status)}</td></tr>
            <tr><th>Visual</th><td>${escapeHtml(scene.visualDescription)}</td></tr>
            <tr><th>Narration</th><td>${escapeHtml(scene.narration)}</td></tr>
            <tr><th>Subtitle</th><td>${escapeHtml(scene.subtitle)}</td></tr>
            <tr><th>Prompt direction</th><td>${escapeHtml(scene.promptDirection)}</td></tr>
            <tr><th>Music</th><td>${escapeHtml(scene.music)}</td></tr>
            <tr><th>Transition</th><td>${escapeHtml(scene.transition)}</td></tr>
          </tbody>
        </table>
        <div class="actions" style="margin-top:16px">
          <button class="button warning" data-action="regenerate-scene" data-scene-id="${scene.id}">Regenerate This Scene</button>
          <button class="button secondary" data-route="preview">Back to Preview</button>
        </div>
      </div>
      <aside class="panel">
        <h2>Scene list</h2>
        <div class="list">
          ${project.scenes.map((item) => `
            <button class="nav-item ${item.id === scene.id ? "active" : ""}" data-action="open-scene" data-scene-id="${item.id}">${item.order}. ${escapeHtml(item.purpose)}</button>
          `).join("")}
        </div>
      </aside>
    </section>
  `;
}

function renderExport() {
  const project = state.currentProject;
  if (!project?.preview) return renderEmpty("No export package yet.", "Create and approve a preview first.", "create");

  const canExport = project.reviewStatus === "Approved" || project.reviewStatus === "Exported";
  return `
    <section class="grid two">
      <div class="panel">
        <h2>Export</h2>
        ${canExport ? "" : `<div class="notice"><strong>Preview approval required.</strong><br>Approve the preview before preparing the export package.</div>`}
        <table class="table" style="margin-top:16px">
          <tbody>
            <tr><th>Project</th><td>${escapeHtml(project.id)}</td></tr>
            <tr><th>Target platform</th><td>${escapeHtml(project.targetPlatform)}</td></tr>
            <tr><th>Format</th><td>Vertical 9:16 MP4 placeholder</td></tr>
            <tr><th>Caption</th><td>${escapeHtml(project.preview.caption)}</td></tr>
            <tr><th>Subtitles</th><td>${project.scenes.length} subtitle lines prepared</td></tr>
            <tr><th>Metadata</th><td>${project.metadata ? "Ready" : "Missing"}</td></tr>
          </tbody>
        </table>
        <div class="actions" style="margin-top:16px">
          <button class="button" data-action="prepare-export" ${canExport ? "" : "disabled"}>Prepare Export Package</button>
          <button class="button secondary" data-route="preview">Back to Preview</button>
        </div>
      </div>
      <aside class="panel">
        <h2>Export result</h2>
        ${state.exportPackage ? renderExportPackage(state.exportPackage) : `<p class="muted">No export package prepared yet.</p>`}
      </aside>
    </section>
  `;
}

function renderSceneRow(scene) {
  return `
    <article class="scene-row">
      <span class="pill">${scene.order}. ${scene.duration}s</span>
      <div>
        <h3>${escapeHtml(scene.purpose)}</h3>
        <p class="muted">${escapeHtml(scene.visualDescription)}</p>
        <p><strong>Subtitle:</strong> ${escapeHtml(scene.subtitle)}</p>
      </div>
      <div class="actions">
        <button class="button secondary" data-action="open-scene" data-scene-id="${scene.id}">Open</button>
        <button class="button secondary" data-action="regenerate-scene" data-scene-id="${scene.id}">Regenerate</button>
      </div>
    </article>
  `;
}

function renderExportPackage(pack) {
  return `
    <table class="table">
      <tbody>
        <tr><th>Status</th><td>${escapeHtml(pack.status)}</td></tr>
        <tr><th>Final MP4</th><td>${escapeHtml(pack.finalMp4Reference)}</td></tr>
        <tr><th>Caption</th><td>${escapeHtml(pack.captionReference)}</td></tr>
        <tr><th>Subtitles</th><td>${escapeHtml(pack.subtitleReference)}</td></tr>
        <tr><th>Metadata</th><td>${escapeHtml(pack.metadataReference)}</td></tr>
      </tbody>
    </table>
  `;
}

function renderMetric(label, value) {
  return `
    <div class="card">
      <p class="muted">${label}</p>
      <h2>${value}</h2>
    </div>
  `;
}

function renderEmpty(title, message, destination) {
  return `
    <section class="panel">
      <h2>${title}</h2>
      <p class="muted">${message}</p>
      <button class="button" data-route="${destination}">Continue</button>
    </section>
  `;
}

function renderValidationErrors(errors) {
  const container = document.querySelector("#validation-errors");
  container.innerHTML = `
    <div class="notice error-list">
      <strong>Required information is missing:</strong>
      <ul>${errors.map((error) => `<li>${escapeHtml(error)}</li>`).join("")}</ul>
    </div>
  `;
}

function field(label, name, value) {
  return `
    <div class="field">
      <label>${label}</label>
      <input name="${name}" value="${escapeHtml(value)}">
    </div>
  `;
}

function textarea(label, name, value) {
  return `
    <div class="field">
      <label>${label}</label>
      <textarea name="${name}">${escapeHtml(value)}</textarea>
    </div>
  `;
}

function readinessRow(label, value) {
  return `<tr><th>${label}</th><td>${value ? escapeHtml(value) : "<span class='error-list'>Missing</span>"}</td></tr>`;
}

function navigate(nextRoute) {
  location.hash = normalizeRoute(nextRoute);
}

function normalizeRoute(nextRoute) {
  const allowed = ["home", "library", "create", "progress", "preview", "scene", "export"];
  return allowed.includes(nextRoute) ? nextRoute : "home";
}

function titleForRoute(currentRoute) {
  const titles = {
    home: "Home",
    library: "Product Library",
    create: "Create Video",
    progress: "Generation Progress",
    preview: "Preview",
    scene: "Scene Detail",
    export: "Export"
  };
  return titles[currentRoute] || "Temple Product Video Generator";
}

function saveAndRender() {
  saveState(state);
  render();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
