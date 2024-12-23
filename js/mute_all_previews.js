import { app } from "../../../scripts/app.js";

function muteAllPreviews(mute) {
  // Iterate through all nodes in the graph
  for (let node of app.graph._nodes) {
    // Check if the node is of type 'PreviewImage'
    if (
      node.type === "PreviewImage" ||
      node.type === "PreviewMask" ||
      node.type === "PreviewBridge" ||
      node.type === "Image Comparer (rgthree)" ||
      node.type === "MaskPreview+"
    ) {
      // Toggle the mute state using the node's internal muting method
      node.mode = mute ? 2 : 0;
    }
  }

  // Update the graph to reflect changes
  app.canvas.draw(true, true);
}

const ext = {
  name: "MutePreviews",
  async setup() {
    // Create a new button for muting/unmuting preview nodes
    let button = document.createElement("button");
    button.id = "mute-previews-button";
    button.textContent = "Mute Previews";

    // Track mute state for toggling
    let isMuted = false;

    button.addEventListener("click", () => {
      isMuted = !isMuted;
      muteAllPreviews(isMuted);
      button.textContent = isMuted ? "Unmute Previews" : "Mute Previews";
    });

    // Add the button to the ComfyUI menu
    document.querySelector("div.comfy-menu").appendChild(button);
  },
};

// Register the extension with ComfyUI
app.registerExtension(ext);
