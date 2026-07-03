"""
Gemini CLI patcher for Antigravity Unlocker.
Patches CodeAssist eligibility checks so OAuth-authenticated users
in sanctioned regions can use the CLI.
AIzaSy-key users (gemini-api-key auth) don't need these patches.
"""
import os
import sys
import subprocess
import json

appdata = os.environ.get("APPDATA", "")
if not appdata:
    print("ERROR: APPDATA not defined", file=sys.stderr)
    sys.exit(1)

cli_dir = os.path.join(appdata, "npm", "node_modules", "@google", "gemini-cli")
bundle_dir = os.path.join(cli_dir, "bundle")

# Check state of the bundle files to decide next step
needs_reinstall = False
is_patched = False
if os.path.exists(bundle_dir):
    for fname in os.listdir(bundle_dir):
        if not fname.endswith(".js"):
            continue
        fpath = os.path.join(bundle_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        # Old/broken patches → reinstall clean
        if "antigravity-vertex-api" in content or '\\"\\"' in content:
            needs_reinstall = True
            break
        # Correct replacement already applied → skip entirely
        if 'projectId || ""' in content:
            is_patched = True

if needs_reinstall:
    print("Detected old patches. Reinstalling clean @google/gemini-cli first...")
    try:
        import shutil
        if os.path.exists(cli_dir):
            shutil.rmtree(cli_dir)
    except Exception:
        pass
    subprocess.run(["npm", "install", "-g", "@google/gemini-cli@latest"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
elif is_patched:
    # Correct replacement found - only apply if some targets still remain
    pass

# DO NOT force selectedType — let the user keep their existing auth method.
# For AIzaSy keys: "gemini-api-key" works out of the box.
# For AQ. tokens: sign in via Google OAuth, then these patches handle region blocks.

# ── Patch JS bundle files ─────────────────────────────────────────────
# IMPORTANT: inside triple-quoted strings, use plain " for JS quotes.
# \\" would produce \" which does NOT match the original JS code.

# Patch 1a: loadCodeAssist — rewrite try block to catch ineligible tiers
t_loadCodeAssist_try = """      return await this.requestPost(
        "loadCodeAssist",
        req
      );"""

r_loadCodeAssist_try = """      const res = await this.requestPost(
        "loadCodeAssist",
        req
      );
      if (res && !res.currentTier && res.ineligibleTiers && res.ineligibleTiers.length > 0) {
        res.currentTier = { id: UserTierId.STANDARD, hasOnboardedPreviously: true };
        delete res.ineligibleTiers;
      }
      return res;"""

# Patch 1b: loadCodeAssist — replace project-specific 403 with a generic handler
t_loadCodeAssist_catch = """      } else if (isPermissionDeniedError(e2) && req.cloudaicompanionProject === "cloudshell-gca") {
        throw new Error("Access to the default Cloud Shell Gemini project was denied.\\nPlease set your own Google Cloud project by running:\\ngcloud config set project [PROJECT_ID]\\nor setting export GOOGLE_CLOUD_PROJECT=...");
      } else {
        throw e2;
      }"""

r_loadCodeAssist_catch = """      } else if (isPermissionDeniedError(e2) || (Array.isArray(e2) && e2.length > 0 && (isPermissionDeniedError(e2[0]) || isPermissionDeniedError(e2[0]?.error)))) {
        return { currentTier: { id: UserTierId.STANDARD, hasOnboardedPreviously: true }, cloudaicompanionProject: req.cloudaicompanionProject || "" };
      } else {
        throw e2;
      }"""

# Patch 2: listExperiments — return empty instead of throwing when no projectId
t_listExperiments = """  async listExperiments(metadata2) {
    if (!this.projectId) {
      throw new Error("projectId is not defined for CodeAssistServer.");
    }"""

r_listExperiments = """  async listExperiments(metadata2) {
    if (!this.projectId) {
      return { flags: [], experimentIds: [] };
    }"""

# Patch 3: setupUser first location — remove hardcoded project fallback
t_setupUser1 = """    if (!loadRes.cloudaicompanionProject) {
      if (projectId) {
        return {
          projectId,
          userTier: loadRes.paidTier?.id ?? loadRes.currentTier.id ?? UserTierId.STANDARD,
          userTierName: loadRes.paidTier?.name ?? loadRes.currentTier.name,
          paidTier: loadRes.paidTier ?? void 0,
          hasOnboardedPreviously: loadRes.currentTier.hasOnboardedPreviously ?? true
        };
      }
      throwIneligibleOrProjectIdError(loadRes);
    }"""

r_setupUser1 = """    if (!loadRes.cloudaicompanionProject) {
      return {
        projectId: projectId || "",
        userTier: loadRes.paidTier?.id ?? loadRes.currentTier.id ?? UserTierId.STANDARD,
        userTierName: loadRes.paidTier?.name ?? loadRes.currentTier.name,
        paidTier: loadRes.paidTier ?? void 0,
        hasOnboardedPreviously: loadRes.currentTier.hasOnboardedPreviously ?? true
      };
    }"""

# Patch 4: setupUser second location — same fix
t_setupUser2 = """  if (!lroRes.response?.cloudaicompanionProject?.id) {
    if (projectId) {
      return {
        projectId,
        userTier: tier.id ?? UserTierId.STANDARD,
        userTierName: tier.name,
        hasOnboardedPreviously: tier.hasOnboardedPreviously ?? false
      };
    }
    throwIneligibleOrProjectIdError(loadRes);
  }"""

r_setupUser2 = """  if (!lroRes.response?.cloudaicompanionProject?.id) {
    return {
      projectId: projectId || "",
      userTier: tier.id ?? UserTierId.STANDARD,
      userTierName: tier.name,
      hasOnboardedPreviously: tier.hasOnboardedPreviously ?? false
    };
  }"""

# Patch 5: requestPost — fallback to cloudshell-gca on 403
t_requestPost = """  async requestPost(method, req, signal, retryDelay = 100) {
    const res = await this.client.request({
      url: this.getMethodUrl(method),
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.httpOptions.headers
      },
      responseType: "json",
      body: JSON.stringify(req),
      signal,
      retryConfig: {
        retryDelay,
        retry: 3,
        noResponseRetries: 3,
        statusCodesToRetry: [
          [429, 429],
          [499, 499],
          [500, 599]
        ]
      }
    });
    return res.data;
  }"""

r_requestPost = """  async requestPost(method, req, signal, retryDelay = 100) {
    try {
      const res = await this.client.request({
        url: this.getMethodUrl(method),
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...this.httpOptions.headers
        },
        responseType: "json",
        body: JSON.stringify(req),
        signal,
        retryConfig: {
          retryDelay,
          retry: 3,
          noResponseRetries: 3,
          statusCodesToRetry: [
            [429, 429],
            [499, 499],
            [500, 599]
          ]
        }
      });
      return res.data;
    } catch (e) {
      if (isPermissionDeniedError(e)) {
        let settingsProject = "";
        try {
          const { homedir } = await import("os");
          const { existsSync, readFileSync } = await import("fs");
          const { join } = await import("path");
          const settingsPath = join(homedir(), ".gemini", "settings.json");
          if (existsSync(settingsPath)) {
            const settings = JSON.parse(readFileSync(settingsPath, "utf8"));
            if (settings && settings.project) {
              settingsProject = settings.project;
            }
          }
        } catch (err) {}

        let fallbackProject = "";
        if (settingsProject && this.projectId !== settingsProject) {
          fallbackProject = settingsProject;
        } else if (this.projectId !== "cloudshell-gca") {
          fallbackProject = "cloudshell-gca";
        }

        if (fallbackProject) {
          if (req && req.project) req.project = fallbackProject;
          if (req && req.cloudaicompanionProject) req.cloudaicompanionProject = fallbackProject;
          this.projectId = fallbackProject;
          return this.requestPost(method, req, signal, retryDelay);
        }
      }
      throw e;
    }
  }"""

# Patch 6: requestStreamingPost — fallback to cloudshell-gca on 403
t_requestStreamingPost = """  async requestStreamingPost(method, req, signal) {
    const res = await this.client.request({
      url: this.getMethodUrl(method),
      method: "POST",
      params: {
        alt: "sse"
      },
      headers: {
        "Content-Type": "application/json",
        ...this.httpOptions.headers
      },
      responseType: "stream",
      body: JSON.stringify(req),
      signal,
      retry: false
    });
    return async function* (server) {"""

r_requestStreamingPost = """  async requestStreamingPost(method, req, signal) {
    let res;
    try {
      res = await this.client.request({
        url: this.getMethodUrl(method),
        method: "POST",
        params: {
          alt: "sse"
        },
        headers: {
          "Content-Type": "application/json",
          ...this.httpOptions.headers
        },
        responseType: "stream",
        body: JSON.stringify(req),
        signal,
        retry: false
      });
    } catch (e) {
      if (isPermissionDeniedError(e)) {
        let settingsProject = "";
        try {
          const { homedir } = await import("os");
          const { existsSync, readFileSync } = await import("fs");
          const { join } = await import("path");
          const settingsPath = join(homedir(), ".gemini", "settings.json");
          if (existsSync(settingsPath)) {
            const settings = JSON.parse(readFileSync(settingsPath, "utf8"));
            if (settings && settings.project) {
              settingsProject = settings.project;
            }
          }
        } catch (err) {}

        let fallbackProject = "";
        if (settingsProject && this.projectId !== settingsProject) {
          fallbackProject = settingsProject;
        } else if (this.projectId !== "cloudshell-gca") {
          fallbackProject = "cloudshell-gca";
        }

        if (fallbackProject) {
          if (req && req.project) req.project = fallbackProject;
          if (req && req.cloudaicompanionProject) req.cloudaicompanionProject = fallbackProject;
          this.projectId = fallbackProject;
          return this.requestStreamingPost(method, req, signal);
        }
      }
      throw e;
    }
    return async function* (server) {"""

# Patch 7: ModelDialog — filter working models and options dynamically
t_modelDialog = """  const preferredModel = config?.getModel() || GEMINI_MODEL_ALIAS_AUTO;
  const shouldShowPreviewModels = config?.getHasAccessToPreviewModel() ?? false;
  const useGemini31 = config?.getGemini31LaunchedSync?.() ?? false;
  const useGemini3_5Flash = config?.hasGemini35FlashGAAccess?.() ?? false;
  const selectedAuthType = settings.merged.security.auth.selectedType;
  const useCustomToolModel = useGemini31 && selectedAuthType === AuthType.USE_GEMINI;
  const manualModelSelected = (0, import_react55.useMemo)(() => {
    if (config?.getExperimentalDynamicModelConfiguration?.() === true && config.getModelConfigService) {
      const def = config.getModelConfigService().getModelDefinition(preferredModel);
      return def && def.tier !== "auto" && def.isVisible === true ? preferredModel : "";
    }
    const manualModels = [
      DEFAULT_GEMINI_MODEL,
      DEFAULT_GEMINI_FLASH_MODEL,
      DEFAULT_GEMINI_FLASH_LITE_MODEL,
      PREVIEW_GEMINI_MODEL,
      PREVIEW_GEMINI_3_1_MODEL,
      PREVIEW_GEMINI_3_1_CUSTOM_TOOLS_MODEL,
      PREVIEW_GEMINI_FLASH_LITE_MODEL,
      PREVIEW_GEMINI_FLASH_MODEL
    ].filter((m) => m !== "none");
    if (manualModels.includes(preferredModel)) {
      return preferredModel;
    }
    return "";
  }, [preferredModel, config]);
  useKeypress(
    (key) => {
      if (key.name === "escape") {
        if (view === "manual" && hasAccessToProModel) {
          setView("main");
        } else {
          onClose();
        }
        return true;
      }
      if (key.name === "tab") {
        setPersistMode((prev) => !prev);
        return true;
      }
      return false;
    },
    { isActive: true }
  );
  const mainOptions = (0, import_react55.useMemo)(() => {
    if (config?.getExperimentalDynamicModelConfiguration?.() === true && config.getModelConfigService) {
      const allOptions = config.getModelConfigService().getAvailableModelOptions({
        useGemini3_1: useGemini31,
        useGemini3_5Flash,
        useCustomTools: useCustomToolModel,
        hasAccessToPreview: shouldShowPreviewModels,
        hasAccessToProModel
      });
      const list2 = allOptions.filter((o) => o.tier === "auto").map((o) => ({
        value: o.modelId,
        title: o.name,
        description: o.description,
        key: o.modelId
      }));
      list2.push({
        value: "Manual",
        title: manualModelSelected ? `Manual (${getDisplayString(manualModelSelected, config ?? void 0)})` : "Manual",
        description: "Manually select a model",
        key: "Manual"
      });
      return list2;
    }
    const list = [
      {
        value: GEMINI_MODEL_ALIAS_AUTO,
        title: getDisplayString(GEMINI_MODEL_ALIAS_AUTO),
        description: getAutoModelDescription(
          shouldShowPreviewModels,
          useGemini31,
          useGemini3_5Flash
        ),
        key: GEMINI_MODEL_ALIAS_AUTO
      },
      {
        value: "Manual",
        title: manualModelSelected ? `Manual (${getDisplayString(manualModelSelected)})` : "Manual",
        description: "Manually select a model",
        key: "Manual"
      }
    ];
    return list;
  }, [
    config,
    shouldShowPreviewModels,
    manualModelSelected,
    useGemini31,
    useGemini3_5Flash,
    useCustomToolModel,
    hasAccessToProModel
  ]);
  const manualOptions = (0, import_react55.useMemo)(() => {
    if (config?.getExperimentalDynamicModelConfiguration?.() === true && config.getModelConfigService) {
      const allOptions = config.getModelConfigService().getAvailableModelOptions({
        useGemini3_1: useGemini31,
        useGemini3_5Flash,
        useCustomTools: useCustomToolModel,
        hasAccessToPreview: shouldShowPreviewModels,
        hasAccessToProModel
      });
      return allOptions.filter((o) => o.tier !== "auto").map((o) => ({
        value: o.modelId,
        title: o.name,
        key: o.modelId
      }));
    }
    const showGemmaModels = config?.getExperimentalGemma() ?? false;
    const options2 = [
      {
        value: DEFAULT_GEMINI_MODEL,
        title: getDisplayString(DEFAULT_GEMINI_MODEL),
        key: DEFAULT_GEMINI_MODEL
      },
      {
        value: DEFAULT_GEMINI_FLASH_LITE_MODEL,
        title: getDisplayString(DEFAULT_GEMINI_FLASH_LITE_MODEL),
        key: DEFAULT_GEMINI_FLASH_LITE_MODEL
      },
      {
        value: DEFAULT_GEMINI_FLASH_MODEL,
        title: getDisplayString(DEFAULT_GEMINI_FLASH_MODEL),
        key: DEFAULT_GEMINI_FLASH_MODEL
      }
    ];
    if (showGemmaModels) {
      options2.push(
        {
          value: GEMMA_4_31B_IT_MODEL,
          title: getDisplayString(GEMMA_4_31B_IT_MODEL),
          key: GEMMA_4_31B_IT_MODEL
        },
        {
          value: GEMMA_4_26B_A4B_IT_MODEL,
          title: getDisplayString(GEMMA_4_26B_A4B_IT_MODEL),
          key: GEMMA_4_26B_A4B_IT_MODEL
        }
      );
    }
    if (shouldShowPreviewModels) {
      const previewProModel = useGemini31 ? PREVIEW_GEMINI_3_1_MODEL : PREVIEW_GEMINI_MODEL;
      const previewProValue = useCustomToolModel ? PREVIEW_GEMINI_3_1_CUSTOM_TOOLS_MODEL : previewProModel;
      const previewOptions = [
        {
          value: previewProValue,
          title: getDisplayString(previewProModel),
          key: previewProModel
        },
        {
          value: PREVIEW_GEMINI_FLASH_MODEL,
          title: getDisplayString(PREVIEW_GEMINI_FLASH_MODEL),
          key: PREVIEW_GEMINI_FLASH_MODEL
        }
      ];
      if (PREVIEW_GEMINI_FLASH_LITE_MODEL !== "none") {
        previewOptions.push({
          value: PREVIEW_GEMINI_FLASH_LITE_MODEL,
          title: getDisplayString(PREVIEW_GEMINI_FLASH_LITE_MODEL),
          key: PREVIEW_GEMINI_FLASH_LITE_MODEL
        });
      }
      options2.unshift(...previewOptions);
    }
    if (!hasAccessToProModel) {
      return options2.filter((option) => !isProModel(option.value));
    }
    return options2;
  }, [
    shouldShowPreviewModels,
    useGemini31,
    useGemini3_5Flash,
    useCustomToolModel,
    hasAccessToProModel,
    config
  ]);"""


r_modelDialog = r"""  const preferredModel = config?.getModel() || GEMINI_MODEL_ALIAS_AUTO;
  const shouldShowPreviewModels = true;
  const useGemini31 = config?.getGemini31LaunchedSync?.() ?? false;
  const useGemini3_5Flash = config?.hasGemini35FlashGAAccess?.() ?? false;
  const selectedAuthType = settings.merged.security.auth.selectedType;
  const [dynamicModels, setDynamicModels] = (0, import_react55.useState)([]);
  const API_KEY_WORKING_MODELS = (0, import_react55.useMemo)(() => new Set([
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-pro",
    "gemini-3-pro-preview",
    "gemini-3.1-pro-preview"
  ]), []);
  const OAUTH_WORKING_MODELS = (0, import_react55.useMemo)(() => new Set([
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview"
  ]), []);
  const isWorkingModel = (0, import_react55.useCallback)((model) => {
    if (selectedAuthType === "gemini-api-key") {
      return API_KEY_WORKING_MODELS.has(model);
    }
    return OAUTH_WORKING_MODELS.has(model);
  }, [selectedAuthType, API_KEY_WORKING_MODELS, OAUTH_WORKING_MODELS]);
  (0, import_react55.useEffect)(() => {
    async function checkAccess() {
      if (!config) return;
      const noAccess = await config.getProModelNoAccess();
      setHasAccessToProModel(true);
      if (noAccess) {
        setView("manual");
      }
    }
    void checkAccess();
  }, [config]);
  (0, import_react55.useEffect)(() => {
    async function loadDynamicModels() {
      if (!config) return;
      const authType = config.contentGeneratorConfig?.authType;
      try {
        if (authType === "gemini-api-key") {
          const apiKey = config.contentGeneratorConfig?.apiKey || process.env["GEMINI_API_KEY"] || process.env["GOOGLE_API_KEY"];
          if (apiKey) {
            const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`;
            const res = await fetch(url);
            if (res.ok) {
              const data = await res.json();
              if (data && Array.isArray(data.models)) {
                const list = data.models
                  .filter((m) => {
                    const id = m.name.replace(/^models\//, "");
                    return API_KEY_WORKING_MODELS.has(id);
                  })
                  .map((m) => {
                    const id = m.name.replace(/^models\//, "");
                    return {
                      value: id,
                      title: m.displayName || id,
                      key: id
                    };
                  });
                setDynamicModels(list);
              }
            }
          }
        } else if (authType === "oauth-personal" || authType === "compute-adc") {
          const quota = await config.refreshUserQuota().catch(() => null);
          const buckets = quota?.buckets || config.getLastRetrievedQuota()?.buckets;
          if (buckets && buckets.length > 0) {
            const list = buckets
              .filter((b) => {
                const id = b.modelId;
                return id && OAUTH_WORKING_MODELS.has(id);
              })
              .map((b) => ({
                value: b.modelId,
                title: getDisplayString(b.modelId),
                key: b.modelId
              }));
            setDynamicModels(list);
          }
        }
      } catch (e) {}
    }
    void loadDynamicModels();
  }, [config, API_KEY_WORKING_MODELS, OAUTH_WORKING_MODELS]);
  const useCustomToolModel = useGemini31 && selectedAuthType === "gemini-api-key" /* USE_GEMINI */;
  const manualModelSelected = (0, import_react55.useMemo)(() => {
    return isWorkingModel(preferredModel) ? preferredModel : "";
  }, [preferredModel, isWorkingModel]);
  const mainOptions = (0, import_react55.useMemo)(() => {
    const defaultMainModels = selectedAuthType === "gemini-api-key" ? [
      "gemini-3.5-flash",
      "gemini-2.5-flash",
      "gemini-2.5-flash-lite",
      "gemini-3.1-flash-lite-preview",
      "gemini-3.1-flash-lite",
      "gemma-4-26b-a4b-it",
      "gemma-4-31b-it",
      "gemini-2.5-pro",
      "gemini-3-pro-preview",
      "gemini-3.1-pro-preview",
      "Manual"
    ] : [
      "gemini-2.5-flash",
      "gemini-2.5-flash-lite",
      "gemini-2.5-pro",
      "gemini-3.1-flash-lite",
      "gemini-3.1-flash-lite-preview",
      "Manual"
    ];
    return defaultMainModels.map((m) => ({
      value: m,
      title: getDisplayString(m),
      key: m
    }));
  }, [
    selectedAuthType,
    shouldShowPreviewModels,
    manualModelSelected,
    useGemini31,
    useGemini3_5Flash,
    useCustomToolModel,
    hasAccessToProModel
  ]);
  useKeypress(
    (key) => {
      if (key.name === "escape") {
        if (view === "manual" && hasAccessToProModel) {
          setView("main");
        } else {
          onClose();
        }
        return true;
      }
      if (key.name === "tab") {
        setPersistMode((prev) => !prev);
        return true;
      }
      return false;
    },
    { isActive: true }
  );
  const manualOptions = (0, import_react55.useMemo)(() => {
    if (dynamicModels && dynamicModels.length > 0) {
      if (!hasAccessToProModel) {
        return dynamicModels.filter((option) => !isProModel(option.value));
      }
      return dynamicModels;
    }
    if (config?.getExperimentalDynamicModelConfiguration?.() === true && config.getModelConfigService) {
      const allOptions = config.getModelConfigService().getAvailableModelOptions({
        useGemini3_1: useGemini31,
        useGemini3_5Flash,
        useCustomTools: useCustomToolModel,
        hasAccessToPreview: shouldShowPreviewModels,
        hasAccessToProModel
      });
      return allOptions.filter((o) => o.tier !== "auto").map((o) => ({
        value: o.modelId,
        title: o.name,
        key: o.modelId
      }));
    }
    const authType = config?.contentGeneratorConfig?.authType;
    let options2 = [];
    if (authType === "oauth-personal" || authType === "compute-adc") {
      const buckets = config?.getLastRetrievedQuota()?.buckets;
      if (buckets && buckets.length > 0) {
        options2 = buckets.filter((b) => b.modelId && OAUTH_WORKING_MODELS.has(b.modelId)).map((b) => ({
          value: b.modelId,
          title: getDisplayString(b.modelId),
          key: b.modelId
        }));
      } else {
        const defaultOAuthModels = [
          "gemini-2.5-flash",
          "gemini-2.5-flash-lite",
          "gemini-2.5-pro",
          "gemini-3.1-flash-lite",
          "gemini-3.1-flash-lite-preview"
        ];
        options2 = defaultOAuthModels.map((m) => ({
          value: m,
          title: getDisplayString(m),
          key: m
        }));
      }
    } else {
      const defaultApiKeyModels = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite",
        "gemma-4-26b-a4b-it",
        "gemma-4-31b-it",
        "gemini-2.5-pro",
        "gemini-3-pro-preview",
        "gemini-3.1-pro-preview"
      ];
      options2 = defaultApiKeyModels.map((m) => ({
        value: m,
        title: getDisplayString(m),
        key: m
      }));
    }
    if (!hasAccessToProModel) {
      return options2.filter((option) => !isProModel(option.value));
    }
    return options2;
  }, [
    shouldShowPreviewModels,
    useGemini31,
    useGemini3_5Flash,
    useCustomToolModel,
    hasAccessToProModel,
    config,
    dynamicModels,
    API_KEY_WORKING_MODELS,
    OAUTH_WORKING_MODELS
  ]);"""

t_modelDialog_alt = t_modelDialog.replace(
    '  const useCustomToolModel = useGemini31 && selectedAuthType === AuthType.USE_GEMINI;',
    '  const useCustomToolModel = useGemini31 && selectedAuthType === "gemini-api-key" /* USE_GEMINI */;'
)

# Patch 11: Force hasGemini35FlashGAAccess to return false (preventing 2.5-flash fallback to 3.5-flash)
t_gaAccess = """  hasGemini35FlashGAAccess() {
    const authType = this.contentGeneratorConfig?.authType;"""

r_gaAccess = """  hasGemini35FlashGAAccess() {
    return false;
    const authType = this.contentGeneratorConfig?.authType;"""

# Patch 12: Force getApiKeyFromEnv to return undefined if settings.json has oauth selected
t_getApiKeyFromEnv = """function getApiKeyFromEnv() {
  const envGoogleApiKey = getEnv("GOOGLE_API_KEY");
  const envGeminiApiKey = getEnv("GEMINI_API_KEY");
  if (envGoogleApiKey && envGeminiApiKey) {
    console.warn("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.");
  }
  return envGoogleApiKey || envGeminiApiKey || void 0;
}"""

r_getApiKeyFromEnv = """function getApiKeyFromEnv() {
  try {
    const { homedir } = require("os");
    const { existsSync, readFileSync } = require("fs");
    const { join } = require("path");
    const settingsPath = join(homedir(), ".gemini", "settings.json");
    if (existsSync(settingsPath)) {
      const settings = JSON.parse(readFileSync(settingsPath, "utf8"));
      if (settings && settings.project) {
        process.env.GOOGLE_CLOUD_PROJECT = settings.project;
      }
      if (settings?.security?.auth?.selectedType === "oauth-personal" || settings?.security?.auth?.selectedType === "compute-adc") {
        return void 0;
      }
    }
  } catch (err) {}
  const envGoogleApiKey = getEnv("GOOGLE_API_KEY");
  const envGeminiApiKey = getEnv("GEMINI_API_KEY");
  if (envGoogleApiKey && envGeminiApiKey) {
    console.warn("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.");
  }
  return envGoogleApiKey || envGeminiApiKey || void 0;
}"""

# Patch 13: Initialize process.env.GOOGLE_CLOUD_PROJECT on chunk load
t_chunkInit = """const require = (await import('node:module')).createRequire(import.meta.url); const __chunk_filename = (await import('node:url')).fileURLToPath(import.meta.url); const __chunk_dirname = (await import('node:path')).dirname(__chunk_filename);"""

r_chunkInit = """const require = (await import('node:module')).createRequire(import.meta.url); const __chunk_filename = (await import('node:url')).fileURLToPath(import.meta.url); const __chunk_dirname = (await import('node:path')).dirname(__chunk_filename);
try {
  const { homedir } = require("os");
  const { existsSync, readFileSync } = require("fs");
  const { join } = require("path");
  const settingsPath = join(homedir(), ".gemini", "settings.json");
  if (existsSync(settingsPath)) {
    const settings = JSON.parse(readFileSync(settingsPath, "utf8"));
    if (settings && settings.project) {
      process.env.GOOGLE_CLOUD_PROJECT = settings.project;
    }
  }
} catch (err) {}"""

patches = [
    (t_loadCodeAssist_try, r_loadCodeAssist_try),
    (t_loadCodeAssist_catch, r_loadCodeAssist_catch),
    (t_listExperiments, r_listExperiments),
    (t_setupUser1, r_setupUser1),
    (t_setupUser2, r_setupUser2),
    (t_requestPost, r_requestPost),
    (t_requestStreamingPost, r_requestStreamingPost),
    (t_modelDialog, r_modelDialog),
    (t_modelDialog_alt, r_modelDialog),
    (t_gaAccess, r_gaAccess),
    (t_getApiKeyFromEnv, r_getApiKeyFromEnv),
    (t_chunkInit, r_chunkInit),
]

patched_files = []
if os.path.exists(bundle_dir):
    for fname in os.listdir(bundle_dir):
        if not fname.endswith(".js"):
            continue
        fpath = os.path.join(bundle_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        changed = False
        content_norm = content.replace("\r\n", "\n")
        for target, replacement in patches:
            target_norm = target.replace("\r\n", "\n")
            replacement_norm = replacement.replace("\r\n", "\n")
            if target_norm in content_norm:
                content_norm = content_norm.replace(target_norm, replacement_norm)
                changed = True

        if changed:
            # Write back with Unix newlines (or keep the normalized content)
            with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                f.write(content_norm)
            patched_files.append(fname)

print(f"OK: patched {len(patched_files)} files")
