(function () {
  function setupMaskDrawer(node) {
    const container = node.querySelector(".node-content");
    if (!container) return;

    // Create Drawing Canvas
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    canvas.style.border = "1px solid #ccc";
    canvas.style.cursor = "crosshair";
    canvas.style.touchAction = "none"; // Prevent default touch behavior
    container.appendChild(canvas);

    const ctx = canvas.getContext("2d");
    let drawing = false;

    // Watch for Image Selection
    node.addEventListener("input", (event) => {
      if (event.detail && event.detail.input_name === "image") {
        const imagePath = event.detail.value;
        const img = new Image();
        img.onload = () => {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx.drawImage(img, 0, 0);
        };
        img.src = `/input/${imagePath}`;
      }
    });

    // 🖱️ **Intercept Mouse Events**
    canvas.addEventListener("mousedown", (e) => {
      drawing = true;
      ctx.beginPath();
      ctx.moveTo(e.offsetX, e.offsetY);
    });

    canvas.addEventListener("mousemove", (e) => {
      if (!drawing) return;
      ctx.lineTo(e.offsetX, e.offsetY);
      ctx.strokeStyle = "rgba(0, 255, 0, 1)"; // Green mask stroke
      ctx.lineWidth = 5;
      ctx.stroke();
    });

    canvas.addEventListener("mouseup", () => {
      drawing = false;
      ctx.closePath();
    });

    canvas.addEventListener("mouseleave", () => {
      drawing = false; // Stop drawing if the mouse leaves the canvas
    });

    // 🖥️ **Ensure Canvas Captures All Events**
    canvas.addEventListener("pointerdown", (e) => e.stopPropagation());
    canvas.addEventListener("pointermove", (e) => e.stopPropagation());
    canvas.addEventListener("pointerup", (e) => e.stopPropagation());

    // 🎯 **Save Mask Data to Backend**
    node.addEventListener("save", () => {
      const maskData = canvas.toDataURL("image/png"); // Encode to Base64
      node.sendData({ mask_data: maskData });
    });
  }

  // Register the node UI handler
  window.addEventListener("ComfyUIReady", () => {
    ComfyUI.registerCustomNodeUI("Genera.MaskDrawer", setupMaskDrawer);
  });
})();
