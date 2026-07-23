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
  notice: "正在載入本機資料..."
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
    state.notice = event.target.files.length ? "已選擇備份檔，按下還原即可執行。" : "尚未選擇備份檔。";
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
  state.notice = "商品已建立並保存。";
}

async function updateProduct() {
  const product = getProduct();
  if (!product) throw new Error("請先選擇商品。");
  await api(`/api/products/${product.id}`, { method: "PUT", body: formData("#product-form") });
  state.notice = "商品資料已更新。";
}

async function deleteProduct(productId) {
  if (!confirm("確定要刪除此商品資料？原始圖片檔會保留在本機資料夾。")) return;
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
  state.notice = "商品照片已上傳，原始檔已保留。";
}

async function deleteMaterial(productId, materialId) {
  await api(`/api/products/${productId}/materials/${materialId}`, { method: "DELETE" });
  state.notice = "照片已從商品中移除，原始檔仍保留。";
}

async function moveMaterial(productId, materialId, direction) {
  await api(`/api/products/${productId}/materials/${materialId}/move`, { method: "PUT", body: { direction } });
  state.notice = direction === "up" ? "照片已往前排序。" : "照片已往後排序。";
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
    state.notice = "照片已替換，舊檔路徑已保留於紀錄。";
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
  state.notice = result.project.status === "Partially Failed" ? "內容已建立，但影片生成失敗，請到進度頁查看。" : "影片草稿與預覽 MP4 已生成。";
  navigate("preview");
}

async function runDemo() {
  const result = await api("/api/demo/run", { method: "POST", body: {} });
  state.selectedProjectId = result.project.id;
  state.selectedProductId = result.project.productId;
  state.selectedSceneId = result.project.scenes[0]?.id || "";
  state.notice = "示範專案已完整跑通並匯出。";
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
  if (!confirm("確定要刪除此專案紀錄？已輸出的檔案不會自動刪除。")) return;
  await api(`/api/projects/${projectId}`, { method: "DELETE" });
  state.selectedProjectId = "";
  state.selectedSceneId = "";
  state.notice = "專案紀錄已刪除，輸出檔案保留。";
}

async function cancelProject(projectId) {
  await api(`/api/projects/${projectId}/cancel`, { method: "POST", body: {} });
  state.notice = "未完成專案已取消並回到草稿狀態。";
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
  state.notice = "場景文字已更新。";
}

async function approveScene(sceneId) {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await api(`/api/projects/${project.id}/scenes/${sceneId}/approve`, { method: "POST", body: {} });
  state.notice = "場景已批准。";
}

async function regenerateScene(sceneId) {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  const result = await api(`/api/projects/${project.id}/scenes/${sceneId}/regenerate`, { method: "POST", body: {} });
  state.selectedProjectId = result.project.id;
  state.selectedSceneId = sceneId;
  state.notice = result.project.status === "Partially Failed" ? "場景已重生，但影片重新組裝失敗。" : "指定場景已重生，其他場景未被改動。";
}

async function approveProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await api(`/api/projects/${project.id}/approve`, { method: "POST", body: {} });
  state.notice = "整支影片已批准，可以匯出。";
}

async function renderProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  await api(`/api/projects/${project.id}/render`, { method: "POST", body: {} });
  state.notice = "預覽影片已重新組裝。";
}

async function exportProject() {
  const project = getProject();
  if (!project) throw new Error("請先選擇專案。");
  const result = await api(`/api/projects/${project.id}/export`, { method: "POST", body: {} });
  state.selectedProjectId = result.project.id;
  state.notice = result.project.status === "Completed" ? "影片與完整內容包已匯出。" : "匯出未完成，請查看錯誤紀錄。";
}

async function saveSettings() {
  await api("/api/settings", { method: "POST", body: formData("#settings-form") });
  state.notice = "設定已保存。";
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
  state.notice = `資料已還原。還原前安全備份：${result.safetyBackup.path}`;
}

async function createEvidence() {
  const result = await api("/api/evidence/screenshots");
  state.notice = `證據圖已建立：${result.directory}`;
}

async function createRelease() {
  const result = await api("/api/release/package");
  state.notice = `Release package 已建立：${result.archive}`;
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
  const ffmpeg = state.health.ffmpeg?.available ? "FFmpeg 可用" : "FFmpeg 未連線";
  return [
    pill(ffmpeg, state.health.ffmpeg?.available ? "ok" : "warn"),
    pill(project?.status ? stateLabel(project.status) : "尚未選擇專案", project?.status === "Completed" ? "ok" : ""),
    pill(state.notice, state.notice.includes("失敗") || state.notice.includes("錯誤") ? "warn" : "")
  ].join("");
}

function renderHome() {
  const latest = [...state.db.projects].reverse()[0];
  return `
    <section class="grid two">
      <div class="panel">
        <h2>建立一支可用的商品短影片</h2>
        <p class="muted">V1 使用本機資料儲存、商品照片、繁體中文內容模板與 FFmpeg，產生可播放的 9:16 MP4 與完整內容包。</p>
        <div class="actions">
          <button class="button" data-route="library">管理商品</button>
          <button class="button secondary" data-route="create">建立影片</button>
          <button class="button secondary" data-action="run-demo">跑完整示範</button>
        </div>
      </div>
      <div class="panel">
        <h2>本機狀態</h2>
        <table class="table"><tbody>
          <tr><th>資料位置</th><td>${escapeHtml(state.health.dataRoot || "")}</td></tr>
          <tr><th>FFmpeg</th><td>${escapeHtml(state.health.ffmpeg?.path || "未找到")}</td></tr>
          <tr><th>ComfyUI</th><td>${escapeHtml(state.health.comfyui?.message || "")}</td></tr>
          <tr><th>Whisper</th><td>${state.health.whisper?.available ? "已設定" : "未設定，V1 使用字幕時間軸 fallback"}</td></tr>
        </tbody></table>
      </div>
    </section>
    <section class="grid three" style="margin-top:18px">
      ${metric("商品", state.db.products.length)}
      ${metric("影片專案", state.db.projects.length)}
      ${metric("最新專案", latest ? stateLabel(latest.status) : "尚無")}
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
          ${input("商品類型", "category", product?.category || "")}
          ${textarea("商品說明", "description", product?.description || "")}
          ${textarea("商品特色", "sellingPoint", product?.sellingPoint || "")}
          ${textarea("靈性／文化資訊", "spiritualInfo", product?.spiritualInfo || "")}
          ${textarea("目標受眾", "targetAudience", product?.targetAudience || "")}
          <div class="actions">
            <button class="button" type="button" data-action="save-product">建立新商品</button>
            <button class="button secondary" type="button" data-action="update-product">更新目前商品</button>
            ${product ? `<button class="button danger" type="button" data-action="delete-product" data-product-id="${product.id}">刪除商品</button>` : ""}
          </div>
        </form>
      </div>
      <div class="panel">
        <h2>商品照片</h2>
        <p class="muted">可上傳多張照片、排序、替換或移除。系統會保留原始檔，生成影片時建立工作副本。</p>
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
        ${input("影片長度秒數", "duration", state.config.defaultDuration || 30, "number")}
        ${textarea("目標受眾", "targetAudience", product?.targetAudience || "")}
        ${textarea("靈性／文化資訊", "spiritualInfo", product?.spiritualInfo || "")}
        ${textarea("繁體中文影片需求", "requirement", "請製作一支溫柔、清楚、有儀式感的商品短影片。")}
        <button class="button" type="button" data-action="create-project">產生腳本、場景與預覽影片</button>
      </form>
      <aside class="panel">
        <h2>生成前檢查</h2>
        <table class="table"><tbody>
          <tr><th>商品名稱</th><td>${escapeHtml(product?.name || "未選擇")}</td></tr>
          <tr><th>照片數</th><td>${product?.materials?.length || 0}</td></tr>
          <tr><th>輸出規格</th><td>1080 × 1920 / MP4 / 9:16</td></tr>
          <tr><th>雲端 API</th><td>未啟用</td></tr>
        </tbody></table>
      </aside>
    </section>
  `;
}

function renderProgress() {
  const project = getProject();
  if (!project) return empty("尚無專案", "請先建立影片專案。", "create");
  const steps = ["Draft", "Planning", "Generating", "Partially Failed", "Ready for Preview", "Approved", "Exporting", "Completed"];
  const current = Math.max(0, steps.indexOf(project.status));
  return `
    <section class="grid two">
      <div class="panel">
        <h2>生成進度</h2>
        <div class="field">
          <label>選擇專案</label>
          <select data-project-select>${state.db.projects.map((item) => option(item.id, `${item.productName}｜${stateLabel(item.status)}`, item.id === project.id)).join("")}</select>
        </div>
        <div class="list">
          ${steps.map((step, index) => `<div class="step ${index <= current ? "done" : ""}"><span class="step-index">${index + 1}</span><div><strong>${stateLabel(step)}</strong><p class="muted">${stepDescription(step)}</p></div></div>`).join("")}
        </div>
      </div>
      <aside class="panel">
        <h2>錯誤與恢復</h2>
        ${project.errors?.length ? project.errors.map((error) => `<div class="notice error-list">${escapeHtml(error.message)}<br>${escapeHtml(error.at)}</div>`).join("") : "<p class='muted'>目前沒有錯誤。</p>"}
        <div class="actions">
          <button class="button secondary" data-action="render-project">重新組裝預覽影片</button>
          <button class="button secondary" data-action="cancel-project" data-project-id="${project.id}">取消未完成專案</button>
          <button class="button danger" data-action="delete-project" data-project-id="${project.id}">刪除專案紀錄</button>
          <button class="button secondary" data-route="preview">前往預覽</button>
        </div>
      </aside>
    </section>
  `;
}

function renderPreview() {
  const project = getProject();
  if (!project) return empty("尚無預覽", "請先建立影片。", "create");
  return `
    <section class="grid two">
      <div class="panel">
        <h2>影片預覽</h2>
        ${project.previewVideo ? `<video class="video-preview" src="${project.previewVideo}" controls></video>` : "<div class='placeholder-video'>尚未產生預覽影片</div>"}
        <div class="actions" style="margin-top:14px">
          <button class="button" data-action="approve-project">批准整支影片</button>
          <button class="button secondary" data-action="render-project">重新組裝</button>
          <button class="button secondary" data-route="export">前往匯出</button>
        </div>
      </div>
      <aside class="panel">
        <h2>內容包摘要</h2>
        <p><strong>Caption：</strong>${escapeHtml(project.caption)}</p>
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
  if (!project || !scene) return empty("尚無場景", "請先建立影片。", "create");
  return `
    <section class="grid two">
      <form id="scene-form" class="panel form-grid">
        <h2>場景細節</h2>
        <p class="muted">第 ${scene.order} 場｜${scene.purpose}｜版本 ${scene.version}｜${scene.approved ? "已批准" : "未批准"}</p>
        ${textarea("畫面說明", "visualDescription", scene.visualDescription)}
        ${textarea("旁白", "narration", scene.narration)}
        ${textarea("字幕", "subtitle", scene.subtitle)}
        ${textarea("Prompt", "prompt", scene.prompt)}
        <div class="actions">
          <button class="button" type="button" data-action="save-scene">保存文字</button>
          <button class="button secondary" type="button" data-action="approve-scene" data-scene-id="${scene.id}">批准場景</button>
          <button class="button warning" type="button" data-action="regenerate-scene" data-scene-id="${scene.id}">重生此場景</button>
          <button class="button secondary" type="button" data-route="preview">返回預覽</button>
        </div>
      </form>
      <aside class="panel">
        <h2>切換場景</h2>
        <div class="list">${project.scenes.map((item) => `<button class="nav-item ${item.id === scene.id ? "active" : ""}" data-action="open-scene" data-scene-id="${item.id}">${item.order}. ${escapeHtml(item.purpose)}｜V${item.version}</button>`).join("")}</div>
      </aside>
    </section>
  `;
}

function renderExport() {
  const project = getProject();
  if (!project) return empty("尚無可匯出專案", "請先建立影片。", "create");
  return `
    <section class="grid two">
      <div class="panel">
        <h2>匯出</h2>
        <p class="muted">匯出會建立 MP4、SRT、旁白稿、Caption、Metadata、Scenes、Prompts、縮圖建議與素材清單。</p>
        <table class="table"><tbody>
          <tr><th>狀態</th><td>${stateLabel(project.status)}</td></tr>
          <tr><th>輸出資料夾</th><td>${escapeHtml(project.outputDir)}</td></tr>
          <tr><th>預覽影片</th><td>${project.previewVideo ? link(project.previewVideo, "開啟 preview.mp4") : "尚無"}</td></tr>
          <tr><th>最終影片</th><td>${project.finalVideo ? link(project.finalVideo, "開啟 final_video.mp4") : "尚未匯出"}</td></tr>
          <tr><th>字幕</th><td>${project.subtitles ? link(project.subtitles, "開啟 subtitles.srt") : "尚無"}</td></tr>
        </tbody></table>
        <div class="actions" style="margin-top:16px">
          <button class="button" data-action="export-project">匯出完整內容包</button>
          <button class="button secondary" data-route="preview">返回預覽</button>
        </div>
      </div>
      <aside class="panel">
        <h2>應包含檔案</h2>
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
      ${input("ComfyUI 位址", "comfyuiUrl", config.comfyuiUrl || "")}
      ${input("ComfyUI 工作流", "comfyuiWorkflow", config.comfyuiWorkflow || "")}
      ${input("FFmpeg 路徑", "ffmpegPath", config.ffmpegPath || "")}
      ${input("Whisper 路徑", "whisperPath", config.whisperPath || "")}
      ${select("TTS 選項", "ttsProvider", ["none", "local"], config.ttsProvider || "none")}
      ${input("輸出資料夾", "outputDir", config.outputDir || "")}
      ${input("預設影片長度", "defaultDuration", config.defaultDuration || 30, "number")}
      ${select("是否加入 Logo", "includeLogo", ["true", "false"], String(config.includeLogo ?? true))}
      ${input("字幕樣式", "subtitleStyle", config.subtitleStyle || "")}
      ${select("Provider 選擇", "providerMode", ["local-first", "comfyui-preferred", "cloud-disabled"], config.providerMode || "local-first")}
      <div class="notice">V1 預設本機優先，不會呼叫付費 API。雲端 Provider 保留為未啟用。</div>
      <button class="button" type="button" data-action="save-settings">保存設定</button>
      <hr>
      <h2>備份、證據與發行</h2>
      <div class="actions">
        <button class="button secondary" type="button" data-action="create-backup">建立資料備份</button>
        <button class="button secondary" type="button" data-action="create-evidence">產生操作證據圖</button>
        <button class="button secondary" type="button" data-action="create-release">建立 Release Package</button>
      </div>
      <div class="field">
        <label>還原備份 zip</label>
        <input id="restore-file" type="file" accept=".zip">
      </div>
      <div class="field">
        <label>還原確認文字</label>
        <input id="restore-confirm" name="restoreConfirm" placeholder="輸入 RESTORE 才會執行">
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
        <h3>${escapeHtml(scene.purpose)}｜V${scene.version}</h3>
        <p class="muted">${escapeHtml(scene.visualDescription)}</p>
        <p><strong>字幕：</strong>${escapeHtml(scene.subtitle)}</p>
      </div>
      <div class="actions">
        <button class="button secondary" data-action="open-scene" data-scene-id="${scene.id}">查看</button>
        <button class="button secondary" data-action="approve-scene" data-scene-id="${scene.id}">批准</button>
        <button class="button secondary" data-action="regenerate-scene" data-scene-id="${scene.id}">重生</button>
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
    throw new Error(payload.message || "本機服務回應失敗。");
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
    reader.onerror = () => reject(new Error("圖片讀取失敗。"));
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
    export: "匯出",
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
    Approved: "已批准",
    Exporting: "匯出中",
    Completed: "已完成"
  }[value] || value;
}

function stepDescription(value) {
  return {
    Draft: "商品資料與需求已建立。",
    Planning: "產生腳本、場景、旁白、字幕與 Prompt。",
    Generating: "使用本機圖片處理與 FFmpeg 組裝影片。",
    "Partially Failed": "保留已完成資料，可重試失敗步驟。",
    "Ready for Preview": "可以播放預覽並檢查每個場景。",
    Approved: "使用者已批准影片方向。",
    Exporting: "正在輸出完整內容包。",
    Completed: "MP4、字幕、metadata 與內容包已完成。"
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
