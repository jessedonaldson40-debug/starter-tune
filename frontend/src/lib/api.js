import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ---- starter tune ----
export const predictHp = (intake) => api.post("/starter-tune/predict-hp", intake).then(r => r.data);
export const vePreview = (intake) => api.post("/starter-tune/ve-preview", intake).then(r => r.data);
export const safetyEnvelope = (intake) => api.post("/starter-tune/safety-envelope", intake).then(r => r.data);
export const generateTune = (intake, adjustments) =>
  api.post("/starter-tune/generate", { intake, adjustments }).then(r => r.data);

// ---- profiles ----
export const listProfiles = () => api.get("/profiles").then(r => r.data);
export const getProfile = (id) => api.get(`/profiles/${id}`).then(r => r.data);
export const createProfile = (payload) => api.post("/profiles", payload).then(r => r.data);
export const deleteProfile = (id) => api.delete(`/profiles/${id}`).then(r => r.data);
export const regenerateProfile = (id, intake, adjustments, note) =>
  api.post(`/profiles/${id}/regenerate`, { intake, adjustments, note }).then(r => r.data);
export const revertProfile = (id, idx) =>
  api.post(`/profiles/${id}/revert/${idx}`).then(r => r.data);
export const compareGenerations = (id, a, b) =>
  api.get(`/profiles/${id}/compare/${a}/${b}`).then(r => r.data);

// ---- exports ----
export const listExportTargets = () => api.get("/export/targets").then(r => r.data);
export const exportProfile = (id, target) =>
  api.post(`/profiles/${id}/export/${target}`).then(r => r.data);

// ---- DIAG-SIM ----
export const listDiagSimScenarios = () => api.get("/diagsim/scenarios").then(r => r.data);
export const runDiagSim = (profileId, scenario = "wot_pull", seed = null) =>
  api.post(`/profiles/${profileId}/diagsim/run`, { scenario, seed }).then(r => r.data);
export const getDiagSimSession = (sessionId) =>
  api.get(`/diagsim/sessions/${sessionId}`).then(r => r.data);
export const listProfileDiagSimSessions = (profileId) =>
  api.get(`/profiles/${profileId}/diagsim/sessions`).then(r => r.data);

// ---- Tune Inspector ----
export const runInspectorAudit = (profileId) =>
  api.post(`/profiles/${profileId}/inspector/audit`).then(r => r.data);
export const getInspectorReport = (reportId) =>
  api.get(`/inspector/reports/${reportId}`).then(r => r.data);
export const listProfileInspectorReports = (profileId) =>
  api.get(`/profiles/${profileId}/inspector/reports`).then(r => r.data);
