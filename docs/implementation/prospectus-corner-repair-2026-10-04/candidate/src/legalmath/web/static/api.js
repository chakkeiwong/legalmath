"use strict";
const element = id => document.getElementById(id);
let specification;
const operations = [];
function showOperation() {
  const operation = operations[Number(element("operation").value)];
  element("request-path").value = operation.path;
  element("idempotency").value = crypto.randomUUID();
  element("request-body").disabled = operation.method === "GET";
  const schema = operation.contract.requestBody?.content?.["application/json"]?.schema;
  const expanded = schema?.$ref ? specification.components.schemas[schema.$ref.split("/").pop()] : schema;
  element("request-contract").textContent = JSON.stringify(expanded || {description: "No request body."}, null, 2);
}
async function initialize() {
  const response = await fetch("/openapi.json");
  if (!response.ok) throw new Error("Could not load the local API contract.");
  specification = await response.json();
  element("operation").replaceChildren();
  for (const [path, methods] of Object.entries(specification.paths)) {
    for (const [method, contract] of Object.entries(methods)) {
      if (!["get", "post", "put", "patch", "delete"].includes(method)) continue;
      const option = document.createElement("option");
      option.value = operations.length;
      option.textContent = `${method.toUpperCase()} ${path}`;
      operations.push({path, method: method.toUpperCase(), contract});
      element("operation").append(option);
    }
  }
  showOperation();
}
element("operation").addEventListener("change", showOperation);
element("api-form").addEventListener("submit", async event => {
  event.preventDefault();
  const operation = operations[Number(element("operation").value)];
  const path = element("request-path").value;
  element("send-request").disabled = true;
  try {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/v1/") || /[{}]/.test(path)) {
      throw new Error("Use a local /v1/ path and replace every placeholder.");
    }
    const options = {method: operation.method, headers: {Authorization: "Bearer " + element("token").value}};
    if (operation.method !== "GET") {
      const body = element("request-body").value;
      JSON.parse(body); // Validate syntax; preserve exact numeric text for the strict server.
      options.body = body;
      options.headers["Content-Type"] = "application/json";
      options.headers["Idempotency-Key"] = element("idempotency").value;
    }
    const response = await fetch(url, options);
    element("response-status").textContent = `HTTP ${response.status}`;
    element("response-body").textContent = await response.text();
  } catch (error) {
    element("response-status").textContent = error.message;
    element("response-body").textContent = "";
  } finally { element("send-request").disabled = false; }
});
initialize().catch(error => { element("response-status").textContent = error.message; });
