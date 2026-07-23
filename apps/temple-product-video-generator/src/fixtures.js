export const platforms = [
  "Instagram Reels",
  "TikTok",
  "YouTube Shorts",
  "Shorts"
];

export const providerRegistry = [
  {
    id: "local-comfyui",
    name: "Local ComfyUI",
    role: "Image and video generation",
    status: "Prepared placeholder",
    approval: "Local runtime connection required later"
  },
  {
    id: "local-whisper",
    name: "Local Whisper",
    role: "Speech recognition and subtitle timing",
    status: "Prepared placeholder",
    approval: "Local model path required later"
  },
  {
    id: "ffmpeg",
    name: "FFmpeg",
    role: "Video assembly, format conversion, export packaging",
    status: "Prepared placeholder",
    approval: "Local executable validation required later"
  },
  {
    id: "future-cloud-provider",
    name: "Future Cloud Provider",
    role: "Optional cloud image, video, narration, or enhancement",
    status: "Prepared placeholder",
    approval: "CEO approval required before paid or external API usage"
  }
];

export const sampleProducts = [
  {
    id: "product-energy-candle",
    name: "Temple Energy Candle",
    category: "Candle",
    description: "A handmade candle designed for meditation, calm, and daily ritual.",
    sellingPoint: "Helps create a focused and peaceful ritual space.",
    mainImage: "materials/temple-energy-candle-main.jpg",
    tags: ["candle", "ritual", "calm", "gift"]
  },
  {
    id: "product-blessing-bracelet",
    name: "Temple Blessing Bracelet",
    category: "Accessory",
    description: "A simple bracelet prepared for daily intention and personal blessing.",
    sellingPoint: "Easy to wear every day as a quiet reminder of intention.",
    mainImage: "materials/temple-blessing-bracelet-main.jpg",
    tags: ["bracelet", "daily ritual", "gift"]
  }
];

export const sceneBlueprint = [
  {
    id: "scene-hook",
    order: 1,
    purpose: "Hook",
    duration: 3,
    visualGoal: "Show the product clearly in a calm first frame.",
    narrationGoal: "Open with a warm question or simple invitation.",
    subtitleGoal: "Short first line that is readable in one glance.",
    music: "Soft ambient opening",
    transition: "Gentle fade in"
  },
  {
    id: "scene-introduction",
    order: 2,
    purpose: "Introduction",
    duration: 5,
    visualGoal: "Introduce product identity and setting.",
    narrationGoal: "Explain what the product is in plain Traditional Chinese.",
    subtitleGoal: "Name the product and core use.",
    music: "Warm, steady background",
    transition: "Slow dissolve"
  },
  {
    id: "scene-features",
    order: 3,
    purpose: "Product Features",
    duration: 7,
    visualGoal: "Show product texture, usage detail, packaging, or close-up.",
    narrationGoal: "State one or two concrete product features.",
    subtitleGoal: "Feature-focused phrase with no exaggerated claim.",
    music: "Light movement",
    transition: "Cut on detail"
  },
  {
    id: "scene-spiritual-value",
    order: 4,
    purpose: "Spiritual Value",
    duration: 6,
    visualGoal: "Show the product in a quiet ritual moment.",
    narrationGoal: "Connect product to calm, intention, and daily practice.",
    subtitleGoal: "Gentle emotional value, not a guaranteed promise.",
    music: "Calm ambient swell",
    transition: "Soft fade"
  },
  {
    id: "scene-cta",
    order: 5,
    purpose: "Call To Action",
    duration: 4,
    visualGoal: "Return to a clean product shot.",
    narrationGoal: "Invite the viewer to learn more or save the product.",
    subtitleGoal: "Gentle CTA.",
    music: "Resolved ending phrase",
    transition: "Fade to end"
  },
  {
    id: "scene-ending",
    order: 6,
    purpose: "Ending",
    duration: 3,
    visualGoal: "Close with product name and brand presence.",
    narrationGoal: "End calmly and clearly.",
    subtitleGoal: "Brand-safe closing line.",
    music: "Soft close",
    transition: "Fade out"
  }
];

export const pipelineStages = [
  {
    id: "intent",
    name: "User Intent Analysis",
    description: "Understand Chinese request, product type, target audience, and marketing objective."
  },
  {
    id: "knowledge",
    name: "Knowledge Loading",
    description: "Load Temple Brand DNA, product information, content model, and product spec."
  },
  {
    id: "story",
    name: "Story Planning",
    description: "Build video outline, scene order, and emotional rhythm."
  },
  {
    id: "scenes",
    name: "Scene Planning",
    description: "Prepare purpose, duration, visual goal, narration goal, and subtitle goal for every scene."
  },
  {
    id: "prompts",
    name: "Prompt Generation",
    description: "Create traceable placeholder prompt records for image, video, narration, subtitle, and thumbnail."
  },
  {
    id: "providers",
    name: "Provider Selection",
    description: "Reserve Local ComfyUI, Local Whisper, FFmpeg, and future cloud provider slots."
  },
  {
    id: "quality",
    name: "Quality Check",
    description: "Validate required scenes, brand tone, caption, subtitle, metadata, and export readiness."
  },
  {
    id: "preview",
    name: "Preview Package",
    description: "Prepare a reviewable placeholder preview package."
  }
];
