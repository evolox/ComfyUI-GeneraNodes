(function () {
  function setupMaskDrawer(node) {
    const container = node.querySelector(".node-content");

    if (!container) return;

    // Create Image Upload Button
    const loadImageButton = document.createElement("button");
    loadImageButton.textContent = "Load Image";
    loadImageButton.style.marginBottom = "10px";
    container.appendChild(loadImageButton);

    // Create Drawing Canvas
    const canvas = document.createElement("canvas");
    canvas.width = 256; // Default size, updated on image load
    canvas.height = 256;
    canvas.style.border = "1px solid #ccc";
    canvas.style.cursor = "crosshair";
    container.appendChild(canvas);

    const ctx = canvas.getContext("2d");
    let drawing = false;

    // Handle Image Loading
    loadImageButton.addEventListener("click", () => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.style.display = "none";

      input.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            node.sendData({ image_data: e.target.result });
          };
          img.src = e.target.result;
        };
        reader.readAsDataURL(file);
      });

      input.click();
    });

    // Drawing Logic
    canvas.addEventListener("mousedown", (e) => {
      drawing = true;
      ctx.beginPath();
      ctx.moveTo(e.offsetX, e.offsetY);
    });

    canvas.addEventListener("mousemove", (e) => {
      if (!drawing) return;
      ctx.lineTo(e.offsetX, e.offsetY);
      ctx.strokeStyle = "rgba(0, 255, 0, 1)";
      ctx.lineWidth = 5;
      ctx.stroke();
    });

    canvas.addEventListener("mouseup", () => {
      drawing = false;
      ctx.closePath();
    });

    // Send Mask Data to Backend
    node.addEventListener("save", () => {
      const maskData = canvas.toDataURL();
      node.sendData({ mask_data: maskData });
    });
  }

  // Register the node UI handler
  window.addEventListener("ComfyUIReady", () => {
    ComfyUI.registerCustomNodeUI("Genera.MaskDrawer", setupMaskDrawer);
  });
})();
