const app = document.querySelector("#app");
const title = document.querySelector("#screen-title");
const statusStrip = document.querySelector("#status-strip");
const navItems = [...document.querySelectorAll(".nav-item")];

let route = normalizeRoute(location.hash.replace("#", "") || "home");
let state = {
  db: { products: [], projects: [] },
  config: {},
  health: {},
  selectedProductId: "",
  selectedProjectId: "",
  selectedSceneId: "",
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
  if (event.target.matches("[data-project-select]")) {
    state.selectedProjectId = event.target.value;
    const project = getProject();
    state.selectedSceneId = project?.scenes?.[0]?.id || "";
    state.notice = "已切換影片專案。";
    render();
  }
  if (event.target.matches("[data-replace-material]")) {
    await replaceMaterial(event.target);
  }
  if (event.target.matches("#restore-file")) {
    state.notice = event.target.files.length ? "已選擇備份檔，請輸入 RESTORE 後再還原。" : "尚未選擇備份檔。";
    render();
  }
});

boot();

async function boot() {
  await refreshState();
  const product = getProduct();
  const project = getProject();
  state.selectedProductId ||= product?.id || "";
  state.selectedProjectId ||= project?.id || "";
  state.selectedSceneId ||= project?.scenes?.[0]?.id || "";
  render();
}

async function refreshState() {
  const payload = await api("/api/state");
  state.db = payload.db;
  state.config = payload.config;
  state.health = payload.health;
  if (!state.selectedProductId && state.db.products[0]) state.selectedProductId = state.db.products[0].id;
  if (!state.selectedProjectId && state.db.projects[0]) state.selectedProjectId = state.db.projects.at(-1).id;
}

async function handleAction(action, target) {
  try {
    setBusy(true);
    if (action === "save-product") await saveProduct();
    if (action === "update-product") await updateProduct();
    if (action === "delete-product") await deleteProduct(target.dataset.productId);
    if (action === "upload-materials") await uploadMaterials();
    if (action === "delete-material") await deleteMaterial(target.dataset.productId, target.dataset.materialId);
    if (action === "move-material") await moveMaterial(target.dataset.productId, target.dataset.materialId, target.dataset.direction);
    if (action === "create-project") await createProject();
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

async function uploadMaterials() {
  const product = getProduct();
  if (!product) throw new Error("請先建立或選擇商品。");
  const input = document.querySelector("#material-files");
  const files = [...input.files];
  if (!files.length) throw new Error("請先選擇商品照片。");
  const encoded = [];
  for (const file of files) {
    encoded.push({ name: file.name, type: file.type, data: await fileToDataUrl(file) });
  }
  await api(`/api/products/${product.id}/materials`, { method: "POST", body: { files: encoded } });
  input.value = "";
  state.notice = "商品照片已上傳，並已存入專案資料夾。";
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
  const product = getProduct();
  if (!product) throw new Error("請先選擇商品。");
  const data = formData("#create-form");
  data.productId = product.id;
  const result = await api("/api/projects", { method: "POST", body: data });
  state.selectedProjectId = result.project.id;
  state.selectedSceneId = result.project.scenes[0]?.id || "";
  state.notice = result.project.status === "Partially Failed"
    ? "內容已建立，但影片輸出遇到問題。請到進度頁查看。"
    : "影片內容已建立，預覽 MP4 已完成。";
  navigate("preview");
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
  const result = await api(`/api/projects/${project.id}/scenes/${sceneId}/regenerate`, { method: "POST", body: {} });
  state.selectedProjectId = result.project.id;
  state.selectedSceneId = sceneId;
  state.notice = result.project.status === "Partially Failed"
    ? "場景已重產，但影片輸出仍遇到問題。"
    : "單一場景已重產，其他場景保持不變。";
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
  await api(`/api/projects/${project.id}/render`, { method: "POST", body: {} });
  state.notice = "影片已重新產生。";
}

async function exportProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  const result = await api(`/api/projects/${project.id}/export`, { method: "POST", body: {} });
  state.selectedProjectId = result.project.id;
  state.notice = result.project.status === "Completed" ? "完整輸出包已建立。" : "輸出遇到問題，請查看錯誤訊息。";
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
  const ffmpeg = state.health.ffmpeg?.available ? "FFmpeg 可使用" : "FFmpeg 未連線";
  return [
    pill(ffmpeg, state.health.ffmpeg?.available ? "ok" : "warn"),
    pill(project?.status ? stateLabel(project.status) : "尚未選擇專案", project?.status === "Completed" ? "ok" : ""),
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
          <tr><th>版本</th><td>${escapeHtml(state.health.version || "1.0.0")}</td></tr>
          <tr><th>FFmpeg</th><td>${escapeHtml(state.health.ffmpeg?.path || "未找到")}</td></tr>
          <tr><th>ComfyUI</th><td>${escapeHtml(state.health.comfyui?.message || "")}</td></tr>
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
  return `
    <section class="grid two">
      <div class="panel">
        <h2>商品資料</h2>
        <div class="field">
          <label>選擇商品</label>
          <select data-product-select>${state.db.products.map((item) => option(item.id, item.name, item.id === state.selectedProductId)).join("")}</select>
        </div>
        <form id="product-form" class="form-grid">
          ${input("商品名稱", "name", product?.name || "")}
          ${input("商品類別", "category", product?.category || "")}
          ${textarea("商品描述", "description", product?.description || "")}
          ${textarea("銷售重點", "sellingPoint", product?.sellingPoint || "")}
          ${textarea("神性與能量資訊", "spiritualInfo", product?.spiritualInfo || "")}
          ${textarea("目標客群", "targetAudience", product?.targetAudience || "")}
          <div class="actions">
            <button class="button" type="button" data-action="save-product">建立新商品</button>
            <button class="button secondary" type="button" data-action="update-product">更新此商品</button>
            ${product ? `<button class="button danger" type="button" data-action="delete-product" data-product-id="${product.id}">刪除商品</button>` : ""}
          </div>
        </form>
      </div>
      <div class="panel">
        <h2>商品照片</h2>
        <p class="muted">請上傳商品主圖、細節圖、包裝圖或情境圖。照片順序會影響影片場景的使用優先順序。</p>
        <div class="field">
          <label>新增照片</label>
          <input id="material-files" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" multiple>
        </div>
        <button class="button" data-action="upload-materials">上傳照片</button>
        <div class="media-grid" style="margin-top:16px">${renderMaterials(product)}</div>
      </div>
    </section>
  `;
}

function renderCreate() {
  const product = getProduct();
  return `
    <section class="grid two">
      <form id="create-form" class="panel form-grid">
        <h2>建立影片</h2>
        <div class="field">
          <label>商品</label>
          <select data-product-select>${state.db.products.map((item) => option(item.id, item.name, item.id === state.selectedProductId)).join("")}</select>
        </div>
        ${select("平台", "platform", ["Instagram Reels", "TikTok", "YouTube Shorts", "Shorts"], "Instagram Reels")}
        ${input("影片秒數", "duration", state.config.defaultDuration || 30, "number")}
        ${textarea("目標客群", "targetAudience", product?.targetAudience || "")}
        ${textarea("神性與能量資訊", "spiritualInfo", product?.spiritualInfo || "")}
        ${textarea("中文影片需求", "requirement", "請做一支溫柔、靜心、有高級感的商品短影音。")}
        <button class="button" type="button" data-action="create-project">產生內容包並建立影片</button>
      </form>
      <aside class="panel">
        <h2>目前素材摘要</h2>
        <table class="table"><tbody>
          <tr><th>商品名稱</th><td>${escapeHtml(product?.name || "未選擇")}</td></tr>
          <tr><th>照片數</th><td>${product?.materials?.length || 0}</td></tr>
          <tr><th>輸出格式</th><td>1080 x 1920 / MP4 / 9:16</td></tr>
          <tr><th>付費 API</th><td>未使用</td></tr>
        </tbody></table>
      </aside>
    </section>
  `;
}

function renderProgress() {
  const project = getProject();
  if (!project) return empty("沒有專案", "請先建立影片專案。", "create");
  const steps = ["Draft", "Planning", "Generating", "Partially Failed", "Ready for Preview", "Approved", "Exporting", "Completed"];
  const current = Math.max(0, steps.indexOf(project.status));
  return `
    <section class="grid two">
      <div class="panel">
        <h2>生成進度</h2>
        <div class="field">
          <label>選擇專案</label>
          <select data-project-select>${state.db.projects.map((item) => option(item.id, `${item.productName} - ${stateLabel(item.status)}`, item.id === project.id)).join("")}</select>
        </div>
        <div class="list">
          ${steps.map((step, index) => `<div class="step ${index <= current ? "done" : ""}"><span class="step-index">${index + 1}</span><div><strong>${stateLabel(step)}</strong><p class="muted">${stepDescription(step)}</p></div></div>`).join("")}
        </div>
      </div>
      <aside class="panel">
        <h2>問題與處理</h2>
        ${project.errors?.length ? project.errors.map((error) => `<div class="notice error-list">${escapeHtml(error.message)}<br>${escapeHtml(error.at)}</div>`).join("") : "<p class='muted'>目前沒有錯誤。</p>"}
        <div class="actions">
          <button class="button secondary" data-action="render-project">重新產生影片</button>
          <button class="button secondary" data-action="cancel-project" data-project-id="${project.id}">取消此專案</button>
          <button class="button danger" data-action="delete-project" data-project-id="${project.id}">刪除專案記錄</button>
          <button class="button secondary" data-route="preview">前往預覽</button>
        </div>
      </aside>
    </section>
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
      ${select("生成模式", "providerMode", ["local-first", "comfyui-preferred", "cloud-disabled"], config.providerMode || "local-first")}
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
    </form>
  `;
}

function renderMaterials(product) {
  if (!product?.materials?.length) return "<p class='muted'>尚未上傳照片。</p>";
  return product.materials
    .sort((a, b) => a.order - b.order)
    .map((item) => `
      <article class="media-card">
        <img src="${item.url}" alt="${escapeHtml(item.fileName)}">
        <strong>${escapeHtml(item.role)}</strong>
        <span>${escapeHtml(item.fileName)}</span>
        <div class="actions">
          <button class="button secondary" data-action="move-material" data-direction="up" data-product-id="${product.id}" data-material-id="${item.id}">上移</button>
          <button class="button secondary" data-action="move-material" data-direction="down" data-product-id="${product.id}" data-material-id="${item.id}">下移</button>
        </div>
        <label class="button secondary file-button">替換<input data-replace-material data-product-id="${product.id}" data-material-id="${item.id}" type="file" accept="image/png,image/jpeg,image/webp,image/bmp"></label>
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
  const init = { method: options.method || "GET", headers: {} };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, init);
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || "系統連線或處理失敗。");
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

function getScene() {
  const project = getProject();
  return project?.scenes?.find((item) => item.id === state.selectedSceneId) || project?.scenes?.[0];
}

function setBusy(value) {
  state.busy = value;
  document.body.classList.toggle("busy", value);
  if (value) state.notice = "正在處理，請稍候...";
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

function input(label, name, value, type = "text") {
  return `<div class="field"><label>${label}</label><input type="${type}" name="${name}" value="${escapeHtml(value)}"></div>`;
}

function textarea(label, name, value) {
  return `<div class="field"><label>${label}</label><textarea name="${name}">${escapeHtml(value)}</textarea></div>`;
}

function select(label, name, values, current) {
  return `<div class="field"><label>${label}</label><select name="${name}">${values.map((value) => option(value, value, String(value) === String(current))).join("")}</select></div>`;
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
