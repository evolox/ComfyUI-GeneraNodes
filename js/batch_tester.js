import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

let state = [];
let running = false;

async function getNodes() {
  while (true) {
    if (!running) {
      state = [];
      for (let node of app.graph._nodes) {
        if (node.type === "Genera.BatchTester") {
          const linkedNodeId = app.graph.links.find(
            (l) => l?.target_id === node.id
          )?.origin_id;
          if (!linkedNodeId) continue;
          const linkedNode = app.graph._nodes.find(
            (n) => n.id === linkedNodeId
          );
          const processingItem = {
            node: linkedNode,
            json: node.widgets[0].value,
          };
          state.push(processingItem);
        }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
}

function parseState(state) {
  console.log(state);
  const variants = [];
  for (let item of state) {
    const node = item.node;
    const json = JSON.parse(item.json);
    console.log(node, json);

    for (const [key, value] of Object.entries(json)) {
      console.log(key, value);
      if (Array.isArray(value)) {
        //string
        const vars = value.map((v) => ({
          nodeId: node.id,
          nodeName: node.title,
          widgetName: key,
          variant: v,
        }));
        variants.push(...vars);
      } else if (typeof value === "object" && value !== null) {
        //number
        const steps = generateVariants(value);
        const vars = steps.map((s) => ({
          nodeId: node.id,
          nodeName: node.title,
          widgetName: key,
          variant: s,
        }));
        variants.push(...vars);
      }
      console.log("vars:", variants);
    }
  }
  return variants;
}

function generateVariants({ min, max, step }) {
  if (
    typeof min !== "number" ||
    typeof max !== "number" ||
    typeof step !== "number"
  ) {
    throw new Error("Invalid input: min, max, and step must be numbers.");
  }
  if (min > max) {
    throw new Error("Invalid range: min should be less than or equal to max.");
  }
  const variants = [];
  for (let i = min; i <= max; i += step) {
    variants.push(i);
  }
  return variants;
}

function generateJobs(variants) {
  const groupedByWidget = variants.reduce((acc, item) => {
    if (!acc[item.widgetName]) {
      acc[item.widgetName] = [];
    }
    acc[item.widgetName].push(item);
    return acc;
  }, {});

  const widgetNames = Object.keys(groupedByWidget);
  const variantGroups = widgetNames.map((index) => groupedByWidget[index]);

  function cartesianProduct(arrays) {
    return arrays.reduce(
      (a, b) => a.flatMap((d) => b.map((e) => [...d, e])),
      [[]]
    );
  }

  const allVariants = cartesianProduct(variantGroups);
  let i = 0;

  const result = allVariants.map((combination) => ({
    fileName: i++,
    combination,
  }));

  console.log("allVariants", result);
  return result;
}

async function runTest() {
  console.log("running");
  running = true;
  const button = document.getElementById("batch-tester-button");
  if (button) {
    button.disabled = true;
    button.style.opacity = 0.5;
  }

  const variants = parseState(state);
  const jobs = generateJobs(variants);
  const uploadNode = app.graph._nodes.find(
    (n) => n.type === "Genera.GCPStorageNode"
  );
  uploadNode.widgets[3].value = JSON.stringify(jobs);

  for (let job of jobs) {
    uploadNode.widgets[0].value = job.fileName;

    for (let combination of job.combination) {
      const node = app.graph.getNodeById(combination.nodeId);
      node.widgets.find((w) => w.name === combination.widgetName).value =
        combination.variant;
    }

    await app.queuePrompt(0, 1);
  }

  if (button) {
    button.disabled = false;
    button.style.opacity = 1;
  }
  running = false;
  console.log("stopped");
}

const ext = {
  name: "BatchTester",
  async setup() {
    let button = document.createElement("button");
    button.id = "batch-tester-button";
    button.textContent = "Batch Tester";

    button.addEventListener("click", () => {
      runTest();
    });

    document.querySelector("div.comfy-menu").appendChild(button);
    getNodes();
  },
};

app.registerExtension(ext);
