import { pipelineStages, providerRegistry, sceneBlueprint } from "./fixtures.js";

export function validateProjectInput(product, draft) {
  const errors = [];

  if (!product?.name?.trim()) errors.push("Product name is required.");
  if (!product?.description?.trim()) errors.push("Product description is required.");
  if (!product?.sellingPoint?.trim()) errors.push("Main selling point is required.");
  if (!product?.mainImage?.trim()) errors.push("At least one product photo reference is required.");
  if (!draft?.targetPlatform?.trim()) errors.push("Target platform is required.");
  if (!draft?.chineseDescription?.trim()) errors.push("Chinese video description is required.");

  return {
    ok: errors.length === 0,
    errors
  };
}

export function createDraftProject(product, draft, projectId) {
  return {
    id: projectId,
    productId: product.id,
    productName: product.name,
    createdAt: new Date().toISOString(),
    targetPlatform: draft.targetPlatform,
    language: "Traditional Chinese",
    tone: draft.tone,
    lengthTarget: draft.lengthTarget,
    chineseDescription: draft.chineseDescription,
    materialNotes: draft.materialNotes,
    reviewStatus: "Draft",
    generationStatus: "Not Started",
    scenes: [],
    promptRecords: [],
    preview: null,
    metadata: null
  };
}

export function buildPreviewPackage(project, product) {
  const scenes = sceneBlueprint.map((scene) => ({
    ...scene,
    version: 1,
    status: "Generated Placeholder",
    visualDescription: `${scene.visualGoal} Use ${product.name} as the central visual reference.`,
    narration: buildNarration(scene.purpose, product),
    subtitle: buildSubtitle(scene.purpose, product),
    promptDirection: `Traceable ${scene.purpose.toLowerCase()} visual prompt direction for ${product.name}.`
  }));

  const promptRecords = scenes.flatMap((scene) => [
    buildPromptRecord(project.id, product.id, scene.id, "Visual"),
    buildPromptRecord(project.id, product.id, scene.id, "Narration"),
    buildPromptRecord(project.id, product.id, scene.id, "Subtitle")
  ]);

  const metadata = {
    projectId: project.id,
    productName: product.name,
    createdDate: project.createdAt,
    targetPlatform: project.targetPlatform,
    sourceImageReference: product.mainImage,
    sceneCount: scenes.length,
    promptVersion: "V1 Alpha Placeholder",
    providerPath: providerRegistry.map((provider) => provider.name).join(" -> "),
    reviewStatus: "Needs Review",
    exportStatus: "Not Exported"
  };

  return {
    ...project,
    reviewStatus: "Needs Review",
    generationStatus: "Completed",
    scenes,
    promptRecords,
    preview: {
      id: `${project.id}-preview-001`,
      createdAt: new Date().toISOString(),
      status: "Reviewable Placeholder",
      title: `${product.name} V1 Alpha Preview`,
      caption: `把${product.name}放進日常儀式裡，讓空間慢慢安定下來。`,
      seoKeywords: [product.name, product.category, "Temple", "ritual", "calm"],
      thumbnailSuggestion: "Use the clearest product close-up with a short Traditional Chinese cover line."
    },
    metadata
  };
}

export function regenerateScene(project, sceneId) {
  if (!project?.scenes?.length) return project;

  return {
    ...project,
    reviewStatus: "Needs Review",
    scenes: project.scenes.map((scene) => {
      if (scene.id !== sceneId) return scene;

      return {
        ...scene,
        version: scene.version + 1,
        status: "Regenerated Placeholder",
        narration: `${scene.narration} 這一幕已重新生成為第 ${scene.version + 1} 版。`,
        subtitle: `${scene.subtitle} V${scene.version + 1}`
      };
    })
  };
}

export function approvePreview(project) {
  if (!project?.preview) return project;

  return {
    ...project,
    reviewStatus: "Approved",
    metadata: {
      ...project.metadata,
      reviewStatus: "Approved"
    }
  };
}

export function prepareExportPackage(project) {
  if (!project?.preview || project.reviewStatus !== "Approved") {
    return {
      ok: false,
      reason: "Preview must be approved before export."
    };
  }

  return {
    ok: true,
    package: {
      id: `${project.id}-export-001`,
      status: "Prepared Placeholder",
      targetPlatform: project.targetPlatform,
      finalMp4Reference: `videos/factory/exports/${project.id}/final-placeholder.mp4`,
      captionReference: `${project.id}/caption.txt`,
      subtitleReference: `${project.id}/subtitles.srt`,
      metadataReference: `${project.id}/metadata.json`,
      thumbnailSuggestion: project.preview.thumbnailSuggestion,
      createdAt: new Date().toISOString()
    }
  };
}

export { pipelineStages, providerRegistry };

function buildPromptRecord(projectId, productId, sceneId, category) {
  return {
    projectId,
    productId,
    sceneId,
    category,
    version: "V1 Alpha Placeholder",
    sourceDocuments: [
      "PRODUCT_SPEC_V1.md",
      "CONTENT_MODEL_V1.md",
      "AI_REASONING_PIPELINE_V1.md",
      "PROMPT_SYSTEM_V1.md"
    ],
    reviewStatus: "Generated Placeholder"
  };
}

function buildNarration(purpose, product) {
  const lines = {
    Hook: `你是否想為每天留下一個安定的片刻？`,
    Introduction: `這是${product.name}，為日常儀式與安靜時光準備。`,
    "Product Features": `它以清楚的質感與簡潔設計，讓使用時刻更容易被感受。`,
    "Spiritual Value": `當你慢下來，它陪你把注意力帶回當下。`,
    "Call To Action": `如果你也想建立自己的儀式感，可以先從這一份開始。`,
    Ending: `Temple AI Studio，為每個產品留下溫柔而清楚的故事。`
  };

  return lines[purpose] || `以溫暖清楚的方式介紹${product.name}。`;
}

function buildSubtitle(purpose, product) {
  const lines = {
    Hook: "為今天留一個安定片刻",
    Introduction: `${product.name}`,
    "Product Features": "看得見的細節與質感",
    "Spiritual Value": "把注意力帶回當下",
    "Call To Action": "從一份日常儀式開始",
    Ending: "Temple AI Studio"
  };

  return lines[purpose] || product.name;
}
