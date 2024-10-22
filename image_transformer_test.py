import cv2
import numpy as np

from image_transformer import ImageTransformer

class OpenCVApp:
    PADDING = 50
    POINT_RADIUS = 5
    POINT_COLOR = (0, 0, 255)  # Red
    POLYLINE_COLOR = (0, 255, 0)  # Green
    POLYLINE_THICKNESS = 2
    SYNC_TOGGLE_KEY = ord('s')
    RESET_KEY = ord('r')
    EXIT_KEY = 27  #  ESC
    CLICK_THRESHOLD = 10
    EXTRA_SPACE = 150  # for UI
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.6
    FONT_COLOR_INSTRUCTIONS = (255, 255, 255)  # White
    FONT_COLOR_COORDS = (0, 255, 0)  # Green
    FONT_COLOR_MATRIX = (255, 255, 0)  # Blue
    TEXT_THICKNESS = 1
    TEXT_START_Y = 20
    TEXT_LINE_HEIGHT = 20

    def __init__(self, image_transformer: ImageTransformer):
        self.pts = np.array([], dtype=np.float32)
        self.initial_pts = np.array([], dtype=np.float32)
        self.dragging_point = -1
        self.sync_points = True
        self.image_transformer = image_transformer
        self.padding = self.PADDING
        self.add_padding()
        self.initialize_points()

    def add_padding(self):
        original_image = self.image_transformer.image
        if original_image is None:
            raise ValueError("No image loaded to add padding.")
        self.image_with_padding = cv2.copyMakeBorder(
            original_image, self.padding, self.padding, self.padding, self.padding,
            cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

    def mouse_callback(self, event, x, y, flags, param):
        x_adj = x - self.padding
        y_adj = y - self.padding

        if event == cv2.EVENT_LBUTTONDOWN:
            for i, pt in enumerate(self.pts):
                if abs(x_adj - pt[0]) < self.CLICK_THRESHOLD and abs(y_adj - pt[1]) < self.CLICK_THRESHOLD:
                    self.dragging_point = i
                    break

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.dragging_point != -1:
                self.pts[self.dragging_point] = [x_adj, y_adj]
                width = param.shape[1] - 2 * self.padding
                x_center = width / 2

                if self.sync_points:
                    idx_other = self.get_synchronized_index(self.dragging_point)
                    if idx_other != -1 and idx_other < len(self.pts):
                        delta_x = x_adj - x_center
                        self.pts[idx_other][0] = x_center - delta_x
                        self.pts[idx_other][1] = y_adj

        elif event == cv2.EVENT_LBUTTONUP:
            if self.dragging_point != -1:
                self.dragging_point = -1

    def get_synchronized_index(self, index):
        pair_mapping = {0: 1, 1: 0, 2: 3, 3: 2}
        return pair_mapping.get(index, -1)

    def reset_points(self):
        self.pts = self.initial_pts.copy()

    def toggle_sync(self):
        self.sync_points = not self.sync_points

    def initialize_points(self):
        original_image = self.image_transformer.image
        if original_image is None:
            raise ValueError("No image loaded to initialize points.")
        height, width = original_image.shape[:2]
        self.pts = np.array([
            [0, 0],                  # UL
            [width - 1, 0],          # UR
            [width - 1, height - 1], # BR
            [0, height - 1]          # BL
        ], dtype=np.float32)
        self.initial_pts = self.pts.copy()

    def draw_text(self, canvas, text, position, color):
        cv2.putText(
            canvas,
            text,
            position,
            self.FONT,
            self.FONT_SCALE,
            color,
            self.TEXT_THICKNESS
        )

    def draw_display(self, combined, M, width, height):
        canvas_height = combined.shape[0] + self.EXTRA_SPACE
        canvas_width = combined.shape[1]
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
        canvas[:combined.shape[0], :combined.shape[1]] = combined

        y_offset = combined.shape[0] + self.TEXT_START_Y

        instructions = [
            f"Press 'S' to toggle sync points (current: {'ON' if self.sync_points else 'OFF'})",
            "Press 'R' to reset points",
            "Press 'ESC' to exit"
        ]
        for i, text in enumerate(instructions):
            self.draw_text(
                canvas,
                text,
                (10, y_offset + i * self.TEXT_LINE_HEIGHT),
                self.FONT_COLOR_INSTRUCTIONS
            )

        for i, pt in enumerate(self.pts):
            coord_text = f"Pt{i}: ({pt[0]:.1f}, {pt[1]:.1f})"
            self.draw_text(
                canvas,
                coord_text,
                (int(canvas_width / 2), y_offset + i * self.TEXT_LINE_HEIGHT),
                self.FONT_COLOR_COORDS
            )

        self.draw_text(
            canvas,
            "Transformation Matrix:",
            (10, y_offset + 60),
            self.FONT_COLOR_MATRIX
        )
        for i in range(3):
            m_text = f"{M[i, 0]:.4f}, {M[i, 1]:.4f}, {M[i, 2]:.4f}"
            self.draw_text(
                canvas,
                m_text,
                (10, y_offset + 80 + i * self.TEXT_LINE_HEIGHT),
                self.FONT_COLOR_MATRIX
            )

        return canvas

    def run(self):
        image_with_padding = self.image_with_padding
        height, width = image_with_padding.shape[:2]
        original_image = self.image_transformer.image
        if original_image is None:
            raise ValueError("No image loaded.")

        cv2.namedWindow('Image', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback('Image', self.mouse_callback, param=image_with_padding)

        while True:
            display_image = image_with_padding.copy()
            display_pts = self.pts + np.array([self.padding, self.padding])

            cv2.polylines(
                display_image,
                [display_pts.astype(int)],
                isClosed=True,
                color=self.POLYLINE_COLOR,
                thickness=self.POLYLINE_THICKNESS
            )
            for pt in display_pts:
                cv2.circle(
                    display_image,
                    tuple(pt.astype(int)),
                    self.POINT_RADIUS,
                    self.POINT_COLOR,
                    -1
                )

            src_pts = self.initial_pts.copy()
            dst_pts = self.pts.copy()

            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            try:
                transformed_image = self.image_transformer.get_transformed_image(M)
            except cv2.error as e:
                print(f"OpenCV error during warpPerspective: {e}")
                break
            except ValueError as e:
                print(f"Value error during warpPerspective: {e}")
                break

            transformed_image_with_padding = cv2.copyMakeBorder(
                transformed_image, self.padding, self.padding, self.padding, self.padding,
                cv2.BORDER_CONSTANT, value=[0, 0, 0]
            )

            combined = np.hstack((display_image, transformed_image_with_padding))
            canvas = self.draw_display(combined, M, width, height)
            cv2.imshow('Image', canvas)

            key = cv2.waitKey(1) & 0xFF

            if key == self.EXIT_KEY:  #  ESC
                print("Exiting application.")
                break
            elif key == self.SYNC_TOGGLE_KEY:
                self.toggle_sync()
            elif key == self.RESET_KEY:
                self.reset_points()

        cv2.destroyAllWindows()

if __name__ == "__main__":
    image_transformer = ImageTransformer()
    image_transformer.load_image("input.jpg")
    app = OpenCVApp(image_transformer)
    app.run()