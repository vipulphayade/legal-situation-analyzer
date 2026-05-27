const form = document.getElementById("analyze-form");
const descriptionField = document.getElementById("description");
const submitButton = document.getElementById("submit-button");
const statusText = document.getElementById("status-text");
const resultContainer = document.getElementById("result");
const followupPanel = document.getElementById("followup-panel");
const followupForm = document.getElementById("followup-form");
const followupField = document.getElementById("followup-question");
const followupButton = document.getElementById("followup-button");
const followupStatus = document.getElementById("followup-status");
const followupResult = document.getElementById("followup-result");

let lastContext = null;

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const renderList = (items) => {
  if (!Array.isArray(items) || items.length === 0) {
    return "<li>No specific details available.</li>";
  }
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
};

const renderConditions = (items) => {
  if (!Array.isArray(items) || items.length === 0) {
    return `<p class="empty-note">No special condition details were found for this result.</p>`;
  }
  return items
    .map(
      (item) => `
        <article class="condition-card">
          <h4>${escapeHtml(item?.requirement || "Requirement not specified")}</h4>
          <p>${escapeHtml(item?.plain_explanation || "No plain-language explanation was provided.")}</p>
        </article>
      `
    )
    .join("");
};

const renderRelatedBylaws = (items) => {
  if (!Array.isArray(items) || items.length === 0) {
    return `<p class="empty-note">No closely linked supporting bye-laws were found.</p>`;
  }
  return items
    .map(
      (item) => `
        <article class="related-rule">
          <div class="related-rule-topline">
            <strong>Bye-law ${escapeHtml(item.section || "")} ${item.subsection ? `(${escapeHtml(item.subsection)})` : ""}</strong>
            <span class="score-pill">${escapeHtml(Math.round((Number(item.score) || 0) * 100))}%</span>
          </div>
          <p class="related-title">${escapeHtml(item.title || "")}</p>
          <p class="related-summary">${escapeHtml(item.statement || item.why_this_applies || "")}</p>
        </article>
      `
    )
    .join("");
};

const renderRelatedRules = (items) => {
  if (!Array.isArray(items) || items.length === 0) {
    return `<p class="empty-note">No closely linked supporting rules were found.</p>`;
  }
  return items
    .map(
      (item) => `
        <article class="related-rule">
          <strong>${escapeHtml(item.section)}${item.subsection ? `(${escapeHtml(item.subsection)})` : ""}</strong>
          <p>${escapeHtml(item.title)}</p>
        </article>
      `
    )
    .join("");
};

const renderStructuredFacts = (facts) => {
  if (!facts || typeof facts !== "object") {
    return `<p class="empty-note">No structured legal facts were provided.</p>`;
  }

  if (Array.isArray(facts)) {
    if (facts.length === 0) {
      return `<p class="empty-note">No structured legal facts were provided.</p>`;
    }
    return facts
      .map((item) => {
        if (item && typeof item === "object") {
          const title = item.title || item.label || item.name || "Fact";
          const value = item.value || item.text || item.description || JSON.stringify(item);
          return `
            <article class="condition-card">
              <h4>${escapeHtml(title)}</h4>
              <p>${escapeHtml(value)}</p>
            </article>
          `;
        }
        return `
          <article class="condition-card">
            <h4>Fact</h4>
            <p>${escapeHtml(item)}</p>
          </article>
        `;
      })
      .join("");
  }

  const entries = Object.entries(facts).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (entries.length === 0) {
    return `<p class="empty-note">No structured legal facts were provided.</p>`;
  }

  return entries
    .map(
      ([key, value]) => `
        <article class="condition-card">
          <h4>${escapeHtml(key.replaceAll("_", " "))}</h4>
          <p>${escapeHtml(typeof value === "object" ? JSON.stringify(value) : value)}</p>
        </article>
      `
    )
    .join("");
};

const renderCollapsibleSection = (title, content, sectionClass = "") => `
  <article class="card result-block accordion ${sectionClass}" data-accordion>
    <button type="button" class="accordion-header" aria-expanded="false">
      <span>${escapeHtml(title)}</span>
      <span class="accordion-icon" aria-hidden="true">+</span>
    </button>
    <div class="accordion-content">
      ${content}
    </div>
  </article>
`;

const initializeCollapsibles = (scope) => {
  const toggles = scope.querySelectorAll(".accordion-header");
  toggles.forEach((toggle) => {
    const accordion = toggle.closest(".accordion");
    const icon = toggle.querySelector(".accordion-icon");
    if (!accordion) return;
    toggle.addEventListener("click", () => {
      const isOpen = accordion.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(isOpen));
      if (icon) icon.textContent = isOpen ? "-" : "+";
    });
  });
};

const resetFollowup = () => {
  if (followupField) followupField.value = "";
  if (followupResult) {
    followupResult.innerHTML = "";
    followupResult.classList.add("hidden");
  }
  if (followupStatus) followupStatus.textContent = "";
  if (followupPanel) followupPanel.classList.add("hidden");
};

const renderResult = (payload) => {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  const confidence = Number.isFinite(Number(safePayload.confidence))
    ? Math.max(0, Math.min(1, Number(safePayload.confidence)))
    : 0;
  const confidencePercent = Math.round(confidence * 100);
  const confidenceLabel = safePayload.confidence_label || (confidence >= 0.82 ? "Strong Match" : confidence >= 0.6 ? "Likely Relevant" : confidence >= 0.4 ? "Broad Topic Match" : "Needs Clarification");
  const bylawLabel = safePayload.section ? `Bye-law ${escapeHtml(safePayload.section)}${safePayload.subsection ? `(${escapeHtml(safePayload.subsection)})` : ""}` : "Needs clarification";
  const relatedBylaws = Array.isArray(safePayload.related_bylaws) ? safePayload.related_bylaws : [];
  const relatedRules = Array.isArray(safePayload.related_rules) ? safePayload.related_rules : [];
  const clarificationQuestions = Array.isArray(safePayload.clarification_questions) ? safePayload.clarification_questions : [];
  const conditionsRequired = Array.isArray(safePayload.conditions_required) ? safePayload.conditions_required : [];
  const possibleChallenges = Array.isArray(safePayload.possible_challenges) ? safePayload.possible_challenges : [];
  const relatedStatutes = Array.isArray(safePayload.related_statutes) ? safePayload.related_statutes : [];
  const whenMayNotApply = Array.isArray(safePayload.when_may_not_apply) ? safePayload.when_may_not_apply : [];
  const structuredFacts = safePayload.structured_specific_data || safePayload.structured_legal_facts || null;
  const officialText =
    safePayload.source_grounded_official_text ||
    safePayload.official_legal_text ||
    safePayload.official_excerpt ||
    safePayload.citation ||
    safePayload.statement ||
    "No official legal text was provided.";

  lastContext = safePayload;
  followupPanel.classList.remove("hidden");
  resultContainer.classList.remove("hidden");
  resultContainer.className = "";
  resultContainer.innerHTML = `
    <div class="result-grid">
      <article class="card result-block accent rule-card">
        <span class="result-label">Relevant bye-law</span>
        <h3>${bylawLabel}</h3>
        <div class="summary-meta">
          <div>
            <span class="result-label">Rule title</span>
            <p>${escapeHtml(payload.title || "Not identified")}</p>
          </div>
          <div>
            <span class="result-label">Grounding status</span>
            <p>${escapeHtml(safePayload.official_grounding_status || "Not specified")}</p>
          </div>
          <div class="confidence-box">
            <span class="result-label">Confidence score</span>
            <div class="confidence-copy">
              <span>${escapeHtml(confidenceLabel)}</span>
              <strong>${escapeHtml(confidencePercent)}%</strong>
            </div>
            <div class="confidence-track" aria-hidden="true">
              <span class="confidence-fill" style="width: ${confidencePercent}%;"></span>
            </div>
          </div>
        </div>
      </article>

      <article class="card result-block explanation-card">
        <span class="result-label">Official legal text</span>
        <p>${escapeHtml(officialText)}</p>
      </article>

      <article class="card result-block explanation-card">
        <span class="result-label">Plain English</span>
        <p>${escapeHtml(safePayload.explanation || "No plain-English explanation was provided.")}</p>
      </article>

      <article class="card result-block example-card">
        <span class="result-label">Why this matched</span>
        <p>${escapeHtml(safePayload.why_this_applies || "The query appears related to this bye-law based on the issue type, topic, or procedure.")}</p>
      </article>

      <article class="card result-block conditions-card">
        <span class="result-label">Practical guidance</span>
        <p>${escapeHtml(safePayload.practical_guidance || "Keep written records, notices, meeting minutes, and supporting documents before acting.")}</p>
      </article>

      ${relatedBylaws.length
        ? renderCollapsibleSection(
            "Related bye-laws (near score)",
            `<div class="related-rule-grid">${renderRelatedBylaws(relatedBylaws)}</div>`
          )
        : renderCollapsibleSection(
            "Related bye-laws (near score)",
            `<div class="related-rule-grid">${renderRelatedRules(relatedRules)}</div>`
          )
      }

      <article class="card result-block conditions-card">
        <span class="result-label">When this may NOT apply</span>
        <ul>${renderList(whenMayNotApply)}</ul>
      </article>

      ${safePayload.needs_clarification || clarificationQuestions.length
        ? renderCollapsibleSection(
            "Clarification needed",
            `<p>${escapeHtml(clarificationQuestions[0] || "Please add more facts about the issue.")}</p><ul>${renderList(clarificationQuestions)}</ul>`
          )
        : ""
      }

      <article class="card result-block conditions-card">
        <span class="result-label">Conditions required</span>
        <div class="condition-grid">${renderConditions(conditionsRequired)}</div>
      </article>

      <article class="card result-block conditions-card">
        <span class="result-label">Structured legal facts</span>
        <div class="condition-grid">${renderStructuredFacts(structuredFacts)}</div>
      </article>

      ${renderCollapsibleSection(
        "Supporting bye-law text",
        `<span class="result-label">Supporting bye-law text</span><p>${escapeHtml(officialText)}</p>`
      )}

      ${renderCollapsibleSection(
        "Possible challenge arguments",
        `<span class="result-label">Possible challenge arguments</span><ul>${renderList(possibleChallenges)}</ul>`
      )}

      ${renderCollapsibleSection(
        "Related statutes",
        `<span class="result-label">Related statutes</span><ul>${renderList(relatedStatutes)}</ul>`
      )}

      <article class="card result-block disclaimer">
        <span class="result-label">Important disclaimer</span>
        <p>${escapeHtml(safePayload.disclaimer || "This information is for informational purposes only.")}</p>
      </article>
    </div>
  `;
  initializeCollapsibles(resultContainer);
};

const renderError = (message) => {
  resultContainer.className = "";
  resultContainer.innerHTML = `
    <div class="result-grid">
      <article class="card result-block error">
        <span class="result-label">Request issue</span>
        <p>${escapeHtml(message)}</p>
      </article>
    </div>
  `;
};

const renderFollowup = (payload) => {
  followupResult.classList.remove("hidden");
  followupResult.innerHTML = `
    <article class="result-block">
      <span class="result-label">Follow-up answer</span>
      <p>${escapeHtml(payload.answer)}</p>
    </article>
    <article class="result-block">
      <span class="result-label">Supporting text</span>
      <p>${escapeHtml(payload.citation)}</p>
    </article>
  `;
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  event.stopPropagation();

  const description = descriptionField.value.trim();
  if (description.length < 10) {
    renderError("Please provide a little more detail so the system can understand the situation.");
    return;
  }

  submitButton.disabled = true;
  statusText.textContent = "Analyzing...";
  resetFollowup();

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      const message = errorPayload?.detail || "The analyzer could not process the request.";
      throw new Error(message);
    }

    const payload = await response.json();
    renderResult(payload);
    statusText.textContent = payload.needs_clarification
      ? "Analysis completed with clarification."
      : "Analysis completed.";
  } catch (error) {
    renderError(error.message || "Unexpected error while contacting the API.");
    statusText.textContent = "Analysis failed.";
    followupPanel.classList.add("hidden");
    lastContext = null;
  } finally {
    submitButton.disabled = false;
  }
});

followupForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = followupField.value.trim();
  if (!lastContext) {
    followupStatus.textContent = "Analyze a situation first.";
    return;
  }

  if (question.length < 2) {
    followupStatus.textContent = "Please enter a short follow-up question.";
    return;
  }

  followupButton.disabled = true;
  followupStatus.textContent = "Getting answer...";

  try {
    const response = await fetch("/api/followup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, context: lastContext }),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      const message = errorPayload?.detail || "The follow-up request could not be processed.";
      throw new Error(message);
    }

    const payload = await response.json();
    renderFollowup(payload);
    followupStatus.textContent = "Follow-up answered.";
  } catch (error) {
    followupResult.classList.remove("hidden");
    followupResult.innerHTML = `
      <article class="result-block error">
        <span class="result-label">Follow-up issue</span>
        <p>${escapeHtml(error.message || "Unexpected follow-up error.")}</p>
      </article>
    `;
    followupStatus.textContent = "Follow-up failed.";
  } finally {
    followupButton.disabled = false;
  }
});
