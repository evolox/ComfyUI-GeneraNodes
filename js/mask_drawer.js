(function () {
  function setupMaskDrawer(node) {
    const container = node.querySelector(".node-content");

    if (!container) return;

    // Create Image Upload Input
    const imageInput = document.createElement("input");
    imageInput.type = "file";
    imageInput.accept = "image/*";
    imageInput.style.marginBottom = "10px";
    container.appendChild(imageInput);

    // Create Drawing Canvas
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    canvas.style.border = "1px solid #ccc";
    canvas.style.cursor = "crosshair";
    container.appendChild(canvas);

    const ctx = canvas.getContext("2d");
    let drawing = false;

    // Handle Image Upload
    imageInput.addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx.drawImage(img, 0, 0);
        };
        img.src = e.target.result;
        node.sendData({ image_data: e.target.result });
      };
      reader.readAsDataURL(file);
    });

    // Drawing Events
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
