import { sampleProducts } from "./fixtures.js";

const STORAGE_KEY = "temple-product-video-generator-alpha";

export function createInitialState() {
  return {
    products: sampleProducts,
    selectedProductId: sampleProducts[0].id,
    currentProject: null,
    selectedSceneId: "scene-hook",
    progressIndex: 0,
    lastNotice: "Alpha prototype loaded.",
    exportPackage: null
  };
}

export function loadState() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return createInitialState();
    }

    const parsed = JSON.parse(stored);
    return {
      ...createInitialState(),
      ...parsed
    };
  } catch {
    return createInitialState();
  }
}

export function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function resetState() {
  const fresh = createInitialState();
  saveState(fresh);
  return fresh;
}

export function createProjectId() {
  const date = new Date();
  const stamp = date.toISOString().slice(0, 10).replaceAll("-", "");
  const token = Math.random().toString(36).slice(2, 7);
  return `tpvg-${stamp}-${token}`;
}

export function getSelectedProduct(state) {
  return state.products.find((product) => product.id === state.selectedProductId) || state.products[0];
}
