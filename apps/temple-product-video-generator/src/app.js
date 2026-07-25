const app = document.querySelector("#app");
const title = document.querySelector("#screen-title");
const statusStrip = document.querySelector("#status-strip");
const navItems = [...document.querySelectorAll(".nav-item")];

let route = normalizeRoute(location.hash.replace("#", "") || "home");
let state = {
  db: { products: [], projects: [], jobs: [] },
  config: {},
  health: {},
  selectedProductId: "",
  selectedProjectId: "",
  selectedSceneId: "",
  selectedJobId: sessionStorage.getItem("tpvg-selected-job") || "",
  createMode: "product",
  formErrors: {},
  apiOnline: true,
  submitting: false,
  busy: false,
  notice: "正在載入系統資料..."
};

window.addEventListener("hashchange", () => {
  route = normalizeRoute(location.hash.replace("#", "") || "home");
  render();
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action], [data-route]");
  if (!target || state.busy) return;
  if (target.dataset.route) {
    navigate(target.dataset.route);
    return;
  }
  await handleAction(target.dataset.action, target);
});

document.addEventListener("change", async (event) => {
  if (event.target.matches("[data-product-select]")) {
    state.selectedProductId = event.target.value;
    state.notice = "已切換商品。";
    render();
  }
  if (event.target.matches("[data-create-mode]")) {
    state.createMode = event.target.value;
    state.formErrors = {};
    state.notice = state.createMode === "text-only"
      ? "已切換為純文字模式，不需要商品或照片。"
      : "已切換為商品影片模式。";
    render();
  }
  if (event.target.matches("[data-project-select]")) {
    state.selectedProjectId = event.target.value;
    const project = getProject();
    state.selectedSceneId = project?.scenes?.[0]?.id || "";
    state.notice = "已切換影片專案。";
    render();
  }
  if (event.target.matches("[data-job-select]")) {
    state.selectedJobId = event.target.value;
    sessionStorage.setItem("tpvg-selected-job", event.target.value);
    const job = getJob();
    if (job?.projectId) state.selectedProjectId = job.projectId;
    state.notice = "已切換生成工作。";
    render();
  }
  if (event.target.matches("[data-replace-material]")) {
    await replaceMaterial(event.target);
  }
  if (event.target.matches("#restore-file")) {
    state.notice = event.target.files.length ? "已選擇備份檔，請輸入 RESTORE 後再還原。" : "尚未選擇備份檔。";
    render();
  }
  if (event.target.matches("#product-import-file")) {
    await importProduct(event.target);
  }
});

boot();
setInterval(refreshLiveState, 1000);

async function boot() {
  try {
    await refreshState();
    const product = getProduct();
    const project = getProject();
    state.selectedProductId ||= product?.id || "";
    state.selectedProjectId ||= project?.id || "";
    state.selectedSceneId ||= project?.scenes?.[0]?.id || "";
    state.notice = state.db.products.length
      ? "系統已就緒。"
      : "目前尚無商品，可建立第一個商品或直接使用純文字模式。";
  } catch (error) {
    state.apiOnline = false;
    state.notice = `後端無法連線：${error.message}`;
  }
  render();
}

async function refreshState() {
  const payload = await api("/api/state");
  state.db = payload.db;
  state.config = payload.config;
  state.health = payload.health;
  state.apiOnline = true;
  if (!state.selectedProductId && state.db.products[0]) state.selectedProductId = state.db.products[0].id;
  if (!state.selectedProjectId && state.db.projects[0]) state.selectedProjectId = state.db.projects.at(-1).id;
  const activeJob = [...(state.db.jobs || [])]
    .reverse()
    .find((item) => ["queued", "running", "cancelling"].includes(item.status));
  const selectedJob = state.db.jobs?.find((item) => item.id === state.selectedJobId);
  if (activeJob && (!selectedJob || ["completed", "failed", "cancelled"].includes(selectedJob.status))) {
    state.selectedJobId = activeJob.id;
    sessionStorage.setItem("tpvg-selected-job", activeJob.id);
  }
  const job = getJob();
  if (job?.projectId) state.selectedProjectId = job.projectId;
}

async function refreshLiveState() {
  const job = getJob();
  const shouldPoll = route === "progress" || ["queued", "running", "cancelling"].includes(job?.status);
  if (!shouldPoll || state.busy) return;
  try {
    await refreshState();
    render();
  } catch (error) {
    state.apiOnline = false;
    state.notice = `進度連線中斷：${error.message}。系統會自動重試。`;
    render();
  }
}

async function handleAction(action, target) {
  try {
    setBusy(true);
    if (action === "save-product") await saveProduct();
    if (action === "start-first-product") navigate("library");
    if (action === "use-text-only") {
      state.createMode = "text-only";
      navigate("create");
    }
    if (action === "update-product") await updateProduct();
    if (action === "delete-product") await deleteProduct(target.dataset.productId);
    if (action === "upload-materials") await uploadMaterials(target.dataset.kind || "image", target.dataset.input || "material-files");
    if (action === "delete-material") await deleteMaterial(target.dataset.productId, target.dataset.materialId);
    if (action === "move-material") await moveMaterial(target.dataset.productId, target.dataset.materialId, target.dataset.direction);
    if (action === "create-project") await createProject();
    if (action === "cancel-job") await cancelJob(target.dataset.jobId);
    if (action === "retry-job") await retryJob(target.dataset.jobId);
    if (action === "open-output") await openOutput(target.dataset.path);
    if (action === "create-next") {
      state.selectedJobId = "";
      state.formErrors = {};
      navigate("create");
    }
    if (action === "run-demo") await runDemo();
    if (action === "open-project") openProject(target.dataset.projectId);
    if (action === "delete-project") await deleteProject(target.dataset.projectId);
    if (action === "cancel-project") await cancelProject(target.dataset.projectId);
    if (action === "open-scene") openScene(target.dataset.sceneId);
    if (action === "save-scene") await saveScene();
    if (action === "approve-scene") await approveScene(target.dataset.sceneId || state.selectedSceneId);
    if (action === "regenerate-scene") await regenerateScene(target.dataset.sceneId || state.selectedSceneId);
    if (action === "approve-project") await approveProject();
    if (action === "render-project") await renderProject();
    if (action === "export-project") await exportProject();
    if (action === "save-settings") await saveSettings();
    if (action === "create-backup") await createBackup();
    if (action === "restore-backup") await restoreBackup();
    if (action === "create-evidence") await createEvidence();
    if (action === "create-release") await createRelease();
    if (action === "create-support") await createSupport();
    await refreshState();
  } catch (error) {
    state.notice = error.message || "操作失敗。";
  } finally {
    setBusy(false);
    render();
  }
}

async function saveProduct() {
  const result = await api("/api/products", { method: "POST", body: formData("#product-form") });
  state.selectedProductId = result.product.id;
  state.notice = "商品已建立並儲存。";
}

async function updateProduct() {
  const product = getProduct();
  if (!product) throw new Error("請先選擇商品。");
  await api(`/api/products/${product.id}`, { method: "PUT", body: formData("#product-form") });
  state.notice = "商品資料已更新。";
}

async function deleteProduct(productId) {
  if (!confirm("確定要刪除此商品資料？相關影片專案不會被刪除，但會失去商品資料參照。")) return;
  await api(`/api/products/${productId}`, { method: "DELETE" });
  state.selectedProductId = "";
  state.notice = "商品資料已刪除。";
}

async function importProduct(input) {
  try {
    const file = input.files[0];
    if (!file) return;
    const raw = await file.text();
    const imported = JSON.parse(raw);
    const payload = imported.product || imported;
    const result = await api("/api/products", { method: "POST", body: payload });
    state.selectedProductId = result.product.id;
    state.notice = "商品 JSON 已匯入並建立新商品。";
    await refreshState();
  } catch (error) {
    state.notice = `商品匯入失敗：${error.message}`;
  } finally {
    input.value = "";
    render();
  }
}

async function uploadMaterials(kind, inputId) {
  const product = getProduct();
  if (!product) throw new Error("請先建立或選擇商品。");
  const input = document.querySelector(`#${inputId}`);
  const files = [...input.files];
  if (!files.length) throw new Error("請先選擇商品素材。");
  const encoded = [];
  for (const file of files) {
    encoded.push({ name: file.name, type: file.type, kind, data: await fileToDataUrl(file) });
  }
  await api(`/api/products/${product.id}/materials`, { method: "POST", body: { files: encoded, kind } });
  input.value = "";
  state.notice = "商品素材已上傳，並已存入正式資料資料夾。";
}

async function deleteMaterial(productId, materialId) {
  await api(`/api/products/${productId}/materials/${materialId}`, { method: "DELETE" });
  state.notice = "照片已從商品資料中移除，原始檔仍保留在資料夾。";
}

async function moveMaterial(productId, materialId, direction) {
  await api(`/api/products/${productId}/materials/${materialId}/move`, { method: "PUT", body: { direction } });
  state.notice = direction === "up" ? "照片已向上排序。" : "照片已向下排序。";
}

async function replaceMaterial(input) {
  try {
    setBusy(true);
    const file = input.files[0];
    if (!file) return;
    await api(`/api/products/${input.dataset.productId}/materials/${input.dataset.materialId}/replace`, {
      method: "PUT",
      body: { file: { name: file.name, type: file.type, data: await fileToDataUrl(file) } }
    });
    state.notice = "照片已替換，新的檔案已保存。";
    await refreshState();
  } catch (error) {
    state.notice = error.message || "照片替換失敗。";
  } finally {
    setBusy(false);
    render();
  }
}

async function createProject() {
  if (state.submitting) return;
  const product = getProduct();
  const data = formData("#create-form");
  data.mode = state.createMode;
  data.productId = state.createMode === "product" ? product?.id || "" : "";
  data.action = "create-project";
  state.formErrors = validateCreateForm(data, product);
  if (Object.keys(state.formErrors).length) {
    state.notice = "請修正表單中標示的欄位。";
    render();
    return;
  }
  state.submitting = true;
  const button = document.querySelector('[data-action="create-project"]');
  if (button) {
    button.disabled = true;
    button.textContent = "正在送出...";
  }
  const idempotencyKey = crypto.randomUUID();
  data.idempotencyKey = idempotencyKey;
  try {
    const result = await api("/api/jobs", { method: "POST", body: data });
    state.selectedJobId = result.job.id;
    sessionStorage.setItem("tpvg-selected-job", result.job.id);
    state.notice = `已建立工作 ${result.job.id}，送出時間 ${formatDateTime(result.job.submittedAt)}。`;
    navigate("progress");
  } catch (error) {
    state.formErrors = error.fieldErrors || {};
    throw error;
  } finally {
    state.submitting = false;
  }
}

function validateCreateForm(data, product) {
  const errors = {};
  if (!String(data.requirement || "").trim()) errors.requirement = "請輸入中文影片需求。";
  const duration = Number(data.duration);
  if (!Number.isFinite(duration) || duration < 5 || duration > 180) errors.duration = "影片秒數必須介於 5 到 180 秒。";
  if (data.mode === "product") {
    if (!product) errors.productId = "請先建立並選擇商品，或改用純文字模式。";
    const visualCount = product?.materials?.filter((item) => ["image", "logo"].includes(item.kind || "image")).length || 0;
    if (product && visualCount === 0) errors.materials = "商品影片至少需要一張商品照片或 Logo。";
  }
  return errors;
}

async function cancelJob(jobId) {
  const result = await api(`/api/jobs/${jobId}/cancel`, { method: "POST", body: {} });
  state.notice = result.job.message;
}

async function retryJob(jobId) {
  const result = await api(`/api/jobs/${jobId}/retry`, { method: "POST", body: {} });
  state.selectedJobId = result.job.id;
  state.notice = `工作 ${result.job.id} 已重新排入佇列。`;
}

async function openOutput(path) {
  if (!path) throw new Error("輸出位置尚未建立。");
  await api("/api/open-path", { method: "POST", body: { path } });
  state.notice = "已開啟輸出資料夾。";
}

async function runDemo() {
  const result = await api("/api/demo/run", { method: "POST", body: {} });
  state.selectedProjectId = result.project.id;
  state.selectedProductId = result.project.productId;
  state.selectedSceneId = result.project.scenes[0]?.id || "";
  state.notice = "示範專案已建立，可直接查看輸出。";
  navigate("export");
}

function openProject(projectId) {
  state.selectedProjectId = projectId;
  const project = getProject();
  state.selectedProductId = project?.productId || state.selectedProductId;
  state.selectedSceneId = project?.scenes?.[0]?.id || "";
  navigate("preview");
}

async function deleteProject(projectId) {
  if (!confirm("確定要刪除此影片專案？已輸出的檔案不會自動刪除。")) return;
  await api(`/api/projects/${projectId}`, { method: "DELETE" });
  state.selectedProjectId = "";
  state.selectedSceneId = "";
  state.notice = "影片專案已移除，輸出檔案請自行管理。";
}

async function cancelProject(projectId) {
  await api(`/api/projects/${projectId}/cancel`, { method: "POST", body: {} });
  state.notice = "此專案已取消，可重新建立新版本。";
}

function openScene(sceneId) {
  state.selectedSceneId = sceneId;
  navigate("scene");
}

async function saveScene() {
  const project = getProject();
  const scene = getScene();
  if (!project || !scene) throw new Error("請先選擇場景。");
  await api(`/api/projects/${project.id}/scenes/${scene.id}/update`, { method: "POST", body: formData("#scene-form") });
  state.notice = "場景內容已更新。";
}

async function approveScene(sceneId) {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await api(`/api/projects/${project.id}/scenes/${sceneId}/approve`, { method: "POST", body: {} });
  state.notice = "場景已核准。";
}

async function regenerateScene(sceneId) {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await submitActionJob("regenerate-scene", { projectId: project.id, sceneId });
}

async function approveProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await api(`/api/projects/${project.id}/approve`, { method: "POST", body: {} });
  state.notice = "完整影片已核准，可以輸出。";
}

async function renderProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await submitActionJob("render-project", { projectId: project.id });
}

async function exportProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await submitActionJob("export-project", { projectId: project.id });
}

async function submitActionJob(action, payload) {
  const result = await api("/api/jobs", {
    method: "POST",
    body: { action, ...payload, idempotencyKey: crypto.randomUUID() }
  });
  state.selectedJobId = result.job.id;
  sessionStorage.setItem("tpvg-selected-job", result.job.id);
  state.notice = `已建立工作 ${result.job.id}。`;
  navigate("progress");
}

async function saveSettings() {
  await api("/api/settings", { method: "POST", body: formData("#settings-form") });
  state.notice = "設定已儲存。";
}

async function createBackup() {
  const result = await api("/api/backup", { method: "POST", body: {} });
  state.notice = `備份完成：${result.backup.path}`;
}

async function restoreBackup() {
  const input = document.querySelector("#restore-file");
  const confirmText = document.querySelector("#restore-confirm").value.trim();
  const file = input.files[0];
  if (!file) throw new Error("請先選擇備份 zip 檔。");
  const result = await api("/api/restore", {
    method: "POST",
    body: { confirm: confirmText, file: { name: file.name, type: file.type, data: await fileToDataUrl(file) } }
  });
  state.notice = `資料已還原，還原前安全備份：${result.safetyBackup.path}`;
}

async function createEvidence() {
  const result = await api("/api/evidence/screenshots");
  state.notice = `證據截圖已建立：${result.directory}`;
}

async function createRelease() {
  const result = await api("/api/release/package");
  state.notice = `發行包已建立：${result.archive}`;
}

async function createSupport() {
  const result = await api("/api/support/package");
  state.notice = `支援包已建立：${result.supportPackage.path}`;
}

function render() {
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.route === route));
  title.textContent = routeTitle(route);
  statusStrip.innerHTML = renderStatus();
  const screens = {
    home: renderHome,
    library: renderLibrary,
    create: renderCreate,
    progress: renderProgress,
    preview: renderPreview,
    scene: renderScene,
    export: renderExport,
    settings: renderSettings
  };
  app.innerHTML = screens[route]();
}

function renderStatus() {
  const project = getProject();
  const job = getJob();
  const ffmpeg = state.health.ffmpeg?.available ? "FFmpeg 可使用" : "FFmpeg 未連線";
  return [
    pill(state.apiOnline ? "後端正常" : "後端離線", state.apiOnline ? "ok" : "warn"),
    pill(ffmpeg, state.health.ffmpeg?.available ? "ok" : "warn"),
    pill(job ? `${jobLabel(job.status)} ${job.progress || 0}%` : project?.status ? stateLabel(project.status) : "尚無工作", job?.status === "completed" ? "ok" : ""),
    pill(state.notice, state.notice.includes("失敗") || state.notice.includes("問題") ? "warn" : "")
  ].join("");
}

function renderHome() {
  const latest = [...state.db.projects].reverse()[0];
  return `
    <section class="grid two">
      <div class="panel">
        <h2>建立一支可交付的商品短影音</h2>
        <p class="muted">V1 會使用商品資料、照片、中文描述與內容模型建立場景、字幕、文案，並用 FFmpeg 輸出 9:16 MP4 與完整輸出包。</p>
        <div class="actions">
          <button class="button" data-route="library">管理商品</button>
          <button class="button secondary" data-route="create">建立影片</button>
          <button class="button secondary" data-action="run-demo">建立示範專案</button>
        </div>
      </div>
      <div class="panel">
        <h2>工具狀態</h2>
        <table class="table"><tbody>
          <tr><th>資料位置</th><td>${escapeHtml(state.health.dataRoot || "")}</td></tr>
          <tr><th>商品資料庫</th><td>${escapeHtml(state.health.database?.path || "")}</td></tr>
          <tr><th>資料庫狀態</th><td>${escapeHtml(state.health.database?.apiHealth || "無法確認")}／${escapeHtml(state.health.database?.migrationStatus || "")}</td></tr>
          <tr><th>版本</th><td>${escapeHtml(state.health.version || "1.1.1")}</td></tr>
          <tr><th>FFmpeg</th><td>${escapeHtml(state.health.ffmpeg?.path || "未找到")}</td></tr>
          <tr><th>ComfyUI</th><td>${escapeHtml(state.health.comfyui?.message || "")}</td></tr>
          <tr><th>正式生產</th><td>${state.health.productionActivation?.overall === "PASS"
            ? "已就緒"
            : `尚未就緒（${state.health.productionActivation?.blockers?.length || 0} 項）`}</td></tr>
          <tr><th>Whisper</th><td>${state.health.whisper?.available ? "已設定" : "未設定，V1 會使用文字旁白備援"}</td></tr>
        </tbody></table>
      </div>
    </section>
    <section class="grid three" style="margin-top:18px">
      ${metric("商品", state.db.products.length)}
      ${metric("影片專案", state.db.projects.length)}
      ${metric("最近狀態", latest ? stateLabel(latest.status) : "無資料")}
    </section>
  `;
}

function renderLibrary() {
  const product = getProduct();
  if (!state.db.products.length) {
    return `
      <section class="empty-state">
        <h2>商品資料庫目前是空的</h2>
        <p>你可以建立第一個商品、匯入商品 JSON，或直接使用純文字模式製作影片。</p>
        <div class="actions">
          <button class="button" data-action="start-first-product">建立第一個商品</button>
          <label class="button secondary file-button">匯入商品 JSON<input id="product-import-file" type="file" accept=".json,application/json"></label>
          <button class="button secondary" data-action="use-text-only">使用純文字模式</button>
        </div>
      </section>
      ${renderProductEditor(null)}
    `;
  }
  return renderProductEditor(product);
}

function renderProductEditor(product) {
  return `
    <section class="grid two">
      <div class="panel">
        <h2>商品資料</h2>
        <div class="field">
          <label>選擇商品</label>
          <select data-product-select>${productOptions()}</select>
        </div>
        <form id="product-form" class="form-grid">
          ${input("商品名稱", "name", product?.name || "")}
          ${input("商品類別", "category", product?.category || "")}
          ${textarea("商品描述", "description", product?.description || "")}
          ${textarea("銷售重點", "sellingPoint", product?.sellingPoint || "")}
          ${textarea("商品資訊／規格", "productInfo", product?.productInfo || "")}
          ${textarea("神性與能量資訊", "spiritualInfo", product?.spiritualInfo || "")}
          ${textarea("目標客群", "targetAudience", product?.targetAudience || "")}
          ${input("標籤（逗號分隔）", "tags", (product?.tags || []).join("、"))}
          ${input("SEO 關鍵字（逗號分隔）", "seoKeywords", (product?.seoKeywords || []).join("、"))}
          <div class="actions">
            <button class="button" type="button" data-action="save-product">建立新商品</button>
            ${product ? `<button class="button secondary" type="button" data-action="update-product">更新此商品</button>` : ""}
            ${product ? `<button class="button danger" type="button" data-action="delete-product" data-product-id="${product.id}">刪除商品</button>` : ""}
            <label class="button secondary file-button">匯入商品 JSON<input id="product-import-file" type="file" accept=".json,application/json"></label>
          </div>
        </form>
      </div>
      <div class="panel">
        <h2>商品素材</h2>
        <p class="muted">照片順序會影響使用優先順序；Logo、商品影片與補充文件也會保存在同一商品下。</p>
        <div class="field">
          <label for="material-files">商品照片</label>
          <input id="material-files" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" multiple>
        </div>
        <button class="button" data-action="upload-materials" data-kind="image" data-input="material-files" ${product ? "" : "disabled"}>上傳照片</button>
        <div class="field">
          <label for="logo-files">品牌 Logo</label>
          <input id="logo-files" type="file" accept="image/png,image/jpeg,image/webp">
        </div>
        <button class="button secondary" data-action="upload-materials" data-kind="logo" data-input="logo-files" ${product ? "" : "disabled"}>上傳 Logo</button>
        <div class="field">
          <label for="video-files">商品影片</label>
          <input id="video-files" type="file" accept="video/mp4,video/quicktime,video/webm" multiple>
        </div>
        <button class="button secondary" data-action="upload-materials" data-kind="video" data-input="video-files" ${product ? "" : "disabled"}>上傳影片</button>
        <div class="field">
          <label for="document-files">補充文件</label>
          <input id="document-files" type="file" accept=".pdf,.txt,.docx" multiple>
        </div>
        <button class="button secondary" data-action="upload-materials" data-kind="document" data-input="document-files" ${product ? "" : "disabled"}>上傳文件</button>
        <div class="media-grid" style="margin-top:16px">${renderMaterials(product)}</div>
      </div>
    </section>
  `;
}

function renderCreate() {
  const product = getProduct();
  const noProducts = state.db.products.length === 0;
  const productVisuals = product?.materials?.filter((item) => ["image", "logo"].includes(item.kind || "image")).length || 0;
  const productBlocked = state.createMode === "product" && (!product || productVisuals === 0);
  const durationWarning = detectDurationConflict(
    document.querySelector('#create-form [name="requirement"]')?.value || "",
    state.config.defaultDuration || 30
  );
  return `
    <section class="grid two">
      <form id="create-form" class="panel form-grid">
        <h2>建立影片</h2>
        ${selectWithAttribute("製作模式", "mode-display", [
          { value: "product", label: "商品影片" },
          { value: "text-only", label: "純文字影片（不需商品或照片）" }
        ], state.createMode, "data-create-mode")}
        <div class="field">
          <label>商品</label>
          <select data-product-select ${state.createMode === "text-only" ? "disabled" : ""}>${productOptions()}</select>
          ${fieldError("productId")}
        </div>
        ${state.createMode === "text-only" ? input("專案名稱（選填）", "textProjectName", "") : ""}
        ${select("平台", "platform", ["Instagram Reels", "TikTok", "YouTube Shorts", "Shorts"], "Instagram Reels")}
        ${input("影片秒數", "duration", state.config.defaultDuration || 30, "number")}
        ${fieldError("duration")}
        ${textarea("目標客群", "targetAudience", state.createMode === "product" ? product?.targetAudience || "" : "")}
        ${textarea("神性與能量資訊", "spiritualInfo", state.createMode === "product" ? product?.spiritualInfo || "" : "")}
        ${textarea("中文影片需求", "requirement", "請做一支溫柔、靜心、有高級感的商品短影音。")}
        ${fieldError("requirement")}
        ${durationWarning ? `<div class="notice warning">${escapeHtml(durationWarning)}</div>` : ""}
        ${productBlocked ? `<div class="notice error-list">${noProducts
          ? "目前沒有商品。請先建立商品，或改用純文字模式。"
          : "此商品還沒有照片或 Logo，請先補上視覺素材。"}${fieldError("materials")}</div>` : ""}
        <div class="actions">
          <button class="button" type="button" data-action="create-project" ${productBlocked || state.submitting ? "disabled" : ""}>${state.submitting ? "正在送出..." : "送出並開始製作"}</button>
          ${productBlocked ? `<button class="button secondary" type="button" data-route="library">前往商品資料庫</button>` : ""}
          ${noProducts && state.createMode === "product" ? `<button class="button secondary" type="button" data-action="use-text-only">改用純文字模式</button>` : ""}
        </div>
      </form>
      <aside class="panel">
        <h2>目前素材摘要</h2>
        <table class="table"><tbody>
          <tr><th>製作模式</th><td>${state.createMode === "text-only" ? "純文字影片" : "商品影片"}</td></tr>
          <tr><th>商品名稱</th><td>${escapeHtml(state.createMode === "text-only" ? "不使用商品" : product?.name || "未選擇")}</td></tr>
          <tr><th>視覺素材數</th><td>${state.createMode === "text-only" ? 0 : productVisuals}</td></tr>
          <tr><th>輸出格式</th><td>1080 x 1920 / MP4 / 9:16</td></tr>
          <tr><th>付費 API</th><td>未使用</td></tr>
        </tbody></table>
      </aside>
    </section>
  `;
}

function renderProgress() {
  const job = getJob();
  if (!job) return empty("目前沒有生成工作", "送出影片需求後，工作編號與即時進度會顯示在這裡。", "create");
  const project = getProject();
  const stages = [
    ["validation", "驗證需求", 3],
    ["product", "載入商品資料", 8],
    ["research", "整理需求與知識", 14],
    ["script", "生成腳本", 22],
    ["storyboard", "規劃分鏡", 32],
    ["images", "處理影像", 44],
    ["emma", "檢查 Emma 一致性", 54],
    ["video", "生成影片", 66],
    ["audio", "處理聲音", 74],
    ["subtitles", "建立字幕", 82],
    ["editing", "自動剪輯", 89],
    ["render", "渲染影片", 96],
    ["export", "完成輸出", 100]
  ];
  const failed = job.status === "failed";
  const completed = job.status === "completed";
  const cancelled = job.status === "cancelled";
  return `
    <section class="panel progress-panel">
      <div class="field job-selector">
        <label>工作紀錄</label>
        <select data-job-select>${[...state.db.jobs].reverse().map((item) => option(item.id, `${item.id}｜${jobLabel(item.status)}｜${item.progress || 0}%`, item.id === job.id)).join("")}</select>
      </div>
      <div class="progress-heading">
        <div>
          <p class="eyebrow">${escapeHtml(job.id)}</p>
          <h2>${jobLabel(job.status)}</h2>
          <p class="muted">${escapeHtml(job.message || "")}</p>
        </div>
        <strong class="progress-number">${job.progress || 0}%</strong>
      </div>
      <div class="progress-bar large" role="progressbar" aria-valuenow="${job.progress || 0}" aria-valuemin="0" aria-valuemax="100">
        <span style="width:${job.progress || 0}%"></span>
      </div>
      <div class="status-grid">
        ${statusItem("工作編號", job.id)}
        ${statusItem("專案", job.projectId || "建立中")}
        ${statusItem("商品", job.productName || project?.productName || (job.payload?.mode === "text-only" ? "純文字影片" : "載入中"))}
        ${statusItem("目前階段", stageLabel(job.currentStage))}
        ${statusItem("上一階段", stageLabel(job.lastStage) || "無")}
        ${statusItem("已用時間", formatSeconds(job.elapsedSeconds))}
        ${statusItem("預估剩餘", job.etaSeconds ? formatSeconds(job.etaSeconds) : "尚無可靠估計")}
        ${statusItem("Provider／模型", `${job.provider || "自動"}／${job.model || "自動"}`)}
        ${statusItem("送出時間", formatDateTime(job.submittedAt))}
        ${statusItem("重試次數", `${job.retryCount || 0} / ${job.maxRetries || 0}`)}
      </div>
    </section>
    ${project?.durationConflict ? `<section class="notice warning" style="margin-top:18px">${escapeHtml(project.durationConflict.message)}</section>` : ""}
    <section class="grid two" style="margin-top:18px">
      <div class="panel">
        <h2>處理階段</h2>
        <div class="list compact">
          ${stages.map(([key, label, threshold], index) => {
            const done = (job.progress || 0) >= threshold || completed;
            const active = job.currentStage === key && !failed && !cancelled;
            return `<div class="step ${done ? "done" : ""} ${active ? "active" : ""}">
              <span class="step-index">${done ? "✓" : index + 1}</span>
              <div><strong>${label}</strong><p class="muted">${active ? escapeHtml(job.message || "處理中") : done ? "已完成" : "等待處理"}</p></div>
            </div>`;
          }).join("")}
        </div>
        ${job.stageHistory?.length ? `
          <h3 style="margin-top:18px">執行時間線</h3>
          <div class="timeline">
            ${job.stageHistory.slice(-8).map((item) => `
              <div><time>${escapeHtml(formatDateTime(item.at))}</time><strong>${escapeHtml(stageLabel(item.stage))} ${item.progress}%</strong><span>${escapeHtml(item.message || "")}</span></div>
            `).join("")}
          </div>
        ` : ""}
      </div>
      <aside class="panel">
        <h2>${completed ? "製作完成" : failed ? "工作失敗" : cancelled ? "工作已取消" : "工作控制"}</h2>
        ${completed ? renderJobSuccess(job, project) : ""}
        ${failed ? renderJobFailure(job) : ""}
        ${cancelled ? `<div class="notice">工作已安全停止。專案與可復用資料仍保留。</div>` : ""}
        ${!completed && !failed && !cancelled ? `<p class="muted">進度由後端工作單持續更新；重新整理或重新開啟後仍會自動恢復。</p>` : ""}
        <div class="actions">
          ${["queued", "running", "cancelling"].includes(job.status) ? `<button class="button warning" data-action="cancel-job" data-job-id="${job.id}" ${job.status === "cancelling" ? "disabled" : ""}>${job.status === "cancelling" ? "正在取消..." : "取消工作"}</button>` : ""}
          ${["failed", "cancelled"].includes(job.status) ? `<button class="button" data-action="retry-job" data-job-id="${job.id}">重試工作</button>` : ""}
          ${project ? `<button class="button secondary" data-route="preview">查看專案</button>` : ""}
          <a class="button secondary" href="/api/logs/jobs.log" target="_blank" rel="noreferrer">查看工作紀錄</a>
        </div>
      </aside>
    </section>
  `;
}

function renderJobSuccess(job, project) {
  const result = job.result || {};
  return `
    <div class="notice success">
      <strong>影片工作已完成</strong>
      <p>${escapeHtml(result.productName || project?.productName || "純文字影片")}</p>
    </div>
    <table class="table"><tbody>
      <tr><th>輸出位置</th><td>${escapeHtml(result.outputDir || project?.outputDir || "尚未建立")}</td></tr>
      <tr><th>總時間</th><td>${formatSeconds(job.elapsedSeconds)}</td></tr>
      <tr><th>品質分數</th><td>${escapeHtml(result.qualityScore ?? "依品質報告")}</td></tr>
      <tr><th>Emma</th><td>${escapeHtml(result.emmaVersion || "依正式設定")}</td></tr>
      <tr><th>聲音</th><td>${escapeHtml(result.voiceVersion || "依正式設定")}</td></tr>
      <tr><th>Provider</th><td>${escapeHtml(result.provider || job.provider || "自動")}</td></tr>
    </tbody></table>
    <div class="actions">
      ${result.previewVideo || project?.previewVideo ? `<a class="button" href="${result.previewVideo || project.previewVideo}" target="_blank" rel="noreferrer">播放預覽</a>` : ""}
      ${result.finalVideo || project?.finalVideo ? `<a class="button" href="${result.finalVideo || project.finalVideo}" target="_blank" rel="noreferrer">播放最終影片</a>` : ""}
      ${result.outputDir || project?.outputDir ? `<button class="button secondary" data-action="open-output" data-path="${escapeHtml(result.outputDir || project.outputDir)}">開啟輸出位置</button>` : ""}
      <button class="button secondary" data-route="preview">檢查場景</button>
      <button class="button secondary" data-action="create-next">建立下一支</button>
    </div>
  `;
}

function renderJobFailure(job) {
  const error = job.error || {};
  return `
    <div class="notice error-list">
      <strong>失敗階段：${escapeHtml(stageLabel(error.stage) || "無法判斷")}</strong>
      <p>${escapeHtml(error.reason || "工作未完成。")}</p>
      <p><strong>建議處理：</strong>${escapeHtml(error.suggestedAction || "請查看工作紀錄後重試。")}</p>
      <p class="muted">自動重試：${job.retryCount || 0} / ${job.maxRetries || 0}</p>
    </div>
  `;
}

function renderPreview() {
  const project = getProject();
  if (!project) return empty("沒有預覽", "請先建立影片。", "create");
  return `
    <section class="grid two">
      <div class="panel">
        <h2>影片預覽</h2>
        ${project.previewVideo ? `<video class="video-preview" src="${project.previewVideo}" controls></video>` : "<div class='placeholder-video'>尚未產生預覽影片</div>"}
        <div class="actions" style="margin-top:14px">
          <button class="button" data-action="approve-project">核准完整影片</button>
          <button class="button secondary" data-action="render-project">重新產生</button>
          <button class="button secondary" data-route="export">前往輸出</button>
        </div>
      </div>
      <aside class="panel">
        <h2>行銷文案</h2>
        <p><strong>貼文文案：</strong>${escapeHtml(project.caption)}</p>
        <p><strong>SEO：</strong>${escapeHtml(project.seoKeywords?.join("、") || "")}</p>
        <p><strong>縮圖建議：</strong>${escapeHtml(project.thumbnailSuggestion)}</p>
      </aside>
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>場景列表</h2>
      <div class="list">${project.scenes.map(renderSceneRow).join("")}</div>
    </section>
  `;
}

function renderScene() {
  const project = getProject();
  const scene = getScene();
  if (!project || !scene) return empty("沒有場景", "請先建立影片。", "create");
  return `
    <section class="grid two">
      <form id="scene-form" class="panel form-grid">
        <h2>場景細節</h2>
        <p class="muted">第 ${scene.order} 場 - ${scene.purpose} - V${scene.version} - ${scene.approved ? "已核准" : "未核准"}</p>
        ${textarea("畫面描述", "visualDescription", scene.visualDescription)}
        ${textarea("旁白", "narration", scene.narration)}
        ${textarea("字幕", "subtitle", scene.subtitle)}
        ${textarea("生成提示詞", "prompt", scene.prompt)}
        <div class="actions">
          <button class="button" type="button" data-action="save-scene">儲存修改</button>
          <button class="button secondary" type="button" data-action="approve-scene" data-scene-id="${scene.id}">核准場景</button>
          <button class="button warning" type="button" data-action="regenerate-scene" data-scene-id="${scene.id}">只重產此場景</button>
          <button class="button secondary" type="button" data-route="preview">回到預覽</button>
        </div>
      </form>
      <aside class="panel">
        <h2>其他場景</h2>
        <div class="list">${project.scenes.map((item) => `<button class="nav-item ${item.id === scene.id ? "active" : ""}" data-action="open-scene" data-scene-id="${item.id}">${item.order}. ${escapeHtml(item.purpose)} - V${item.version}</button>`).join("")}</div>
      </aside>
    </section>
  `;
}

function renderExport() {
  const project = getProject();
  if (!project) return empty("沒有可輸出的專案", "請先建立影片。", "create");
  return `
    <section class="grid two">
      <div class="panel">
        <h2>輸出</h2>
        <p class="muted">輸出會建立 MP4、字幕、旁白、貼文文案、metadata、scenes、prompts 與素材使用記錄。</p>
        <table class="table"><tbody>
          <tr><th>狀態</th><td>${stateLabel(project.status)}</td></tr>
          <tr><th>輸出資料夾</th><td>${escapeHtml(project.outputDir)}</td></tr>
          <tr><th>預覽影片</th><td>${project.previewVideo ? link(project.previewVideo, "開啟 preview.mp4") : "無資料"}</td></tr>
          <tr><th>最終影片</th><td>${project.finalVideo ? link(project.finalVideo, "開啟 final_video.mp4") : "尚未輸出"}</td></tr>
          <tr><th>字幕</th><td>${project.subtitles ? link(project.subtitles, "開啟 subtitles.srt") : "無資料"}</td></tr>
        </tbody></table>
        <div class="actions" style="margin-top:16px">
          <button class="button" data-action="export-project">輸出完整交付包</button>
          <button class="button secondary" data-route="preview">回到預覽</button>
        </div>
      </div>
      <aside class="panel">
        <h2>交付內容</h2>
        <ul>
          <li>final_video.mp4</li>
          <li>final_video_subtitled.mp4</li>
          <li>subtitles.srt</li>
          <li>narration.txt</li>
          <li>caption.txt</li>
          <li>metadata.json</li>
          <li>scenes.json</li>
          <li>prompts.json</li>
          <li>thumbnail_suggestion.txt</li>
          <li>materials_used.txt</li>
        </ul>
      </aside>
    </section>
  `;
}

function renderSettings() {
  const config = state.config;
  const database = state.health.database || {};
  return `
    <form id="settings-form" class="panel form-grid">
      <h2>設定</h2>
      ${input("ComfyUI 連線網址", "comfyuiUrl", config.comfyuiUrl || "")}
      ${input("ComfyUI 工作流程", "comfyuiWorkflow", config.comfyuiWorkflow || "")}
      ${input("FFmpeg 路徑", "ffmpegPath", config.ffmpegPath || "")}
      ${input("Whisper 路徑", "whisperPath", config.whisperPath || "")}
      ${select("TTS 模式", "ttsProvider", ["none", "local"], config.ttsProvider || "none")}
      ${input("輸出資料夾", "outputDir", config.outputDir || "")}
      ${input("預設影片秒數", "defaultDuration", config.defaultDuration || 30, "number")}
      ${select("是否加入 Logo", "includeLogo", ["true", "false"], String(config.includeLogo ?? true))}
      ${input("字幕樣式", "subtitleStyle", config.subtitleStyle || "")}
      ${select("生成模式", "providerMode", [
        { value: "production", label: "正式生產" },
        { value: "local-first", label: "本機預覽" },
        { value: "comfyui-preferred", label: "優先使用 ComfyUI" },
        { value: "cloud-disabled", label: "停用雲端服務" }
      ], config.providerMode || "local-first")}
      <div class="notice">V1 預設使用本機流程，不會自動呼叫付費 API。未連線的工具會使用可用的本機備援。</div>
      <button class="button" type="button" data-action="save-settings">儲存設定</button>
      <hr>
      <h2>備份、證據與支援</h2>
      <div class="actions">
        <button class="button secondary" type="button" data-action="create-backup">建立資料備份</button>
        <button class="button secondary" type="button" data-action="create-evidence">建立畫面證據</button>
        <button class="button secondary" type="button" data-action="create-release">建立發行包</button>
        <button class="button secondary" type="button" data-action="create-support">建立支援包</button>
      </div>
      <div class="field">
        <label>還原備份 zip</label>
        <input id="restore-file" type="file" accept=".zip">
      </div>
      <div class="field">
        <label>還原確認文字</label>
        <input id="restore-confirm" name="restoreConfirm" placeholder="輸入 RESTORE 才能還原">
      </div>
      <button class="button warning" type="button" data-action="restore-backup">還原備份</button>
      <hr>
      <h2>正式環境診斷</h2>
      <table class="table"><tbody>
        <tr><th>正式資料根目錄</th><td>${escapeHtml(state.health.dataRoot || "")}</td></tr>
        <tr><th>商品資料庫</th><td>${escapeHtml(database.path || "")}</td></tr>
        <tr><th>存在／可讀／可寫</th><td>${yesNo(database.exists)}／${yesNo(database.readable)}／${yesNo(database.writable)}</td></tr>
        <tr><th>資料版本</th><td>${escapeHtml(database.schemaVersion ?? "未知")}（目標 ${escapeHtml(database.targetSchemaVersion ?? "未知")}）</td></tr>
        <tr><th>遷移狀態</th><td>${escapeHtml(database.migrationStatus || "")}</td></tr>
        <tr><th>商品／工作數</th><td>${database.productCount || 0}／${database.jobCount || 0}</td></tr>
        <tr><th>商品 API</th><td>${escapeHtml(database.apiHealth || "無法確認")}</td></tr>
        <tr><th>ComfyUI</th><td>${escapeHtml(state.health.comfyui?.message || "未連線")}</td></tr>
        <tr><th>TTS</th><td>${state.health.tts?.available ? "已連線" : "未連線或使用正式流程設定"}</td></tr>
      </tbody></table>
      ${database.recovery?.recovered ? `<div class="notice error-list">${escapeHtml(database.recovery.message)}<br>原檔備份：${escapeHtml(database.recovery.backupPath)}</div>` : ""}
      <div class="actions">
        <a class="button secondary" href="/api/logs/app.log" target="_blank" rel="noreferrer">應用程式紀錄</a>
        <a class="button secondary" href="/api/logs/generation.log" target="_blank" rel="noreferrer">生成紀錄</a>
        <a class="button secondary" href="/api/logs/recovery.log" target="_blank" rel="noreferrer">復原紀錄</a>
      </div>
    </form>
  `;
}

function renderMaterials(product) {
  if (!product?.materials?.length) return "<p class='muted'>尚未上傳商品素材。</p>";
  return product.materials
    .sort((a, b) => a.order - b.order)
    .map((item) => `
      <article class="media-card">
        ${["image", "logo"].includes(item.kind || "image")
          ? `<img src="${item.url}" alt="${escapeHtml(item.fileName)}">`
          : `<div class="file-preview"><strong>${item.kind === "video" ? "影片" : "文件"}</strong><span>${escapeHtml(item.fileName)}</span></div>`}
        <strong>${escapeHtml(item.role)}</strong>
        <span>${escapeHtml(item.fileName)}</span>
        ${(item.kind || "image") === "image" ? `<div class="actions">
          <button class="button secondary" data-action="move-material" data-direction="up" data-product-id="${product.id}" data-material-id="${item.id}">上移</button>
          <button class="button secondary" data-action="move-material" data-direction="down" data-product-id="${product.id}" data-material-id="${item.id}">下移</button>
        </div>` : ""}
        ${["image", "logo"].includes(item.kind || "image") ? `<label class="button secondary file-button">替換<input data-replace-material data-product-id="${product.id}" data-material-id="${item.id}" type="file" accept="image/png,image/jpeg,image/webp,image/bmp"></label>` : ""}
        <button class="button secondary" data-action="delete-material" data-product-id="${product.id}" data-material-id="${item.id}">移除</button>
      </article>
    `)
    .join("");
}

function renderSceneRow(scene) {
  return `
    <article class="scene-row">
      <span class="pill ${scene.approved ? "ok" : ""}">${scene.order}. ${scene.duration}s</span>
      <div>
        <h3>${escapeHtml(scene.purpose)} - V${scene.version}</h3>
        <p class="muted">${escapeHtml(scene.visualDescription)}</p>
        <p><strong>字幕：</strong>${escapeHtml(scene.subtitle)}</p>
      </div>
      <div class="actions">
        <button class="button secondary" data-action="open-scene" data-scene-id="${scene.id}">編輯</button>
        <button class="button secondary" data-action="approve-scene" data-scene-id="${scene.id}">核准</button>
        <button class="button secondary" data-action="regenerate-scene" data-scene-id="${scene.id}">重產</button>
      </div>
    </article>
  `;
}

async function api(path, options = {}) {
  const init = { method: options.method || "GET", headers: {}, cache: "no-store" };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    throw new Error(`無法連線到 Temple AI Studio 後端（${error.message}）`);
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`後端回應格式錯誤（HTTP ${response.status}）`);
  }
  if (!response.ok || payload.ok === false) {
    const error = new Error(payload.message || "系統連線或處理失敗。");
    error.fieldErrors = payload.fieldErrors || {};
    throw error;
  }
  return payload;
}

function formData(selector) {
  return Object.fromEntries(new FormData(document.querySelector(selector)).entries());
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("檔案讀取失敗。"));
    reader.readAsDataURL(file);
  });
}

function getProduct() {
  return state.db.products.find((item) => item.id === state.selectedProductId) || state.db.products[0];
}

function getProject() {
  return state.db.projects.find((item) => item.id === state.selectedProjectId) || state.db.projects.at(-1);
}

function getJob() {
  return state.db.jobs?.find((item) => item.id === state.selectedJobId) || state.db.jobs?.at(-1);
}

function getScene() {
  const project = getProject();
  return project?.scenes?.find((item) => item.id === state.selectedSceneId) || project?.scenes?.[0];
}

function setBusy(value) {
  state.busy = value;
  document.body.classList.toggle("busy", value);
  if (value && !state.submitting) state.notice = "正在處理，請稍候...";
  statusStrip.innerHTML = renderStatus();
}

function navigate(nextRoute) {
  location.hash = normalizeRoute(nextRoute);
}

function normalizeRoute(value) {
  return ["home", "library", "create", "progress", "preview", "scene", "export", "settings"].includes(value) ? value : "home";
}

function routeTitle(value) {
  return {
    home: "首頁",
    library: "商品資料庫",
    create: "建立影片",
    progress: "生成進度",
    preview: "影片預覽",
    scene: "場景細節",
    export: "輸出",
    settings: "設定"
  }[value];
}

function stateLabel(value) {
  return {
    Draft: "草稿",
    Planning: "規劃中",
    Generating: "生成中",
    "Partially Failed": "部分失敗",
    "Ready for Preview": "可預覽",
    Approved: "已核准",
    Exporting: "輸出中",
    Completed: "已完成"
  }[value] || value;
}

function stepDescription(value) {
  return {
    Draft: "商品資料與需求已建立。",
    Planning: "系統正在規劃場景、旁白、字幕與生成提示詞。",
    Generating: "系統正在建立內容並用 FFmpeg 產生影片。",
    "Partially Failed": "部分步驟已完成，但需要查看錯誤訊息。",
    "Ready for Preview": "可以預覽影片並檢查每個場景。",
    Approved: "完整影片已核准，可以輸出。",
    Exporting: "正在輸出完整交付包。",
    Completed: "MP4、字幕、文案與 metadata 已完成。"
  }[value] || "";
}

function jobLabel(value) {
  return {
    queued: "已排入佇列",
    running: "製作中",
    cancelling: "正在取消",
    cancelled: "已取消",
    failed: "失敗",
    completed: "已完成"
  }[value] || value || "未知";
}

function stageLabel(value) {
  return {
    validation: "驗證需求",
    product: "載入商品資料",
    research: "整理需求與知識",
    script: "生成腳本",
    storyboard: "規劃分鏡",
    images: "處理影像",
    emma: "檢查 Emma 一致性",
    video: "生成影片",
    audio: "處理聲音",
    subtitles: "建立字幕",
    editing: "自動剪輯",
    render: "渲染影片",
    export: "完成輸出"
  }[value] || value || "";
}

function productOptions() {
  if (!state.db.products.length) return '<option value="">目前沒有商品</option>';
  return state.db.products
    .map((item) => option(item.id, `${item.name}（${item.id}）`, item.id === state.selectedProductId))
    .join("");
}

function fieldError(name) {
  const message = state.formErrors?.[name];
  return message ? `<span class="field-error">${escapeHtml(message)}</span>` : "";
}

function selectWithAttribute(label, name, values, current, attribute) {
  const id = `field-${name}`;
  return `<div class="field"><label for="${id}">${label}</label><select id="${id}" name="${name}" ${attribute}>${values.map((item) => option(item.value, item.label, item.value === current)).join("")}</select></div>`;
}

function statusItem(label, value) {
  return `<div class="status-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function formatSeconds(value) {
  const total = Number(value || 0);
  if (total < 60) return `${total} 秒`;
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes} 分 ${seconds} 秒`;
}

function formatDateTime(value) {
  if (!value) return "未知";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-TW", { hour12: false });
}

function yesNo(value) {
  return value ? "是" : "否";
}

function detectDurationConflict(requirement, selectedDuration) {
  const matches = [...String(requirement || "").matchAll(/(\d{1,3})\s*(?:秒鐘|秒|seconds?|secs?|s)/gi)];
  if (!matches.length) return "";
  const requested = Number(matches.at(-1)[1]);
  const selected = Number(selectedDuration);
  return requested !== selected ? `文字需求提到 ${requested} 秒；送出時會以介面設定的 ${selected} 秒為準。` : "";
}

function input(label, name, value, type = "text") {
  const id = `field-${name}`;
  return `<div class="field"><label for="${id}">${label}</label><input id="${id}" type="${type}" name="${name}" value="${escapeHtml(value)}"></div>`;
}

function textarea(label, name, value) {
  const id = `field-${name}`;
  return `<div class="field"><label for="${id}">${label}</label><textarea id="${id}" name="${name}">${escapeHtml(value)}</textarea></div>`;
}

function select(label, name, values, current) {
  const id = `field-${name}`;
  return `<div class="field"><label for="${id}">${label}</label><select id="${id}" name="${name}">${values.map((item) => {
    const value = typeof item === "object" ? item.value : item;
    const text = typeof item === "object" ? item.label : item;
    return option(value, text, String(value) === String(current));
  }).join("")}</select></div>`;
}

function option(value, label, selected) {
  return `<option value="${escapeHtml(value)}" ${selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
}

function metric(label, value) {
  return `<div class="card"><p class="muted">${label}</p><h2>${escapeHtml(value)}</h2></div>`;
}

function pill(text, mode = "") {
  return `<span class="pill ${mode}">${escapeHtml(text)}</span>`;
}

function link(href, text) {
  return `<a href="${href}" target="_blank" rel="noreferrer">${escapeHtml(text)}</a>`;
}

function empty(headline, copy, destination) {
  return `<section class="panel"><h2>${headline}</h2><p class="muted">${copy}</p><button class="button" data-route="${destination}">前往</button></section>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
