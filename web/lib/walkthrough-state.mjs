/** @param {string|null} raw @param {string[]} stepIds */
export function readProgress(raw, stepIds) {
  try {
    const value = JSON.parse(raw || "null");
    if (
      !value ||
      value.version !== 1 ||
      !stepIds.includes(value.stepId) ||
      !Array.isArray(value.completed)
    )
      return null;
    const completed = [
      ...new Set(
        value.completed.filter(
          (id) => typeof id === "string" && stepIds.includes(id),
        ),
      ),
    ];
    return { stepId: value.stepId, completed };
  } catch {
    return null;
  }
}
/** @param {string[]} completed @param {{id:string,event?:string}} step @param {string} event */
export function completeFromEvent(completed, step, event) {
  return step.event && step.event === event && !completed.includes(step.id)
    ? [...completed, step.id]
    : completed;
}
/** @param {{id:string,event?:string}} step @param {string[]} completed */
export function canContinue(step, completed) {
  return !step.event || completed.includes(step.id);
}

/** @param {{upload:boolean,reprocess:boolean,processed:number,failed:number}} result */
export function processingEvent(result) {
  if (result.upload && result.failed > 0) return "upload-failed";
  if (result.failed > 0 || result.processed < 1) return null;
  return result.upload
    ? "upload-succeeded"
    : result.reprocess
      ? "records-refreshed"
      : "samples-processed";
}
